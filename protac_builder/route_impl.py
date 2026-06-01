from __future__ import annotations

import base64
import io
import json
import os
import re
import secrets
import traceback
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
from flask import Blueprint, Response, current_app, jsonify, render_template, request, send_file
from rdkit import Chem
from rdkit.Chem import Draw, rdDepictor, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D

from .backup_client import backup_events_async
from .builder_api import (
    detect_linker_smiles_column,
    detect_name_column,
    get_smiles_input,
    inspect_linker_csv,
    parse_structure_input,
    read_csv_smart,
    read_name_smiles_csv,
    safe_str,
    to_csv_string,
)
from .chemistry import (
    build_protac_smiles,
    convert_smiles_to_molblock,
    find_pdb_info,
    generate_protac_molblock,
    ligase_card_metadata,
    load_pdb_as_preview,
    load_raw_sdf_molblock,
    load_sdf_as_preview,
    molblock_to_mapped_smiles,
    molblock_to_smiles,
    normalize_attachment_smiles,
    render_smiles_data_url,
    smiles_to_svg,
)
from .io_utils import (
    api_linkers_exists,
    apply_cors_headers,
    get_builder_usage_counts,
    find_ligand_smiles,
    get_client_ip,
    get_linkers_df,
    get_template_download_count,
    get_warheads_df,
    log_builder_usage,
    log_legacy_protac_components,
    log_generated_protac,
    log_linker_library_usage,
    log_template_download,
    write_frontend_log,
)
from .paths import (
    API_LINKERS_CSV,
    GENERATED_SMILES_PATH,
    LIGASE_DIR,
    LIGASE_IMAGE_DIR,
    LINKER_IMAGE_DIR,
    PDB_STRUCTURES_DIR,
    RECRUITER_LIGASES_DIR,
    RECRUITER_TMP_DIR,
    WARHEAD_HUNTER_IMPORTS_DIR,
)
from .warhead_handoff import (
    WarheadJobIdError,
    extract_safe_warhead_file_ref,
    fetch_remote_job_diagnostics,
    fetch_remote_job_file,
    missing_job_payload,
    normalize_job_id,
    normalize_safe_warhead_file_ref,
)


DEBUG_PROTAC = True
bp = Blueprint("copy_app", __name__)


def _missing_path_error(path: Path, status: int = 500):
    return jsonify({"error": "Missing required data file", "path": str(path)}), status


def _missing_folder_error(path: Path, message: str = "Missing required folder", status: int = 500):
    return jsonify({"error": message, "path": str(path)}), status


def _get_root_ligase_names() -> list[str]:
    if not LIGASE_DIR.exists():
        raise FileNotFoundError(str(LIGASE_DIR))
    return sorted(path.stem for path in LIGASE_DIR.glob("*.sdf"))


def _get_index_context(**extra):
    linkers_df = get_linkers_df()
    warheads_df = get_warheads_df()
    return {
        "linkers": [{"id": row["Compound ID"]} for _, row in linkers_df.iterrows()],
        "warheads": warheads_df.to_dict(orient="records"),
        "ligases": _get_root_ligase_names(),
        **extra,
    }


def _alias_ligase_name(name: str) -> str:
    alias_map = {
        "VHL_VH032": "VHL_3JF",
        "CRBN_Thalidomide": "CRBN_EF2",
        "CRBN_Pomalidomide": "CRBN_Y70",
        "CRBN_Lenalidomide": "CRBN_LVY",
    }
    return alias_map.get(name, name)


def _ligase_image_url(name: str) -> str:
    return f"/static/Ligase_Images/{name}.png"


def _ensure_ligase_png(sdf_path: Path, image_path: Path) -> None:
    if image_path.exists():
        return
    supplier = Chem.SDMolSupplier(str(sdf_path))
    mol = next((item for item in supplier if item is not None), None)
    if mol is None:
        return
    rdDepictor.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DCairo(300, 300)
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    image_path.write_bytes(drawer.GetDrawingText())


def _mol_input_to_attachment_smiles(value: str, expected_label: str | None = None) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("Missing structure input")

    if "\n" not in value and "M  END" not in value:
        return normalize_attachment_smiles(value)

    smiles, _warnings = molblock_to_mapped_smiles(value)
    if expected_label == "R1" and "[*:1]" not in smiles:
        raise ValueError("Warhead MOL block missing attachment point [*:1]")
    if expected_label == "R2" and "[*:2]" not in smiles:
        raise ValueError("Ligase MOL block missing attachment point [*:2]")
    return normalize_attachment_smiles(smiles)


@bp.after_request
def add_cors_headers(response: Response) -> Response:
    return apply_cors_headers(request, response)


@bp.route("/COPYindex")
def index():
    try:
        return render_template("COPYindex.html", **_get_index_context())
    except FileNotFoundError as exc:
        return _missing_path_error(Path(str(exc)))


@bp.route("/COPYindex/build")
def copyindex_build():
    try:
        return render_template(
            "COPYindex.html",
            **_get_index_context(converted_session=request.args.get("session")),
        )
    except FileNotFoundError as exc:
        return _missing_path_error(Path(str(exc)))


@bp.route("/COPYbuilder")
def protac_builder_api():
    return render_template("COPYbuilder.html")


@bp.route("/about")
def protac_about():
    return render_template("copy_about.html")


@bp.route("/api")
def api_reference():
    return render_template("COPYapi.html")


@bp.route("/modify_ligand", methods=["POST"])
def modify_ligand():
    data = request.get_json(silent=True) or {}
    smiles = safe_str(data.get("smiles"))
    mol_block = convert_smiles_to_molblock(smiles)
    if not mol_block:
        return jsonify({"error": "Invalid SMILES"}), 400
    return jsonify({"mol_block": mol_block, "smiles": normalize_attachment_smiles(smiles)})


@bp.route("/generate_protac", methods=["POST"])
def generate_protac():
    data = request.get_json(silent=True) or {}
    warhead_mol = data.get("warhead_mol", "")
    linker_mol = data.get("linker_mol", "")
    ligase_mol = data.get("ligase_mol", "")
    if not warhead_mol or not linker_mol or not ligase_mol:
        return jsonify({"error": "One or more MOL blocks are missing!"}), 400

    try:
        protac_mol_block = generate_protac_molblock(warhead_mol, linker_mol, ligase_mol)
        protac_smiles = molblock_to_smiles(protac_mol_block) or ""
        client_ip = get_client_ip(request)
        log_generated_protac(
            client_ip=client_ip,
            warhead_mol=warhead_mol,
            linker_mol=linker_mol,
            ligase_mol=ligase_mol,
            protac_mol=protac_mol_block,
            protac_smiles=protac_smiles,
        )
        return jsonify(
            {
                "success": True,
                "protac_mol_block": protac_mol_block,
                "protac_smiles": protac_smiles,
            }
        )
    except Exception as exc:
        return jsonify({"error": f"Internal Server Error: {exc}"}), 500


@bp.route("/download_smiles", methods=["POST"])
def download_smiles():
    data = request.get_json(silent=True) or {}
    protac_smiles = safe_str(data.get("protac_smiles"))
    if not protac_smiles:
        return jsonify({"error": "No SMILES data provided!"}), 400

    GENERATED_SMILES_PATH.write_text(protac_smiles, encoding="utf-8")
    payload = io.BytesIO(protac_smiles.encode("utf-8"))
    return send_file(payload, as_attachment=True, download_name="generated_protac.smi", mimetype="text/plain")


@bp.route("/convert_smiles_to_mol", methods=["POST"])
def convert_smiles_to_mol():
    data = request.get_json(silent=True) or {}
    mol_block = convert_smiles_to_molblock(safe_str(data.get("smiles")))
    if not mol_block:
        return jsonify({"error": "Invalid SMILES"}), 400
    return jsonify({"success": True, "mol": mol_block, "mol_block": mol_block})


@bp.route("/convert_mol_to_smiles", methods=["POST"])
def convert_mol_to_smiles_route():
    data = request.get_json(silent=True) or {}
    mol_block = data.get("molBlock", "") or data.get("mol", "")
    if not mol_block:
        return jsonify({"error": "No MOL block provided"}), 400
    smiles = molblock_to_smiles(mol_block)
    if not smiles:
        return jsonify({"error": "Invalid MOL block"}), 400
    return jsonify({"success": True, "smiles": smiles})


@bp.route("/render_smiles", methods=["POST"])
def render_smiles():
    data = request.get_json(silent=True) or {}
    image = render_smiles_data_url(safe_str(data.get("smiles")))
    if not image:
        return jsonify({"error": "Invalid SMILES"}), 400
    return jsonify({"success": True, "image": image})


@bp.route("/get_ligand_smiles")
def get_ligand_smiles():
    ligand_id = request.args.get("ligand", "").strip().upper()
    if not ligand_id:
        return jsonify({"error": "No ligand ID provided"}), 400
    try:
        ligand_data = find_ligand_smiles(ligand_id)
    except FileNotFoundError as exc:
        return _missing_path_error(Path(str(exc)))
    if not ligand_data:
        return jsonify({"error": f"Ligand '{ligand_id}' not found!"}), 404
    return jsonify({"ligand": ligand_data["ligand"], "smiles": ligand_data["smiles"], "source": ligand_data["source"]})


@bp.route("/get_ligand_data", methods=["GET"])
def get_ligand_data():
    ligand_id = request.args.get("ligand", "").strip().upper()
    if not ligand_id:
        return jsonify({"error": "No ligand specified"}), 400
    try:
        ligand_data = find_ligand_smiles(ligand_id)
    except FileNotFoundError as exc:
        return _missing_path_error(Path(str(exc)))
    if not ligand_data:
        return jsonify({"error": "Ligand not found"}), 404
    smiles = ligand_data["smiles"]
    mol_block = convert_smiles_to_molblock(smiles)
    if not mol_block:
        return jsonify({"error": "MOL block conversion failed"}), 500
    return jsonify(
        {
            "ligand": ligand_data["ligand"],
            "smiles": smiles,
            "mol_block": mol_block,
            "name": ligand_data.get("name", ""),
            "source": ligand_data["source"],
        }
    )


@bp.route("/ligand_editor")
def ligand_editor():
    ligand_id = request.args.get("ligand", "").strip().upper()
    if not ligand_id:
        return jsonify({"error": "No ligand ID provided!"}), 400
    try:
        ligand_data = find_ligand_smiles(ligand_id)
    except FileNotFoundError as exc:
        return _missing_path_error(Path(str(exc)))
    if not ligand_data:
        return jsonify({"error": f"Ligand '{ligand_id}' not found!"}), 404
    smiles = ligand_data["smiles"]
    mol_block = convert_smiles_to_molblock(smiles)
    if not mol_block:
        return jsonify({"error": "Invalid SMILES format!"}), 400
    return render_template(
        "ligand_editor.html",
        ligand_data={"ligand": ligand_id, "smiles": smiles, "mol_block": mol_block},
    )


@bp.route("/store_ligand", methods=["POST", "OPTIONS"])
def store_ligand():
    if request.method == "OPTIONS":
        return jsonify({"message": "CORS preflight success"})
    data = request.get_json(silent=True) or {}
    if "ligand" not in data:
        return jsonify({"error": "Missing required field: ligand"}), 400
    return jsonify({"message": f"Ligand {data['ligand']} stored successfully!"}), 200


@bp.route("/get_curated_linkers", methods=["GET"])
def get_curated_linkers():
    try:
        linkers_df = get_linkers_df()
    except FileNotFoundError as exc:
        return _missing_path_error(Path(str(exc)))

    page = int(request.args.get("page", 1))
    per_page = 100
    sort_options = {
        "Molecular Weight": "Molecular Weight",
        "Rotatable Bond Count": "Rotatable Bond Count",
        "Topological Polar Surface Area": "Topological Polar Surface Area",
        "XLogP3": "XLogP3",
        "Ring Count": "Ring Count",
    }

    sort_by = request.args.get("sort_by", "Molecular Weight")
    if sort_by not in sort_options:
        return jsonify({"error": "Invalid sort option"}), 400

    filtered_df = linkers_df.sort_values(
        by=sort_options[sort_by],
        ascending=request.args.get("sort_order", "asc") == "asc",
    )

    for key, column in sort_options.items():
        min_val = request.args.get(f"min_{key}")
        max_val = request.args.get(f"max_{key}")
        if min_val not in {None, ""}:
            filtered_df = filtered_df[filtered_df[column] >= float(min_val)]
        if max_val not in {None, ""}:
            filtered_df = filtered_df[filtered_df[column] <= float(max_val)]

    start_index = max((page - 1) * per_page, 0)
    rows = filtered_df.iloc[start_index : start_index + per_page]
    response = [
        {
            "id": row["Compound ID"],
            "svg": smiles_to_svg(row["Smiles"]),
            "smiles": row["Smiles"],
            "molecular_weight": row["Molecular Weight"],
        }
        for _, row in rows.iterrows()
    ]
    return jsonify(response)


@bp.route("/list_ligases")
def list_ligases():
    if not LIGASE_DIR.exists():
        return _missing_folder_error(LIGASE_DIR, "Missing ligase folder")
    return jsonify(_get_root_ligase_names())


@bp.route("/load_ligase_raw/<name>")
def load_ligase_raw(name: str):
    path = LIGASE_DIR / f"{name}.sdf"
    if not path.exists():
        return jsonify({"error": f"Ligase not found: {name}"}), 404
    try:
        return jsonify({"mol_block": load_raw_sdf_molblock(path)})
    except Exception:
        return jsonify({"error": f"Failed to load ligase: {name}"}), 500


@bp.route("/ligase_ligandalyzer")
def ligase_ligandalyzer():
    if not LIGASE_DIR.exists():
        return _missing_folder_error(LIGASE_DIR, "Missing ligase folder")

    ligase_cards = []
    for sdf_path in sorted(LIGASE_DIR.glob("*.sdf")):
        image_path = LIGASE_IMAGE_DIR / f"{sdf_path.stem}.png"
        try:
            _ensure_ligase_png(sdf_path, image_path)
            ligase_cards.append(ligase_card_metadata(sdf_path, _ligase_image_url(sdf_path.stem)))
        except Exception:
            continue

    return render_template(
        "ligase_ligandalyzer.html",
        ligases=ligase_cards,
        LIGANDALYZER_URL="https://e3ligandalyzer.com/",
    )


@bp.route("/view_ligase")
def view_ligase():
    ligase_name = request.args.get("name", "").strip()
    if not ligase_name:
        return "Ligase name is required!", 400

    ligase_name = _alias_ligase_name(ligase_name)
    pdb_id, _pdb_path, chain, residue, ligand_code = find_pdb_info(ligase_name)
    if not pdb_id:
        return f"PDB file for {ligase_name} not found!", 404

    return render_template(
        "view_ligase.html",
        ligase={
            "name": ligase_name,
            "ligand_code": ligand_code,
            "pdb_id": pdb_id,
            "chain": chain if chain else "Not Found",
            "residue": residue if residue else "Not Found",
            "image": _ligase_image_url(ligase_name),
        },
    )


@bp.route("/render_ligase", methods=["GET"])
def render_ligase():
    ligase_name = request.args.get("ligase", "").strip()
    if not ligase_name:
        return jsonify({"error": "Missing ligase parameter"}), 400

    tmp_path = RECRUITER_TMP_DIR / f"{ligase_name}.sdf"
    if tmp_path.exists():
        try:
            return jsonify(load_sdf_as_preview(tmp_path))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    recruiter_name = ligase_name.split("_")[0]
    recruiter_path = RECRUITER_LIGASES_DIR / recruiter_name / "SDF" / f"{ligase_name}.sdf"
    if recruiter_path.exists():
        try:
            return jsonify(load_sdf_as_preview(recruiter_path))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    _pdb_id, pdb_path, _chain, _residue, _ligand_code = find_pdb_info(_alias_ligase_name(ligase_name))
    if pdb_path and pdb_path.exists():
        try:
            return jsonify(load_pdb_as_preview(pdb_path))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    return jsonify({"error": f"Ligase not found: {ligase_name}"}), 404


@bp.route("/load_recruiter/<name>")
def load_recruiter(name: str):
    parts = name.split("_")
    if len(parts) < 2:
        return jsonify({"error": "Format must be LIGASE_LIG"}), 400

    sdf_path = RECRUITER_LIGASES_DIR / parts[0] / "SDF" / f"{name}.sdf"
    if not sdf_path.exists():
        return jsonify(
            {
                "error": "SDF not found",
                "path": str(sdf_path),
                "hint": "Optional recruiter-module dataset was not copied in full. Add the needed SDF under Ligases/MODULE/e3-recruiter-mod/Ligases/<LIGASE>/SDF/.",
            }
        ), 404

    try:
        preview = load_sdf_as_preview(sdf_path)
        mol = Chem.MolFromMolBlock(preview["mol_block"], sanitize=False)
        smiles = Chem.MolToSmiles(mol) if mol else ""
        return jsonify({"name": name, "smiles": smiles, "mol_block": preview["mol_block"]})
    except Exception:
        return jsonify({"error": "Invalid SDF file"}), 500


@bp.route("/load_converted/<session_id>", methods=["GET"])
def load_converted(session_id: str):
    clean_session = str(session_id or "").strip()
    if not clean_session or clean_session.lower() in {"none", "null", "undefined"}:
        return jsonify({"error": "Missing converted recruiter session ID"}), 400

    base_url = os.environ.get("PROTAC_CONVERTED_SESSION_BASE", "https://stan.rove-vernier.ts.net").rstrip("/")
    response = requests.get(f"{base_url}/api/serve_session/{clean_session}", timeout=10)
    if response.status_code != 200:
        return jsonify({"error": "Session SDF not found"}), 404

    mol = Chem.MolFromMolBlock(response.text, sanitize=False)
    if mol is None:
        return jsonify({"error": "Invalid SDF"}), 500
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        pass
    rdDepictor.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DSVG(300, 300)
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    image = base64.b64encode(drawer.GetDrawingText().encode("utf-8")).decode("utf-8")
    return jsonify(
        {
            "session_id": clean_session,
            "mol_block": Chem.MolToMolBlock(mol),
            "image": f"data:image/svg+xml;base64,{image}",
        }
    )


@bp.route("/log_protac_frontend", methods=["POST"])
def log_protac_frontend():
    try:
        data = request.get_json(silent=True) or {}
        client_ip = get_client_ip(request)
        warhead_mol = data.get("warhead_mol", "")
        linker_mol = data.get("linker_mol", "")
        ligase_mol = data.get("ligase_mol", "")
        protac_mol = data.get("protac_mol", "")
        protac_smiles = data.get("protac_smiles", "")
        warhead_smiles = ""
        linker_smiles = ""
        ligase_smiles = ""

        try:
            warhead_smiles = molblock_to_smiles(warhead_mol) or normalize_attachment_smiles(molblock_to_mapped_smiles(warhead_mol))
        except Exception:
            warhead_smiles = ""
        try:
            linker_smiles = molblock_to_smiles(linker_mol) or normalize_attachment_smiles(molblock_to_mapped_smiles(linker_mol))
        except Exception:
            linker_smiles = ""
        try:
            ligase_smiles = molblock_to_smiles(ligase_mol) or normalize_attachment_smiles(molblock_to_mapped_smiles(ligase_mol))
        except Exception:
            ligase_smiles = ""

        log_generated_protac(
            client_ip=client_ip,
            warhead_mol=warhead_mol,
            linker_mol=linker_mol,
            ligase_mol=ligase_mol,
            protac_mol=protac_mol,
            protac_smiles=protac_smiles,
        )
        log_legacy_protac_components(
            client_ip=client_ip,
            protac_smiles=protac_smiles,
            warhead_smiles=warhead_smiles,
            linker_smiles=linker_smiles,
            ligase_smiles=ligase_smiles,
        )
        write_frontend_log(
            client_ip=client_ip,
            warhead_mol=warhead_mol,
            linker_mol=linker_mol,
            ligase_mol=ligase_mol,
            protac_mol=protac_mol,
            protac_smiles=protac_smiles,
        )

        if data.get("count_usage") and protac_smiles:
            log_builder_usage(
                source=str(data.get("source") or "web").strip().lower() or "web",
                endpoint="generate",
                status="ok",
                built=1,
                failed=0,
                extra="frontend_generate",
            )
        return jsonify({"success": True})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@bp.route("/api/protac/batch_linkers", methods=["POST"])
def batch_protac_from_csv():
    warhead_input = request.form.get("warhead_mol", "")
    ligase_input = request.form.get("ligase_mol", "")
    csv_file = request.files.get("linker_csv")
    if not all([warhead_input, ligase_input, csv_file]):
        return jsonify({"error": "Missing inputs"}), 400

    try:
        warhead_smiles = _mol_input_to_attachment_smiles(warhead_input, "R1")
        ligase_smiles = _mol_input_to_attachment_smiles(ligase_input, "R2")
        df = pd.read_csv(csv_file)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    smiles_col = detect_linker_smiles_column(df)
    name_col = detect_name_column(df, smiles_col)
    if smiles_col is None:
        return jsonify({"error": "No linker SMILES column with [*:1]/[*:2] found"}), 400

    results = []
    for index, row in df.iterrows():
        linker_smiles = normalize_attachment_smiles(safe_str(row.get(smiles_col)))
        linker_name = safe_str(row.get(name_col)) if name_col else f"LINKER_{index + 1}"
        try:
            product = build_protac_smiles(warhead_smiles, linker_smiles, ligase_smiles)
        except Exception:
            continue
        results.append({"name": f"{linker_name}_PROTAC", "smiles": product})

    return jsonify({"count": len(results), "results": results})


@bp.route("/api/protac/structure/convert", methods=["POST"])
def protac_structure_convert():
    try:
        mol_block, smiles = parse_structure_input(request.form.get("smiles", ""), request.files.get("structure_file"))
        return jsonify({"mol_block": mol_block, "smiles": smiles})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/api/protac/structure/mapped_smiles", methods=["POST"])
def protac_structure_mapped_smiles():
    data = request.get_json(silent=True) or {}
    mol_block = data.get("molBlock", "")
    if not mol_block:
        return jsonify({"error": "Missing molBlock"}), 400
    try:
        smiles, warnings = molblock_to_mapped_smiles(mol_block)
        return jsonify({"smiles": smiles, "warnings": warnings})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/api/protac/linkers/inspect", methods=["POST"])
def inspect_linker_csv_route():
    csv_file = request.files.get("linker_csv") or request.files.get("file")
    if not csv_file:
        return jsonify({"error": "Missing linker_csv"}), 400
    try:
        return jsonify(inspect_linker_csv(csv_file))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Could not read CSV: {exc}"}), 400


@bp.route("/api/protac/builder/batch", methods=["POST"])
def protac_builder_batch():
    source = safe_str(request.form.get("source") or "web").lower() or "web"
    client_ip = get_client_ip(request)
    batch_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + secrets.token_hex(4)

    def fail(payload, status_code=400, extra=""):
        try:
            log_builder_usage(source=source, endpoint="builder_batch", status="error", extra=extra)
        except Exception:
            pass
        return jsonify(payload), status_code

    try:
        warhead_smiles = normalize_attachment_smiles(safe_str(request.form.get("warhead_smiles")))
        ligase_smiles = normalize_attachment_smiles(safe_str(request.form.get("ligase_smiles")))
        csv_file = request.files.get("linker_csv")
        smiles_col = safe_str(request.form.get("smiles_col"))
        name_col = safe_str(request.form.get("name_col"))

        if not warhead_smiles or not ligase_smiles or not csv_file:
            return fail({"error": "Missing inputs (warhead_smiles, ligase_smiles, linker_csv)"}, 400, "missing_inputs")

        try:
            df = read_csv_smart(csv_file)
        except Exception as exc:
            return fail({"error": f"Could not read CSV: {exc}"}, 400, "csv_read_failed")

        if df.empty:
            return fail({"error": "CSV is empty"}, 400, "csv_empty")

        if smiles_col not in df.columns:
            return fail({"error": f"Chosen SMILES column not found: {smiles_col}", "columns": list(df.columns)}, 400, "smiles_col_missing")

        warnings = []
        if name_col and name_col not in df.columns:
            warnings.append(f"Chosen name_col not found ({name_col}). Falling back to LINKER_#.")
            name_col = ""

        results = []
        failures = []
        component_records = []

        for index, row in df.iterrows():
            raw_linker = safe_str(row.get(smiles_col))
            linker_smiles = normalize_attachment_smiles(raw_linker)
            linker_name = safe_str(row.get(name_col)) if name_col else f"LINKER_{index + 1}"

            if "[*:1]" not in linker_smiles or "[*:2]" not in linker_smiles:
                failures.append({"row": int(index), "name": linker_name, "linker_smiles": raw_linker, "reason": "Linker missing [*:1] and/or [*:2]."})
                continue

            try:
                product = build_protac_smiles(warhead_smiles, linker_smiles, ligase_smiles)
            except Exception as exc:
                failures.append({"row": int(index), "name": linker_name, "linker_smiles": linker_smiles, "reason": str(exc)})
                continue

            log_legacy_protac_components(
                client_ip=client_ip,
                protac_smiles=product,
                warhead_smiles=warhead_smiles,
                linker_smiles=linker_smiles,
                ligase_smiles=ligase_smiles,
            )
            protac_name = f"{linker_name}_PROTAC"
            results.append(
                {
                    "name": protac_name,
                    "smiles": product,
                    "warhead_smiles": warhead_smiles,
                    "linker_smiles": linker_smiles,
                    "ligase_smiles": ligase_smiles,
                }
            )
            component_records.append(
                {
                    "event_type": "protac_component_record",
                    "source": source,
                    "endpoint": "builder_batch",
                    "status": "ok",
                    "run_id": batch_id,
                    "job_id": batch_id,
                    "row_number": int(index) + 1,
                    "protac_name": protac_name,
                    "warhead_smiles": warhead_smiles,
                    "linker_smiles": linker_smiles,
                    "ligase_smiles": ligase_smiles,
                    "protac_smiles": product,
                }
            )

        if component_records:
            backup_events_async(component_records)

        log_builder_usage(source=source, endpoint="builder_batch", status="ok", built=len(results), failed=len(failures), extra=batch_id)
        log_linker_library_usage(
            source=source,
            endpoint="builder_batch",
            status="ok",
            run_id=batch_id,
            client_ip=client_ip,
            filename=getattr(csv_file, "filename", "") or "uploaded_linker_csv",
            rows_total=len(df),
            built=len(results),
            failed=len(failures),
            name_col=name_col,
            smiles_col=smiles_col,
            extra="api_builder_web_batch",
        )
        return jsonify(
            {
                "count": len(results),
                "failed": len(failures),
                "warnings": warnings,
                "message": f"Built {len(results)} PROTAC(s). Skipped {len(failures)} row(s).",
                "results": results,
                "failures": failures,
            }
        )
    except Exception as exc:
        log_builder_usage(source=source, endpoint="builder_batch", status="error", extra="exception")
        return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500


@bp.route("/api/protac/builder/cli", methods=["POST"])
def protac_builder_cli():
    source = safe_str(request.form.get("source") or "cli").lower() or "cli"
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + secrets.token_hex(4)

    def fail(payload, status_code=400, extra=""):
        try:
            log_builder_usage(source=source, endpoint="builder_cli", status="error", extra=extra or run_id)
        except Exception:
            pass
        return jsonify(payload), status_code

    try:
        target = normalize_attachment_smiles(get_smiles_input(request, "target"))
        ligase = normalize_attachment_smiles(get_smiles_input(request, "ligase"))
        library = request.files.get("library")
        if not target or not ligase or library is None:
            return fail({"error": "Missing required inputs. Expect form-data: target, ligase, library (CSV)."}, 400, "missing_inputs")

        rows = read_name_smiles_csv(library)
        results = []
        failures = []
        component_records = []
        log_lines = [
            f"run_id: {run_id}",
            f"started: {datetime.utcnow().isoformat()}Z",
            f"client_ip: {get_client_ip(request)}",
            f"rows_in_csv: {len(rows)}",
        ]

        for row_number, name, linker_smiles in rows:
            try:
                if not name:
                    raise ValueError("Missing NAME")
                if not linker_smiles:
                    raise ValueError("Missing SMILES")
                product = build_protac_smiles(target, linker_smiles, ligase)
                results.append((name, product))
                component_records.append(
                    {
                        "event_type": "protac_component_record",
                        "source": source,
                        "endpoint": "builder_cli",
                        "status": "ok",
                        "run_id": run_id,
                        "job_id": run_id,
                        "row_number": int(row_number),
                        "protac_name": name,
                        "warhead_smiles": target,
                        "linker_smiles": linker_smiles,
                        "ligase_smiles": ligase,
                        "protac_smiles": product,
                    }
                )
            except Exception as exc:
                failures.append((row_number, name, str(exc), linker_smiles))
                log_lines.append(f"[FAIL row={row_number} name={name}] {type(exc).__name__}: {exc}")

        log_lines.append(f"built: {len(results)}")
        log_lines.append(f"failed: {len(failures)}")

        if component_records:
            backup_events_async(component_records)

        log_builder_usage(source=source, endpoint="builder_cli", status="ok", built=len(results), failed=len(failures), extra=run_id)
        log_linker_library_usage(
            source=source,
            endpoint="builder_cli",
            status="ok",
            run_id=run_id,
            client_ip=get_client_ip(request),
            filename=getattr(library, "filename", "") or "API_Linkers.csv",
            rows_total=len(rows),
            built=len(results),
            failed=len(failures),
            name_col="NAME",
            smiles_col="SMILES",
            extra="cli_zip_build",
        )

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("PBuilder-Smiles.csv", to_csv_string(["PROTAC_Name", "PROTAC_SMILES"], results))
            bundle.writestr("PBuilder-Failed-Linkers.csv", to_csv_string(["row", "name", "reason", "linker_smiles"], failures))
            bundle.writestr("PBuilder-Run.log", "\n".join(log_lines) + "\n")
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"protac_batch_{run_id}.zip", mimetype="application/zip")
    except Exception as exc:
        log_builder_usage(source=source, endpoint="builder_cli", status="error", extra=run_id)
        return jsonify({"error": str(exc), "run_id": run_id, "traceback": traceback.format_exc()}), 500


@bp.route("/api/protac/builder/usage", methods=["GET"])
def protac_builder_usage():
    response = jsonify(get_builder_usage_counts())
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.route("/api/protac/builder/template/linkers", methods=["GET"])
def download_api_linkers_template():
    if not api_linkers_exists():
        return _missing_path_error(API_LINKERS_CSV)
    log_template_download(request=request, filename="API_Linkers.csv")
    return send_file(API_LINKERS_CSV, as_attachment=True, download_name="API_Linkers.csv")


@bp.route("/api/protac/builder/template/download-count", methods=["GET"])
def protac_template_download_count():
    return jsonify({"downloads": get_template_download_count()})


def _scan_hunter_job_dir(base_dir: Path) -> list[dict[str, str | None]]:
    pattern = re.compile(
        r"^(?P<pdb>[0-9a-zA-Z]{4})_(?P<chain>[A-Za-z0-9])_(?P<ligand>[A-Za-z0-9]{3})_(?P<resid>[0-9]+)"
    )
    no_resid_pattern = re.compile(r"^(?P<pdb>[0-9a-zA-Z]{4})_(?P<chain>[A-Za-z0-9])_(?P<ligand>[A-Za-z0-9]{3})\.pdb$")
    options: dict[str, dict[str, str | None]] = {}
    pdb_no_resid: dict[tuple[str, str, str], str] = {}

    manifest_path = base_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = manifest.get("files") or {}
            pdb_file = files.get("pdb") or manifest.get("pdb_file")
            sdf_file = files.get("sdf") or manifest.get("sdf")
            pdb = str(manifest.get("pdb") or "")[:4].lower()
            ligand = str(manifest.get("warhead") or manifest.get("ligand") or "").upper()
            chain = str(manifest.get("chain") or "")
            resid = manifest.get("resid")
            if pdb_file or sdf_file:
                key = "_".join(part for part in [pdb, chain, ligand, str(resid or "")] if part)
                options[key or "manifest"] = {
                    "key": key or "manifest",
                    "pdb": pdb,
                    "chain": chain,
                    "ligand": ligand,
                    "resid": str(resid) if resid else None,
                    "svg_plain": files.get("svg_plain") or files.get("plain_svg"),
                    "svg_exposed": files.get("svg_exposed") or files.get("exposed_svg"),
                    "sdf": sdf_file,
                    "pdb_file": pdb_file,
                }
        except Exception:
            pass

    for root, _dirs, files in os.walk(base_dir):
        for filename in files:
            rel_ref = (Path(root) / filename).relative_to(base_dir).as_posix()
            match = pattern.match(filename)
            if match:
                key = f"{match.group('pdb')}_{match.group('chain')}_{match.group('ligand')}_{match.group('resid')}"
                option = options.setdefault(
                    key,
                    {
                        "key": key,
                        "pdb": match.group("pdb").lower(),
                        "chain": match.group("chain"),
                        "ligand": match.group("ligand"),
                        "resid": match.group("resid"),
                        "svg_plain": None,
                        "svg_exposed": None,
                        "sdf": None,
                        "pdb_file": None,
                    },
                )
                lower = filename.lower()
                if lower.endswith("_plain.svg"):
                    option["svg_plain"] = rel_ref
                elif lower.endswith("_exposed.svg"):
                    option["svg_exposed"] = rel_ref
                elif lower.endswith(".sdf"):
                    option["sdf"] = rel_ref
                elif lower.endswith(".pdb"):
                    option["pdb_file"] = rel_ref
                continue

            no_resid_match = no_resid_pattern.match(filename)
            if no_resid_match:
                pdb_no_resid[
                    (
                        no_resid_match.group("pdb").lower(),
                        no_resid_match.group("chain"),
                        no_resid_match.group("ligand"),
                    )
                ] = rel_ref

    for option in options.values():
        if not option["pdb_file"]:
            lookup = (str(option["pdb"]), str(option["chain"]), str(option["ligand"]))
            if lookup in pdb_no_resid:
                option["pdb_file"] = pdb_no_resid[lookup]

    return [item for item in options.values() if item["svg_plain"] or item["svg_exposed"] or item["sdf"] or item["pdb_file"]]


def _scan_hunter_file_refs(file_refs: list[str]) -> list[dict[str, str | None]]:
    pattern = re.compile(
        r"^(?P<pdb>[0-9a-zA-Z]{4})_(?P<chain>[A-Za-z0-9])_(?P<ligand>[A-Za-z0-9]{3})_(?P<resid>[0-9]+)"
    )
    no_resid_pattern = re.compile(r"^(?P<pdb>[0-9a-zA-Z]{4})_(?P<chain>[A-Za-z0-9])_(?P<ligand>[A-Za-z0-9]{3})\.pdb$")
    options: dict[str, dict[str, str | None]] = {}
    pdb_no_resid: dict[tuple[str, str, str], str] = {}

    for ref in file_refs:
        filename = Path(ref).name
        match = pattern.match(filename)
        if match:
            key = f"{match.group('pdb')}_{match.group('chain')}_{match.group('ligand')}_{match.group('resid')}"
            option = options.setdefault(
                key,
                {
                    "key": key,
                    "pdb": match.group("pdb").lower(),
                    "chain": match.group("chain"),
                    "ligand": match.group("ligand"),
                    "resid": match.group("resid"),
                    "svg_plain": None,
                    "svg_exposed": None,
                    "sdf": None,
                    "pdb_file": None,
                },
            )
            lower = filename.lower()
            if lower.endswith("_plain.svg"):
                option["svg_plain"] = ref
            elif lower.endswith("_exposed.svg"):
                option["svg_exposed"] = ref
            elif lower.endswith(".sdf"):
                option["sdf"] = ref
            elif lower.endswith(".pdb"):
                option["pdb_file"] = ref
            continue

        no_resid_match = no_resid_pattern.match(filename)
        if no_resid_match:
            pdb_no_resid[
                (
                    no_resid_match.group("pdb").lower(),
                    no_resid_match.group("chain"),
                    no_resid_match.group("ligand"),
                )
            ] = ref

    for option in options.values():
        if not option["pdb_file"]:
            lookup = (str(option["pdb"]), str(option["chain"]), str(option["ligand"]))
            if lookup in pdb_no_resid:
                option["pdb_file"] = pdb_no_resid[lookup]

    return [item for item in options.values() if item["svg_plain"] or item["svg_exposed"] or item["sdf"] or item["pdb_file"]]


def _warheadhunter_public_base(job_id: str) -> str:
    return f"/api/warheadhunter/job/{job_id}/file"


def _warheadhunter_public_file_url(job_id: str, file_ref: str | None) -> str | None:
    safe_ref = extract_safe_warhead_file_ref(file_ref)
    if not safe_ref:
        return None
    return f"{_warheadhunter_public_base(job_id)}/{quote(safe_ref, safe='/')}"


def _normalize_hunter_option(option: dict[str, object]) -> dict[str, object]:
    normalized = dict(option)
    pdb_ref = extract_safe_warhead_file_ref(
        option.get("pdb_file") or option.get("pdb_path") or option.get("target_pdb")
    )
    sdf_ref = extract_safe_warhead_file_ref(
        option.get("sdf") or option.get("sdf_path") or option.get("warhead_sdf")
    )
    svg_plain_ref = extract_safe_warhead_file_ref(option.get("svg_plain") or option.get("svg_plain_path"))
    svg_exposed_ref = extract_safe_warhead_file_ref(option.get("svg_exposed") or option.get("svg_exposed_path"))

    normalized["pdb_file"] = pdb_ref
    normalized["sdf"] = sdf_ref
    normalized["svg_plain"] = svg_plain_ref
    normalized["svg_exposed"] = svg_exposed_ref
    return normalized


def _extract_remote_options(raw: dict[str, object]) -> list[dict[str, object]]:
    files = raw.get("files")
    if isinstance(files, list):
        curated_refs = []
        for item in files:
            if not isinstance(item, dict):
                continue
            ref = item.get("relative_path") or item.get("path_in_root") or item.get("name")
            root = str(item.get("root") or "")
            if root != "job" or not isinstance(ref, str) or "/" in ref:
                continue
            safe_ref = extract_safe_warhead_file_ref(ref)
            if safe_ref:
                curated_refs.append(safe_ref)
        curated_options = _scan_hunter_file_refs(sorted(set(curated_refs)))
        if curated_options:
            return [dict(option) for option in curated_options]

    raw_options = raw.get("options")
    if isinstance(raw_options, dict):
        return [raw_options]
    if isinstance(raw_options, list):
        return [item for item in raw_options if isinstance(item, dict)]
    if isinstance(files, dict):
        return [files]

    fallback_option = {
        key: raw.get(key)
        for key in (
            "pdb",
            "pdb_id",
            "chain",
            "ligand",
            "resid",
            "residue",
            "label",
            "pdb_file",
            "pdb_path",
            "pdb_url",
            "target_pdb",
            "sdf",
            "sdf_path",
            "sdf_url",
            "warhead_sdf",
            "svg_plain",
            "svg_plain_path",
            "svg_plain_url",
            "svg_exposed",
            "svg_exposed_path",
            "svg_exposed_url",
            "smiles",
            "mol",
            "mol_block",
        )
        if raw.get(key) not in (None, "")
    }
    return [fallback_option] if fallback_option else []


def _hunter_option_id(job_id: str, option: dict[str, object], index: int) -> str:
    parts = [
        str(option.get("pdb") or option.get("pdb_id") or "").lower(),
        str(option.get("chain") or "").upper(),
        str(option.get("ligand") or "").upper(),
        str(option.get("resid") or ""),
    ]
    compact = "-".join(part for part in parts if part)
    return compact or f"{job_id}-option-{index + 1}"


def _hunter_option_label(option: dict[str, object], index: int) -> str:
    custom = str(option.get("label") or "").strip()
    if custom:
        return custom
    pdb = str(option.get("pdb") or option.get("pdb_id") or "").upper()
    chain = str(option.get("chain") or "").upper()
    ligand = str(option.get("ligand") or "").upper()
    resid = str(option.get("resid") or option.get("residue") or "")
    parts = []
    if pdb:
        parts.append(pdb)
    if chain:
        parts.append(f"chain {chain}")
    if ligand:
        parts.append(f"ligand {ligand}")
    if resid:
        parts.append(f"resid {resid}")
    return " ".join(parts) if parts else f"Warhead option {index + 1}"


def normalize_hunter_payload_for_frontend(
    job_id: str,
    payload: dict[str, object] | None,
    *,
    source: str | None = None,
) -> dict[str, object]:
    raw = dict(payload or {})
    public_base = _warheadhunter_public_base(job_id)

    options_source = _extract_remote_options(raw)

    options: list[dict[str, object]] = []
    for index, option in enumerate(options_source):
        normalized_option = _normalize_hunter_option(option)
        normalized_option["option_id"] = _hunter_option_id(job_id, normalized_option, index)
        normalized_option["label"] = _hunter_option_label(normalized_option, index)
        normalized_option["preview_url"] = (
            _warheadhunter_public_file_url(job_id, str(normalized_option.get("svg_plain")))
            or _warheadhunter_public_file_url(job_id, str(normalized_option.get("svg_exposed")))
        )
        normalized_option["svg_plain_url"] = _warheadhunter_public_file_url(job_id, str(normalized_option.get("svg_plain")))
        normalized_option["svg_exposed_url"] = _warheadhunter_public_file_url(job_id, str(normalized_option.get("svg_exposed")))
        normalized_option["target_pdb_url"] = _warheadhunter_public_file_url(job_id, str(normalized_option.get("pdb_file")))
        normalized_option["warhead_sdf_url"] = _warheadhunter_public_file_url(job_id, str(normalized_option.get("sdf")))
        invalid_parts: list[str] = []
        if not normalized_option.get("target_pdb_url"):
            invalid_parts.append("missing target PDB")
        if not normalized_option.get("warhead_sdf_url"):
            invalid_parts.append("missing warhead SDF")
        normalized_option["invalid_reason"] = ", ".join(invalid_parts) if invalid_parts else None
        normalized_option["is_valid"] = not invalid_parts
        options.append(normalized_option)

    normalized: dict[str, object] = dict(raw)
    normalized["ok"] = bool(raw.get("ok", True))
    normalized["job_id"] = job_id
    normalized["source"] = source or str(raw.get("source") or "unknown")
    normalized["public_base"] = public_base
    normalized["options"] = options
    normalized["option_count"] = len(options)
    normalized["first_option"] = options[0] if options else {}
    valid_options = [option for option in options if option.get("is_valid")]
    normalized["valid_option_count"] = len(valid_options)
    normalized["requires_selection"] = len(valid_options) > 1
    normalized["source_policy"] = "remote_only"
    normalized["local_lookup"] = "disabled"

    detected_source = raw.get("detected") if isinstance(raw.get("detected"), dict) else {}
    first_complete = next((option for option in valid_options if option.get("target_pdb_url") and option.get("warhead_sdf_url")), None)

    detected_pdb = None
    detected_sdf = None
    if first_complete:
        detected_pdb = str(first_complete.get("target_pdb_url"))
        detected_sdf = str(first_complete.get("warhead_sdf_url"))
    else:
        detected_pdb = _warheadhunter_public_file_url(
            job_id,
            detected_source.get("target_pdb") or raw.get("target_pdb"),
        )
        detected_sdf = _warheadhunter_public_file_url(
            job_id,
            detected_source.get("warhead_sdf") or raw.get("warhead_sdf"),
        )

    if detected_pdb and detected_sdf:
        normalized["detected"] = {
            "target_pdb": detected_pdb,
            "warhead_sdf": detected_sdf,
        }
    else:
        normalized.pop("detected", None)

    warhead_source = first_complete or (options[0] if options else {})
    warhead = {
        "pdb_id": str(warhead_source.get("pdb") or warhead_source.get("pdb_id") or "").upper(),
        "ligand": str(warhead_source.get("ligand") or "").upper(),
    }
    if warhead_source.get("chain"):
        warhead["chain"] = str(warhead_source.get("chain"))
    if warhead_source.get("resid"):
        warhead["resid"] = str(warhead_source.get("resid"))
    if any(warhead.values()):
        normalized["warhead"] = warhead

    normalized["selected_option_id"] = str(first_complete.get("option_id")) if len(valid_options) == 1 and first_complete else None

    normalized["has_detected_target_pdb"] = bool(normalized.get("detected", {}).get("target_pdb")) if isinstance(normalized.get("detected"), dict) else False
    normalized["has_detected_warhead_sdf"] = bool(normalized.get("detected", {}).get("warhead_sdf")) if isinstance(normalized.get("detected"), dict) else False
    return normalized


def _contains_smiles_only_payload(payload: dict[str, object]) -> bool:
    options = _extract_remote_options(payload)
    if not options:
        return False
    saw_smiles_like = False
    for option in options:
        if not isinstance(option, dict):
            continue
        if option.get("smiles") or option.get("mol") or option.get("mol_block"):
            saw_smiles_like = True
        if extract_safe_warhead_file_ref(option.get("pdb_file") or option.get("pdb_path") or option.get("target_pdb")):
            return False
        if extract_safe_warhead_file_ref(option.get("sdf") or option.get("sdf_path") or option.get("warhead_sdf")):
            return False
    return saw_smiles_like


def _remote_debug_payload(job_id: str, remote_result: dict[str, object]) -> dict[str, object]:
    payload = remote_result.get("payload")
    normalized = normalize_hunter_payload_for_frontend(job_id, payload or {}, source="WARHEAD_HUNTER_JOB_API_BASE") if payload else {}
    raw_keys = sorted(payload.keys()) if isinstance(payload, dict) else []
    contains_smiles_only = _contains_smiles_only_payload(payload) if isinstance(payload, dict) else False
    return {
        "ok": bool(normalized.get("valid_option_count")) if payload else False,
        "job_id": job_id,
        "source_policy": "remote_only",
        "local_lookup": "disabled",
        "remote": {
            "configured": bool(remote_result.get("configured")),
            "attempted": bool(remote_result.get("attempted")),
            "status_code": remote_result.get("status_code"),
            "payload_keys": raw_keys,
            "option_count": normalized.get("option_count", 0) if payload else 0,
            "valid_option_count": normalized.get("valid_option_count", 0) if payload else 0,
            "contains_smiles_only": contains_smiles_only,
            "error": remote_result.get("error"),
            "debug_hint": remote_result.get("debug_hint"),
        },
        "final_decision": (
            "remote_ok"
            if payload and normalized.get("valid_option_count")
            else "remote_payload_missing_structure_files"
            if contains_smiles_only
            else remote_result.get("error") or "remote_no_valid_options"
        ),
    }


@bp.route("/api/warheadhunter/job/<job_id>", methods=["GET"])
def warheadhunter_job_index(job_id: str):
    try:
        job_id = normalize_job_id(job_id)
        debug_mode = request.args.get("debug", "").strip() in {"1", "true", "yes"}
        remote_result = fetch_remote_job_diagnostics(job_id)
        if debug_mode:
            return jsonify(_remote_debug_payload(job_id, remote_result))

        remote_payload = remote_result.get("payload")
        if remote_payload:
            normalized = normalize_hunter_payload_for_frontend(
                job_id,
                remote_payload,
                source="WARHEAD_HUNTER_JOB_API_BASE",
            )
            normalized["remote_configured"] = bool(remote_result.get("configured"))
            normalized["remote_attempted"] = bool(remote_result.get("attempted"))
            normalized["remote_status_code"] = remote_result.get("status_code")
            if normalized.get("valid_option_count"):
                return jsonify(normalized), 200

            contains_smiles_only = _contains_smiles_only_payload(remote_payload if isinstance(remote_payload, dict) else {})
            normalized["ok"] = False
            normalized["remote_configured"] = bool(remote_result.get("configured"))
            normalized["remote_attempted"] = bool(remote_result.get("attempted"))
            normalized["remote_status_code"] = remote_result.get("status_code")
            normalized["remote_error"] = remote_result.get("error")
            if contains_smiles_only:
                normalized["status"] = "remote_payload_missing_structure_files"
                normalized["error"] = "RANDY returned a job payload, but it did not include importable PDB/SDF files."
                normalized["debug_hint"] = "This import path requires a target PDB and warhead SDF. A SMILES-only payload is not enough for Target Builder import."
            else:
                normalized["status"] = "no_valid_options"
                normalized["error"] = "RANDY returned the job, but it did not include importable PDB/SDF files."
                normalized["debug_hint"] = "Remote API returned a payload, but none of the options contained both a target PDB and warhead SDF."
            return jsonify(normalized), 502

        payload = missing_job_payload(job_id, debug=False)
        payload["remote_configured"] = bool(remote_result.get("configured"))
        payload["remote_attempted"] = bool(remote_result.get("attempted"))
        payload["remote_status_code"] = remote_result.get("status_code")
        payload["remote_error"] = remote_result.get("error")
        payload["option_count"] = 0
        payload["valid_option_count"] = 0
        payload["first_option"] = {}
        payload["has_detected_target_pdb"] = False
        payload["has_detected_warhead_sdf"] = False
        payload["source_policy"] = "remote_only"
        payload["local_lookup"] = "disabled"
        if not remote_result.get("configured"):
            payload["error"] = "Remote Warhead Hunter handoff is not configured on this server."
            payload["status"] = "remote_not_configured"
            payload["debug_hint"] = "WARHEAD_HUNTER_JOB_API_BASE is not configured."
            return jsonify(payload), 503
        if remote_result.get("status_code") == 404 or remote_result.get("error") == "remote_not_found":
            payload["error"] = "RANDY did not find this job ID."
            payload["status"] = "remote_not_found"
            payload["debug_hint"] = "Remote API returned 404 for this job ID."
            return jsonify(payload), 404
        payload["error"] = "RANDY lookup failed."
        payload["status"] = "remote_lookup_failed"
        payload["debug_hint"] = str(remote_result.get("debug_hint") or "Remote lookup failed.")
        return jsonify(payload), 502

    except WarheadJobIdError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/api/warheadhunter/job/<job_id>/file/<path:filename>", methods=["GET"])
def warheadhunter_job_file(job_id: str, filename: str):
    try:
        job_id = normalize_job_id(job_id)
        safe_ref = normalize_safe_warhead_file_ref(filename)
        cache_dir = (WARHEAD_HUNTER_IMPORTS_DIR / job_id).resolve()
        if cache_dir.exists():
            direct_path = (cache_dir / safe_ref).resolve()
            try:
                direct_path.relative_to(cache_dir)
            except ValueError:
                return jsonify({"ok": False, "error": "Invalid resolved file path"}), 400
            if direct_path.is_file():
                return send_file(direct_path, as_attachment=False)

        # Local cache miss: proxy from RANDY using server-side token.
        content, content_type = fetch_remote_job_file(job_id, safe_ref)
        cached_file = (cache_dir / safe_ref).resolve()
        try:
            cached_file.relative_to(cache_dir)
        except ValueError:
            cached_file = None
        if cached_file is not None:
            cached_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                cached_file.write_bytes(content)
            except Exception:
                pass

        return Response(
            content,
            mimetype=content_type or "application/octet-stream",
            headers={
                "Cache-Control": "no-store",
                "X-Warhead-Handoff-Source": "WARHEAD_HUNTER_JOB_API_BASE",
            },
        )

    except WarheadJobIdError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except FileNotFoundError as exc:
        return jsonify({"ok": False, "error": str(exc), "source_policy": "remote_only", "local_lookup": "disabled"}), 503
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        return jsonify({"ok": False, "error": f"Remote file fetch failed: HTTP {status}"}), status
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
