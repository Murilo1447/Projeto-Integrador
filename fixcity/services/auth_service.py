import re
from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from ..db import get_db, mysql_enabled, mysql_insert_id
from ..utils import agora_iso, cpf_valido, image_extension, imagem_permitida, telefone_valido


def cadastro_defaults() -> dict:
    return {
        "nome": "",
        "cpf": "",
        "telefone": "",
        "email": "",
    }


def normalizar_cadastro_form(form) -> dict:
    return {
        "nome": (form.get("nome") or "").strip(),
        "cpf": re.sub(r"\D", "", form.get("cpf") or ""),
        "telefone": re.sub(r"\D", "", form.get("telefone") or ""),
        "email": (form.get("email") or "").strip().lower(),
        "senha": form.get("senha") or "",
    }


def buscar_usuario_por_id(user_id: int | None):
    if not user_id:
        return None

    query = "SELECT id_usuario, nome, email, senha, telefone, cpf, is_admin, foto_perfil FROM usuarios WHERE id_usuario = ?"
    return get_db().execute(query, (user_id,)).fetchone()


def buscar_usuario_por_email(email: str):
    if not email:
        return None

    query = "SELECT id_usuario, nome, email, senha, telefone, cpf, is_admin, foto_perfil FROM usuarios WHERE email = ?"
    return get_db().execute(query, (email,)).fetchone()


def buscar_usuario_por_cpf(cpf: str):
    if not cpf:
        return None

    query = "SELECT id_usuario, nome, email, senha, telefone, cpf, is_admin, foto_perfil FROM usuarios WHERE cpf = ?"
    return get_db().execute(query, (cpf,)).fetchone()


def autenticar_usuario(email: str, senha: str):
    usuario = buscar_usuario_por_email(email)
    if usuario and check_password_hash(usuario["senha"], senha):
        return usuario
    return None


def validar_cadastro(data: dict, foto) -> dict:
    errors = {}

    if len(data["nome"]) < 3:
        errors["nome"] = "Informe um nome completo valido."
    if not cpf_valido(data["cpf"]):
        errors["cpf"] = "Informe um CPF valido."
    if not telefone_valido(data["telefone"]):
        errors["telefone"] = "Informe um telefone com DDD."
    if "@" not in data["email"]:
        errors["email"] = "Informe um e-mail valido."
    if len(data["senha"]) < 6:
        errors["senha"] = "A senha precisa ter pelo menos 6 caracteres."
    if foto and foto.filename and not imagem_permitida(foto.filename):
        errors["foto_perfil"] = "Envie uma imagem PNG, JPG, JPEG, WEBP ou GIF."
    if buscar_usuario_por_email(data["email"]):
        errors["email"] = "Este e-mail ja esta cadastrado."
    if buscar_usuario_por_cpf(data["cpf"]):
        errors["cpf"] = "Este CPF ja esta cadastrado."

    return errors


def salvar_foto_perfil(foto) -> str:
    if not foto or not foto.filename:
        return ""

    filename = secure_filename(foto.filename)
    extensao = image_extension(filename)
    unique_name = f"{uuid4().hex}.{extensao}"
    relative_path = Path(current_app.config["PROFILE_UPLOAD_SUBDIR"]) / unique_name
    target_path = Path(current_app.static_folder) / relative_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    foto.save(target_path)
    return relative_path.as_posix()


def criar_usuario(data: dict, foto_path: str) -> int:
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO usuarios (nome, email, senha, telefone, cpf, foto_perfil, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["nome"],
            data["email"],
            generate_password_hash(data["senha"]),
            data["telefone"],
            data["cpf"],
            foto_path,
            agora_iso(),
        ),
    )
    db.commit()
    return mysql_insert_id(cursor) if mysql_enabled() else cursor.lastrowid
