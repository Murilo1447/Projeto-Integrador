CREATE DATABASE IF NOT EXISTS FixcityDB
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE FixcityDB;

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL,
    senha VARCHAR(255) NOT NULL,
    telefone VARCHAR(20) NOT NULL,
    cpf VARCHAR(14) NOT NULL,
    is_admin TINYINT(1) NOT NULL DEFAULT 0,
    foto_perfil VARCHAR(255) DEFAULT '',
    criado_em VARCHAR(40) NOT NULL,
    CONSTRAINT uq_usuarios_email UNIQUE (email),
    CONSTRAINT uq_usuarios_cpf UNIQUE (cpf)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS endereco (
    id_endereco INT AUTO_INCREMENT PRIMARY KEY,
    cidade VARCHAR(100) NOT NULL,
    bairro VARCHAR(100) DEFAULT '',
    nome_rua VARCHAR(100) NOT NULL,
    cep CHAR(8) DEFAULT '',
    estado VARCHAR(100) DEFAULT '',
    numero VARCHAR(30) DEFAULT '',
    referencia VARCHAR(1000) DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS upvotes_denuncia (
    id_upvote INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    id_denuncia INT NOT NULL,
    criado_em VARCHAR(40) NOT NULL,
    CONSTRAINT uq_upvotes_denuncia_usuario UNIQUE (id_usuario, id_denuncia),
    CONSTRAINT fk_upvotes_denuncia_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario)
        ON DELETE CASCADE,
    CONSTRAINT fk_upvotes_denuncia_chamado
        FOREIGN KEY (id_denuncia) REFERENCES denuncias (id_denuncia)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
