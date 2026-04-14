import io
import shutil
import tempfile
import unittest
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
                "DB_BACKEND": "sqlite",
                "DATABASE": str(self.db_path),
                "SECRET_KEY": "test-secret",
            }
        )
        self.client = self.app.test_client()
        self.created_uploads = []

    def tearDown(self):
        for upload_path in self.created_uploads:
            Path(upload_path).unlink(missing_ok=True)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def cadastrar_usuario(self, com_foto=False):
        data = {
            "nome": "Maria da Silva",
            "cpf": "52998224725",
            "telefone": "11999999999",
            "email": "maria@example.com",
            "senha": "senha123",
        }
        if com_foto:
            data["foto_perfil"] = (io.BytesIO(b"imagem-teste"), "avatar.png")

        response = self.client.post("/cadastro/", data=data, follow_redirects=True)

        if com_foto:
            with self.app.app_context():
                from app import buscar_usuario_por_email

                usuario = buscar_usuario_por_email("maria@example.com")
                if usuario and usuario["foto_perfil"]:
                    self.created_uploads.append(Path(self.app.static_folder) / usuario["foto_perfil"])

        return response

    def criar_chamado_autenticado(self):
        with patch("app.geocodificar_endereco", return_value=(None, None)), patch(
            "app.buscar_endereco_por_cep",
            return_value={"rua": "Rua A", "bairro": "Centro", "cidade": "Sao Paulo", "estado": "SP"},
        ):
            return self.client.post(
                "/denuncias/",
                data={
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

    def test_paginas_publicas_carregam_e_denuncias_exige_login(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/login/").status_code, 200)
        self.assertEqual(self.client.get("/cadastro/").status_code, 200)

        response = self.client.get("/denuncias/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.headers["Location"])

    def test_cadastro_login_e_chamado_funcionam(self):
        cadastro = self.cadastrar_usuario()
        self.assertEqual(cadastro.status_code, 200)
        self.assertIn(b"Conta criada com sucesso", cadastro.data)
        self.assertIn(b"Novo Chamado", cadastro.data)

        response = self.criar_chamado_autenticado()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Chamado registrado com sucesso.", response.data)
        self.assertIn(b"Rua A", response.data)
        self.assertIn(b"Maria da Silva", response.data)

    def test_login_funciona_apos_logout(self):
        self.cadastrar_usuario()
        self.client.post("/logout/", follow_redirects=True)

        response = self.client.post(
            "/login/",
            data={"email": "maria@example.com", "senha": "senha123"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Login realizado com sucesso.", response.data)

    def test_comentario_exibe_autor_e_foto_de_perfil(self):
        self.cadastrar_usuario(com_foto=True)
        self.criar_chamado_autenticado()

        response = self.client.post(
            "/denuncias/1/comentarios/",
            data={"texto": "Isso aqui precisa de atencao urgente."},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Comentario adicionado.", response.data)
        self.assertIn(b"Maria da Silva", response.data)
        self.assertIn(b"uploads/profiles/", response.data)


if __name__ == "__main__":
    unittest.main()
