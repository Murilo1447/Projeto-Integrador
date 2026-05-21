from functools import wraps

from flask import flash, g, redirect, request, session, url_for

from .services.auth_service import buscar_usuario_por_id
from .services.notification_service import contar_notificacoes_nao_lidas, listar_notificacoes_usuario
from .utils import login_redirect_target, user_is_admin


def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = buscar_usuario_por_id(user_id) if user_id else None


def inject_user():
    user = g.get("user")
    if not user:
        return {
            "current_user": None,
            "notification_summary": {"unread_count": 0, "recent": []},
        }

    user_id = user["id_usuario"]
    return {
        "current_user": user,
        "notification_summary": {
            "unread_count": contar_notificacoes_nao_lidas(user_id),
            "recent": listar_notificacoes_usuario(user_id),
        },
    }


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("Faca login para continuar.", "error")
            return redirect(url_for("login", next=login_redirect_target()))
        return view(*args, **kwargs)

    return wrapped_view


def guest_only(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is not None:
            return redirect(url_for("home"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("Faca login para continuar.", "error")
            return redirect(url_for("login", next=login_redirect_target()))
        if not user_is_admin(g.user):
            flash("Acesso restrito ao painel administrativo.", "error")
            return redirect(url_for("home"))
        return view(*args, **kwargs)

    return wrapped_view
