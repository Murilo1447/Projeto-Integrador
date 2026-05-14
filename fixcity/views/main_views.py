from flask import flash, render_template, request, redirect, url_for

from ..auth import login_required
from ..config import CATEGORIAS, STATUS_CHOICES, STATUS_LABELS
from ..services.chamado_service import (
    adicionar_comentario,
    alternar_upvote,
    calcular_stats,
    form_defaults,
    listar_chamados,
    normalizar_formulario,
    preparar_localizacao,
    salvar_chamado,
    atualizar_status_chamado,
    usuario_pode_atualizar_status,
    validar_chamado,
)
from ..utils import current_user


def aba_valida(valor: str | None, default: str = "feed") -> str:
    aba = (valor or default).strip().lower()
    return aba if aba in {"feed", "novo"} else default


def build_map_data(chamados: list[dict]) -> list[dict]:
    return [
        {
            "id": chamado["id"],
            "autor": chamado["autor_exibicao"],
            "categoria": chamado["categoria_label"],
            "descricao": chamado["descricao"],
            "endereco": chamado["endereco_completo"],
            "status": chamado["status_label"],
            "status_css": chamado["status_css"],
            "status_color": chamado["status_color"],
            "latitude": chamado["latitude"],
            "longitude": chamado["longitude"],
            "tempo_relativo": chamado["tempo_relativo"],
            "upvotes_label": chamado["upvotes_label"],
            "comentarios_label": chamado["comentarios_label"],
            "comentarios": [
                {
                    "autor": comentario["autor_exibicao"],
                    "texto": comentario["texto"],
                    "tempo_relativo": comentario["tempo_relativo"],
                }
                for comentario in chamado["comentarios"]
            ],
        }
        for chamado in chamados
        if chamado["latitude"] is not None and chamado["longitude"] is not None
    ]


def home():
    chamados = listar_chamados()
    stats = calcular_stats(chamados)
    map_data = build_map_data(chamados)
    return render_template("fixcity/index.html", chamados=chamados, stats=stats, map_data=map_data)


def mapa_ao_vivo():
    chamados = listar_chamados()
    stats = calcular_stats(chamados)
    map_data = build_map_data(chamados)
    return render_template("fixcity/mapa.html", chamados=chamados, stats=stats, map_data=map_data)


@login_required
def denuncias():
    user = current_user()
    form_data = form_defaults(user)
    errors = {}
    active_tab = aba_valida(request.args.get("aba"), default="feed")

    if request.method == "POST":
        form_data = normalizar_formulario(request.form, user)
        errors = validar_chamado(form_data)

        if not errors:
            preparar_localizacao(form_data)
            salvar_chamado(form_data, user)
            flash("Chamado registrado com sucesso.", "success")
            return redirect(url_for("denuncias", aba="feed"))

        active_tab = "novo"
        flash("Revise os campos destacados e tente novamente.", "error")

    chamados = listar_chamados(viewer_user_id=user["id_usuario"], sort_mode="social")
    feed_stats = {
        "total": len(chamados),
        "com_mapa": sum(1 for chamado in chamados if chamado["coordinates_available"]),
        "apoios": sum(chamado["upvotes_count"] for chamado in chamados),
        "comentarios": sum(chamado["comentarios_count"] for chamado in chamados),
    }
    return render_template(
        "fixcity/denuncias.html",
        chamados=chamados,
        status_choices=STATUS_CHOICES,
        category_choices=CATEGORIAS,
        form_data=form_data,
        errors=errors,
        active_tab=active_tab,
        feed_stats=feed_stats,
    )


@login_required
def atualizar_status(pk: int):
    status = (request.form.get("status") or "").strip().upper()
    if status not in STATUS_LABELS:
        flash("Nao foi possivel atualizar o status.", "error")
        return redirect(url_for("denuncias", aba=aba_valida(request.form.get("aba"))))

    if not usuario_pode_atualizar_status(pk, current_user()):
        flash("Voce nao tem permissao para alterar o status desta denuncia.", "error")
        return redirect(url_for("denuncias", aba=aba_valida(request.form.get("aba"))))

    atualizar_status_chamado(pk, status)
    flash("Status atualizado.", "success")
    return redirect(url_for("denuncias", aba=aba_valida(request.form.get("aba"))))


@login_required
def adicionar_comentario_view(pk: int):
    texto = (request.form.get("texto") or "").strip()
    if not texto:
        flash("Escreva um comentario valido antes de enviar.", "error")
        return redirect(url_for("denuncias", aba=aba_valida(request.form.get("aba"))))

    adicionar_comentario(pk, texto, current_user())
    flash("Comentario adicionado.", "success")
    return redirect(url_for("denuncias", aba=aba_valida(request.form.get("aba"))))


@login_required
def alternar_upvote_view(pk: int):
    resultado = alternar_upvote(pk, current_user())
    if resultado is None:
        flash("Nao foi possivel registrar seu apoio.", "error")
    return redirect(url_for("denuncias", aba=aba_valida(request.form.get("aba"))))
