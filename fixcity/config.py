import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


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
    base_dir = Path(__file__).resolve().parent.parent
    db_dir = Path(os.environ.get("FIXCITY_DB_DIR", Path(os.environ.get("LOCALAPPDATA", base_dir)) / "FixCity"))
    db_dir.mkdir(parents=True, exist_ok=True)
    return Path(os.environ.get("FIXCITY_DB_NAME", db_dir / "fixcity.sqlite3"))


def default_app_config() -> dict:
    return {
        "SECRET_KEY": os.environ.get("FIXCITY_SECRET_KEY", "fixcity-flask-dev"),
        "DB_BACKEND": os.environ.get("FIXCITY_DB_BACKEND", "sqlite"),
        "DATABASE": str(default_database_path()),
        "MYSQL_HOST": os.environ.get("FIXCITY_MYSQL_HOST", "127.0.0.1"),
        "MYSQL_PORT": int(os.environ.get("FIXCITY_MYSQL_PORT", "3306")),
        "MYSQL_USER": os.environ.get("FIXCITY_MYSQL_USER", "root"),
        "MYSQL_PASSWORD": os.environ.get("FIXCITY_MYSQL_PASSWORD", ""),
        "MYSQL_DATABASE": os.environ.get("FIXCITY_MYSQL_DATABASE", "FixcityDB"),
        "MYSQL_CHARSET": os.environ.get("FIXCITY_MYSQL_CHARSET", "utf8mb4"),
        "PROFILE_UPLOAD_SUBDIR": "uploads/profiles",
        "MAX_CONTENT_LENGTH": 5 * 1024 * 1024,
    }
