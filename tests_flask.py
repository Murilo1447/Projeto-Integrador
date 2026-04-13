import tempfile
import unittest
import shutil
from pathlib import Path
from unittest.mock import patch

from app import create_app


class FixCityFlaskTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test.sqlite3"
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(self.db_path),
                "SECRET_KEY": "test-secret",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_paginas_principais_carregam(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/denuncias/").status_code, 200)
        self.assertEqual(self.client.get("/login/").status_code, 200)
        self.assertEqual(self.client.get("/cadastro/").status_code, 200)

    @patch("app.geocodificar_endereco", return_value=(None, None))
    @patch(
        "app.buscar_endereco_por_cep",
        return_value={"rua": "Rua A", "bairro": "Centro", "cidade": "Sao Paulo", "estado": "SP"},
    )
    def test_cadastro_de_chamado_funciona(self, _mock_cep, _mock_geo):
        response = self.client.post(
            "/denuncias/",
            data={
                "cpf": "52998224725",
                "nome": "Maria",
                "email": "maria@example.com",
                "categoria": "BURACO",
                "cep": "01001000",
                "rua": "",
                "bairro": "",
                "cidade": "",
                "numero": "123",
                "descricao": "Existe um buraco grande na via.",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Chamado registrado com sucesso.", response.data)
        self.assertIn(b"Rua A", response.data)

    def test_comentario_com_nome_opcional_funciona(self):
        with self.app.app_context():
            from app import get_db

            db = get_db()
            db.execute(
                """
                INSERT INTO chamados (
                    cpf, nome, email, categoria, cep, rua, bairro, cidade, numero,
                    descricao, status, latitude, longitude, criado_em, atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "52998224725",
                    "",
                    "",
                    "OUTRO",
                    "",
                    "",
                    "",
                    "Sao Paulo",
                    "",
                    "Teste",
                    "PROBLEMA",
                    None,
                    None,
                    "2026-01-01T12:00:00-03:00",
                    "2026-01-01T12:00:00-03:00",
                ),
            )
            db.commit()

        response = self.client.post(
            "/denuncias/1/comentarios/",
            data={"autor_nome": "Felipe", "texto": "Isso aqui precisa de atencao urgente."},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Felipe", response.data)
        self.assertIn(b"Comentario adicionado.", response.data)


if __name__ == "__main__":
    unittest.main()
