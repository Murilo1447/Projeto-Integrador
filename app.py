import os
import re
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from flask import Flask, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from services import buscar_endereco_por_cep, geocodificar_endereco

try:
    import mysql.connector
except ImportError:
    mysql = None


load_dotenv()


TIMEZONE = ZoneInfo("America/Sao_Paulo")
PALAVRAS_PROIBIDAS = ("idiota", "burro", "lixo")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
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
SQLITE_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL,
        telefone TEXT NOT NULL,
        cpf TEXT NOT NULL UNIQUE,
        foto_perfil TEXT DEFAULT '',
        criado_em TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chamados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario INTEGER,
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
        atualizado_em TEXT NOT NULL,
        FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS comentarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario INTEGER,
        chamado_id INTEGER NOT NULL,
        autor_nome TEXT DEFAULT '',
        texto TEXT NOT NULL,
        criado_em TEXT NOT NULL,
        FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario) ON DELETE SET NULL,
        FOREIGN KEY (chamado_id) REFERENCES chamados (id) ON DELETE CASCADE
    )
    """,
]

MYSQL_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id_usuario INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(150) NOT NULL,
        email VARCHAR(150) NOT NULL,
        senha VARCHAR(255) NOT NULL,
        telefone VARCHAR(20) NOT NULL,
        cpf VARCHAR(14) NOT NULL,
        foto_perfil VARCHAR(255) DEFAULT '',
        criado_em VARCHAR(40) NOT NULL,
        CONSTRAINT uq_usuarios_email UNIQUE (email),
        CONSTRAINT uq_usuarios_cpf UNIQUE (cpf)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS endereco (
        id_endereco INT AUTO_INCREMENT PRIMARY KEY,
        cidade VARCHAR(100) NOT NULL,
        bairro VARCHAR(100) DEFAULT '',
        nome_rua VARCHAR(100) NOT NULL,
        cep CHAR(8) DEFAULT '',
        estado VARCHAR(100) DEFAULT '',
        numero VARCHAR(30) DEFAULT '',
        referencia VARCHAR(1000) DEFAULT ''
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS denuncias (
        id_denuncia INT AUTO_INCREMENT PRIMARY KEY,
        id_usuario INT NULL,
        id_endereco INT NOT NULL,
        cpf VARCHAR(14) NOT NULL,
        nome_usuario VARCHAR(150) DEFAULT '',
        email_usuario VARCHAR(150) DEFAULT '',
        categoria VARCHAR(30) NOT NULL,
        data_denuncia VARCHAR(40) NOT NULL,
        descricao TEXT NOT NULL,
        status ENUM('PROBLEMA', 'PENDENTE', 'RESOLVIDO') NOT NULL DEFAULT 'PROBLEMA',
        latitude DOUBLE,
        longitude DOUBLE,
        atualizado_em VARCHAR(40) NOT NULL,
        CONSTRAINT fk_denuncias_usuario
            FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario)
            ON DELETE SET NULL,
        CONSTRAINT fk_denuncias_endereco
            FOREIGN KEY (id_endereco) REFERENCES endereco (id_endereco)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS comentarios (
        id_comentario INT AUTO_INCREMENT PRIMARY KEY,
        id_usuario INT NULL,
        id_denuncia INT NOT NULL,
        nome_usuario VARCHAR(150) DEFAULT '',
        comentario TEXT NOT NULL,
        criado_em VARCHAR(40) NOT NULL,
        CONSTRAINT fk_comentarios_usuario
            FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario)
            ON DELETE SET NULL,
        CONSTRAINT fk_comentarios_denuncia
            FOREIGN KEY (id_denuncia) REFERENCES denuncias (id_denuncia)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]


def default_database_path() -> Path:
    base_dir = Path(__file__).resolve().parent
    db_dir = Path(os.environ.get("FIXCITY_DB_DIR", Path(os.environ.get("LOCALAPPDATA", base_dir)) / "FixCity"))
    db_dir.mkdir(parents=True, exist_ok=True)
    return Path(os.environ.get("FIXCITY_DB_NAME", db_dir / "fixcity.sqlite3"))


class DatabaseConnection:
    def __init__(self, backend: str, connection):
        self.backend = backend
        self.connection = connection

    def execute(self, query: str, params=()):
        if self.backend == "mysql":
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query.replace("?", "%s"), params)
            return cursor

        return self.connection.execute(query, params)

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()

    def init_schema(self):
        statements = MYSQL_SCHEMA_STATEMENTS if self.backend == "mysql" else SQLITE_SCHEMA_STATEMENTS
        for statement in statements:
            self.execute(statement)
        self.commit()
        ensure_schema_compatibility(self)


def db_backend_from_config() -> str:
    return (current_app.config.get("DB_BACKEND") or "sqlite").strip().lower()


def sqlite_enabled() -> bool:
    return db_backend_from_config() == "sqlite"


def mysql_enabled() -> bool:
    return db_backend_from_config() == "mysql"


def connect_mysql() -> DatabaseConnection:
    if mysql is None:
        raise RuntimeError(
            "O suporte a MySQL nao esta instalado. Execute 'pip install -r requirements.txt' para usar o MySQL Workbench."
        )

    connection = mysql.connector.connect(
        host=current_app.config["MYSQL_HOST"],
        port=current_app.config["MYSQL_PORT"],
        user=current_app.config["MYSQL_USER"],
        password=current_app.config["MYSQL_PASSWORD"],
        database=current_app.config["MYSQL_DATABASE"],
        charset=current_app.config["MYSQL_CHARSET"],
    )
    return DatabaseConnection("mysql", connection)


def mysql_insert_id(cursor) -> int | None:
    return getattr(cursor, "lastrowid", None)


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


def mapping_get(row: Mapping[str, Any], key: str, default=None):
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


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("Faca login para continuar.", "error")
            return redirect(url_for("login", next=request.full_path if request.query_string else request.path))
        return view(*args, **kwargs)

    return wrapped_view


def guest_only(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is not None:
            return redirect(url_for("home"))
        return view(*args, **kwargs)

    return wrapped_view


def pluralizar_comentario(total: int) -> str:
    return f"{total} comentario" if total == 1 else f"{total} comentarios"


def serialize_comment(row: Mapping[str, Any]) -> dict:
    autor_exibicao = (row["autor_nome"] or "").strip() or "morador.local"
    return {
        "id": row["id"],
        "autor_exibicao": autor_exibicao,
        "texto": row["texto"],
        "tempo_relativo": tempo_relativo(row["criado_em"]),
        **avatar_payload(autor_exibicao, mapping_get(row, "autor_foto", "")),
    }


def serialize_call(row: Mapping[str, Any], comments: list[dict]) -> dict:
    autor_exibicao = (row["nome"] or "").strip() or "morador.local"
    endereco = ", ".join(
        parte for parte in [row["rua"], row["numero"], row["bairro"], row["cidade"]] if parte
    ) or "Endereco nao informado"
    return {
        "id": row["id"],
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
        "comentarios": comments,
        "comentarios_count": len(comments),
        "comentarios_label": pluralizar_comentario(len(comments)),
        **avatar_payload(autor_exibicao, mapping_get(row, "foto_perfil", "")),
    }


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        SECRET_KEY=os.environ.get("FIXCITY_SECRET_KEY", "fixcity-flask-dev"),
        DB_BACKEND=os.environ.get("FIXCITY_DB_BACKEND", "sqlite"),
        DATABASE=str(default_database_path()),
        MYSQL_HOST=os.environ.get("FIXCITY_MYSQL_HOST", "127.0.0.1"),
        MYSQL_PORT=int(os.environ.get("FIXCITY_MYSQL_PORT", "3306")),
        MYSQL_USER=os.environ.get("FIXCITY_MYSQL_USER", "root"),
        MYSQL_PASSWORD=os.environ.get("FIXCITY_MYSQL_PASSWORD", ""),
        MYSQL_DATABASE=os.environ.get("FIXCITY_MYSQL_DATABASE", "FixcityDB"),
        MYSQL_CHARSET=os.environ.get("FIXCITY_MYSQL_CHARSET", "utf8mb4"),
        PROFILE_UPLOAD_SUBDIR="uploads/profiles",
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)

    if (app.config.get("DB_BACKEND") or "sqlite").strip().lower() == "sqlite":
        Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    profile_upload_dir = Path(app.static_folder) / app.config["PROFILE_UPLOAD_SUBDIR"]
    profile_upload_dir.mkdir(parents=True, exist_ok=True)

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")
        g.user = buscar_usuario_por_id(user_id) if user_id else None

    @app.context_processor
    def inject_user():
        return {"current_user": g.get("user")}

    @app.errorhandler(413)
    def arquivo_grande(_error):
        flash("A foto de perfil deve ter no maximo 5 MB.", "error")
        return redirect(request.referrer or url_for("cadastro"))

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

    @app.route("/login/", methods=["GET", "POST"])
    @guest_only
    def login():
        form_data = {"email": ""}

        if request.method == "POST":
            form_data["email"] = (request.form.get("email") or "").strip().lower()
            senha = request.form.get("senha") or ""
            usuario = buscar_usuario_por_email(form_data["email"])

            if usuario and check_password_hash(usuario["senha"], senha):
                session.clear()
                session["user_id"] = usuario["id_usuario"]
                flash("Login realizado com sucesso.", "success")
                return redirect(normalize_next_url(request.args.get("next")))

            flash("Email ou senha incorretos.", "error")

        return render_template("fixcity/login.html", form_data=form_data)

    @app.route("/cadastro/", methods=["GET", "POST"])
    @guest_only
    def cadastro():
        form_data = cadastro_defaults()
        errors = {}

        if request.method == "POST":
            form_data = normalizar_cadastro_form(request.form)
            foto = request.files.get("foto_perfil")
            errors = validar_cadastro(form_data, foto)

            if not errors:
                foto_path = salvar_foto_perfil(foto)
                usuario_id = criar_usuario(form_data, foto_path)
                session.clear()
                session["user_id"] = usuario_id
                flash("Conta criada com sucesso. Voce ja esta logado.", "success")
                return redirect(url_for("denuncias"))

            flash("Revise os campos destacados e tente novamente.", "error")

        return render_template("fixcity/cadastro.html", form_data=form_data, errors=errors)

    @app.post("/logout/")
    @login_required
    def logout():
        session.clear()
        flash("Voce saiu da sua conta.", "success")
        return redirect(url_for("home"))

    @app.route("/denuncias/", methods=["GET", "POST"])
    @login_required
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
    @login_required
    def atualizar_status(pk: int):
        status = (request.form.get("status") or "").strip().upper()
        if status not in STATUS_LABELS:
            flash("Nao foi possivel atualizar o status.", "error")
            return redirect(url_for("denuncias"))

        db = get_db()
        if mysql_enabled():
            db.execute(
                "UPDATE denuncias SET status = ?, atualizado_em = ? WHERE id_denuncia = ?",
                (status, agora_iso(), pk),
            )
        else:
            db.execute("UPDATE chamados SET status = ?, atualizado_em = ? WHERE id = ?", (status, agora_iso(), pk))
        db.commit()
        flash("Status atualizado.", "success")
        return redirect(url_for("denuncias"))

    @app.post("/denuncias/<int:pk>/comentarios/")
    @login_required
    def adicionar_comentario(pk: int):
        texto = (request.form.get("texto") or "").strip()

        if not texto:
            flash("Escreva um comentario valido antes de enviar.", "error")
            return redirect(url_for("denuncias"))

        usuario = usuario_logado()
        db = get_db()
        if mysql_enabled():
            db.execute(
                """
                INSERT INTO comentarios (id_usuario, id_denuncia, nome_usuario, comentario, criado_em)
                VALUES (?, ?, ?, ?, ?)
                """,
                (usuario["id_usuario"], pk, usuario["nome"], texto, agora_iso()),
            )
        else:
            db.execute(
                """
                INSERT INTO comentarios (id_usuario, chamado_id, autor_nome, texto, criado_em)
                VALUES (?, ?, ?, ?, ?)
                """,
                (usuario["id_usuario"], pk, usuario["nome"], texto, agora_iso()),
            )
        db.commit()
        flash("Comentario adicionado.", "success")
        return redirect(url_for("denuncias"))

    @app.teardown_appcontext
    def close_db(_error=None):
        database = g.pop("db", None)
        if database is not None:
            database.close()

    return app


def get_db() -> DatabaseConnection:
    if "db" not in g:
        if sqlite_enabled():
            connection = sqlite3.connect(current_app.config["DATABASE"])
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            g.db = DatabaseConnection("sqlite", connection)
        else:
            g.db = connect_mysql()

        g.db.init_schema()
    return g.db


def init_db():
    db = get_db()
    db.init_schema()


def sqlite_columns(table_name: str) -> set[str]:
    rows = get_db().execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def mysql_columns(table_name: str) -> set[str]:
    rows = get_db().execute(f"SHOW COLUMNS FROM {table_name}").fetchall()
    return {row["Field"] for row in rows}


def ensure_schema_compatibility(db: DatabaseConnection):
    if db.backend == "sqlite":
        sqlite_migrations = {
            "usuarios": {
                "cpf": "ALTER TABLE usuarios ADD COLUMN cpf TEXT DEFAULT ''",
                "foto_perfil": "ALTER TABLE usuarios ADD COLUMN foto_perfil TEXT DEFAULT ''",
                "criado_em": "ALTER TABLE usuarios ADD COLUMN criado_em TEXT DEFAULT ''",
            },
            "chamados": {
                "id_usuario": "ALTER TABLE chamados ADD COLUMN id_usuario INTEGER",
            },
            "comentarios": {
                "id_usuario": "ALTER TABLE comentarios ADD COLUMN id_usuario INTEGER",
            },
        }
        for table_name, migrations in sqlite_migrations.items():
            existing_columns = sqlite_columns(table_name)
            for column_name, statement in migrations.items():
                if column_name not in existing_columns:
                    db.execute(statement)
        db.commit()
        return

    mysql_migrations = {
        "usuarios": {
            "foto_perfil": "ALTER TABLE usuarios ADD COLUMN foto_perfil VARCHAR(255) DEFAULT ''",
            "criado_em": "ALTER TABLE usuarios ADD COLUMN criado_em VARCHAR(40) NOT NULL DEFAULT ''",
        }
    }
    for table_name, migrations in mysql_migrations.items():
        existing_columns = mysql_columns(table_name)
        for column_name, statement in migrations.items():
            if column_name not in existing_columns:
                db.execute(statement)
    db.commit()


def cadastro_defaults() -> dict:
    return {
        "nome": "",
        "cpf": "",
        "telefone": "",
        "email": "",
    }


def form_defaults() -> dict:
    usuario = usuario_logado()
    return {
        "cpf": usuario["cpf"] if usuario else "",
        "nome": usuario["nome"] if usuario else "",
        "email": usuario["email"] if usuario else "",
        "categoria": "",
        "cep": "",
        "rua": "",
        "bairro": "",
        "cidade": "",
        "numero": "",
        "descricao": "",
    }


def normalizar_cadastro_form(form) -> dict:
    return {
        "nome": (form.get("nome") or "").strip(),
        "cpf": re.sub(r"\D", "", form.get("cpf") or ""),
        "telefone": re.sub(r"\D", "", form.get("telefone") or ""),
        "email": (form.get("email") or "").strip().lower(),
        "senha": form.get("senha") or "",
    }


def normalizar_formulario(form) -> dict:
    data = form_defaults()
    for field in ("categoria", "cep", "rua", "bairro", "cidade", "numero", "descricao"):
        data[field] = (form.get(field) or "").strip()
    data["cep"] = re.sub(r"\D", "", data["cep"])
    data["categoria"] = data["categoria"].upper()
    return data


def buscar_usuario_por_id(user_id: int | None):
    if not user_id:
        return None

    query = "SELECT id_usuario, nome, email, senha, telefone, cpf, foto_perfil FROM usuarios WHERE id_usuario = ?"
    return get_db().execute(query, (user_id,)).fetchone()


def buscar_usuario_por_email(email: str):
    if not email:
        return None

    query = "SELECT id_usuario, nome, email, senha, telefone, cpf, foto_perfil FROM usuarios WHERE email = ?"
    return get_db().execute(query, (email,)).fetchone()


def buscar_usuario_por_cpf(cpf: str):
    if not cpf:
        return None

    query = "SELECT id_usuario, nome, email, senha, telefone, cpf, foto_perfil FROM usuarios WHERE cpf = ?"
    return get_db().execute(query, (cpf,)).fetchone()


def usuario_logado():
    return g.get("user")


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
    usuario = usuario_logado()
    db = get_db()
    if mysql_enabled():
        endereco_cursor = db.execute(
            """
            INSERT INTO endereco (cidade, bairro, nome_rua, cep, estado, numero, referencia)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["cidade"] or "",
                data["bairro"] or "",
                data["rua"] or "",
                data["cep"] or "",
                "",
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
                usuario["id_usuario"],
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
                id_usuario, cpf, nome, email, categoria, cep, rua, bairro, cidade, numero,
                descricao, status, latitude, longitude, criado_em, atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                usuario["id_usuario"],
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
    if mysql_enabled():
        chamados_rows = db.execute(
            """
            SELECT
                d.id_denuncia AS id,
                d.cpf,
                COALESCE(u.nome, d.nome_usuario) AS nome,
                COALESCE(u.email, d.email_usuario) AS email,
                u.foto_perfil,
                d.categoria,
                e.cep,
                e.nome_rua AS rua,
                e.bairro,
                e.cidade,
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

    return [serialize_call(row, comentarios_por_chamado.get(row["id"], [])) for row in chamados_rows]


def calcular_stats(chamados: list[dict]) -> dict:
    return {
        "total": len(chamados),
        "problemas": sum(1 for chamado in chamados if chamado["status"] == "PROBLEMA"),
        "pendentes": sum(1 for chamado in chamados if chamado["status"] == "PENDENTE"),
        "resolvidos": sum(1 for chamado in chamados if chamado["status"] == "RESOLVIDO"),
    }


from fixcity import create_app as modular_create_app
from fixcity.db import get_db as modular_get_db, init_db as modular_init_db
from fixcity.services.auth_service import (
    buscar_usuario_por_email as modular_buscar_usuario_por_email,
    buscar_usuario_por_id as modular_buscar_usuario_por_id,
)


create_app = modular_create_app
get_db = modular_get_db
init_db = modular_init_db
buscar_usuario_por_email = modular_buscar_usuario_por_email
buscar_usuario_por_id = modular_buscar_usuario_por_id
app = create_app()


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
