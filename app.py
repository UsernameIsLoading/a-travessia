import os, sqlite3, json
from datetime import date, timedelta
from flask import Flask, send_file, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'travessia.db'))
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'troque-esta-chave-em-producao')
CLASSES = ('corpo','mente','alma')
DEFAULT_STREAKS = {c:{'dias':0,'ultimoDia':None} for c in CLASSES}

def db():
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; return conn

def today(): return date.today()
def iso(d): return d.isoformat()
def parse_days(v):
    try:
        a=sorted(set(int(x) for x in (v or []) if 0 <= int(x) <= 6))
        return a
    except Exception: return [0,1,2,3,4,5,6]

def init_db():
    conn=db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, last_processed_day TEXT);
    CREATE TABLE IF NOT EXISTS characters (user_id INTEGER PRIMARY KEY, body REAL NOT NULL DEFAULT 0, mind REAL NOT NULL DEFAULT 0, soul REAL NOT NULL DEFAULT 0, class_name TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, text TEXT NOT NULL, class TEXT NOT NULL, type TEXT NOT NULL DEFAULT 'todo', frequency_json TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]', FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS completions (task_id INTEGER NOT NULL, day TEXT NOT NULL, PRIMARY KEY(task_id,day), FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS streaks (user_id INTEGER NOT NULL, class TEXT NOT NULL, days INTEGER NOT NULL DEFAULT 0, last_day TEXT, PRIMARY KEY(user_id,class), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    ''')
    # Migration for databases created by the previous version.
    cols=[r['name'] for r in conn.execute('PRAGMA table_info(tasks)').fetchall()]
    if 'frequency_json' not in cols: conn.execute("ALTER TABLE tasks ADD COLUMN frequency_json TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]'")
    ucols=[r['name'] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
    if 'last_processed_day' not in ucols: conn.execute('ALTER TABLE users ADD COLUMN last_processed_day TEXT')
    conn.commit(); conn.close()
init_db()

def current_user():
    uid=session.get('user_id')
    if not uid:return None
    conn=db(); u=conn.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone(); conn.close(); return u

def require_user():
    u=current_user(); return (u,None) if u else (None,(jsonify(error='Faça login para continuar.'),401))

def get_tasks(conn, uid):
    rows=conn.execute('SELECT * FROM tasks WHERE user_id=? ORDER BY id',(uid,)).fetchall()
    out=[]
    for r in rows:
        try: freq=json.loads(r['frequency_json'])
        except: freq=list(range(7))
        out.append({'id':r['id'],'texto':r['text'],'classe':r['class'],'tipo':r['type'],'frequencia':parse_days(freq)})
    return out

def completion_set(conn, uid, day):
    rows=conn.execute('SELECT c.task_id FROM completions c JOIN tasks t ON t.id=c.task_id WHERE t.user_id=? AND c.day=?',(uid,day)).fetchall()
    return {r['task_id'] for r in rows}

def process_until_yesterday(conn, user):
    last=user['last_processed_day']
    yesterday=today()-timedelta(days=1)
    start=(date.fromisoformat(last)+timedelta(days=1)) if last else yesterday
    if start>yesterday:
        return
    streak={c:{'dias':0,'ultimoDia':None} for c in CLASSES}
    for r in conn.execute('SELECT class,days,last_day FROM streaks WHERE user_id=?',(user['id'],)):
        streak[r['class']]={'dias':int(r['days'] or 0),'ultimoDia':r['last_day']}
    tasks=get_tasks(conn,user['id'])
    for d in (start + timedelta(days=i) for i in range((yesterday-start).days+1)):
        wd=d.weekday(); ds=iso(d); done=completion_set(conn,user['id'],ds)
        for cls in CLASSES:
            due=[t for t in tasks if t['classe']==cls and wd in t['frequencia']]
            if not due: continue
            todo=next((t for t in due if t['tipo']=='todo'),None)
            vote=next((t for t in due if t['tipo']=='voto'),None)
            if vote and vote['id'] not in done:
                streak[cls]={'dias':0,'ultimoDia':None}
                continue
            if todo:
                if todo['id'] in done:
                    streak[cls]['dias'] += 1
                    streak[cls]['ultimoDia']=ds
                else:
                    streak[cls]['dias']=max(0,streak[cls]['dias']-1)
            elif vote and vote['id'] in done:
                streak[cls]['dias'] += 1; streak[cls]['ultimoDia']=ds
    for cls in CLASSES:
        s=streak[cls]
        conn.execute('INSERT INTO streaks(user_id,class,days,last_day) VALUES (?,?,?,?) ON CONFLICT(user_id,class) DO UPDATE SET days=excluded.days,last_day=excluded.last_day',(user['id'],cls,s['dias'],s['ultimoDia']))
    conn.execute('UPDATE users SET last_processed_day=? WHERE id=?',(iso(yesterday),user['id']))

def current_day_streaks(conn, uid, base):
    out={c:dict(base[c]) for c in CLASSES}
    ds=iso(today()); wd=today().weekday(); done=completion_set(conn,uid,ds)
    tasks=get_tasks(conn,uid)
    for cls in CLASSES:
        due=[t for t in tasks if t['classe']==cls and wd in t['frequencia']]
        if not due: continue
        vote=next((t for t in due if t['tipo']=='voto'),None)
        todo=next((t for t in due if t['tipo']=='todo'),None)
        if vote and vote['id'] in done:
            out[cls]['dias']=int(out[cls]['dias'])+1
        elif not vote and todo and todo['id'] in done:
            out[cls]['dias']=int(out[cls]['dias'])+1
    return out

def user_payload(u):
    conn=db(); process_until_yesterday(conn,u)
    tasks=get_tasks(conn,u['id'])
    # Today's check marks are independent; they never carry to tomorrow.
    done=completion_set(conn,u['id'],iso(today()))
    for t in tasks: t['concluida']=t['id'] in done
    s={k:dict(v) for k,v in DEFAULT_STREAKS.items()}
    for r in conn.execute('SELECT class,days,last_day FROM streaks WHERE user_id=?',(u['id'],)): s[r['class']]={'dias':r['days'],'ultimoDia':r['last_day']}
    s=current_day_streaks(conn,u['id'],s)
    c=conn.execute('SELECT * FROM characters WHERE user_id=?',(u['id'],)).fetchone()
    char=None if not c else {'body':c['body'],'mind':c['mind'],'soul':c['soul'],'classe':c['class_name']}
    conn.commit(); conn.close()
    return {'tarefas':tasks,'streaks':s,'personagem':char}

@app.get('/')
def index(): return send_file(os.path.join(BASE_DIR,'index.html'))

@app.post('/api/register')
def register():
    data=request.get_json(silent=True) or {}; username=str(data.get('usuario','')).strip(); password=str(data.get('senha',''))
    if len(username)<3 or len(username)>40:return jsonify(error='O usuário precisa ter entre 3 e 40 caracteres.'),400
    if not all(c.isalnum() or c in '_.-' for c in username):return jsonify(error='Use apenas letras, números, ponto, hífen ou underline.'),400
    if len(password)<4:return jsonify(error='A senha precisa ter pelo menos 4 caracteres.'),400
    conn=db()
    try:
        cur=conn.execute('INSERT INTO users(username,password_hash,last_processed_day) VALUES (?,?,?)',(username,generate_password_hash(password),iso(today()-timedelta(days=1))))
        uid=cur.lastrowid
        for cls in CLASSES: conn.execute('INSERT INTO streaks(user_id,class,days,last_day) VALUES (?,?,0,NULL)',(uid,cls))
        conn.commit()
    except sqlite3.IntegrityError: conn.rollback(); conn.close(); return jsonify(error='Esse usuário já existe.'),409
    conn.close(); return jsonify(ok=True)

@app.post('/api/login')
def login():
    data=request.get_json(silent=True) or {}; username=str(data.get('usuario','')).strip(); password=str(data.get('senha',''))
    conn=db(); u=conn.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone(); conn.close()
    if not u or not check_password_hash(u['password_hash'],password):return jsonify(error='Usuário ou senha incorretos.'),401
    session.clear(); session['user_id']=u['id']; return jsonify(ok=True,usuario=u['username'])

@app.get('/api/me')
def me():
    u=current_user(); return jsonify(autenticado=bool(u),usuario=u['username'] if u else None)
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
    payload=request.get_json(silent=True) or {}; tasks=payload.get('tarefas',[])
    if not isinstance(tasks,list) or len(tasks)>6:return jsonify(error='Limite de 6 tarefas.'),400
    conn=db()
    existing={r['id'] for r in conn.execute('SELECT id FROM tasks WHERE user_id=?',(u['id'],)).fetchall()}
    kept=set()
    for t in tasks:
        text=str(t.get('texto','')).strip(); cls=t.get('classe'); typ=t.get('tipo','todo'); freq=parse_days(t.get('frequencia'))
        if not text or cls not in CLASSES or typ not in ('todo','voto') or not freq: continue
        tid=t.get('id')
        if tid and int(tid) in existing:
            tid=int(tid); kept.add(tid)
            conn.execute('UPDATE tasks SET text=?,class=?,type=?,frequency_json=? WHERE id=? AND user_id=?',(text,cls,typ,json.dumps(freq),tid,u['id']))
        else:
            conn.execute('INSERT INTO tasks(user_id,text,class,type,frequency_json) VALUES (?,?,?,?,?)',(u['id'],text,cls,typ,json.dumps(freq)))
    for tid in existing-kept: conn.execute('DELETE FROM tasks WHERE id=? AND user_id=?',(tid,u['id']))
    conn.commit(); conn.close(); return jsonify(ok=True)

@app.post('/api/tasks/<int:task_id>/complete')
def complete_task(task_id):
    u,err=require_user()
    if err:return err
    conn=db(); t=conn.execute('SELECT * FROM tasks WHERE id=? AND user_id=?',(task_id,u['id'])).fetchone()
    if not t: conn.close(); return jsonify(error='Tarefa não encontrada.'),404
    ds=iso(today())
    exists=conn.execute('SELECT 1 FROM completions WHERE task_id=? AND day=?',(task_id,ds)).fetchone()
    if exists: conn.execute('DELETE FROM completions WHERE task_id=? AND day=?',(task_id,ds)); done=False
    else: conn.execute('INSERT INTO completions(task_id,day) VALUES (?,?)',(task_id,ds)); done=True
    conn.commit(); conn.close(); return jsonify(ok=True,concluida=done)

@app.put('/api/streaks')
def save_streaks():
    u,err=require_user()
    if err:return err
    # Kept for compatibility; streaks are now calculated server-side.
    return jsonify(ok=True)

@app.put('/api/character')
def save_character():
    u,err=require_user()
    if err:return err
    p=request.get_json(silent=True).get('personagem',{}) or {}
    body=float(p.get('body',0)); mind=float(p.get('mind',0)); soul=float(p.get('soul',0)); cls=str(p.get('classe',''))
    if any(x<0 or x>3 for x in (body,mind,soul)) or body+mind+soul>3.5:return jsonify(error='Atributos inválidos.'),400
    conn=db(); conn.execute('INSERT INTO characters(user_id,body,mind,soul,class_name) VALUES (?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET body=excluded.body,mind=excluded.mind,soul=excluded.soul,class_name=excluded.class_name',(u['id'],body,mind,soul,cls)); conn.commit(); conn.close(); return jsonify(ok=True)

def effective_attributes(conn,uid):
    c=conn.execute('SELECT * FROM characters WHERE user_id=?',(uid,)).fetchone()
    base={'body':float(c['body'] or 0),'mind':float(c['mind'] or 0),'soul':float(c['soul'] or 0)} if c else {'body':0.0,'mind':0.0,'soul':0.0}
    done=completion_set(conn,uid,iso(today()))
    for r in conn.execute("SELECT id,class FROM tasks WHERE user_id=? AND type='voto'",(uid,)):
        if r['id'] in done: base[r['class']]+=0.5
    return base

def stats_for(attrs,days):
    days=max(1,int(days or 1))
    def F(a): return 30/((1+a/10)*days+30)
    fb,fm,fs=F(attrs['body']),F(attrs['mind']),F(attrs['soul'])
    return {'F':{'corpo':fb,'mente':fm,'alma':fs},'HP':200*(1-fb),'ATK':(200*(1-fb))/10,'CE':1000*(1-fs),'CT':1/fm}

@app.get('/api/profile')
def profile():
    u,err=require_user()
    if err:return err
    conn=db(); process_until_yesterday(conn,u)
    vals={r['class']:{'dias':int(r['days']),'ultimoDia':None} for r in conn.execute('SELECT class,days FROM streaks WHERE user_id=?',(u['id'],))}
    for c in CLASSES: vals.setdefault(c,{'dias':0,'ultimoDia':None})
    vals=current_day_streaks(conn,u['id'],vals)
    attrs=effective_attributes(conn,u['id']); days={c:int(vals.get(c,{}).get('dias',0)) for c in CLASSES}
    # Day 1 must be valid for the formula, even when no streak has started yet.
    stats=stats_for(attrs,max(days.values()) if max(days.values())>0 else 1)
    conn.commit(); conn.close()
    return jsonify(usuario=u['username'],atributos=attrs,dias=days,stats=stats)

@app.get('/api/leaderboard')
def leaderboard():
    conn=db(); users=conn.execute('SELECT * FROM users ORDER BY username').fetchall(); result=[]
    for user in users:
        process_until_yesterday(conn,user)
        vals={r['class']:{'dias':int(r['days']),'ultimoDia':None} for r in conn.execute('SELECT class,days FROM streaks WHERE user_id=?',(user['id'],))}
        for c in CLASSES: vals.setdefault(c,{'dias':0,'ultimoDia':None})
        vals=current_day_streaks(conn,user['id'],vals)
        corpo=int(vals.get('corpo',{}).get('dias',0)); mente=int(vals.get('mente',{}).get('dias',0)); alma=int(vals.get('alma',{}).get('dias',0))
        result.append({'usuario':user['username'],'corpo':corpo,'mente':mente,'alma':alma,'total':corpo+mente+alma})
    conn.commit(); conn.close(); result.sort(key=lambda x:(-x['total'],-max(x['corpo'],x['mente'],x['alma']),x['usuario'].lower())); return jsonify(result)

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=True)
