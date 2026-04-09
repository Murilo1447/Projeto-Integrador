from django.urls import path

from fixcity.views import adicionar_comentario, atualizar_status, denuncias, home

app_name = "fixcity"

urlpatterns = [
    path("", home, name="home"),
    path("denuncias/", denuncias, name="denuncias"),
    path("denuncias/<int:pk>/status/", atualizar_status, name="atualizar_status"),
    path("denuncias/<int:pk>/comentarios/", adicionar_comentario, name="adicionar_comentario"),
]
