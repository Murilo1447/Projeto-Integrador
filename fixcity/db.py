import sqlite3

from flask import current_app, g

from .config import MYSQL_SCHEMA_STATEMENTS, SQLITE_SCHEMA_STATEMENTS

try:
    import mysql.connector
except ImportError:
    mysql = None


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


def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def init_db():
    db = get_db()
    db.init_schema()


def sqlite_columns(db: DatabaseConnection, table_name: str) -> set[str]:
    rows = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def mysql_columns(db: DatabaseConnection, table_name: str) -> set[str]:
    rows = db.execute(f"SHOW COLUMNS FROM {table_name}").fetchall()
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
            existing_columns = sqlite_columns(db, table_name)
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
        existing_columns = mysql_columns(db, table_name)
        for column_name, statement in migrations.items():
            if column_name not in existing_columns:
                db.execute(statement)
    db.commit()
