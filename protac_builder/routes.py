from __future__ import annotations

from pathlib import Path

from flask import Blueprint, jsonify, render_template, request

from . import route_impl as impl
from .io_utils import apply_cors_headers


ui_bp = Blueprint("ui", __name__)


def _missing_path_error(path: Path, status: int = 500):
    return jsonify({"error": "Missing required data file", "path": str(path)}), status


@ui_bp.after_request
def add_cors_headers(response):
    return apply_cors_headers(request, response)


@ui_bp.get("/")
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


@ui_bp.get("/api-builder")
def api_builder():
    return render_template("api_builder.html")


@ui_bp.get("/api-docs")
def api_docs():
    return render_template("api_docs.html")


@ui_bp.get("/about")
def about():
    return render_template("about.html")


@ui_bp.get("/ligand-editor")
def ligand_editor():
    return impl.ligand_editor()


@ui_bp.get("/ligase-ligandalyzer")
def ligase_ligandalyzer():
    return impl.ligase_ligandalyzer()


@ui_bp.get("/view-ligase")
def view_ligase():
    return impl.view_ligase()


@ui_bp.get("/healthz")
def healthz():
    return jsonify({"ok": True, "app": "protac_builder"}), 200
