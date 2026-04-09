from django.contrib import admin
from fixcity.models import Chamado, Comentario


class ComentarioInline(admin.TabularInline):
    model = Comentario
    extra = 0


@admin.register(Chamado)
class ChamadoAdmin(admin.ModelAdmin):
    list_display = ("id", "categoria", "cidade", "status", "criado_em")
    list_filter = ("categoria", "status", "cidade")
    search_fields = ("cpf", "nome", "descricao", "cidade", "rua")
    inlines = [ComentarioInline]
