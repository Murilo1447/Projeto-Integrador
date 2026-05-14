import re
from datetime import datetime

from flask import g, request, url_for

from .config import ALLOWED_IMAGE_EXTENSIONS, TIMEZONE


def agora_iso() -> str:
    return datetime.now(TIMEZONE).isoformat()


def cpf_valido(cpf: str) -> bool:
    numeros = re.sub(r"\D", "", cpf or "")
    if len(numeros) != 11 or len(set(numeros)) == 1:
        return False

    for tamanho in (9, 10):
        soma = sum(int(digito) * peso for digito, peso in zip(numeros[:tamanho], range(tamanho + 1, 1, -1)))
        resto = (soma * 10) % 11
        digito_esperado = 0 if resto == 10 else resto
        if digito_esperado != int(numeros[tamanho]):
            return False

    return True


def telefone_valido(telefone: str) -> bool:
    return 10 <= len(re.sub(r"\D", "", telefone or "")) <= 11


def avatar_iniciais(nome: str) -> str:
    partes = [parte for parte in nome.replace(".", " ").split() if parte]
    if not partes:
        return "ML"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return f"{partes[0][0]}{partes[1][0]}".upper()


def tempo_relativo(data_iso: str) -> str:
    criado_em = datetime.fromisoformat(data_iso)
    delta = datetime.now(TIMEZONE) - criado_em
    segundos = int(delta.total_seconds())

    if segundos < 60:
        return "agora"
    if segundos < 3600:
        return f"{segundos // 60} min"
    if segundos < 86400:
        return f"{segundos // 3600} h"

    dias = segundos // 86400
    if dias < 30:
        return f"{dias} d"

    meses = dias // 30
    if meses < 12:
        return f"{meses} mes"

    return f"{meses // 12} ano"


def mapping_get(row, key: str, default=None):
    if hasattr(row, "keys") and key in row.keys():
        return row[key]
    if isinstance(row, dict):
        return row.get(key, default)
    return default


def image_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def imagem_permitida(filename: str) -> bool:
    return image_extension(filename) in ALLOWED_IMAGE_EXTENSIONS


def avatar_payload(nome: str, foto_perfil: str) -> dict:
    relative_path = (foto_perfil or "").strip().replace("\\", "/")
    return {
        "avatar_url": url_for("static", filename=relative_path) if relative_path else "",
        "avatar_iniciais": avatar_iniciais(nome),
    }


def normalize_next_url(target: str | None) -> str:
    if not target or not target.startswith("/"):
        return url_for("home")
    return target


def current_user():
    return g.get("user")


def user_is_admin(user) -> bool:
    return bool(mapping_get(user, "is_admin", 0))


def login_redirect_target():
    return request.full_path if request.query_string else request.path
