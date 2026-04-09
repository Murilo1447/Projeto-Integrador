from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from fixcity.models import Chamado


class FixCityViewsTests(TestCase):
    def test_paginas_principais_carregam(self):
        self.assertEqual(self.client.get(reverse("fixcity:home")).status_code, 200)
        self.assertEqual(self.client.get(reverse("fixcity:denuncias")).status_code, 200)

    @patch("fixcity.views.views.geocodificar_endereco", return_value=(None, None))
    @patch(
        "fixcity.views.views.buscar_endereco_por_cep",
        return_value={"rua": "Rua A", "bairro": "Centro", "cidade": "Sao Paulo", "estado": "SP"},
    )
    def test_cadastro_de_chamado_funciona(self, _mock_cep, _mock_geo):
        response = self.client.post(
            reverse("fixcity:denuncias"),
            data={
                "cpf": "52998224725",
                "nome": "Maria",
                "email": "maria@example.com",
                "categoria": Chamado.Categoria.BURACO,
                "cep": "01001000",
                "rua": "",
                "bairro": "",
                "cidade": "",
                "numero": "123",
                "descricao": "Existe um buraco grande na via.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        chamado = Chamado.objects.get()
        self.assertEqual(chamado.rua, "Rua A")
        self.assertEqual(chamado.cidade, "Sao Paulo")
