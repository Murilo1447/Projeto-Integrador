from pathlib import Path

from flask import Flask, flash, redirect, request, url_for

from .auth import inject_user, load_logged_in_user
from .config import default_app_config
from .db import close_db
from .views.auth_views import cadastro, login, logout
from .views.main_views import (
    adicionar_comentario_view,
    alternar_upvote_view,
    atualizar_status,
    denuncias,
    home,
    mapa_ao_vivo,
)


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.update(default_app_config())

    if test_config:
        app.config.update(test_config)

    if (app.config.get("DB_BACKEND") or "sqlite").strip().lower() == "sqlite":
        Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    profile_upload_dir = Path(app.static_folder) / app.config["PROFILE_UPLOAD_SUBDIR"]
    profile_upload_dir.mkdir(parents=True, exist_ok=True)

    app.before_request(load_logged_in_user)
    app.context_processor(inject_user)
    app.teardown_appcontext(close_db)

    @app.errorhandler(413)
    def arquivo_grande(_error):
        flash("A foto de perfil deve ter no maximo 5 MB.", "error")
        return redirect(request.referrer or url_for("cadastro"))

    app.add_url_rule("/", view_func=home, endpoint="home")
    app.add_url_rule("/mapa/", view_func=mapa_ao_vivo, endpoint="mapa_ao_vivo")
    app.add_url_rule("/login/", view_func=login, methods=["GET", "POST"], endpoint="login")
    app.add_url_rule("/cadastro/", view_func=cadastro, methods=["GET", "POST"], endpoint="cadastro")
    app.add_url_rule("/logout/", view_func=logout, methods=["POST"], endpoint="logout")
    app.add_url_rule("/denuncias/", view_func=denuncias, methods=["GET", "POST"], endpoint="denuncias")
    app.add_url_rule(
        "/denuncias/<int:pk>/status/",
        view_func=atualizar_status,
        methods=["POST"],
        endpoint="atualizar_status",
    )
    app.add_url_rule(
        "/denuncias/<int:pk>/comentarios/",
        view_func=adicionar_comentario_view,
        methods=["POST"],
        endpoint="adicionar_comentario",
    )
    app.add_url_rule(
        "/denuncias/<int:pk>/upvote/",
        view_func=alternar_upvote_view,
        methods=["POST"],
        endpoint="alternar_upvote",
    )

    return app
