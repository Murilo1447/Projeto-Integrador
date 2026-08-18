import re
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import get_db, mysql_enabled, mysql_insert_id
from ..utils import (
    agora_iso,
    cpf_valido,
    imagem_permitida,
    ler_upload_imagem_blob,
    telefone_valido,
)


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

    query = """
        SELECT id_usuario, nome, email, senha, telefone, cpf, is_admin, is_private, foto_perfil, foto_perfil_blob, foto_perfil_mime
        FROM usuarios
        WHERE id_usuario = %s
    """
    return get_db().execute(query, (user_id,)).fetchone()


def buscar_usuario_por_email(email: str):
    if not email:
        return None

    query = """
        SELECT id_usuario, nome, email, senha, telefone, cpf, is_admin, is_private, foto_perfil, foto_perfil_blob, foto_perfil_mime
        FROM usuarios
        WHERE email = %s
    """
    return get_db().execute(query, (email,)).fetchone()


def buscar_usuario_por_cpf(cpf: str):
    if not cpf:
        return None

    query = """
        SELECT id_usuario, nome, email, senha, telefone, cpf, is_admin, is_private, foto_perfil, foto_perfil_blob, foto_perfil_mime
        FROM usuarios
        WHERE cpf = %s
    """
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


def salvar_foto_perfil(foto) -> tuple[bytes | None, str]:
    return ler_upload_imagem_blob(foto)


def criar_usuario(data: dict, foto_blob: bytes | None, foto_mime: str) -> int:
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO usuarios (nome, email, senha, telefone, cpf, is_private, foto_perfil, foto_perfil_blob, foto_perfil_mime, criado_em)
        VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s, %s)
        """,
        (
            data["nome"],
            data["email"],
            generate_password_hash(data["senha"]),
            data["telefone"],
            data["cpf"],
            "",
            foto_blob,
            foto_mime,
            agora_iso(),
        ),
    )
    if hasattr(db, "commit"):
        db.commit()
    return mysql_insert_id(cursor) if mysql_enabled() else cursor.lastrowid

def alternar_privacidade_usuario(user_id: int) -> bool:
    """Alterna o status de privacidade do usuário entre público e privado."""
    db = get_db()

    # 1. Busca o status atual garantindo o tipo bool
    row = db.execute(
        "SELECT is_private FROM usuarios WHERE id_usuario = %s",
        (user_id,)
    ).fetchone()

    novo_status = True
    if row:
        # Pega o valor independente se row é dicionário ou tupla
        val = row["is_private"] if isinstance(row, dict) else row[0]
        # Inverte o valor (se era 1/True vira False, se era 0/False vira True)
        novo_status = not bool(val)

    # 2. Executa o UPDATE (converte bool para int 1/0 para compatibilidade total com MySQL/MariaDB)
    valor_banco = 1 if novo_status else 0
    db.execute(
        "UPDATE usuarios SET is_private = %s WHERE id_usuario = %s",
        (valor_banco, user_id)
    )

    # 3. Força o commit no driver interno se existir
    if hasattr(db, "conn") and hasattr(db.conn, "commit"):
        db.conn.commit()
    elif hasattr(db, "commit"):
        db.commit()

    return novo_status