# FixCity

O projeto foi reorganizado em arquitetura MVC com Flask, mantendo as funcionalidades de cadastro, login, denuncias, comentarios, upvotes, notificacoes, mapa e painel administrativo.

## Estrutura MVC

```text
fixcity/
├── controllers/   # Fluxo HTTP, rotas e respostas Flask
├── models/        # Regras de negocio e acesso aos dados
├── services/      # Integracoes externas e compatibilidade
├── auth.py        # Decorators e injecao do usuario logado
├── config.py      # Configuracoes e schema
├── db.py          # Conexao e inicializacao do banco
└── factory.py     # App factory

templates/fixcity/ # Views HTML
static/            # CSS, JS e uploads
app.py             # Ponto de entrada da aplicacao
```

## Como ficou separado

- `controllers`: recebem `request`, validam fluxo e renderizam templates ou redirecionam.
- `models`: concentram persistencia, serializacao e regras de negocio dos usuarios, chamados e notificacoes.
- `views`: no Flask ficam nos templates Jinja em `templates/fixcity`.
- `services`: lidam com CEP e geocodificacao, sem misturar isso com controller ou model.

## Executar com SQLite

1. Ative o ambiente virtual.
2. Instale as dependencias com `pip install -r requirements.txt`.
3. Rode a aplicacao com `python app.py`.

O SQLite continua sendo o backend padrao.

## Como conectar com MySQL Workbench

1. Abra o MySQL Workbench e execute o script [database/fixcity_mysql.sql](/c:/Users/felipe.srosa3/OneDrive%20-%20SENAC%20-%20SP/Documentos/pi/Projeto-Integrador/database/fixcity_mysql.sql:1).
2. Instale as dependencias do projeto com `pip install -r requirements.txt`.
3. Defina estas variaveis de ambiente antes de iniciar a aplicacao:

```powershell
$env:FIXCITY_DB_BACKEND = "mysql"
$env:FIXCITY_MYSQL_HOST = "127.0.0.1"
$env:FIXCITY_MYSQL_PORT = "3306"
$env:FIXCITY_MYSQL_USER = "root"
$env:FIXCITY_MYSQL_PASSWORD = "felipe123"
$env:FIXCITY_MYSQL_DATABASE = "FixcityDB"
```

4. Rode a aplicacao normalmente.

## Testes

Execute:

```powershell
.\venv\Scripts\python.exe -m unittest tests_flask.py
```
