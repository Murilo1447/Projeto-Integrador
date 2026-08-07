from pathlib import Path

from flask import Flask, flash, redirect, request, url_for

from .auth import inject_user, load_logged_in_user
from .config import default_app_config
from .controllers import register_routes
from .db import close_db


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.update(default_app_config())

    if test_config:
        app.config.update(test_config)

    if (app.config.get("DB_BACKEND") or "sqlite").strip().lower() == "sqlite":
        Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    profile_upload_dir = Path(app.static_folder) / app.config["PROFILE_UPLOAD_SUBDIR"]
    profile_upload_dir.mkdir(parents=True, exist_ok=True)
    call_upload_dir = Path(app.static_folder) / app.config["CALL_UPLOAD_SUBDIR"]
    call_upload_dir.mkdir(parents=True, exist_ok=True)

    app.before_request(load_logged_in_user)
    app.context_processor(inject_user)
    app.teardown_appcontext(close_db)

    @app.errorhandler(413)
    def arquivo_grande(_error):
        flash("As imagens devem ter no maximo 5 MB.", "error")
        return redirect(request.referrer or url_for("cadastro"))

    register_routes(app)
    return app
