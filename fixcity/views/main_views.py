from flask import flash, render_template, request, redirect, url_for

from ..auth import admin_required, login_required
from ..config import CATEGORIAS, STATUS_CHOICES, STATUS_LABELS
from ..services.chamado_service import (
    adicionar_comentario,
    alternar_upvote,
    buscar_chamado_por_id,
    calcular_stats,
    construir_filtro_localizacao,
    filtrar_chamados_por_localizacao,
    form_defaults,
    LOCATION_FILTER_CHOICES,
    listar_comentarios_recentes,
    listar_chamados,
    montar_dashboard_admin,
    normalizar_formulario,
    obter_perfil_publico,
    preparar_localizacao,
    remover_comentario,
    salvar_chamado,
    salvar_foto_chamado,
    atualizar_status_chamado,
    usuario_pode_atualizar_status,
    validar_chamado,
)
from ..services.notification_service import criar_notificacao, marcar_notificacoes_como_lidas
from ..utils import current_user, normalize_next_url


def aba_valida(valor: str | None, default: str = "feed") -> str:
    aba = (valor or default).strip().lower()
    return aba if aba in {"feed", "novo"} else default


def filtro_localizacao_da_request(source) -> dict:
    return construir_filtro_localizacao(source.get("campo_localizacao"), source.get("busca_localizacao"))


def args_redirecionamento_feed(source) -> dict:
    args = {"aba": aba_valida(source.get("aba"), default="feed")}
    filtro = filtro_localizacao_da_request(source)
    if filtro["ativo"]:
        args["campo_localizacao"] = filtro["campo"]
        args["busca_localizacao"] = filtro["busca"]
    return args


def build_map_data(chamados: list[dict]) -> list[dict]:
    return [
        {
            "id": chamado["id"],
            "owner_user_id": chamado["owner_user_id"],
            "autor": chamado["autor_exibicao"],
            "categoria": chamado["categoria_label"],
            "descricao": chamado["descricao"],
            "endereco": chamado["endereco_completo"],
            "status": chamado["status_label"],
            "status_css": chamado["status_css"],
            "status_color": chamado["status_color"],
            "priority_score": chamado["priority_score"],
            "priority_label": chamado["priority_label"],
            "priority_css": chamado["priority_css"],
            "heat_weight": max(0.25, min(chamado["priority_score"] / 24, 1)),
            "foto_chamado_url": chamado["foto_chamado_url"],
            "latitude": chamado["latitude"],
            "longitude": chamado["longitude"],
            "bairro": chamado["bairro"],
            "cidade": chamado["cidade"],
            "estado": chamado["estado"],
            "pais": chamado["pais"],
            "regiao": chamado["regiao"],
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
    return render_template(
        "fixcity/index.html",
        chamados=chamados,
        stats=stats,
        map_data=map_data,
        comentarios_recentes=listar_comentarios_recentes(limit=4),
    )


def mapa_ao_vivo():
    chamados = listar_chamados()
    location_filter = filtro_localizacao_da_request(request.args)
    chamados = filtrar_chamados_por_localizacao(chamados, location_filter)
    stats = calcular_stats(chamados)
    map_data = build_map_data(chamados)
    return render_template(
        "fixcity/mapa.html",
        chamados=chamados,
        stats=stats,
        map_data=map_data,
        location_filter=location_filter,
        location_filter_choices=LOCATION_FILTER_CHOICES,
    )


@login_required
def denuncias():
    user = current_user()
    form_data = form_defaults(user)
    errors = {}
    active_tab = aba_valida(request.args.get("aba"), default="feed")
    location_filter = filtro_localizacao_da_request(request.args)

    if request.method == "POST":
        form_data = normalizar_formulario(request.form, user)
        foto = request.files.get("foto_chamado")
        errors = validar_chamado(form_data, foto)

        if not errors:
            form_data["foto_chamado"] = salvar_foto_chamado(foto)
            preparar_localizacao(form_data)
            salvar_chamado(form_data, user)
            flash("Chamado registrado com sucesso.", "success")
            return redirect(url_for("denuncias", **args_redirecionamento_feed(request.args)))

        active_tab = "novo"
        flash("Revise os campos destacados e tente novamente.", "error")

    chamados = listar_chamados(viewer_user_id=user["id_usuario"], sort_mode="social")
    chamados = filtrar_chamados_por_localizacao(chamados, location_filter)
    feed_stats = {
        "total": len(chamados),
        "com_mapa": sum(1 for chamado in chamados if chamado["coordinates_available"]),
        "apoios": sum(chamado["upvotes_count"] for chamado in chamados),
        "comentarios": sum(chamado["comentarios_count"] for chamado in chamados),
        "prioridade_alta": sum(1 for chamado in chamados if chamado["priority_css"] == "alta"),
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
        location_filter=location_filter,
        location_filter_choices=LOCATION_FILTER_CHOICES,
    )


@login_required
def atualizar_status(pk: int):
    user = current_user()
    status = (request.form.get("status") or "").strip().upper()
    if status not in STATUS_LABELS:
        flash("Nao foi possivel atualizar o status.", "error")
        return redirect(url_for("denuncias", **args_redirecionamento_feed(request.form)))

    if not usuario_pode_atualizar_status(pk, user):
        flash("Voce nao tem permissao para alterar o status desta denuncia.", "error")
        return redirect(url_for("denuncias", **args_redirecionamento_feed(request.form)))

    owner_user_id = atualizar_status_chamado(pk, status)
    if owner_user_id and owner_user_id != user["id_usuario"]:
        criar_notificacao(
            destinatario_usuario_id=owner_user_id,
            ator_usuario_id=user["id_usuario"],
            chamado_id=pk,
            tipo="status",
            titulo="Status atualizado",
            mensagem=f'{user["nome"]} atualizou o status da sua denuncia para {STATUS_LABELS[status]}.',
        )
    flash("Status atualizado.", "success")
    return redirect(url_for("denuncias", **args_redirecionamento_feed(request.form)))


@login_required
def adicionar_comentario_view(pk: int):
    texto = (request.form.get("texto") or "").strip()
    if not texto:
        flash("Escreva um comentario valido antes de enviar.", "error")
        return redirect(url_for("denuncias", **args_redirecionamento_feed(request.form)))

    adicionar_comentario(pk, texto, current_user())
    flash("Comentario adicionado.", "success")
    return redirect(url_for("denuncias", **args_redirecionamento_feed(request.form)))


@login_required
def alternar_upvote_view(pk: int):
    resultado = alternar_upvote(pk, current_user())
    if resultado is None:
        flash("Nao foi possivel registrar seu apoio.", "error")
    return redirect(url_for("denuncias", **args_redirecionamento_feed(request.form)))


@login_required
def marcar_notificacoes_lidas_view():
    user = current_user()
    marcar_notificacoes_como_lidas(user["id_usuario"])
    flash("Notificacoes marcadas como lidas.", "success")
    return redirect(normalize_next_url(request.form.get("next")))


def perfil_publico(user_id: int):
    viewer = current_user()
    perfil = obter_perfil_publico(user_id, viewer_user_id=viewer["id_usuario"] if viewer else None)
    if not perfil:
        flash("Perfil nao encontrado.", "error")
        return redirect(url_for("home"))

    return render_template("fixcity/perfil.html", perfil=perfil)


@admin_required
def dashboard_admin():
    dashboard = montar_dashboard_admin()
    return render_template("fixcity/admin.html", dashboard=dashboard, status_choices=STATUS_CHOICES)


@admin_required
def excluir_comentario_admin(comment_id: int):
    remover_comentario(comment_id)
    flash("Comentario removido pelo painel administrativo.", "success")
    return redirect(url_for("dashboard_admin"))
