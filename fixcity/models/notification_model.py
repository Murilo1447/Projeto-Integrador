from ..db import get_db, mysql_enabled, mysql_insert_id
from ..utils import agora_iso, mapping_get


def criar_notificacao(
    destinatario_usuario_id: int,
    tipo: str,
    titulo: str,
    mensagem: str,
    ator_usuario_id: int | None = None,
    chamado_id: int | None = None,
):
    if not destinatario_usuario_id:
        return None

    db = get_db()
    if mysql_enabled():
        cursor = db.execute(
            """
            INSERT INTO notificacoes (
                destinatario_usuario_id, ator_usuario_id, id_denuncia, tipo, titulo, mensagem, lida, criado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (destinatario_usuario_id, ator_usuario_id, chamado_id, tipo, titulo, mensagem, agora_iso()),
        )
        db.commit()
        return mysql_insert_id(cursor)

    cursor = db.execute(
        """
        INSERT INTO notificacoes (
            destinatario_usuario_id, ator_usuario_id, chamado_id, tipo, titulo, mensagem, lida, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (destinatario_usuario_id, ator_usuario_id, chamado_id, tipo, titulo, mensagem, agora_iso()),
    )
    db.commit()
    return cursor.lastrowid


def listar_notificacoes_usuario(user_id: int, limit: int = 8) -> list[dict]:
    if not user_id:
        return []

    db = get_db()
    params = (user_id, limit)
    if mysql_enabled():
        rows = db.execute(
            """
            SELECT
                n.id_notificacao AS id,
                n.id_denuncia AS chamado_id,
                n.tipo,
                n.titulo,
                n.mensagem,
                n.lida,
                n.criado_em,
                u.nome AS ator_nome
            FROM notificacoes n
            LEFT JOIN usuarios u ON u.id_usuario = n.ator_usuario_id
            WHERE n.destinatario_usuario_id = ?
            ORDER BY n.criado_em DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT
                n.id,
                n.chamado_id,
                n.tipo,
                n.titulo,
                n.mensagem,
                n.lida,
                n.criado_em,
                u.nome AS ator_nome
            FROM notificacoes n
            LEFT JOIN usuarios u ON u.id_usuario = n.ator_usuario_id
            WHERE n.destinatario_usuario_id = ?
            ORDER BY n.criado_em DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

    return [
        {
            "id": row["id"],
            "chamado_id": mapping_get(row, "chamado_id"),
            "tipo": row["tipo"],
            "titulo": row["titulo"],
            "mensagem": row["mensagem"],
            "lida": bool(row["lida"]),
            "criado_em": row["criado_em"],
            "ator_nome": mapping_get(row, "ator_nome", ""),
        }
        for row in rows
    ]


def contar_notificacoes_nao_lidas(user_id: int) -> int:
    if not user_id:
        return 0

    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) AS total FROM notificacoes WHERE destinatario_usuario_id = ? AND lida = 0",
        (user_id,),
    ).fetchone()
    return int(row["total"] or 0) if row else 0


def marcar_notificacoes_como_lidas(user_id: int):
    if not user_id:
        return

    db = get_db()
    db.execute("UPDATE notificacoes SET lida = 1 WHERE destinatario_usuario_id = ?", (user_id,))
    db.commit()
