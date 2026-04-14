# FixCity

O projeto continua funcionando com `SQLite` por padrao, mas agora tambem aceita `MySQL`, o que permite administrar o banco pelo MySQL Workbench.

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

4. Rode a aplicacao normalmente. No MySQL, o projeto agora usa as tabelas `usuarios`, `endereco`, `denuncias` e `comentarios`.

## O que foi adaptado no script

O arquivo SQL foi ajustado para encaixar no projeto atual:

- `id_usuario` e `id_endereco` agora usam `INT`, para combinar com as chaves primarias.
- A ordem de criacao das tabelas foi corrigida para evitar erro de chave estrangeira.
- As denuncias agora guardam os campos que o app realmente usa hoje, como `cpf`, `categoria`, `email_usuario`, `latitude` e `longitude`.
- Os comentarios ficaram ligados a `denuncias`, mas `id_usuario` continua opcional porque o login/cadastro ainda nao foi migrado para o backend.

## Voltar para SQLite

Se quiser usar o banco local em arquivo novamente, basta remover `FIXCITY_DB_BACKEND` ou defini-la como `sqlite`.
