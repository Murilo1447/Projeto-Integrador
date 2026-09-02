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
        SELECT id_usuario, nome, email, senha, telefone, cpf, is_admin, is_superuser, is_private, foto_perfil, foto_perfil_blob, foto_perfil_mime
        FROM usuarios
        WHERE id_usuario = ?
    """
    return get_db().execute(query, (user_id,)).fetchone()


def buscar_usuario_por_email(email: str):
    if not email:
        return None

    query = """
        SELECT id_usuario, nome, email, senha, telefone, cpf, is_admin, is_superuser, is_private, foto_perfil, foto_perfil_blob, foto_perfil_mime
        FROM usuarios
        WHERE email = ?
    """
    return get_db().execute(query, (email,)).fetchone()


def buscar_usuario_por_cpf(cpf: str):
    if not cpf:
        return None

    query = """
        SELECT id_usuario, nome, email, senha, telefone, cpf, is_admin, is_superuser, is_private, foto_perfil, foto_perfil_blob, foto_perfil_mime
        FROM usuarios
        WHERE cpf = ?
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
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
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


def tornar_usuario_admin(email: str) -> bool:
    usuario = buscar_usuario_por_email(email.strip().lower())
    if not usuario:
        return False

    db = get_db()
    db.execute(
        "UPDATE usuarios SET is_admin = 1 WHERE id_usuario = ?",
        (usuario["id_usuario"],),
    )
    db.commit()
    return True


def tornar_usuario_superuser(email: str) -> bool:
    usuario = buscar_usuario_por_email(email.strip().lower())
    if not usuario:
        return False

    db = get_db()
    db.execute(
        "UPDATE usuarios SET is_admin = 1, is_superuser = 1 WHERE id_usuario = ?",
        (usuario["id_usuario"],),
    )
    db.commit()
    return True


def listar_usuarios_painel() -> list[dict]:
    rows = get_db().execute(
        """
        SELECT
            id_usuario,
            nome,
            email,
            telefone,
            cpf,
            is_admin,
            is_superuser,
            is_private,
            criado_em
        FROM usuarios
        ORDER BY id_usuario ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def atualizar_nivel_usuario(user_id: int, nivel: str, ator_user_id: int) -> str:
    niveis = {
        "usuario": (0, 0),
        "admin": (1, 0),
        "superuser": (1, 1),
    }
    if nivel not in niveis:
        return "nivel_invalido"
    if user_id == ator_user_id:
        return "propria_conta"

    db = get_db()
    if not db.execute(
        "SELECT 1 FROM usuarios WHERE id_usuario = ?",
        (user_id,),
    ).fetchone():
        return "nao_encontrado"

    is_admin, is_superuser = niveis[nivel]
    db.execute(
        """
        UPDATE usuarios
        SET is_admin = ?, is_superuser = ?
        WHERE id_usuario = ?
        """,
        (is_admin, is_superuser, user_id),
    )
    db.commit()
    return "atualizado"


def excluir_usuario(user_id: int, ator_user_id: int) -> str:
    if user_id == ator_user_id:
        return "propria_conta"

    db = get_db()
    if not db.execute(
        "SELECT 1 FROM usuarios WHERE id_usuario = ?",
        (user_id,),
    ).fetchone():
        return "nao_encontrado"

    db.execute("DELETE FROM usuarios WHERE id_usuario = ?", (user_id,))
    db.commit()
    return "excluido"


def alternar_privacidade_usuario(user_id: int) -> bool | None:
    db = get_db()
    row = db.execute(
        "SELECT is_private FROM usuarios WHERE id_usuario = ?",
        (user_id,),
    ).fetchone()
    if not row:
        return None

    novo_status = not bool(row["is_private"])
    db.execute(
        "UPDATE usuarios SET is_private = ? WHERE id_usuario = ?",
        (int(novo_status), user_id),
    )
    db.commit()

    return novo_status
