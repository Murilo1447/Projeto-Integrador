from flask import flash, redirect, render_template, request, session, url_for

from ..auth import guest_only, login_required
from ..models.user_model import (
    autenticar_usuario,
    cadastro_defaults,
    criar_usuario,
    normalizar_cadastro_form,
    salvar_foto_perfil,
    validar_cadastro,
)
from ..utils import normalize_next_url


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


def register_auth_routes(app):
    app.add_url_rule("/login/", view_func=login, methods=["GET", "POST"], endpoint="login")
    app.add_url_rule("/cadastro/", view_func=cadastro, methods=["GET", "POST"], endpoint="cadastro")
    app.add_url_rule("/logout/", view_func=logout, methods=["POST"], endpoint="logout")
