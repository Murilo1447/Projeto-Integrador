import re
import unicodedata
from typing import Any, Mapping

from services import buscar_endereco_por_cep, geocodificar_endereco

from ..config import CATEGORIA_LABELS, PALAVRAS_PROIBIDAS, STATUS_CHOICES, STATUS_CORES, STATUS_LABELS
from ..db import get_db, mysql_enabled, mysql_insert_id
from ..utils import agora_iso, avatar_payload, cpf_valido, mapping_get, tempo_relativo, user_is_admin
from .auth_service import buscar_usuario_por_id

BRAZIL_STATE_REGIONS = {
    "AC": "Norte",
    "AL": "Nordeste",
    "AP": "Norte",
    "AM": "Norte",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "DF": "Centro-Oeste",
    "ES": "Sudeste",
    "GO": "Centro-Oeste",
    "MA": "Nordeste",
    "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "MG": "Sudeste",
    "PA": "Norte",
    "PB": "Nordeste",
    "PR": "Sul",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RJ": "Sudeste",
    "RN": "Nordeste",
    "RS": "Sul",
    "RO": "Norte",
    "RR": "Norte",
    "SC": "Sul",
    "SP": "Sudeste",
    "SE": "Nordeste",
    "TO": "Norte",
}

LOCATION_FILTER_CHOICES = [
    ("all", "Todos os campos"),
    ("regiao", "Regiao"),
    ("estado", "Estado"),
    ("cidade", "Cidade"),
    ("bairro", "Bairro"),
    ("pais", "Pais"),
    ("cep", "CEP"),
    ("endereco", "Endereco"),
]
LOCATION_FILTER_LABELS = dict(LOCATION_FILTER_CHOICES)


def pluralizar_comentario(total: int) -> str:
    return f"{total} comentario" if total == 1 else f"{total} comentarios"


def pluralizar_apoio(total: int) -> str:
    return f"{total} apoio" if total == 1 else f"{total} apoios"


def serialize_comment(row: Mapping[str, Any]) -> dict:
    autor_exibicao = (row["autor_nome"] or "").strip() or "morador.local"
    return {
        "id": row["id"],
        "autor_exibicao": autor_exibicao,
        "texto": row["texto"],
        "tempo_relativo": tempo_relativo(row["criado_em"]),
        **avatar_payload(autor_exibicao, mapping_get(row, "autor_foto", "")),
    }


def serialize_call(row: Mapping[str, Any], comments: list[dict], vote_info: Mapping[str, Any] | None = None) -> dict:
    autor_exibicao = (row["nome"] or "").strip() or "morador.local"
    endereco = ", ".join(
        parte for parte in [row["rua"], row["numero"], row["bairro"], row["cidade"]] if parte
    ) or "Endereco nao informado"
    localizacao_parts = [row["bairro"], row["cidade"], row["estado"], row["pais"]]
    localizacao_resumida = " - ".join(
        parte
        for parte in [
            ", ".join(parte for parte in localizacao_parts[:2] if parte),
            ", ".join(parte for parte in localizacao_parts[2:] if parte),
        ]
        if parte
    )
    upvotes_count = int(mapping_get(vote_info, "total", 0) or 0)
    has_upvoted = bool(mapping_get(vote_info, "has_upvoted", 0))
    return {
        "id": row["id"],
        "owner_user_id": mapping_get(row, "id_usuario"),
        "cpf": row["cpf"],
        "nome": row["nome"] or "",
        "email": row["email"] or "",
        "autor_exibicao": autor_exibicao,
        "categoria": row["categoria"],
        "categoria_label": CATEGORIA_LABELS.get(row["categoria"], row["categoria"]),
        "cep": row["cep"] or "",
        "rua": row["rua"] or "",
        "bairro": row["bairro"] or "",
        "cidade": row["cidade"] or "",
        "estado": row["estado"] or "",
        "pais": row["pais"] or "",
        "regiao": row["regiao"] or "",
        "numero": row["numero"] or "",
        "descricao": row["descricao"],
        "status": row["status"],
        "status_label": STATUS_LABELS.get(row["status"], row["status"]),
        "status_css": row["status"].lower(),
        "status_color": STATUS_CORES.get(row["status"], "#5b6472"),
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "tempo_relativo": tempo_relativo(row["criado_em"]),
        "endereco_completo": endereco,
        "localizacao_resumida": localizacao_resumida,
        "coordinates_available": row["latitude"] is not None and row["longitude"] is not None,
        "comentarios": comments,
        "comentarios_count": len(comments),
        "comentarios_label": pluralizar_comentario(len(comments)),
        "upvotes_count": upvotes_count,
        "upvotes_label": pluralizar_apoio(upvotes_count),
        "has_upvoted": has_upvoted,
        **avatar_payload(autor_exibicao, mapping_get(row, "foto_perfil", "")),
    }


def form_defaults(user=None) -> dict:
    user = user or None
    return {
        "cpf": user["cpf"] if user else "",
        "nome": user["nome"] if user else "",
        "email": user["email"] if user else "",
        "categoria": "",
        "cep": "",
        "rua": "",
        "bairro": "",
        "cidade": "",
        "estado": "",
        "pais": "",
        "regiao": "",
        "numero": "",
        "descricao": "",
    }


def normalizar_formulario(form, user=None) -> dict:
    data = form_defaults(user)
    for field in ("categoria", "cep", "rua", "bairro", "cidade", "numero", "descricao"):
        data[field] = (form.get(field) or "").strip()
    data["cep"] = re.sub(r"\D", "", data["cep"])
    data["categoria"] = data["categoria"].upper()
    return data


def validar_chamado(data: dict) -> dict:
    errors = {}

    if not cpf_valido(data["cpf"]):
        errors["cpf"] = "Seu perfil precisa ter um CPF valido para abrir chamados."
    if data["categoria"] not in CATEGORIA_LABELS:
        errors["categoria"] = "Selecione uma categoria valida."
    if not data["descricao"]:
        errors["descricao"] = "Descreva o problema encontrado."
    if any(palavra in data["descricao"].lower() for palavra in PALAVRAS_PROIBIDAS):
        errors["descricao"] = "A descricao contem linguagem inadequada."
    if data["cep"] and len(data["cep"]) != 8:
        errors["cep"] = "Informe um CEP com 8 digitos."
    if data["email"] and "@" not in data["email"]:
        errors["email"] = "Informe um e-mail valido."

    return errors


def enriquecer_endereco(data: dict):
    if data["cep"] and (not data["rua"] or not data["bairro"] or not data["cidade"]):
        endereco = buscar_endereco_por_cep(data["cep"])
        if endereco:
            data["rua"] = data["rua"] or endereco["rua"]
            data["bairro"] = data["bairro"] or endereco["bairro"]
            data["cidade"] = data["cidade"] or endereco["cidade"]
            data["estado"] = data["estado"] or endereco["estado"]


def inferir_regiao_por_estado(estado: str) -> str:
    return BRAZIL_STATE_REGIONS.get((estado or "").strip().upper(), "")


def normalizar_localizacao(data: dict):
    data["estado"] = (data.get("estado") or "").strip().upper()
    data["pais"] = (data.get("pais") or "").strip()
    data["regiao"] = (data.get("regiao") or "").strip()

    if data["estado"] and not data["regiao"]:
        data["regiao"] = inferir_regiao_por_estado(data["estado"])

    if data["estado"] and not data["pais"]:
        data["pais"] = "Brasil"


def normalizar_texto_busca(value: str) -> str:
    texto = unicodedata.normalize("NFKD", (value or "").strip().lower())
    return "".join(char for char in texto if not unicodedata.combining(char))


def filtro_localizacao_defaults() -> dict:
    return {
        "campo": "all",
        "campo_label": LOCATION_FILTER_LABELS["all"],
        "busca": "",
        "ativo": False,
        "descricao": "",
    }


def construir_filtro_localizacao(campo: str | None = None, busca: str | None = None) -> dict:
    normalized_field = (campo or "all").strip().lower()
    if normalized_field not in LOCATION_FILTER_LABELS:
        normalized_field = "all"

    normalized_query = (busca or "").strip()
    filtro = {
        "campo": normalized_field,
        "campo_label": LOCATION_FILTER_LABELS[normalized_field],
        "busca": normalized_query,
        "ativo": bool(normalized_query),
        "descricao": "",
    }
    if filtro["ativo"]:
        filtro["descricao"] = f'{filtro["campo_label"]}: "{normalized_query}"'
    return filtro


def filtrar_chamados_por_localizacao(chamados: list[dict], filtro: dict) -> list[dict]:
    if not filtro.get("ativo"):
        return chamados

    field = filtro["campo"]
    query = normalizar_texto_busca(filtro["busca"])

    def searchable_values(chamado: dict) -> list[str]:
        if field == "all":
            return [
                chamado["regiao"],
                chamado["cidade"],
                chamado["estado"],
                chamado["pais"],
                chamado["bairro"],
                chamado["cep"],
                chamado["rua"],
                chamado["endereco_completo"],
            ]
        if field == "endereco":
            return [chamado["endereco_completo"], chamado["rua"], chamado["bairro"], chamado["cidade"]]
        return [chamado.get(field, "")]

    return [
        chamado
        for chamado in chamados
        if any(query in normalizar_texto_busca(value) for value in searchable_values(chamado) if value)
    ]


def endereco_completo(data: dict) -> str:
    partes = [data["rua"], data["numero"], data["bairro"], data["cidade"]]
    return ", ".join(parte for parte in partes if parte)


def preparar_localizacao(data: dict):
    enriquecer_endereco(data)
    normalizar_localizacao(data)
    latitude, longitude = geocodificar_endereco(endereco_completo(data))
    data["latitude"] = latitude
    data["longitude"] = longitude


def salvar_chamado(data: dict, user):
    agora = agora_iso()
    db = get_db()
    if mysql_enabled():
        endereco_cursor = db.execute(
            """
            INSERT INTO endereco (cidade, bairro, nome_rua, cep, estado, pais, regiao, numero, referencia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["cidade"] or "",
                data["bairro"] or "",
                data["rua"] or "",
                data["cep"] or "",
                data["estado"] or "",
                data["pais"] or "",
                data["regiao"] or "",
                data["numero"] or "",
                "",
            ),
        )
        id_endereco = mysql_insert_id(endereco_cursor)

        db.execute(
            """
            INSERT INTO denuncias (
                id_usuario, id_endereco, cpf, nome_usuario, email_usuario, categoria,
                data_denuncia, descricao, status, latitude, longitude, atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id_usuario"],
                id_endereco,
                data["cpf"],
                data["nome"],
                data["email"],
                data["categoria"],
                agora,
                data["descricao"],
                "PROBLEMA",
                float(data["latitude"]) if data.get("latitude") is not None else None,
                float(data["longitude"]) if data.get("longitude") is not None else None,
                agora,
            ),
        )
    else:
        db.execute(
            """
            INSERT INTO chamados (
                id_usuario, cpf, nome, email, categoria, cep, rua, bairro, cidade, estado, pais, regiao, numero,
                descricao, status, latitude, longitude, criado_em, atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id_usuario"],
                data["cpf"],
                data["nome"],
                data["email"],
                data["categoria"],
                data["cep"],
                data["rua"],
                data["bairro"],
                data["cidade"],
                data["estado"],
                data["pais"],
                data["regiao"],
                data["numero"],
                data["descricao"],
                "PROBLEMA",
                float(data["latitude"]) if data.get("latitude") is not None else None,
                float(data["longitude"]) if data.get("longitude") is not None else None,
                agora,
                agora,
            ),
        )
    db.commit()


def atualizar_status_chamado(pk: int, status: str):
    db = get_db()
    if mysql_enabled():
        db.execute(
            "UPDATE denuncias SET status = ?, atualizado_em = ? WHERE id_denuncia = ?",
            (status, agora_iso(), pk),
        )
    else:
        db.execute("UPDATE chamados SET status = ?, atualizado_em = ? WHERE id = ?", (status, agora_iso(), pk))
    db.commit()


def usuario_pode_atualizar_status(pk: int, user) -> bool:
    user_id = mapping_get(user, "id_usuario")
    if not user_id:
        return False

    if user_is_admin(user):
        return True

    db = get_db()
    if mysql_enabled():
        row = db.execute("SELECT id_usuario FROM denuncias WHERE id_denuncia = ?", (pk,)).fetchone()
    else:
        row = db.execute("SELECT id_usuario FROM chamados WHERE id = ?", (pk,)).fetchone()

    return mapping_get(row, "id_usuario") == user_id


def adicionar_comentario(pk: int, texto: str, user):
    db = get_db()
    if mysql_enabled():
        db.execute(
            """
            INSERT INTO comentarios (id_usuario, id_denuncia, nome_usuario, comentario, criado_em)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user["id_usuario"], pk, user["nome"], texto, agora_iso()),
        )
    else:
        db.execute(
            """
            INSERT INTO comentarios (id_usuario, chamado_id, autor_nome, texto, criado_em)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user["id_usuario"], pk, user["nome"], texto, agora_iso()),
        )
    db.commit()


def buscar_resumo_upvotes(viewer_user_id: int | None = None) -> dict[int, dict]:
    db = get_db()
    params = (viewer_user_id,)
    if mysql_enabled():
        rows = db.execute(
            """
            SELECT
                id_denuncia AS chamado_id,
                COUNT(*) AS total,
                MAX(CASE WHEN id_usuario = ? THEN 1 ELSE 0 END) AS has_upvoted
            FROM upvotes_denuncia
            GROUP BY id_denuncia
            """,
            params,
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT
                chamado_id,
                COUNT(*) AS total,
                MAX(CASE WHEN id_usuario = ? THEN 1 ELSE 0 END) AS has_upvoted
            FROM upvotes_chamado
            GROUP BY chamado_id
            """,
            params,
        ).fetchall()

    return {
        row["chamado_id"]: {
            "total": int(row["total"] or 0),
            "has_upvoted": int(row["has_upvoted"] or 0),
        }
        for row in rows
    }


def _chamado_existe(pk: int) -> bool:
    db = get_db()
    if mysql_enabled():
        row = db.execute("SELECT 1 FROM denuncias WHERE id_denuncia = ?", (pk,)).fetchone()
    else:
        row = db.execute("SELECT 1 FROM chamados WHERE id = ?", (pk,)).fetchone()
    return row is not None


def alternar_upvote(pk: int, user) -> bool | None:
    user_id = mapping_get(user, "id_usuario")
    if not user or not user_id or not _chamado_existe(pk):
        return None

    db = get_db()
    params = (user_id, pk)
    if mysql_enabled():
        existing = db.execute(
            "SELECT id_upvote FROM upvotes_denuncia WHERE id_usuario = ? AND id_denuncia = ?",
            params,
        ).fetchone()
        if existing:
            db.execute("DELETE FROM upvotes_denuncia WHERE id_usuario = ? AND id_denuncia = ?", params)
            db.commit()
            return False

        db.execute(
            """
            INSERT INTO upvotes_denuncia (id_usuario, id_denuncia, criado_em)
            VALUES (?, ?, ?)
            """,
            (user_id, pk, agora_iso()),
        )
    else:
        existing = db.execute(
            "SELECT id FROM upvotes_chamado WHERE id_usuario = ? AND chamado_id = ?",
            params,
        ).fetchone()
        if existing:
            db.execute("DELETE FROM upvotes_chamado WHERE id_usuario = ? AND chamado_id = ?", params)
            db.commit()
            return False

        db.execute(
            """
            INSERT INTO upvotes_chamado (id_usuario, chamado_id, criado_em)
            VALUES (?, ?, ?)
            """,
            (user_id, pk, agora_iso()),
        )

    db.commit()
    return True


def listar_chamados(viewer_user_id: int | None = None, sort_mode: str = "recent") -> list[dict]:
    db = get_db()
    if mysql_enabled():
        chamados_rows = db.execute(
            """
            SELECT
                d.id_denuncia AS id,
                d.id_usuario,
                d.cpf,
                COALESCE(u.nome, d.nome_usuario) AS nome,
                COALESCE(u.email, d.email_usuario) AS email,
                u.foto_perfil,
                d.categoria,
                e.cep,
                e.nome_rua AS rua,
                e.bairro,
                e.cidade,
                e.estado,
                e.pais,
                e.regiao,
                e.numero,
                d.descricao,
                d.status,
                d.latitude,
                d.longitude,
                d.data_denuncia AS criado_em,
                d.atualizado_em
            FROM denuncias d
            INNER JOIN endereco e ON e.id_endereco = d.id_endereco
            LEFT JOIN usuarios u ON u.id_usuario = d.id_usuario
            ORDER BY d.data_denuncia DESC
            """
        ).fetchall()
        comentarios_rows = db.execute(
            """
            SELECT
                c.id_comentario AS id,
                c.id_denuncia AS chamado_id,
                COALESCE(u.nome, c.nome_usuario) AS autor_nome,
                c.comentario AS texto,
                c.criado_em,
                u.foto_perfil AS autor_foto
            FROM comentarios c
            LEFT JOIN usuarios u ON u.id_usuario = c.id_usuario
            ORDER BY c.criado_em ASC
            """
        ).fetchall()
    else:
        chamados_rows = db.execute(
            """
            SELECT
                c.*,
                u.foto_perfil
            FROM chamados c
            LEFT JOIN usuarios u ON u.id_usuario = c.id_usuario
            ORDER BY c.criado_em DESC
            """
        ).fetchall()
        comentarios_rows = db.execute(
            """
            SELECT
                cm.id,
                cm.chamado_id,
                COALESCE(u.nome, cm.autor_nome) AS autor_nome,
                cm.texto,
                cm.criado_em,
                u.foto_perfil AS autor_foto
            FROM comentarios cm
            LEFT JOIN usuarios u ON u.id_usuario = cm.id_usuario
            ORDER BY cm.criado_em ASC
            """
        ).fetchall()

    comentarios_por_chamado: dict[int, list[dict]] = {}
    for comentario in comentarios_rows:
        comentarios_por_chamado.setdefault(comentario["chamado_id"], []).append(serialize_comment(comentario))

    votos_por_chamado = buscar_resumo_upvotes(viewer_user_id)
    chamados = [
        serialize_call(row, comentarios_por_chamado.get(row["id"], []), votos_por_chamado.get(row["id"]))
        for row in chamados_rows
    ]

    if sort_mode == "social":
        chamados.sort(key=lambda chamado: (chamado["upvotes_count"], chamado["comentarios_count"], chamado["id"]), reverse=True)

    return chamados


def calcular_stats(chamados: list[dict]) -> dict:
    return {
        "total": len(chamados),
        "problemas": sum(1 for chamado in chamados if chamado["status"] == "PROBLEMA"),
        "pendentes": sum(1 for chamado in chamados if chamado["status"] == "PENDENTE"),
        "resolvidos": sum(1 for chamado in chamados if chamado["status"] == "RESOLVIDO"),
    }
