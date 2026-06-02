from flask import flash, redirect, render_template, request, url_for

from ..auth import admin_required, login_required
from ..config import CATEGORIAS, STATUS_CHOICES, STATUS_LABELS
from ..models.call_model import (
    LOCATION_FILTER_CHOICES,
    adicionar_comentario,
    alternar_upvote,
    atualizar_status_chamado,
    build_map_data,
    calcular_stats,
    construir_filtro_localizacao,
    filtrar_chamados_por_localizacao,
    form_defaults,
    listar_chamados,
    listar_comentarios_recentes,
    montar_dashboard_admin,
    normalizar_formulario,
    obter_perfil_publico,
    preparar_localizacao,
    remover_comentario,
    salvar_chamado,
    salvar_foto_chamado,
    usuario_pode_atualizar_status,
    validar_chamado,
)
from ..models.notification_model import criar_notificacao, marcar_notificacoes_como_lidas
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


def register_main_routes(app):
    app.add_url_rule("/", view_func=home, endpoint="home")
    app.add_url_rule("/mapa/", view_func=mapa_ao_vivo, endpoint="mapa_ao_vivo")
    app.add_url_rule("/usuarios/<int:user_id>/", view_func=perfil_publico, endpoint="perfil_publico")
    app.add_url_rule("/admin/", view_func=dashboard_admin, endpoint="dashboard_admin")
    app.add_url_rule("/denuncias/", view_func=denuncias, methods=["GET", "POST"], endpoint="denuncias")
    app.add_url_rule(
        "/notificacoes/marcar-lidas/",
        view_func=marcar_notificacoes_lidas_view,
        methods=["POST"],
        endpoint="marcar_notificacoes_lidas",
    )
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
    app.add_url_rule(
        "/admin/comentarios/<int:comment_id>/excluir/",
        view_func=excluir_comentario_admin,
        methods=["POST"],
        endpoint="excluir_comentario_admin",
    )
