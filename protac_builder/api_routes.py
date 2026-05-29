from __future__ import annotations

from flask import Blueprint, jsonify, make_response, request, send_file

from . import route_impl as impl
from .admet import create_admet_report, get_admet_file
from .deeppk import DeepPkPipelineError, get_deeppk_file, run_deeppk_pipeline
from .io_utils import apply_cors_headers
from .usage import get_template_download_count, get_usage_summary, log_builder_usage


api_bp = Blueprint("api", __name__)


def _usage_source(default: str = "web") -> str:
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        value = payload.get("source")
        if value:
            return str(value).strip().lower() or default
    value = request.form.get("source", "")
    if value:
        return value.strip().lower() or default
    return default


def _log_success(endpoint: str, *, source: str | None = None, built: int = 1, extra: str = "") -> None:
    log_builder_usage(
        source=source or _usage_source(),
        endpoint=endpoint,
        metadata={"status": "ok", "built": built, "extra": extra},
    )


@api_bp.after_request
def add_cors_headers(response):
    return apply_cors_headers(request, response)


@api_bp.get("/api/linkers/curated")
def curated_linkers():
    return impl.get_curated_linkers()


@api_bp.get("/api/ligases")
def ligases():
    return impl.list_ligases()


@api_bp.get("/api/ligase/render")
def render_ligase():
    return impl.render_ligase()


@api_bp.get("/api/ligase/raw/<name>")
def ligase_raw(name: str):
    return impl.load_ligase_raw(name)


@api_bp.get("/api/recruiter/<name>")
def recruiter(name: str):
    return impl.load_recruiter(name)


@api_bp.get("/api/recruiter/converted/<session_id>")
def recruiter_converted(session_id: str):
    clean_session = str(session_id or "").strip()
    if not clean_session or clean_session.lower() in {"none", "null", "undefined"}:
        return jsonify({"success": False, "error": "Missing converted recruiter session ID"}), 400
    return impl.load_converted(clean_session)


@api_bp.get("/api/ligand/smiles")
def ligand_smiles():
    return impl.get_ligand_smiles()


@api_bp.get("/api/ligand/data")
def ligand_data():
    return impl.get_ligand_data()


@api_bp.post("/api/ligand/modify")
def modify_ligand():
    return impl.modify_ligand()


@api_bp.route("/api/ligand/store", methods=["POST", "OPTIONS"])
def store_ligand():
    return impl.store_ligand()


@api_bp.post("/api/molecule/smiles-to-mol")
def smiles_to_mol():
    return impl.convert_smiles_to_mol()


@api_bp.post("/api/molecule/mol-to-smiles")
def mol_to_smiles():
    return impl.convert_mol_to_smiles_route()


@api_bp.post("/api/molecule/render-smiles")
def render_smiles():
    return impl.render_smiles()


@api_bp.post("/api/protac/generate")
def generate_protac():
    response = make_response(impl.generate_protac())
    if response.status_code < 400:
        _log_success("generate", source=_usage_source("web"), built=1)
    return response


@api_bp.post("/api/protac/download-smiles")
def download_smiles():
    return impl.download_smiles()


@api_bp.post("/api/protac/log")
def protac_log():
    return impl.log_protac_frontend()


@api_bp.post("/api/protac/batch-linkers")
def batch_linkers():
    return impl.batch_protac_from_csv()


@api_bp.post("/api/protac/structure/convert")
def structure_convert():
    return impl.protac_structure_convert()


@api_bp.post("/api/protac/structure/mapped-smiles")
def mapped_smiles():
    response = make_response(impl.protac_structure_mapped_smiles())
    if response.status_code < 400:
        _log_success("mapped_smiles", source=_usage_source("api"), built=1)
    return response


@api_bp.post("/api/protac/linkers/inspect")
def inspect_linkers():
    return impl.inspect_linker_csv_route()


@api_bp.post("/api/protac/builder/batch")
def builder_batch():
    return impl.protac_builder_batch()


@api_bp.post("/api/protac/builder/cli")
def builder_cli():
    return impl.protac_builder_cli()


@api_bp.get("/api/protac/builder/usage")
def protac_builder_usage():
    response = jsonify(get_usage_summary())
    response.headers["Cache-Control"] = "no-store"
    return response


@api_bp.get("/api/protac/builder/template/linkers")
def template_linkers():
    return make_response(impl.download_api_linkers_template())


@api_bp.get("/api/protac/builder/template/download-count")
def template_download_count():
    return jsonify({"downloads": get_template_download_count()})


@api_bp.get("/api/warheadhunter/job/<job_id>")
@api_bp.get("/api/warheadhunter/job/<path:job_id>")
def warhead_hunter_job(job_id: str):
    return impl.warheadhunter_job_index(job_id)


@api_bp.get("/api/warheadhunter/job/<job_id>/file/<filename>")
def warhead_hunter_job_file(job_id: str, filename: str):
    return impl.warheadhunter_job_file(job_id, filename)


@api_bp.post("/api/deeppk/run")
def run_deeppk():
    payload = request.get_json(silent=True) or {}
    smiles = str(payload.get("smiles", "")).strip()
    mol_block = str(payload.get("mol_block", "") or payload.get("molBlock", "")).strip()
    try:
        result = run_deeppk_pipeline(smiles=smiles, mol_block=mol_block)
        return jsonify(result)
    except DeepPkPipelineError as exc:
        return jsonify(exc.payload), exc.status_code
    except Exception as exc:
        fallback = {
            "success": False,
            "error": "DeepPK report generation failed.",
            "details": str(exc) or "Unexpected DeepPK backend error.",
            "stage": "response",
            "job_id": None,
            "rdkit_descriptors": {},
            "retryable": True,
        }
        return jsonify(fallback), 500


@api_bp.get("/api/deeppk/download/<job_id>/<filename>")
def download_deeppk_file(job_id: str, filename: str):
    try:
        path = get_deeppk_file(job_id, filename)
    except FileNotFoundError:
        return jsonify({"success": False, "error": "DeepPK report file not found"}), 404
    return send_file(path, as_attachment=True, download_name=path.name)


@api_bp.post("/api/admet/run")
def run_admet():
    payload = request.get_json(silent=True) or {}
    smiles = str(payload.get("smiles", "")).strip()
    mol_block = str(payload.get("mol_block", "") or payload.get("molBlock", "")).strip()
    if not smiles and not mol_block:
        return jsonify({"success": False, "error": "No SMILES or MOL block provided"}), 400
    try:
        result = create_admet_report(smiles=smiles, mol_block=mol_block)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@api_bp.get("/api/admet/download/<filename>")
def download_admet_file(filename: str):
    try:
        path = get_admet_file(filename)
    except FileNotFoundError:
        return jsonify({"success": False, "error": "Report file not found"}), 404
    return send_file(path, as_attachment=True, download_name=path.name)
