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
    CREATE TABLE IF NOT EXISTS vote_bonuses (user_id INTEGER NOT NULL, task_id INTEGER NOT NULL UNIQUE, class TEXT NOT NULL, bonus REAL NOT NULL DEFAULT 0.5, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS combats (id INTEGER PRIMARY KEY AUTOINCREMENT, challenger_id INTEGER NOT NULL, defender_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending', turn_user_id INTEGER, challenger_hp REAL, defender_hp REAL, challenger_ce REAL, defender_ce REAL, effects_json TEXT NOT NULL DEFAULT '{}', log_json TEXT NOT NULL DEFAULT '[]', created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(challenger_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(defender_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS combat_skills (combat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, skill_id INTEGER NOT NULL, PRIMARY KEY(combat_id,user_id,skill_id), FOREIGN KEY(combat_id) REFERENCES combats(id) ON DELETE CASCADE, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS user_skills (user_id INTEGER NOT NULL, skill_id INTEGER NOT NULL, PRIMARY KEY(user_id,skill_id), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    ''')
    # Migration for databases created by the previous version.
    cols=[r['name'] for r in conn.execute('PRAGMA table_info(tasks)').fetchall()]
    if 'frequency_json' not in cols: conn.execute("ALTER TABLE tasks ADD COLUMN frequency_json TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]'")
    ucols=[r['name'] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
    if 'last_processed_day' not in ucols: conn.execute('ALTER TABLE users ADD COLUMN last_processed_day TEXT')
    # Backfill vote bonuses created by older versions.
    conn.execute("INSERT OR IGNORE INTO vote_bonuses(user_id,task_id,class,bonus) SELECT user_id,id,class,0.5 FROM tasks WHERE type='voto'")
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
            oldrow=conn.execute('SELECT type,class FROM tasks WHERE id=? AND user_id=?',(tid,u['id'])).fetchone()
            conn.execute('UPDATE tasks SET text=?,class=?,type=?,frequency_json=? WHERE id=? AND user_id=?',(text,cls,typ,json.dumps(freq),tid,u['id']))
            if typ=='voto':
                conn.execute('INSERT OR IGNORE INTO vote_bonuses(user_id,task_id,class,bonus) VALUES (?,?,?,0.5)',(u['id'],tid,cls))
                conn.execute('UPDATE vote_bonuses SET class=? WHERE user_id=? AND task_id=?',(cls,u['id'],tid))
            elif oldrow and oldrow['type']=='voto':
                conn.execute('DELETE FROM vote_bonuses WHERE user_id=? AND task_id=?',(u['id'],tid))
        else:
            cur=conn.execute('INSERT INTO tasks(user_id,text,class,type,frequency_json) VALUES (?,?,?,?,?)',(u['id'],text,cls,typ,json.dumps(freq)))
            tid=cur.lastrowid
            if typ=='voto': conn.execute('INSERT INTO vote_bonuses(user_id,task_id,class,bonus) VALUES (?,?,?,0.5)',(u['id'],tid,cls))
    for tid in existing-kept:
        conn.execute('DELETE FROM vote_bonuses WHERE task_id=? AND user_id=?',(tid,u['id']))
        conn.execute('DELETE FROM tasks WHERE id=? AND user_id=?',(tid,u['id']))
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
    for r in conn.execute("SELECT class,COALESCE(SUM(bonus),0) AS bonus FROM vote_bonuses WHERE user_id=? GROUP BY class",(uid,)):
        base[r['class']]+=float(r['bonus'] or 0)
    return base

SKILLS = [
('Bola de Fogo','elemental',2,10,'1d6'),('Explosão Ígnea','elemental',3,25,'2d4'),('Muralha de Fogo','elemental',3,20,'1d4x3'),('Incinerar','elemental',4,40,'2d6'),('Chama Negra','elemental',5,50,'2d6'),
('Pedrada','elemental',1,5,'1d4'),('Lança de Pedra','elemental',2,12,'1d6'),('Terremoto','elemental',4,35,'2d4'),('Armadura de Terra','elemental',3,20,'defesa'),
("Jato d'Água",'elemental',1,5,'1d4'),('Onda Violenta','elemental',3,25,'2d4'),('Prisão de Água','elemental',4,30,'controle'),('Tsunami','elemental',5,60,'2d6'),
('Rajada de Vento','elemental',1,5,'1d4'),('Lâmina de Vento','elemental',2,15,'1d6'),('Tornado','elemental',4,35,'2d4'),('Raio','elemental',2,15,'1d6'),('Tempestade','elemental',4,40,'2d6'),('Congelamento','elemental',3,20,'controle'),('Raio Solar','elemental',5,50,'2d6'),
('Artes Marciais','reforco',1,0,'buff'),('Força Bruta','reforco',2,10,'buff_d4'),('Fortificação','reforco',2,15,'defesa_d4'),('Cura','reforco',2,20,'cura_d6'),('Grande Cura','reforco',4,40,'cura_2d6'),
('Segundo Fôlego','reforco',3,30,'cura_d6_clean'),('Voar','reforco',1,5,'esquiva'),('Foco Absoluto','reforco',2,15,'buff2'),('Concentração','reforco',2,10,'ce_d4'),('Meditação','reforco',3,20,'ce_d6'),
('Reservas de Energia','reforco',4,30,'ce_2d6'),('Adrenalina','reforco',3,15,'buff_lowhp'),('Golpe Poderoso','reforco',2,15,'upgrade'),('Combo','reforco',3,25,'combo'),('Agilidade','reforco',2,10,'esquiva'),
('Postura Defensiva','reforco',2,10,'defesa2'),('Sobrecarga','reforco',4,30,'upgrade'),('Determinação','reforco',3,20,'laststand'),('Regeneração','reforco',4,25,'regen'),('Equilíbrio','reforco',5,30,'balance'),
('Sangramento','enfraquecimento',2,10,'bleed'),('Veneno','enfraquecimento',3,15,'poison'),('Queimadura','enfraquecimento',2,10,'burn'),('Congelar','enfraquecimento',3,20,'controle'),('Atordoamento','enfraquecimento',3,25,'controle'),
('Cegueira','enfraquecimento',3,20,'blind'),('Lentidão','enfraquecimento',2,15,'slow'),('Silêncio','enfraquecimento',4,30,'silence'),('Maldição','enfraquecimento',4,35,'curse'),('Infecção','enfraquecimento',3,20,'infection'),
('Confusão','enfraquecimento',4,25,'confusion'),('Medo','enfraquecimento',2,15,'weak'),('Aprisionamento','enfraquecimento',4,30,'bind'),('Perturbação Mental','enfraquecimento',3,20,'mental'),('Drenagem','enfraquecimento',4,30,'drain'),
('Dreno Vital','enfraquecimento',5,40,'lifedrain'),('Fragilidade','enfraquecimento',3,20,'fragile'),('Provocação','enfraquecimento',2,5,'taunt'),('Exaustão','enfraquecimento',4,25,'exhaust'),('Sentença','enfraquecimento',5,50,'sentence')
]

def roll(expr):
    import random
    if expr=='1d4': return random.randint(1,4)
    if expr=='1d6': return random.randint(1,6)
    if expr=='2d4': return random.randint(1,4)+random.randint(1,4)
    if expr=='2d6': return random.randint(1,6)+random.randint(1,6)
    return 0

def combat_days(conn,uid):
    rows=conn.execute('SELECT days FROM streaks WHERE user_id=?',(uid,)).fetchall()
    vals=[int(r['days'] or 0) for r in rows]
    return max(vals) if vals and max(vals)>0 else 1

def combat_stats(conn,uid):
    return stats_for(effective_attributes(conn,uid),combat_days(conn,uid))

def combat_effects(c):
    try: return json.loads(c['effects_json'] or '{}')
    except: return {}

def save_combat_state(conn,c,hp1,hp2,ce1,ce2,effects,logs,status=None,turn=None):
    conn.execute('UPDATE combats SET challenger_hp=?,defender_hp=?,challenger_ce=?,defender_ce=?,effects_json=?,log_json=?,status=COALESCE(?,status),turn_user_id=COALESCE(?,turn_user_id) WHERE id=?',(hp1,hp2,ce1,ce2,json.dumps(effects),json.dumps(logs[-40:]),status,turn,c['id']))

def skill_payload():
    return [{'id':i+1,'nome':x[0],'categoria':x[1],'ct':x[2],'ce':x[3],'dano':x[4]} for i,x in enumerate(SKILLS)]

@app.get('/api/skills')
def skills_api():
    u,err=require_user()
    if err:return err
    conn=db(); st=combat_stats(conn,u['id']); slots=int(st['CT']); conn.close()
    equipped=[r['skill_id'] for r in conn.execute('SELECT skill_id FROM user_skills WHERE user_id=?',(u['id'],))]; return jsonify(skills=skill_payload(),ct=st['CT'],slots=slots,equipped=equipped)

@app.post('/api/skills/equip')
def skills_equip():
    u,err=require_user()
    if err:return err
    data=request.get_json(silent=True) or {}; ids=data.get('skills',[])
    try: ids=sorted(set(int(x) for x in ids))
    except: return jsonify(error='Skills inválidas.'),400
    if any(x<1 or x>len(SKILLS) for x in ids): return jsonify(error='Skill inválida.'),400
    conn=db(); slots=int(combat_stats(conn,u['id'])['CT']); total=sum(SKILLS[i-1][2] for i in ids)
    if total>slots: conn.close(); return jsonify(error=f'Você tem {slots} slots de CT e tentou equipar {total}.'),400
    conn.execute('DELETE FROM user_skills WHERE user_id=?',(u['id'],))
    conn.executemany('INSERT INTO user_skills(user_id,skill_id) VALUES (?,?)',[(u['id'],i) for i in ids]); conn.commit(); conn.close(); return jsonify(ok=True,slots=slots,usado=total)

@app.get('/api/combat/users')
def combat_users():
    u,err=require_user()
    if err:return err
    conn=db(); rows=conn.execute('SELECT username FROM users WHERE id<>? ORDER BY username',(u['id'],)).fetchall(); conn.close(); return jsonify([r['username'] for r in rows])

def public_combat(conn,c,uid):
    mine=c['challenger_id']==uid; mehp=c['challenger_hp'] if mine else c['defender_hp']; opphp=c['defender_hp'] if mine else c['challenger_hp']; mece=c['challenger_ce'] if mine else c['defender_ce']; oppce=c['defender_ce'] if mine else c['challenger_ce'];
    skills=[r['skill_id'] for r in conn.execute('SELECT skill_id FROM combat_skills WHERE combat_id=? AND user_id=?',(c['id'],uid))]
    return {'id':c['id'],'oponente':conn.execute('SELECT username FROM users WHERE id=?',(c['defender_id'] if mine else c['challenger_id'],)).fetchone()['username'],'status':c['status'],'minha_vez':c['turn_user_id']==uid,'hp':mehp,'hp_oponente':opphp,'ce':mece,'ce_oponente':oppce,'skills':skills,'logs':json.loads(c['log_json'] or '[]')}

@app.post('/api/combat/challenge')
def combat_challenge():
    u,err=require_user()
    if err:return err
    data=request.get_json(silent=True) or {}; target=str(data.get('usuario','')).strip()
    conn=db(); v=conn.execute('SELECT * FROM users WHERE username=? COLLATE NOCASE',(target,)).fetchone()
    if not v or v['id']==u['id']: conn.close(); return jsonify(error='Jogador inválido.'),400
    active=conn.execute("SELECT id FROM combats WHERE status IN ('pending','active') AND ((challenger_id=? AND defender_id=?) OR (challenger_id=? AND defender_id=?))",(u['id'],v['id'],v['id'],u['id'])).fetchone()
    if active: conn.close(); return jsonify(error='Já existe um combate pendente ou ativo entre vocês.'),409
    conn.execute('INSERT INTO combats(challenger_id,defender_id,status,turn_user_id) VALUES (?,?,?,?)',(u['id'],v['id'],'pending',None)); conn.commit(); conn.close(); return jsonify(ok=True)

@app.get('/api/combat')
def combat_list():
    u,err=require_user()
    if err:return err
    conn=db(); rows=conn.execute("SELECT * FROM combats WHERE (challenger_id=? OR defender_id=?) AND status IN ('pending','active') ORDER BY id DESC",(u['id'],u['id'])).fetchall(); out=[public_combat(conn,r,u['id']) | {'desafiador':conn.execute('SELECT username FROM users WHERE id=?',(r['challenger_id'],)).fetchone()['username'],'sou_desafiador':r['challenger_id']==u['id']} for r in rows]; conn.close(); return jsonify(out)

@app.post('/api/combat/<int:combat_id>/accept')
def combat_accept(combat_id):
    u,err=require_user()
    if err:return err
    conn=db(); c=conn.execute('SELECT * FROM combats WHERE id=?',(combat_id,)).fetchone()
    if not c or c['defender_id']!=u['id'] or c['status']!='pending': conn.close(); return jsonify(error='Desafio inválido.'),400
    a=combat_stats(conn,c['challenger_id']); b=combat_stats(conn,c['defender_id']);
    conn.execute("UPDATE combats SET status='active',turn_user_id=?,challenger_hp=?,defender_hp=?,challenger_ce=?,defender_ce=?,effects_json=?,log_json=? WHERE id=?",(c['challenger_id'],a['HP'],b['HP'],a['CE'],b['CE'],json.dumps({}),json.dumps([f"{u['username']} aceitou o combate."]),combat_id))
    for uid in (c['challenger_id'],c['defender_id']):
        for r in conn.execute('SELECT skill_id FROM user_skills WHERE user_id=?',(uid,)).fetchall():
            conn.execute('INSERT OR IGNORE INTO combat_skills(combat_id,user_id,skill_id) VALUES (?,?,?)',(combat_id,uid,r['skill_id']))
    conn.commit(); conn.close(); return jsonify(ok=True)

@app.post('/api/combat/<int:combat_id>/decline')
def combat_decline(combat_id):
    u,err=require_user()
    if err:return err
    conn=db(); c=conn.execute('SELECT * FROM combats WHERE id=?',(combat_id,)).fetchone()
    if not c or c['defender_id']!=u['id'] or c['status']!='pending': conn.close(); return jsonify(error='Desafio inválido.'),400
    conn.execute("UPDATE combats SET status='declined' WHERE id=?",(combat_id,)); conn.commit(); conn.close(); return jsonify(ok=True)

@app.post('/api/combat/<int:combat_id>/action')
def combat_action(combat_id):
    import random
    u,err=require_user()
    if err:return err
    data=request.get_json(silent=True) or {}; action=str(data.get('action','basic')); sid=int(data.get('skill_id',0) or 0)
    conn=db(); c=conn.execute('SELECT * FROM combats WHERE id=?',(combat_id,)).fetchone()
    if not c or c['status']!='active': conn.close(); return jsonify(error='Combate não está ativo.'),400
    if c['turn_user_id']!=u['id']: conn.close(); return jsonify(error='Ainda não é sua vez.'),400
    mine=c['challenger_id']==u['id']; mehp=float(c['challenger_hp'] if mine else c['defender_hp']); opphp=float(c['defender_hp'] if mine else c['challenger_hp']); mece=float(c['challenger_ce'] if mine else c['defender_ce']); oppce=float(c['defender_ce'] if mine else c['challenger_ce']); effects=combat_effects(c); logs=json.loads(c['log_json'] or '[]')
    target_id=c['defender_id'] if mine else c['challenger_id']; oppkey='d' if mine else 'c'; mekey='c' if mine else 'd'
    effects.setdefault('c',{}); effects.setdefault('d',{})
    if action=='skill':
        if not 1<=sid<=len(SKILLS): conn.close(); return jsonify(error='Skill inválida.'),400
        sk=SKILLS[sid-1]; owned=conn.execute('SELECT 1 FROM combat_skills WHERE combat_id=? AND user_id=? AND skill_id=?',(combat_id,u['id'],sid)).fetchone()
        if not owned or mece<sk[3]: conn.close(); return jsonify(error='Você não possui essa skill neste combate ou não tem CE suficiente.'),400
        mece-=sk[3]; name,cat,ct,ce,kind=sk; dmg=0
        if kind in ('1d4','1d6','2d4','2d6'): dmg=roll(kind)
        elif kind=='1d4x3': effects[oppkey]['dot']=max(effects[oppkey].get('dot',0),3); effects[oppkey]['dot_dmg']=roll('1d4')
        elif kind=='defesa': effects[mekey]['def']=roll('1d4')
        elif kind=='controle': effects[oppkey]['skip']=1
        elif kind in ('buff','buff_d4','buff2','buff_lowhp','upgrade','combo','defesa_d4','defesa2','esquiva','laststand','regen','balance','ce_d4','ce_d6','ce_2d6','cura_d6','cura_2d6','cura_d6_clean'): pass
        if kind=='buff': effects[mekey]['bonus']=effects[mekey].get('bonus',0)+1
        elif kind=='buff_d4': effects[mekey]['next_bonus']=roll('1d4')
        elif kind=='buff2': effects[mekey]['next_bonus']=2
        elif kind=='buff_lowhp': effects[mekey]['lowhp']=True
        elif kind in ('upgrade','combo'): effects[mekey]['upgrade']=True if kind=='upgrade' else effects[mekey].get('upgrade',False)
        elif kind=='defesa_d4': effects[mekey]['def']=roll('1d4')
        elif kind=='defesa2': effects[mekey]['def']=2
        elif kind=='esquiva': effects[mekey]['dodge']=1
        elif kind=='cura_d6': mehp+=roll('1d6')
        elif kind in ('cura_2d6','cura_d6_clean'): mehp+=roll('2d6') if kind=='cura_2d6' else roll('1d6')
        elif kind=='ce_d4': mece+=roll('1d4')
        elif kind=='ce_d6': mece+=roll('1d6')
        elif kind=='ce_2d6': mece+=roll('2d6')
        elif kind=='laststand': effects[mekey]['laststand']=True
        elif kind=='regen': effects[mekey]['regen']=3
        elif kind=='balance': effects[mekey]['balance']=3
        elif kind in ('bleed','poison','burn'): effects[oppkey]['dot']=3 if kind!='poison' else 4; effects[oppkey]['dot_dmg']=roll('1d4')
        elif kind in ('blind','slow','silence','curse','infection','confusion','weak','bind','mental','fragile','taunt','exhaust','sentence'): effects[oppkey][kind]=3 if kind in ('curse','infection') else 1
        elif kind=='drain': stolen=roll('1d4'); oppce=max(0,oppce-stolen); mece+=stolen
        elif kind=='lifedrain': dmg=roll('1d6'); mehp+=dmg/2
        logs.append(f"{u['username']} usou {name}.")
        if dmg:
            if effects[oppkey].get('dodge'): effects[oppkey]['dodge']=0; logs.append('O ataque foi evitado!'); dmg=0
            else:
                dmg+=effects[mekey].pop('bonus',0)+effects[mekey].pop('next_bonus',0)
                if effects[mekey].get('lowhp') and mehp<=combat_stats(conn,u['id'])['HP']*.25: dmg+=2
                if effects[mekey].get('upgrade'): dmg=max(roll('2d4'),dmg); effects[mekey]['upgrade']=False
                red=effects[oppkey].pop('def',0); dmg=max(0,dmg-red); opphp-=dmg; logs.append(f"Dano causado: {dmg:.0f}.")
    else:
        if effects[oppkey].get('dodge'): effects[oppkey]['dodge']=0; logs.append(f"{u['username']} atacou, mas o golpe foi evitado.")
        else:
            dmg=roll('1d4'); dmg+=effects[mekey].pop('bonus',0)+effects[mekey].pop('next_bonus',0); red=effects[oppkey].pop('def',0); dmg=max(0,dmg-red); opphp-=dmg; logs.append(f"{u['username']} usou ATAQUE BÁSICO e causou {dmg:.0f} dano.")
    # efeitos por turno
    for key in (oppkey,):
        e=effects[key]
        if e.get('dot',0)>0:
            tick=e.get('dot_dmg',1); opphp-=tick; e['dot']-=1; logs.append(f"Efeito contínuo causou {tick} dano.")
    if effects[mekey].get('regen',0)>0:
        heal=roll('1d4'); mehp+=heal; effects[mekey]['regen']-=1
    mehp=max(0,mehp); opphp=max(0,opphp); mece=max(0,min(mece,combat_stats(conn,u['id'])['CE'])); oppce=max(0,oppce)
    status=None; turn=target_id
    if opphp<=0:
        status='finished'; turn=None; logs.append(f"{u['username']} venceu o combate!")
    save_combat_state(conn,c,mehp if mine else opphp,opphp if mine else mehp,mece if mine else oppce,oppce if mine else mece,effects,logs,status,turn)
    conn.commit(); fresh=conn.execute('SELECT * FROM combats WHERE id=?',(combat_id,)).fetchone(); out=public_combat(conn,fresh,u['id']); conn.close(); return jsonify(out)

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
    c=conn.execute('SELECT * FROM characters WHERE user_id=?',(u['id'],)).fetchone()
    base={'body':float(c['body'] or 0),'mind':float(c['mind'] or 0),'soul':float(c['soul'] or 0)} if c else {'body':0.0,'mind':0.0,'soul':0.0}
    votes={c:attrs[c]-base[c] for c in CLASSES}
    stats=stats_for(attrs,max(days.values()) if max(days.values())>0 else 1)
    conn.commit(); conn.close()
    return jsonify(usuario=u['username'],atributos=attrs,base=base,votos=votes,dias=days,stats=stats)

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
