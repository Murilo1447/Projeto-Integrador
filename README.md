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

## Criar um administrador

O administrador e uma conta comum com a permissao `is_admin` ativada. Primeiro,
inicie a aplicacao e cadastre a conta pela pagina `/cadastro/`. Depois, pare a
aplicacao e execute o comando correspondente ao seu sistema na raiz do projeto.

No Windows com PowerShell:

```powershell
.\venv\Scripts\python.exe -m flask --app app tornar-admin admin@exemplo.com
```

No Linux ou no console Bash do PythonAnywhere, com o ambiente virtual dentro do
projeto:

```bash
./venv/bin/python -m flask --app app tornar-admin 'admin@exemplo.com'
```

Substitua `admin@exemplo.com` pelo e-mail usado no cadastro. O comando utiliza o
backend configurado nas variaveis de ambiente (`sqlite` ou `mysql`). Ao entrar
novamente nessa conta, o botao **Admin** dara acesso ao painel em `/admin/`.

Se o ambiente virtual ja estiver ativo, tanto no Windows quanto no Linux, use a
forma abreviada:

```bash
python -m flask --app app tornar-admin 'admin@exemplo.com'
```

No PythonAnywhere, confirme que o terminal usa o mesmo ambiente virtual e as
mesmas variaveis de banco da aplicacao web. Um ambiente virtual criado no Windows
nao funciona no Linux e precisa ser recriado no servidor.

## Criar um superuser

O superuser herda o acesso de administrador e tambem pode executar acoes globais
destrutivas, como excluir publicacoes de qualquer conta. Cadastre primeiro uma
conta comum e promova o e-mail com:

```powershell
.\venv\Scripts\python.exe -m flask --app app tornar-superuser superuser@exemplo.com
```

No Linux ou no Bash do PythonAnywhere, com o ambiente virtual ativo:

```bash
python -m flask --app app tornar-superuser 'superuser@exemplo.com'
```

Depois do login, acesse `/superuser/` ou use o botao **Superuser** no cabecalho.
O painel permite consultar todas as contas, trocar niveis de acesso, excluir
contas, alterar o status ou excluir publicacoes e remover comentarios. Por
seguranca, a conta atualmente conectada nao pode excluir ou rebaixar a si mesma.

Conceda esse nivel apenas a pessoas de confianca. A exclusao de publicacoes e
permanente e remove tambem os comentarios, apoios e notificacoes relacionados.

## Como conectar com MySQL Workbench

1. Abra o MySQL Workbench e execute o script `database/fixcity_mysql.sql`.
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
