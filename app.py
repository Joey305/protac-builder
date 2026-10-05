import os
import traceback

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional until requirements are installed
    def load_dotenv():
        return False

from protac_builder.io_utils import initialize_runtime_files
from protac_builder.paths import BASE_DIR, LOGS_DIR, ensure_runtime_dirs
from protac_builder.analytics import initialize_store, remote_enabled
from protac_builder.api_routes import api_bp
from protac_builder.legacy_routes import legacy_bp
from protac_builder.routes import ui_bp

load_dotenv()


def _env_url(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip() or default
    return value.rstrip("/")


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )

    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me"),
        BASE_DIR=str(BASE_DIR),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
        PROTAC_PUBLIC_BASE_URL=_env_url("PROTAC_PUBLIC_BASE_URL", "https://protacbuilder.com"),
        PROTAC_LOCAL_BASE_URL=_env_url("PROTAC_LOCAL_BASE_URL", "http://127.0.0.1:5069"),
        ANALYTICS_DB_PATH=os.environ.get("ANALYTICS_DB_PATH", "").strip() or str(BASE_DIR / "uploads" / "runtime_data" / "conference_analytics.sqlite3"),
        ADMIN_EMAIL=os.environ.get("ADMIN_EMAIL", "").strip(),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", ""),
        ECOSYSTEM_TOOL_URLS={
            "warheadhunter": _env_url("WARHEAD_HUNTER_URL", "https://warheadhunter.com"),
            "vlisemod": _env_url("VLISEMOD_URL", "https://vlisemod.com"),
            "e3_ligandalyzer": _env_url("E3_LIGANDALYZER_URL", "https://e3ligandalyzer.com/explorer"),
            "protac_builder": _env_url("PROTAC_BUILDER_URL", "https://protacbuilder.com") + "/builder",
            # No separate deployed URLs are present in this repository. Keep these configurable,
            # while the conference page accurately points Ternary Modeling to existing guidance.
            "ternary_modeling": _env_url("TERNARY_MODELING_URL", "https://protacbuilder.com") + "/downstream-modeling",
            "pymacs": os.environ.get("PYMACS_URL", "").strip(),
        },
    )

    @app.context_processor
    def inject_base_urls():
        return {
            "public_base_url": app.config["PROTAC_PUBLIC_BASE_URL"],
            "local_base_url": app.config["PROTAC_LOCAL_BASE_URL"],
        }

    ensure_runtime_dirs()
    if not remote_enabled():
        initialize_store(app.config["ANALYTICS_DB_PATH"])
    initialize_runtime_files()
    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(legacy_bp)

    @app.errorhandler(Exception)
    def api_json_error(exc):
        api_prefixes = ("/api/deeppk", "/api/admet", "/run-drug-analysis")
        if not request.path.startswith(api_prefixes):
            if isinstance(exc, HTTPException):
                return exc
            raise exc
        status_code = exc.code if isinstance(exc, HTTPException) else 500
        if request.path.startswith(("/api/deeppk", "/run-drug-analysis")):
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            with (LOGS_DIR / "deeppk_errors.log").open("a", encoding="utf-8") as handle:
                handle.write(f"[global-error] path={request.path}\n")
                handle.write(traceback.format_exc())
                handle.write("\n")
        return jsonify(
            {
                "success": False,
                "error": "DeepPK report generation failed." if "deeppk" in request.path.lower() or request.path == "/run-drug-analysis" else "ADMET request failed.",
                "details": str(exc) or exc.__class__.__name__,
                "stage": "flask_error_handler",
                "job_id": None,
                "rdkit_descriptors": {},
                "retryable": status_code >= 500,
            }
        ), status_code

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5069"))
    app.run(host="0.0.0.0", port=port, debug=True)
