import os, sqlite3
from flask import Flask, render_template, send_file, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'travessia.db'))
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'troque-esta-chave-em-producao')

DEFAULT_STREAKS = {'corpo': {'dias': 0, 'ultimoDia': None}, 'mente': {'dias': 0, 'ultimoDia': None}, 'alma': {'dias': 0, 'ultimoDia': None}}

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn=db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS characters (user_id INTEGER PRIMARY KEY, body INTEGER NOT NULL DEFAULT 0, mind INTEGER NOT NULL DEFAULT 0, soul INTEGER NOT NULL DEFAULT 0, class_name TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, text TEXT NOT NULL, class TEXT NOT NULL, type TEXT NOT NULL DEFAULT 'todo', completed INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS streaks (user_id INTEGER NOT NULL, class TEXT NOT NULL, days INTEGER NOT NULL DEFAULT 0, last_day TEXT, PRIMARY KEY(user_id,class), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    ''')
    conn.commit(); conn.close()

init_db()

def current_user():
    uid=session.get('user_id')
    if not uid:return None
    conn=db(); u=conn.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone(); conn.close()
    return u

def require_user():
    u=current_user()
    if not u: return None, (jsonify(error='Faça login para continuar.'),401)
    return u, None

def user_payload(u):
    conn=db()
    tasks=[{'id':r['id'],'texto':r['text'],'classe':r['class'],'tipo':r['type'],'concluida':bool(r['completed'])} for r in conn.execute('SELECT * FROM tasks WHERE user_id=? ORDER BY id',(u['id'],))]
    s={k:dict(v) for k,v in DEFAULT_STREAKS.items()}
    for r in conn.execute('SELECT class,days,last_day FROM streaks WHERE user_id=?',(u['id'],)):
        s[r['class']]={'dias':r['days'],'ultimoDia':r['last_day']}
    c=conn.execute('SELECT * FROM characters WHERE user_id=?',(u['id'],)).fetchone()
    char=None if not c else {'body':c['body'],'mind':c['mind'],'soul':c['soul'],'classe':c['class_name']}
    conn.close()
    return {'tarefas':tasks,'streaks':s,'personagem':char}

@app.get('/')
def index():
    # Serve the frontend directly from the project root. This avoids deployment
    # problems if the GitHub web uploader does not preserve the templates folder.
    return send_file(os.path.join(BASE_DIR, 'index.html'))

@app.post('/api/register')
def register():
    data=request.get_json(silent=True) or {}; username=str(data.get('usuario','')).strip(); password=str(data.get('senha',''))
    if len(username)<3 or len(username)>40: return jsonify(error='O usuário precisa ter entre 3 e 40 caracteres.'),400
    if not all(c.isalnum() or c in '_.-' for c in username): return jsonify(error='Use apenas letras, números, ponto, hífen ou underline.'),400
    if len(password)<4: return jsonify(error='A senha precisa ter pelo menos 4 caracteres.'),400
    conn=db()
    try:
        cur=conn.execute('INSERT INTO users(username,password_hash) VALUES (?,?)',(username,generate_password_hash(password)))
        uid=cur.lastrowid
        for cls in ('corpo','mente','alma'): conn.execute('INSERT INTO streaks(user_id,class,days,last_day) VALUES (?,?,0,NULL)',(uid,cls))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback(); conn.close(); return jsonify(error='Esse usuário já existe.'),409
    conn.close(); return jsonify(ok=True)

@app.post('/api/login')
def login():
    data=request.get_json(silent=True) or {}; username=str(data.get('usuario','')).strip(); password=str(data.get('senha',''))
    conn=db(); u=conn.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone(); conn.close()
    if not u or not check_password_hash(u['password_hash'],password): return jsonify(error='Usuário ou senha incorretos.'),401
    session.clear(); session['user_id']=u['id']; return jsonify(ok=True,usuario=u['username'])

@app.get('/api/me')
def me():
    u=current_user(); return jsonify(autenticado=bool(u), usuario=u['username'] if u else None)

@app.post('/api/logout')
def logout(): session.clear(); return jsonify(ok=True)

@app.get('/api/data')
def data():
    u,err=require_user()
    if err:return err
    return jsonify(user_payload(u))

@app.put('/api/tasks')
def save_tasks():
    u,err=require_user()
    if err:return err
    tasks=request.get_json(silent=True).get('tarefas',[])
    if not isinstance(tasks,list) or len(tasks)>6:return jsonify(error='Limite de 6 tarefas.'),400
    conn=db(); conn.execute('DELETE FROM tasks WHERE user_id=?',(u['id'],))
    for t in tasks:
        text=str(t.get('texto','')).strip(); cls=t.get('classe','corpo'); typ=t.get('tipo','todo')
        if not text or cls not in ('corpo','mente','alma') or typ not in ('todo','voto'): continue
        conn.execute('INSERT INTO tasks(user_id,text,class,type,completed) VALUES (?,?,?,?,?)',(u['id'],text,cls,typ,1 if t.get('concluida') else 0))
    conn.commit(); conn.close(); return jsonify(ok=True)

@app.put('/api/streaks')
def save_streaks():
    u,err=require_user()
    if err:return err
    streaks=request.get_json(silent=True).get('streaks',{})
    conn=db()
    for cls in ('corpo','mente','alma'):
        s=streaks.get(cls,{}) or {}; days=max(0,int(s.get('dias',0) or 0)); last=s.get('ultimoDia')
        conn.execute('INSERT INTO streaks(user_id,class,days,last_day) VALUES (?,?,?,?) ON CONFLICT(user_id,class) DO UPDATE SET days=excluded.days,last_day=excluded.last_day',(u['id'],cls,days,last))
    conn.commit(); conn.close(); return jsonify(ok=True)

@app.put('/api/character')
def save_character():
    u,err=require_user()
    if err:return err
    p=request.get_json(silent=True).get('personagem',{}) or {}
    body=int(p.get('body',0)); mind=int(p.get('mind',0)); soul=int(p.get('soul',0)); cls=str(p.get('classe',''))
    if any(x<0 or x>3 for x in (body,mind,soul)): return jsonify(error='Atributos inválidos.'),400
    conn=db(); conn.execute('INSERT INTO characters(user_id,body,mind,soul,class_name) VALUES (?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET body=excluded.body,mind=excluded.mind,soul=excluded.soul,class_name=excluded.class_name',(u['id'],body,mind,soul,cls)); conn.commit(); conn.close(); return jsonify(ok=True)

@app.get('/api/leaderboard')
def leaderboard():
    u=current_user()
    conn=db()
    users=conn.execute('SELECT id,username FROM users ORDER BY username').fetchall()
    result=[]
    for user in users:
        vals={r['class']:r['days'] for r in conn.execute('SELECT class,days FROM streaks WHERE user_id=?',(user['id'],))}
        corpo=int(vals.get('corpo',0)); mente=int(vals.get('mente',0)); alma=int(vals.get('alma',0))
        total=corpo+mente+alma
        result.append({'usuario':user['username'],'corpo':corpo,'mente':mente,'alma':alma,'total':total})
    conn.close(); result.sort(key=lambda x:(-x['total'],-max(x['corpo'],x['mente'],x['alma']),x['usuario'].lower()))
    return jsonify(result)

@app.get('/api/leaderboard/<username>')
def leaderboard_user(username):
    conn=db(); u=conn.execute('SELECT id FROM users WHERE username=?',(username,)).fetchone()
    if not u: conn.close(); return jsonify(error='Usuário não encontrado.'),404
    vals={r['class']:r['days'] for r in conn.execute('SELECT class,days FROM streaks WHERE user_id=?',(u['id'],))}; conn.close()
    return jsonify(corpo=vals.get('corpo',0),mente=vals.get('mente',0),alma=vals.get('alma',0))

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=True)
