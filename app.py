import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, current_app, flash, g, redirect, render_template, request, url_for

from services import buscar_endereco_por_cep, geocodificar_endereco


TIMEZONE = ZoneInfo("America/Sao_Paulo")
PALAVRAS_PROIBIDAS = ("idiota", "burro", "lixo")
CATEGORIAS = [
    ("BURACO", "Buraco"),
    ("LIXO", "Lixo"),
    ("ILUMINACAO", "Iluminacao"),
    ("OUTRO", "Outro"),
]
STATUS_CHOICES = [
    ("PROBLEMA", "Problema"),
    ("PENDENTE", "Pendente"),
    ("RESOLVIDO", "Resolvido"),
]
CATEGORIA_LABELS = dict(CATEGORIAS)
STATUS_LABELS = dict(STATUS_CHOICES)
STATUS_CORES = {
    "PROBLEMA": "#d64545",
    "PENDENTE": "#d39b0d",
    "RESOLVIDO": "#2c8f4f",
}
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS chamados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cpf TEXT NOT NULL,
    nome TEXT DEFAULT '',
    email TEXT DEFAULT '',
    categoria TEXT NOT NULL,
    cep TEXT DEFAULT '',
    rua TEXT DEFAULT '',
    bairro TEXT DEFAULT '',
    cidade TEXT DEFAULT '',
    numero TEXT DEFAULT '',
    descricao TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROBLEMA',
    latitude REAL,
    longitude REAL,
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comentarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chamado_id INTEGER NOT NULL,
    autor_nome TEXT DEFAULT '',
    texto TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    FOREIGN KEY (chamado_id) REFERENCES chamados (id) ON DELETE CASCADE
);
"""


def default_database_path() -> Path:
    base_dir = Path(__file__).resolve().parent
    db_dir = Path(os.environ.get("FIXCITY_DB_DIR", Path(os.environ.get("LOCALAPPDATA", base_dir)) / "FixCity"))
    db_dir.mkdir(parents=True, exist_ok=True)
    return Path(os.environ.get("FIXCITY_DB_NAME", db_dir / "fixcity.sqlite3"))


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


def pluralizar_comentario(total: int) -> str:
    return f"{total} comentario" if total == 1 else f"{total} comentarios"


def serialize_comment(row: sqlite3.Row) -> dict:
    autor_exibicao = (row["autor_nome"] or "").strip() or "morador.local"
    return {
        "id": row["id"],
        "autor_exibicao": autor_exibicao,
        "avatar_iniciais": avatar_iniciais(autor_exibicao),
        "texto": row["texto"],
        "tempo_relativo": tempo_relativo(row["criado_em"]),
    }


def serialize_call(row: sqlite3.Row, comments: list[dict]) -> dict:
    endereco = ", ".join(
        parte for parte in [row["rua"], row["numero"], row["bairro"], row["cidade"]] if parte
    ) or "Endereco nao informado"
    return {
        "id": row["id"],
        "cpf": row["cpf"],
        "nome": row["nome"] or "",
        "email": row["email"] or "",
        "categoria": row["categoria"],
        "categoria_label": CATEGORIA_LABELS.get(row["categoria"], row["categoria"]),
        "cep": row["cep"] or "",
        "rua": row["rua"] or "",
        "bairro": row["bairro"] or "",
        "cidade": row["cidade"] or "",
        "numero": row["numero"] or "",
        "descricao": row["descricao"],
        "status": row["status"],
        "status_label": STATUS_LABELS.get(row["status"], row["status"]),
        "status_css": row["status"].lower(),
        "status_color": STATUS_CORES.get(row["status"], "#5b6472"),
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "endereco_completo": endereco,
        "comentarios": comments,
        "comentarios_count": len(comments),
        "comentarios_label": pluralizar_comentario(len(comments)),
    }


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        SECRET_KEY=os.environ.get("FIXCITY_SECRET_KEY", "fixcity-flask-dev"),
        DATABASE=str(default_database_path()),
    )

    if test_config:
        app.config.update(test_config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    @app.teardown_appcontext
    def close_db(_error=None):
        database = g.pop("db", None)
        if database is not None:
            database.close()

    @app.route("/")
    def home():
        chamados = listar_chamados()
        stats = calcular_stats(chamados)
        map_data = [
            {
                "id": chamado["id"],
                "categoria": chamado["categoria_label"],
                "descricao": chamado["descricao"],
                "endereco": chamado["endereco_completo"],
                "status": chamado["status_label"],
                "status_color": chamado["status_color"],
                "latitude": chamado["latitude"],
                "longitude": chamado["longitude"],
                "comentarios": [
                    f'{comentario["autor_exibicao"]}: {comentario["texto"]}'
                    for comentario in chamado["comentarios"]
                ],
            }
            for chamado in chamados
            if chamado["latitude"] is not None and chamado["longitude"] is not None
        ]
        return render_template("fixcity/index.html", chamados=chamados, stats=stats, map_data=map_data)

    @app.route("/login/")
    def login():
        return render_template("fixcity/login.html")

    @app.route("/cadastro/")
    def cadastro():
        return render_template("fixcity/cadastro.html")

    @app.route("/denuncias/", methods=["GET", "POST"])
    def denuncias():
        form_data = form_defaults()
        errors = {}

        if request.method == "POST":
            form_data = normalizar_formulario(request.form)
            errors = validar_chamado(form_data)

            if not errors:
                enriquecer_endereco(form_data)
                latitude, longitude = geocodificar_endereco(endereco_completo(form_data))
                form_data["latitude"] = latitude
                form_data["longitude"] = longitude
                salvar_chamado(form_data)
                flash("Chamado registrado com sucesso.", "success")
                return redirect(url_for("denuncias"))

            flash("Revise os campos destacados e tente novamente.", "error")

        chamados = listar_chamados()
        return render_template(
            "fixcity/denuncias.html",
            chamados=chamados,
            status_choices=STATUS_CHOICES,
            category_choices=CATEGORIAS,
            form_data=form_data,
            errors=errors,
        )

    @app.post("/denuncias/<int:pk>/status/")
    def atualizar_status(pk: int):
        status = (request.form.get("status") or "").strip().upper()
        if status not in STATUS_LABELS:
            flash("Nao foi possivel atualizar o status.", "error")
            return redirect(url_for("denuncias"))

        db = get_db()
        db.execute("UPDATE chamados SET status = ?, atualizado_em = ? WHERE id = ?", (status, agora_iso(), pk))
        db.commit()
        flash("Status atualizado.", "success")
        return redirect(url_for("denuncias"))

    @app.post("/denuncias/<int:pk>/comentarios/")
    def adicionar_comentario(pk: int):
        autor_nome = (request.form.get("autor_nome") or "").strip()
        texto = (request.form.get("texto") or "").strip()

        if not texto:
            flash("Escreva um comentario valido antes de enviar.", "error")
            return redirect(url_for("denuncias"))

        db = get_db()
        db.execute(
            "INSERT INTO comentarios (chamado_id, autor_nome, texto, criado_em) VALUES (?, ?, ?, ?)",
            (pk, autor_nome, texto, agora_iso()),
        )
        db.commit()
        flash("Comentario adicionado.", "success")
        return redirect(url_for("denuncias"))

    return app


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.executescript(SCHEMA_SQL)
        g.db.commit()
    return g.db


def init_db():
    db = get_db()
    db.executescript(SCHEMA_SQL)
    db.commit()


def form_defaults() -> dict:
    return {
        "cpf": "",
        "nome": "",
        "email": "",
        "categoria": "",
        "cep": "",
        "rua": "",
        "bairro": "",
        "cidade": "",
        "numero": "",
        "descricao": "",
    }


def normalizar_formulario(form) -> dict:
    data = form_defaults()
    for field in data:
        data[field] = (form.get(field) or "").strip()
    data["cpf"] = re.sub(r"\D", "", data["cpf"])
    data["cep"] = re.sub(r"\D", "", data["cep"])
    data["categoria"] = data["categoria"].upper()
    return data


def validar_chamado(data: dict) -> dict:
    errors = {}

    if not cpf_valido(data["cpf"]):
        errors["cpf"] = "Informe um CPF valido."
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


def endereco_completo(data: dict) -> str:
    partes = [data["rua"], data["numero"], data["bairro"], data["cidade"]]
    return ", ".join(parte for parte in partes if parte)


def salvar_chamado(data: dict):
    agora = agora_iso()
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
            data["cpf"],
            data["nome"],
            data["email"],
            data["categoria"],
            data["cep"],
            data["rua"],
            data["bairro"],
            data["cidade"],
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


def listar_chamados() -> list[dict]:
    db = get_db()
    chamados_rows = db.execute("SELECT * FROM chamados ORDER BY criado_em DESC").fetchall()
    comentarios_rows = db.execute("SELECT * FROM comentarios ORDER BY criado_em ASC").fetchall()
    comentarios_por_chamado: dict[int, list[dict]] = {}

    for comentario in comentarios_rows:
        comentarios_por_chamado.setdefault(comentario["chamado_id"], []).append(serialize_comment(comentario))

    return [serialize_call(row, comentarios_por_chamado.get(row["id"], [])) for row in chamados_rows]


def calcular_stats(chamados: list[dict]) -> dict:
    return {
        "total": len(chamados),
        "problemas": sum(1 for chamado in chamados if chamado["status"] == "PROBLEMA"),
        "pendentes": sum(1 for chamado in chamados if chamado["status"] == "PENDENTE"),
        "resolvidos": sum(1 for chamado in chamados if chamado["status"] == "RESOLVIDO"),
    }


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
