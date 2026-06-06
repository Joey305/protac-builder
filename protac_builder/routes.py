from __future__ import annotations
from pathlib import Path

from flask import Blueprint, Response, current_app, jsonify, redirect, render_template, request, url_for

from . import route_impl as impl
from .io_utils import apply_cors_headers
from .site_content import OPENAPI_SPEC, SITEMAP_PATHS, get_page_meta, llms_text, yaml_dump


ui_bp = Blueprint("ui", __name__)


def _missing_path_error(path: Path, status: int = 500):
    return jsonify({"error": "Missing required data file", "path": str(path)}), status


@ui_bp.after_request
def add_cors_headers(response):
    return apply_cors_headers(request, response)


def _render_page(page_key: str):
    page = get_page_meta(page_key)
    return render_template(page["template"], page=page)


@ui_bp.get("/")
def home():
    return _render_page("home")


@ui_bp.get("/builder")
def builder():
    try:
        return render_template(
            "builder.html",
            **impl._get_index_context(converted_session=request.args.get("session")),
            tutorial_url="https://youtu.be/CYYsG1MpsE4",
            show_builder_popup=True,
        )
    except FileNotFoundError as exc:
        return _missing_path_error(Path(str(exc)))


@ui_bp.get("/build")
def legacy_build_alias():
    return redirect(url_for("ui.builder", **request.args), code=302)


@ui_bp.get("/api-builder")
def api_builder():
    return render_template("api_builder.html")


@ui_bp.get("/api-docs")
def api_docs():
    return render_template("api_docs.html")


@ui_bp.get("/about")
def about():
    return render_template("about.html")


@ui_bp.get("/what-is-a-protac")
def what_is_a_protac():
    return _render_page("what_is_a_protac")


@ui_bp.get("/how-to-build-a-protac")
def how_to_build_a_protac():
    return _render_page("how_to_build_a_protac")


@ui_bp.get("/examples")
def examples():
    return _render_page("examples")


@ui_bp.get("/component-hubs")
def component_hubs():
    return _render_page("component_hubs")


@ui_bp.get("/warheads")
def warheads():
    return _render_page("warheads")


@ui_bp.get("/protac-warhead-library")
def protac_warhead_library():
    return redirect(url_for("ui.warheads"), code=301)


@ui_bp.get("/linkers")
def linkers():
    return _render_page("linkers")


@ui_bp.get("/protac-linker-library")
def protac_linker_library():
    return redirect(url_for("ui.linkers"), code=301)


@ui_bp.get("/e3-ligase-recruiters")
def e3_ligase_recruiters():
    return _render_page("e3_ligase_recruiters")


@ui_bp.get("/e3-recruiter-library")
def e3_recruiter_library():
    return redirect(url_for("ui.e3_ligase_recruiters"), code=301)


@ui_bp.get("/constraint-driven-protac-design")
def constraint_driven_protac_design():
    return _render_page("constraint_driven_protac_design")


@ui_bp.get("/in-silico-protac-modeling")
def in_silico_protac_modeling():
    return _render_page("in_silico_protac_modeling")


@ui_bp.get("/benchmarking")
def benchmarking():
    return _render_page("benchmarking")


@ui_bp.get("/downstream-modeling-tools")
def downstream_modeling_tools():
    return _render_page("downstream_modeling_tools")


@ui_bp.get("/ecosystem")
def ecosystem():
    return _render_page("ecosystem")


@ui_bp.get("/faq")
def faq():
    return _render_page("faq")


@ui_bp.get("/methods")
def methods():
    return _render_page("methods")


@ui_bp.get("/database-schema")
def database_schema():
    return _render_page("database_schema")


@ui_bp.get("/release-notes")
def release_notes():
    return _render_page("release_notes")


@ui_bp.get("/download-manifest")
def download_manifest():
    return _render_page("download_manifest")


@ui_bp.get("/case-studies")
def case_studies():
    return _render_page("case_studies")


@ui_bp.get("/submit-data")
def submit_data():
    return _render_page("submit_data")


@ui_bp.get("/api-examples")
def api_examples():
    return _render_page("api_examples")


@ui_bp.get("/batch-workflows")
def batch_workflows():
    return _render_page("batch_workflows")


@ui_bp.get("/ligand-editor")
def ligand_editor():
    return impl.ligand_editor()


@ui_bp.get("/ligase-ligandalyzer")
def ligase_ligandalyzer():
    return impl.ligase_ligandalyzer()


@ui_bp.get("/view-ligase")
def view_ligase():
    return impl.view_ligase()


@ui_bp.get("/robots.txt")
def robots_txt():
    base_url = current_app.config["PROTAC_PUBLIC_BASE_URL"]
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )
    return Response(body, mimetype="text/plain")


@ui_bp.get("/llms.txt")
def llms_txt():
    return Response(
        llms_text(current_app.config["PROTAC_PUBLIC_BASE_URL"]),
        mimetype="text/plain",
    )


@ui_bp.get("/sitemap.xml")
def sitemap_xml():
    base_url = current_app.config["PROTAC_PUBLIC_BASE_URL"]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in SITEMAP_PATHS:
        loc = f"{base_url}{path}" if path != "/" else base_url
        lines.extend(
            [
                "  <url>",
                f"    <loc>{loc}</loc>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")
    return Response("\n".join(lines), mimetype="application/xml")


@ui_bp.get("/openapi.json")
def openapi_json():
    spec = dict(OPENAPI_SPEC)
    spec["servers"] = [{"url": current_app.config["PROTAC_PUBLIC_BASE_URL"]}]
    return jsonify(spec)


@ui_bp.get("/openapi.yaml")
def openapi_yaml():
    spec = dict(OPENAPI_SPEC)
    spec["servers"] = [{"url": current_app.config["PROTAC_PUBLIC_BASE_URL"]}]
    return Response(yaml_dump(spec) + "\n", mimetype="application/yaml")


@ui_bp.get("/healthz")
def healthz():
    return jsonify({"ok": True, "app": "protac_builder"}), 200
