from __future__ import annotations

from flask import Blueprint, redirect, request, url_for

from . import api_routes
from .api_routes import run_admet, run_deeppk
from .io_utils import apply_cors_headers


legacy_bp = Blueprint("legacy", __name__)


@legacy_bp.after_request
def add_cors_headers(response):
    return apply_cors_headers(request, response)


@legacy_bp.get("/copy/COPYindex")
def legacy_builder():
    return redirect(url_for("ui.builder", **request.args), code=302)


@legacy_bp.get("/copy/COPYindex/build")
def legacy_builder_with_session():
    return redirect(url_for("ui.builder", **request.args), code=302)


@legacy_bp.get("/copy/COPYbuilder")
def legacy_api_builder():
    return redirect(url_for("ui.api_builder"), code=302)


@legacy_bp.get("/copy/about")
def legacy_about():
    return redirect(url_for("ui.about"), code=302)


@legacy_bp.get("/copy/api")
def legacy_api_docs():
    return redirect(url_for("ui.api_docs"), code=302)


@legacy_bp.get("/copy/ligand_editor")
def legacy_ligand_editor():
    return redirect(url_for("ui.ligand_editor", **request.args), code=302)


@legacy_bp.get("/copy/ligase_ligandalyzer")
def legacy_ligase_ligandalyzer():
    return redirect(url_for("ui.ligase_ligandalyzer"), code=302)


@legacy_bp.get("/copy/view_ligase")
def legacy_view_ligase():
    return redirect(url_for("ui.view_ligase", **request.args), code=302)


@legacy_bp.post("/copy/modify_ligand")
def legacy_modify_ligand():
    return api_routes.modify_ligand()


@legacy_bp.post("/copy/generate_protac")
def legacy_generate_protac():
    return api_routes.generate_protac()


@legacy_bp.post("/copy/download_smiles")
def legacy_download_smiles():
    return api_routes.download_smiles()


@legacy_bp.post("/copy/convert_smiles_to_mol")
def legacy_smiles_to_mol():
    return api_routes.smiles_to_mol()


@legacy_bp.post("/copy/convert_mol_to_smiles")
def legacy_mol_to_smiles():
    return api_routes.mol_to_smiles()


@legacy_bp.post("/copy/render_smiles")
def legacy_render_smiles():
    return api_routes.render_smiles()


@legacy_bp.get("/copy/get_ligand_smiles")
def legacy_ligand_smiles():
    return api_routes.ligand_smiles()


@legacy_bp.get("/copy/get_ligand_data")
def legacy_ligand_data():
    return api_routes.ligand_data()


@legacy_bp.route("/copy/store_ligand", methods=["POST", "OPTIONS"])
def legacy_store_ligand():
    return api_routes.store_ligand()


@legacy_bp.get("/copy/get_curated_linkers")
def legacy_curated_linkers():
    return api_routes.curated_linkers()


@legacy_bp.get("/copy/render_ligase")
def legacy_render_ligase():
    return api_routes.render_ligase()


@legacy_bp.get("/copy/load_recruiter/<name>")
def legacy_load_recruiter(name: str):
    return api_routes.recruiter(name)


@legacy_bp.get("/copy/load_converted/<session_id>")
def legacy_load_converted(session_id: str):
    return api_routes.recruiter_converted(session_id)


@legacy_bp.get("/copy/list_ligases")
def legacy_list_ligases():
    return api_routes.ligases()


@legacy_bp.get("/copy/load_ligase_raw/<name>")
def legacy_load_ligase_raw(name: str):
    return api_routes.ligase_raw(name)


@legacy_bp.post("/copy/log_protac_frontend")
def legacy_log_protac_frontend():
    return api_routes.protac_log()


@legacy_bp.post("/copy/api/protac/batch_linkers")
def legacy_batch_linkers():
    return api_routes.batch_linkers()


@legacy_bp.post("/copy/api/protac/structure/convert")
def legacy_structure_convert():
    return api_routes.structure_convert()


@legacy_bp.post("/copy/api/protac/structure/mapped_smiles")
def legacy_mapped_smiles():
    return api_routes.mapped_smiles()


@legacy_bp.post("/copy/api/protac/linkers/inspect")
def legacy_inspect_linkers():
    return api_routes.inspect_linkers()


@legacy_bp.post("/copy/api/protac/builder/batch")
def legacy_builder_batch():
    return api_routes.builder_batch()


@legacy_bp.post("/copy/api/protac/builder/cli")
def legacy_builder_cli():
    return api_routes.builder_cli()


@legacy_bp.get("/copy/api/protac/builder/usage")
def legacy_builder_usage():
    return api_routes.protac_builder_usage()


@legacy_bp.get("/copy/api/protac/builder/template/linkers")
def legacy_template_linkers():
    return api_routes.template_linkers()


@legacy_bp.get("/copy/api/protac/builder/template/download-count")
def legacy_template_download_count():
    return api_routes.template_download_count()


@legacy_bp.get("/copy/api/warheadhunter/job/<job_id>")
def legacy_warheadhunter_job(job_id: str):
    return api_routes.warhead_hunter_job(job_id)


@legacy_bp.post("/run-drug-analysis")
def legacy_run_drug_analysis():
    return run_deeppk()
