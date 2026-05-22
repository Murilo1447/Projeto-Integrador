from functools import wraps

from flask import flash, g, redirect, request, session, url_for

from .services.auth_service import buscar_usuario_por_id
from .services.notification_service import contar_notificacoes_nao_lidas, listar_notificacoes_usuario
from .utils import avatar_payload, login_redirect_target, mapping_get, user_is_admin


def load_logged_in_user():
    user_id = session.get("user_id")
    user = buscar_usuario_por_id(user_id) if user_id else None
    if user:
        user = dict(user)
        user.update(
            avatar_payload(
                user["nome"],
                mapping_get(user, "foto_perfil", ""),
                user_id=user["id_usuario"],
                has_blob=bool(mapping_get(user, "foto_perfil_blob")),
            )
        )
    g.user = user


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
