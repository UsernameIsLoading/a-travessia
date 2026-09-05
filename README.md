# A TRAVESSIA — Flask

Projeto preparado para publicar o site como uma aplicação Flask, com contas, tarefas, streaks e leaderboard compartilhados entre os usuários.

## Rodar no computador

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000`.

## Publicar no Render

1. Crie um repositório no GitHub e envie estes arquivos.
2. No Render, crie um **Web Service** conectado ao repositório.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. Crie `SECRET_KEY` como variável de ambiente com valor aleatório (o `render.yaml` já pede geração automática).
6. Para persistência de dados em produção, use um banco PostgreSQL ou um disco persistente; o SQLite deste projeto é ótimo para testes locais.

## Observação

O frontend original foi mantido em `templates/index.html`. A persistência deixou de depender do `localStorage`: login, tarefas, personagem, streaks e leaderboard passam pela API Flask.
