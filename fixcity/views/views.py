from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from fixcity.forms import ChamadoForm, ComentarioForm, StatusForm
from fixcity.models import Chamado
from fixcity.services import buscar_endereco_por_cep, geocodificar_endereco


def _enriquecer_chamado(chamado: Chamado):
    if chamado.cep and (not chamado.rua or not chamado.bairro or not chamado.cidade):
        endereco = buscar_endereco_por_cep(chamado.cep)
        if endereco:
            chamado.rua = chamado.rua or endereco["rua"]
            chamado.bairro = chamado.bairro or endereco["bairro"]
            chamado.cidade = chamado.cidade or endereco["cidade"]

    if not chamado.latitude or not chamado.longitude:
        latitude, longitude = geocodificar_endereco(chamado.endereco_completo)
        if latitude is not None and longitude is not None:
            chamado.latitude = latitude
            chamado.longitude = longitude


def _contexto_base():
    chamados = list(Chamado.objects.prefetch_related("comentarios").all())
    return {
        "chamados": chamados,
        "stats": {
            "total": len(chamados),
            "problemas": sum(1 for chamado in chamados if chamado.status == Chamado.Status.PROBLEMA),
            "pendentes": sum(1 for chamado in chamados if chamado.status == Chamado.Status.PENDENTE),
            "resolvidos": sum(1 for chamado in chamados if chamado.status == Chamado.Status.RESOLVIDO),
        },
        "comentario_form": ComentarioForm(),
    }


def home(request):
    contexto = _contexto_base()
    contexto["map_data"] = [
        {
            "id": chamado.pk,
            "categoria": chamado.get_categoria_display(),
            "descricao": chamado.descricao,
            "endereco": chamado.endereco_completo,
            "status": chamado.get_status_display(),
            "status_color": chamado.status_cor,
            "latitude": float(chamado.latitude),
            "longitude": float(chamado.longitude),
            "comentarios": [comentario.texto for comentario in chamado.comentarios.all()],
        }
        for chamado in contexto["chamados"]
        if chamado.latitude is not None and chamado.longitude is not None
    ]
    return render(request, "fixcity/index.html", contexto)


def denuncias(request):
    if request.method == "POST":
        form = ChamadoForm(request.POST)
        if form.is_valid():
            chamado = form.save(commit=False)
            _enriquecer_chamado(chamado)
            chamado.save()
            messages.success(request, "Chamado registrado com sucesso.")
            return redirect("fixcity:denuncias")
        messages.error(request, "Revise os campos destacados e tente novamente.")
    else:
        form = ChamadoForm()

    contexto = _contexto_base()
    contexto["form"] = form
    contexto["status_choices"] = Chamado.Status.choices
    return render(request, "fixcity/denuncias.html", contexto)


def atualizar_status(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    if request.method == "POST":
        form = StatusForm(request.POST, instance=chamado)
        if form.is_valid():
            form.save()
            messages.success(request, "Status atualizado.")
        else:
            messages.error(request, "Nao foi possivel atualizar o status.")
    return redirect("fixcity:denuncias")


def adicionar_comentario(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    if request.method == "POST":
        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.chamado = chamado
            comentario.save()
            messages.success(request, "Comentario adicionado.")
        else:
            messages.error(request, "Escreva um comentario valido antes de enviar.")
    return redirect("fixcity:denuncias")
