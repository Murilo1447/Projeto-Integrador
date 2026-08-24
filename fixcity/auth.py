from functools import wraps
from flask import flash, g, redirect, render_template, request, session, url_for

from .models.notification_model import (
    contar_notificacoes_nao_lidas,
    listar_notificacoes_usuario,
)
from .models.user_model import (
    autenticar_usuario,
    buscar_usuario_por_id,
    cadastro_defaults,
    criar_usuario,
    normalizar_cadastro_form,
    salvar_foto_perfil,
    validar_cadastro,
    alternar_privacidade_usuario,
)
from .utils import (
    avatar_payload,
    login_redirect_target,
    mapping_get,
    normalize_next_url,
    user_is_admin,
)


def load_logged_in_user():
    user_id = session.get("user_id")
    user = buscar_usuario_por_id(user_id) if user_id else None
    if user:
        user = dict(user) if not isinstance(user, dict) else user
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


@guest_only
def login():
    form_data = {"email": ""}

    if request.method == "POST":
        form_data["email"] = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""
        usuario = autenticar_usuario(form_data["email"], senha)

        if usuario:
            session.clear()
            session["user_id"] = usuario["id_usuario"]
            flash("Login realizado com sucesso.", "success")
            return redirect(normalize_next_url(request.args.get("next")))

        flash("Email ou senha incorretos.", "error")

    return render_template("fixcity/login.html", form_data=form_data)


@guest_only
def cadastro():
    form_data = cadastro_defaults()
    errors = {}

    if request.method == "POST":
        form_data = normalizar_cadastro_form(request.form)
        foto = request.files.get("foto_perfil")
        errors = validar_cadastro(form_data, foto)

        if not errors:
            foto_blob, foto_mime = salvar_foto_perfil(foto)
            usuario_id = criar_usuario(form_data, foto_blob, foto_mime)
            session.clear()
            session["user_id"] = usuario_id
            flash("Conta criada com sucesso. Voce ja esta logado.", "success")
            return redirect(url_for("denuncias"))

        flash("Revise os campos destacados e tente novamente.", "error")

    return render_template("fixcity/cadastro.html", form_data=form_data, errors=errors)


@login_required
def logout():
    session.clear()
    flash("Voce saiu da sua conta.", "success")
    return redirect(url_for("home"))


@login_required
def alternar_privacidade():
    user_id = session.get("user_id")

    if user_id:
        status_privado = alternar_privacidade_usuario(user_id)
        if status_privado:
            flash("Seu perfil agora esta privado.", "success")
        else:
            flash("Seu perfil agora esta publico.", "success")

    return redirect(url_for("perfil_publico", user_id=user_id))


def register_auth_routes(app):
    app.add_url_rule("/login/", view_func=login, methods=["GET", "POST"], endpoint="login")
    app.add_url_rule("/cadastro/", view_func=cadastro, methods=["GET", "POST"], endpoint="cadastro")
    app.add_url_rule("/logout/", view_func=logout, methods=["POST"], endpoint="logout")
    app.add_url_rule("/perfil/alternar-privacidade/", view_func=alternar_privacidade, methods=["POST"], endpoint="alternar_privacidade")