import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from fixcity.db import get_db
from fixcity.services.auth_service import buscar_usuario_por_email


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

    def cadastrar_usuario(self, com_foto=False, nome="Maria da Silva", cpf="52998224725", email="maria@example.com"):
        data = {
            "nome": nome,
            "cpf": cpf,
            "telefone": "11999999999",
            "email": email,
            "senha": "senha123",
        }
        if com_foto:
            data["foto_perfil"] = (io.BytesIO(b"imagem-teste"), "avatar.png")

        response = self.client.post("/cadastro/", data=data, follow_redirects=True)

        if com_foto:
            with self.app.app_context():
                usuario = buscar_usuario_por_email(email)
                if usuario and usuario["foto_perfil"]:
                    self.created_uploads.append(Path(self.app.static_folder) / usuario["foto_perfil"])

        return response

    def criar_chamado_autenticado(self, coords=(None, None)):
        with patch("fixcity.services.chamado_service.geocodificar_endereco", return_value=coords), patch(
            "fixcity.services.chamado_service.buscar_endereco_por_cep",
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

    def test_feed_social_exibe_mini_mapa_e_permite_upvote(self):
        self.cadastrar_usuario()
        self.criar_chamado_autenticado(coords=(-23.55052, -46.633308))

        response = self.client.post("/denuncias/1/upvote/", data={"aba": "feed"}, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Feed da comunidade", response.data)
        self.assertIn(b"mini-map-1", response.data)
        self.assertIn(b"Apoiado", response.data)

    def test_status_so_pode_ser_alterado_pelo_autor_ou_admin(self):
        self.cadastrar_usuario(nome="Maria da Silva", cpf="52998224725", email="maria@example.com")
        self.criar_chamado_autenticado()
        self.client.post("/logout/", follow_redirects=True)

        self.cadastrar_usuario(nome="Joao Pereira", cpf="11144477735", email="joao@example.com")
        response = self.client.post(
            "/denuncias/1/status/",
            data={"status": "RESOLVIDO", "aba": "feed"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Voce nao tem permissao para alterar o status desta denuncia.", response.data)
        with self.app.app_context():
            status_atual = get_db().execute("SELECT status FROM chamados WHERE id = ?", (1,)).fetchone()["status"]
        self.assertEqual(status_atual, "PROBLEMA")

        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE usuarios SET is_admin = 1 WHERE email = ?", ("joao@example.com",))
            db.commit()

        self.client.post("/logout/", follow_redirects=True)
        self.client.post(
            "/login/",
            data={"email": "joao@example.com", "senha": "senha123"},
            follow_redirects=True,
        )
        admin_response = self.client.post(
            "/denuncias/1/status/",
            data={"status": "RESOLVIDO", "aba": "feed"},
            follow_redirects=True,
        )

        self.assertEqual(admin_response.status_code, 200)
        self.assertIn(b"Status atualizado.", admin_response.data)
        with self.app.app_context():
            status_final = get_db().execute("SELECT status FROM chamados WHERE id = ?", (1,)).fetchone()["status"]
        self.assertEqual(status_final, "RESOLVIDO")


if __name__ == "__main__":
    unittest.main()
