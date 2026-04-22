from functools import wraps

from flask import flash, g, redirect, request, session, url_for

from .services.auth_service import buscar_usuario_por_id
from .utils import login_redirect_target


def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = buscar_usuario_por_id(user_id) if user_id else None


def inject_user():
    return {"current_user": g.get("user")}


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
