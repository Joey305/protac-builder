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

import pandas as pd
import requests
from flask import Blueprint, Response, current_app, jsonify, render_template, request, send_file
from rdkit import Chem
from rdkit.Chem import Draw, rdDepictor, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D

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
)
from .warhead_handoff import (
    WarheadJobIdError,
    fetch_remote_job,
    missing_job_payload,
    normalize_job_id,
    resolve_job_dir,
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
                metadata={
                    "status": "ok",
                    "built": 1,
                    "failed": 0,
                    "extra": "frontend_generate",
                },
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
            results.append(
                {
                    "name": f"{linker_name}_PROTAC",
                    "smiles": product,
                    "warhead_smiles": warhead_smiles,
                    "linker_smiles": linker_smiles,
                    "ligase_smiles": ligase_smiles,
                }
            )

        log_builder_usage(source=source, endpoint="builder_batch", status="ok", built=len(results), failed=len(failures))
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
                results.append((name, build_protac_smiles(target, linker_smiles, ligase)))
            except Exception as exc:
                failures.append((row_number, name, str(exc), linker_smiles))
                log_lines.append(f"[FAIL row={row_number} name={name}] {type(exc).__name__}: {exc}")

        log_lines.append(f"built: {len(results)}")
        log_lines.append(f"failed: {len(failures)}")

        log_builder_usage(source=source, endpoint="builder_cli", status="ok", built=len(results), failed=len(failures), extra=run_id)

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
                    option["svg_plain"] = filename
                elif lower.endswith("_exposed.svg"):
                    option["svg_exposed"] = filename
                elif lower.endswith(".sdf"):
                    option["sdf"] = filename
                elif lower.endswith(".pdb"):
                    option["pdb_file"] = filename
                continue

            no_resid_match = no_resid_pattern.match(filename)
            if no_resid_match:
                pdb_no_resid[
                    (
                        no_resid_match.group("pdb").lower(),
                        no_resid_match.group("chain"),
                        no_resid_match.group("ligand"),
                    )
                ] = filename

    for option in options.values():
        if not option["pdb_file"]:
            lookup = (str(option["pdb"]), str(option["chain"]), str(option["ligand"]))
            if lookup in pdb_no_resid:
                option["pdb_file"] = pdb_no_resid[lookup]

    return [item for item in options.values() if item["svg_plain"] or item["svg_exposed"] or item["sdf"] or item["pdb_file"]]


@bp.route("/api/warheadhunter/job/<job_id>", methods=["GET"])
def warheadhunter_job_index(job_id: str):
    try:
        job_id = normalize_job_id(job_id)

        resolved = resolve_job_dir(job_id)
        if not resolved:
            try:
                remote_payload = fetch_remote_job(job_id)
                if remote_payload:
                    remote_payload.setdefault("ok", True)
                    remote_payload.setdefault("job_id", job_id)
                    remote_payload.setdefault("source", "WARHEAD_HUNTER_JOB_API_BASE")
                    return jsonify(remote_payload)
            except Exception as exc:
                payload = missing_job_payload(job_id, debug=bool(current_app.debug))
                payload["remote_error"] = str(exc)
                return jsonify(payload), 502

            payload = missing_job_payload(job_id, debug=False)
            payload["hint"] = ", ".join(payload.get("available", []))
            return jsonify(payload), 404

        base_dir = Path(resolved["job_dir"])
        options = _scan_hunter_job_dir(base_dir)
        if not options:
            return jsonify({"ok": False, "job_id": job_id, "error": "No valid warhead options found", "source": resolved["source"]}), 404

        return jsonify(
            {
                "ok": True,
                "job_id": job_id,
                "public_base": f"/api/warheadhunter/job/{job_id}/file",
                "source": resolved["source"],
                "options": options,
            }
        )
    except WarheadJobIdError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/api/warheadhunter/job/<job_id>/file/<filename>", methods=["GET"])
def warheadhunter_job_file(job_id: str, filename: str):
    try:
        job_id = normalize_job_id(job_id)
        if Path(filename).name != filename or not filename.lower().endswith((".pdb", ".sdf", ".svg", ".json")):
            return jsonify({"ok": False, "error": "Invalid filename"}), 400
        resolved = resolve_job_dir(job_id, cache_external=False)
        if not resolved:
            return jsonify(missing_job_payload(job_id)), 404
        candidate = (Path(resolved["job_dir"]) / filename).resolve()
        root = Path(resolved["job_dir"]).resolve()
        if root not in candidate.parents or not candidate.exists():
            return jsonify({"ok": False, "error": "File not found"}), 404
        return send_file(candidate)
    except WarheadJobIdError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
