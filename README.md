# A TRAVESSIA — Flask

Aplicação Flask com login, tarefas, personagem, streaks, skills, combates, maldições e leaderboard.

## Banco persistente (PostgreSQL)

O projeto agora suporta PostgreSQL através da variável de ambiente `DATABASE_URL`. Quando ela estiver definida, o app usa PostgreSQL; sem ela, continua usando SQLite local para facilitar o desenvolvimento.

No Render, conecte o Web Service a um banco PostgreSQL e configure `DATABASE_URL` com a Internal Database URL fornecida pelo Render. O app adiciona `sslmode=require` automaticamente quando necessário.

**Importante:** o filesystem padrão do Render é efêmero, então o banco não deve ficar em `travessia.db` em produção. O PostgreSQL mantém os dados separados do filesystem da aplicação.

### Render
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Environment Variable: `DATABASE_URL` = URL do PostgreSQL
- Environment Variable: `SECRET_KEY` = pode usar `generateValue: true` no Blueprint

### Desenvolvimento local
Sem `DATABASE_URL`, o projeto continua usando `travessia.db`.

### Migrar um SQLite existente
Se você tiver um `travessia.db` com dados importantes, use `migrate_sqlite_to_postgres.py` com `SOURCE_DB_PATH` apontando para o SQLite e `DATABASE_URL` apontando para o PostgreSQL.

## GitHub
Envie estes arquivos para a raiz do repositório:
- `app.py`
- `index.html`
- `requirements.txt`
- `render.yaml`
- `README.md`
- `migrate_sqlite_to_postgres.py`
