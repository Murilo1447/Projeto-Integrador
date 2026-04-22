from flask import flash, render_template, request, redirect, url_for

from ..auth import login_required
from ..config import CATEGORIAS, STATUS_CHOICES, STATUS_LABELS
from ..services.chamado_service import (
    adicionar_comentario,
    calcular_stats,
    form_defaults,
    listar_chamados,
    normalizar_formulario,
    preparar_localizacao,
    salvar_chamado,
    atualizar_status_chamado,
    validar_chamado,
)
from ..utils import current_user


def home():
    chamados = listar_chamados()
    stats = calcular_stats(chamados)
    map_data = [
        {
            "id": chamado["id"],
            "categoria": chamado["categoria_label"],
            "descricao": chamado["descricao"],
            "endereco": chamado["endereco_completo"],
            "status": chamado["status_label"],
            "status_color": chamado["status_color"],
            "latitude": chamado["latitude"],
            "longitude": chamado["longitude"],
            "comentarios": [
                f'{comentario["autor_exibicao"]}: {comentario["texto"]}'
                for comentario in chamado["comentarios"]
            ],
        }
        for chamado in chamados
        if chamado["latitude"] is not None and chamado["longitude"] is not None
    ]
    return render_template("fixcity/index.html", chamados=chamados, stats=stats, map_data=map_data)


@login_required
def denuncias():
    user = current_user()
    form_data = form_defaults(user)
    errors = {}

    if request.method == "POST":
        form_data = normalizar_formulario(request.form, user)
        errors = validar_chamado(form_data)

        if not errors:
            preparar_localizacao(form_data)
            salvar_chamado(form_data, user)
            flash("Chamado registrado com sucesso.", "success")
            return redirect(url_for("denuncias"))

        flash("Revise os campos destacados e tente novamente.", "error")

    chamados = listar_chamados()
    return render_template(
        "fixcity/denuncias.html",
        chamados=chamados,
        status_choices=STATUS_CHOICES,
        category_choices=CATEGORIAS,
        form_data=form_data,
        errors=errors,
    )


@login_required
def atualizar_status(pk: int):
    status = (request.form.get("status") or "").strip().upper()
    if status not in STATUS_LABELS:
        flash("Nao foi possivel atualizar o status.", "error")
        return redirect(url_for("denuncias"))

    atualizar_status_chamado(pk, status)
    flash("Status atualizado.", "success")
    return redirect(url_for("denuncias"))


@login_required
def adicionar_comentario_view(pk: int):
    texto = (request.form.get("texto") or "").strip()
    if not texto:
        flash("Escreva um comentario valido antes de enviar.", "error")
        return redirect(url_for("denuncias"))

    adicionar_comentario(pk, texto, current_user())
    flash("Comentario adicionado.", "success")
    return redirect(url_for("denuncias"))
