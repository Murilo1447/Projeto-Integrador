from django.db import models
from django.utils import timezone


class Chamado(models.Model):
    class Categoria(models.TextChoices):
        BURACO = "BURACO", "Buraco"
        LIXO = "LIXO", "Lixo"
        ILUMINACAO = "ILUMINACAO", "Iluminacao"
        OUTRO = "OUTRO", "Outro"

    class Status(models.TextChoices):
        PROBLEMA = "PROBLEMA", "Problema"
        PENDENTE = "PENDENTE", "Pendente"
        RESOLVIDO = "RESOLVIDO", "Resolvido"

    cpf = models.CharField(max_length=11)
    nome = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices)
    cep = models.CharField(max_length=8, blank=True)
    rua = models.CharField(max_length=120, blank=True)
    bairro = models.CharField(max_length=120, blank=True)
    cidade = models.CharField(max_length=120, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    descricao = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROBLEMA)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    criado_em = models.DateTimeField(default=timezone.now)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Chamado"
        verbose_name_plural = "Chamados"

    def __str__(self):
        return f"{self.get_categoria_display()} - {self.endereco_completo}"

    @property
    def endereco_completo(self):
        partes = [self.rua, self.numero, self.bairro, self.cidade]
        return ", ".join(parte for parte in partes if parte).strip(", ") or "Endereco nao informado"

    @property
    def status_css(self):
        return self.status.lower()

    @property
    def status_cor(self):
        return {
            self.Status.PROBLEMA: "#d64545",
            self.Status.PENDENTE: "#d39b0d",
            self.Status.RESOLVIDO: "#2c8f4f",
        }.get(self.status, "#5b6472")


class Comentario(models.Model):
    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name="comentarios")
    texto = models.TextField()
    criado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["criado_em"]
        verbose_name = "Comentario"
        verbose_name_plural = "Comentarios"

    def __str__(self):
        return f"Comentario #{self.pk} no chamado #{self.chamado_id}"
