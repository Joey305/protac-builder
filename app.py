import os

from flask import Flask

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional until requirements are installed
    def load_dotenv():
        return False

from protac_builder.io_utils import initialize_runtime_files
from protac_builder.paths import BASE_DIR, ensure_runtime_dirs
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
    )

    @app.context_processor
    def inject_base_urls():
        return {
            "public_base_url": app.config["PROTAC_PUBLIC_BASE_URL"],
            "local_base_url": app.config["PROTAC_LOCAL_BASE_URL"],
        }

    ensure_runtime_dirs()
    initialize_runtime_files()
    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(legacy_bp)

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5069"))
    app.run(host="0.0.0.0", port=port, debug=True)
