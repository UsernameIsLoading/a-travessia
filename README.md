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

## Novidades desta versão

### Limite de PvP
Cada jogador pode participar de no máximo **2 combates PvP por dia**. O limite vale tanto para combates iniciados pelo jogador quanto para desafios recebidos. A contagem fica no PostgreSQL em `pvp_daily`.

### Painel ADM
O login administrativo usa:
- Usuário: `ADMIN`
- Senha padrão: `1984`

A senha pode ser alterada no Render criando a variável de ambiente `ADMIN_PASSWORD`.

O painel ADM permite:
- listar jogadores;
- excluir contas;
- baixar um backup SQL do PostgreSQL;
- enviar/restaurar um backup SQL.

### Backup SQL no Render Free
O PostgreSQL Free do Render expira após 30 dias. Por isso, use o painel ADM para baixar regularmente o arquivo `travessia_backup.sql` e guardá-lo fora do Render. O próprio Render informa que o Postgres Free não possui backups gerenciados; backups externos com `pg_dump` são outra opção. O painel do jogo fornece uma exportação SQL dos dados usados pelo A Travessia.

Para restaurar, entre como `ADMIN`, escolha o arquivo `.sql` e confirme. A restauração substitui os dados atuais das tabelas do jogo.


## Alterações recentes — 07/09/2026

### PvP por desafio
- Criar um PvP agora apenas envia um desafio ao segundo jogador.
- O desafiado pode **ACEITAR** ou **RECUSAR**.
- O combate só fica ativo após a aceitação.
- Ao aceitar, o primeiro turno é sorteado com **50/50** entre os dois jogadores.
- O limite diário de 2 combates PvP passa a ser contabilizado quando o desafio é aceito, e não quando é enviado.

### Imagens
As quatro imagens incorporadas na página de atributos/personagem foram substituídas por arquivos da **Jujutsu Kaisen Wiki**: Toji Fushiguro, Satoru Gojo, Yuta Okkotsu e Yuji Itadori.

### Lembrete de backup
O painel ADMIN possui um lembrete de backup SQL em ciclos de 30 dias a partir de **05/09/2026**. O próximo vencimento após essa data é calculado automaticamente pelo servidor e mostrado no painel administrativo.
