import os, sqlite3, json, secrets
from datetime import date, timedelta
from flask import Flask, send_file, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'travessia.db'))
os.makedirs(os.path.dirname(DB_PATH) or BASE_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
CLASSES = ('corpo', 'mente', 'alma')

SKILLS = [
('bola-fogo','Bola de Fogo','elementar',2,10,'1d6 de dano.'),('explosao-ignea','Explosão Ígnea','elementar',3,25,'2d4 de dano.'),('muralha-fogo','Muralha de Fogo','elementar',3,20,'1d4 de dano por 3 turnos.'),('incinerar','Incinerar','elementar',4,40,'2d6 de dano.'),('chama-negra','Chama Negra','elementar',5,50,'2d6 de dano e ignora parte da defesa.'),
('pedrada','Pedrada','elementar',1,5,'1d4 de dano.'),('lanca-pedra','Lança de Pedra','elementar',2,12,'1d6 de dano.'),('terremoto','Terremoto','elementar',4,35,'2d4 de dano e pode atordoar.'),('armadura-terra','Armadura de Terra','elementar',3,20,'Reduz o próximo dano recebido em 1d4.'),('jato-agua','Jato d’Água','elementar',1,5,'1d4 de dano.'),
('onda-violenta','Onda Violenta','elementar',3,25,'2d4 de dano.'),('prisao-agua','Prisão de Água','elementar',4,30,'1d4 de dano e pode impedir a próxima ação.'),('tsunami','Tsunami','elementar',5,60,'2d6 de dano.'),('rajada-vento','Rajada de Vento','elementar',1,5,'1d4 de dano.'),('lamina-vento','Lâmina de Vento','elementar',2,15,'1d6 de dano.'),
('tornado','Tornado','elementar',4,35,'2d4 de dano e pode controlar o alvo.'),('raio','Raio','elementar',2,15,'1d6 de dano.'),('tempestade','Tempestade','elementar',4,40,'2d6 de dano.'),('congelamento','Congelamento','elementar',3,20,'1d4 de dano e pode impedir uma ação.'),('raio-solar','Raio Solar','elementar',5,50,'2d6 de dano.'),
('artes-marciais','Artes Marciais','reforco',1,0,'Ataques básicos causam +1 dano.'),('forca-bruta','Força Bruta','reforco',2,10,'Próximo ataque recebe +1d4 de dano.'),('fortificacao','Fortificação','reforco',2,15,'Reduz o próximo dano recebido em 1d4.'),('cura','Cura','reforco',2,20,'Recupera 1d6 HP.'),('grande-cura','Grande Cura','reforco',4,40,'Recupera 2d6 HP.'),
('segundo-folego','Segundo Fôlego','reforco',3,30,'Recupera 1d6 HP e remove um efeito negativo.'),('voar','Voar','reforco',1,5,'Reduz a chance de ataques físicos por 2 turnos.'),('foco-absoluto','Foco Absoluto','reforco',2,15,'Próximo ataque recebe +2 dano.'),('concentracao','Concentração','reforco',2,10,'Recupera 1d4 CE.'),('meditacao','Meditação','reforco',3,20,'Recupera 1d6 CE.'),
('reservas-energia','Reservas de Energia','reforco',4,30,'Recupera 2d6 CE.'),('adrenalina','Adrenalina','reforco',3,15,'Abaixo de 25% HP, recebe +2 dano.'),('golpe-poderoso','Golpe Poderoso','reforco',2,15,'Próximo ataque sobe uma categoria de dano.'),('combo','Combo','reforco',3,25,'Faz dois ataques de 1d4.'),('agilidade','Agilidade','reforco',2,10,'Chance de evitar completamente o próximo ataque.'),
('postura-defensiva','Postura Defensiva','reforco',2,10,'Reduz dano recebido em 2 por 2 turnos.'),('sobrecarga','Sobrecarga','reforco',4,30,'Próxima skill ofensiva sobe uma categoria.'),('determinacao','Determinação','reforco',3,20,'Se chegaria a 0 HP, fica com 1 HP.'),('regeneracao','Regeneração','reforco',4,25,'Recupera 1d4 HP por 3 turnos.'),('equilibrio','Equilíbrio','reforco',5,30,'Por 3 turnos, causa +2 e recebe -2 dano.'),
('sangramento','Sangramento','enfraquecimento',2,10,'1d4 de dano por 3 turnos.'),('veneno','Veneno','enfraquecimento',3,15,'1d4 de dano por 4 turnos.'),('queimadura','Queimadura','enfraquecimento',2,10,'1d4 de dano no início do próximo turno.'),('congelar','Congelar','enfraquecimento',3,20,'Chance de impedir a próxima ação.'),('atordoamento','Atordoamento','enfraquecimento',3,25,'Chance de perder a próxima ação.'),
('cegueira','Cegueira','enfraquecimento',3,20,'Próximo ataque tem chance de errar.'),('lentidao','Lentidão','enfraquecimento',2,15,'Reduz a capacidade ofensiva por 2 turnos.'),('silencio','Silêncio','enfraquecimento',4,30,'Impede uso de skills por 1 turno.'),('maldicao','Maldição','enfraquecimento',4,35,'Recebe +2 dano de todas as fontes por 3 turnos.'),('infeccao','Infecção','enfraquecimento',3,20,'Recebe +1 dano durante 4 turnos.'),
('confusao','Confusão','enfraquecimento',4,25,'Chance de perder a ação.'),('medo','Medo','enfraquecimento',2,15,'Causa -2 dano por 2 turnos.'),('aprisionamento','Aprisionamento','enfraquecimento',4,30,'Impede ataques físicos por 1 turno.'),('perturbacao-mental','Perturbação Mental','enfraquecimento',3,20,'Próxima skill custa +10 CE.'),('drenagem','Drenagem','enfraquecimento',4,30,'Rouba 1d4 CE.'),
('dreno-vital','Dreno Vital','enfraquecimento',5,40,'1d6 de dano e recupera metade do dano.'),('fragilidade','Fragilidade','enfraquecimento',3,20,'Próximo dano recebido recebe +1d4.'),('provocacao','Provocação','enfraquecimento',2,5,'Oponente é obrigado a usar ataque básico no próximo turno.'),('exaustao','Exaustão','enfraquecimento',4,25,'Próxima skill custa +50% CE.'),('sentenca','Sentença','enfraquecimento',5,50,'Após 3 turnos, causa 2d6 de dano.')]


ENTITY_GRADES = [
    {'grade':'Grade 4','min_streak':0,'chance':1.00,'hp':('20','d4'),'damage':('0','d4'),'ct':0},
    {'grade':'Grade 3','min_streak':30,'chance':0.50,'hp':('30','d6'),'damage':('0','d6'),'ct':1},
    {'grade':'Grade 2','min_streak':60,'chance':1/3,'hp':('50','2d4'),'damage':('0','2d4'),'ct':2},
    {'grade':'Grade 1','min_streak':90,'chance':0.25,'hp':('80','2d6'),'damage':('0','2d6'),'ct':3},
    {'grade':'Special Grade','min_streak':120,'chance':0.20,'hp':('120','2d6'),'damage':('4','2d6'),'ct':4},
    {'grade':'Calamity Grade','min_streak':150,'chance':0.16,'hp':('188','2d6'),'damage':('8','2d6'),'ct':5},
]

def roll_dice(expr):
    import random, re
    total=0
    for part in str(expr).split('+'):
        part=part.strip()
        if not part: continue
        if 'd' in part:
            n,faces=part.split('d',1); n=int(n or 1); faces=int(faces); total += sum(random.randint(1,faces) for _ in range(n))
        else: total += int(part)
    return total

def nearest_int(v): return int(v + 0.5)

def player_xp_reward(player_hp, opponent_hp): return max(0, nearest_int(8 * float(opponent_hp) / max(1.0,float(player_hp))))
def entity_xp_reward(player_hp, monster_hp): return max(0, nearest_int(5 * float(monster_hp) / max(1.0,float(player_hp))))


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def today(): return date.today()
def iso(d): return d.isoformat()
def parse_days(v):
    try:
        return sorted(set(int(x) for x in (v or []) if 0 <= int(x) <= 6))
    except Exception: return list(range(7))

def init_db():
    c=db(); c.executescript('''
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL UNIQUE COLLATE NOCASE,password_hash TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,last_processed_day TEXT,xp INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS characters(user_id INTEGER PRIMARY KEY,body REAL NOT NULL DEFAULT 0,mind REAL NOT NULL DEFAULT 0,soul REAL NOT NULL DEFAULT 0,class_name TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,text TEXT NOT NULL,class TEXT NOT NULL,type TEXT NOT NULL DEFAULT 'todo',frequency_json TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]',FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS completions(task_id INTEGER NOT NULL,day TEXT NOT NULL,PRIMARY KEY(task_id,day),FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS streaks(user_id INTEGER NOT NULL,class TEXT NOT NULL,days INTEGER NOT NULL DEFAULT 0,last_day TEXT,PRIMARY KEY(user_id,class),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS vote_bonuses(user_id INTEGER NOT NULL,class TEXT NOT NULL,bonus REAL NOT NULL DEFAULT 0.5,PRIMARY KEY(user_id,class),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS user_skills(user_id INTEGER NOT NULL,skill_id TEXT NOT NULL,equipped INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,skill_id),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS battles(id INTEGER PRIMARY KEY AUTOINCREMENT,player1 INTEGER NOT NULL,player2 INTEGER NOT NULL,turn_user INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'active',hp1 REAL,ce1 REAL,hp2 REAL,ce2 REAL,log_json TEXT NOT NULL DEFAULT '[]',FOREIGN KEY(player1) REFERENCES users(id),FOREIGN KEY(player2) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS hunts(user_id INTEGER NOT NULL,day TEXT NOT NULL,entities_json TEXT NOT NULL,PRIMARY KEY(user_id,day),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS entity_battles(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,entity_json TEXT NOT NULL,hp_player REAL,ce_player REAL,hp_entity REAL,status TEXT NOT NULL DEFAULT 'active',turn TEXT NOT NULL DEFAULT 'player',log_json TEXT NOT NULL DEFAULT '[]',FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    ''')
    cols=[r['name'] for r in c.execute('PRAGMA table_info(tasks)')]
    if 'frequency_json' not in cols: c.execute("ALTER TABLE tasks ADD COLUMN frequency_json TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]'")
    cols=[r['name'] for r in c.execute('PRAGMA table_info(users)')]
    if 'last_processed_day' not in cols: c.execute('ALTER TABLE users ADD COLUMN last_processed_day TEXT')
    # Every existing vote task gets the immediate +0.5 bonus once.
    for r in c.execute("SELECT DISTINCT user_id,class FROM tasks WHERE type='voto'").fetchall():
        c.execute('INSERT OR IGNORE INTO vote_bonuses(user_id,class,bonus) VALUES (?,?,0.5)',(r['user_id'],r['class']))
    c.commit(); c.close()
init_db()

DEFAULT_STREAKS={x:{'dias':0,'ultimoDia':None} for x in CLASSES}
def current_user():
    uid=session.get('user_id')
    if not uid:return None
    c=db(); u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone(); c.close(); return u

def require_user():
    u=current_user(); return (u,None) if u else (None,(jsonify(error='Faça login para continuar.'),401))

def get_tasks(c,uid):
    out=[]
    for r in c.execute('SELECT * FROM tasks WHERE user_id=? ORDER BY id',(uid,)):
        try: freq=json.loads(r['frequency_json'])
        except Exception: freq=list(range(7))
        out.append({'id':r['id'],'texto':r['text'],'classe':r['class'],'tipo':r['type'],'frequencia':parse_days(freq)})
    return out

def completion_set(c,uid,day):
    return {r['task_id'] for r in c.execute('SELECT c.task_id FROM completions c JOIN tasks t ON t.id=c.task_id WHERE t.user_id=? AND c.day=?',(uid,day))}

def process_until_yesterday(c,user):
    yesterday=today()-timedelta(days=1); last=user['last_processed_day']
    start=(date.fromisoformat(last)+timedelta(days=1)) if last else yesterday
    if start>yesterday:return
    streak={x:{'dias':0,'ultimoDia':None} for x in CLASSES}
    for r in c.execute('SELECT class,days,last_day FROM streaks WHERE user_id=?',(user['id'],)): streak[r['class']]={'dias':int(r['days'] or 0),'ultimoDia':r['last_day']}
    tasks=get_tasks(c,user['id'])
    for i in range((yesterday-start).days+1):
        d=start+timedelta(days=i); done=completion_set(c,user['id'],iso(d)); wd=d.weekday()
        for cls in CLASSES:
            due=[t for t in tasks if t['classe']==cls and wd in t['frequencia']]
            if not due:
                streak[cls]['dias']+=1; streak[cls]['ultimoDia']=iso(d); continue
            vote=next((t for t in due if t['tipo']=='voto'),None); todo=next((t for t in due if t['tipo']=='todo'),None)
            if vote and vote['id'] not in done: streak[cls]={'dias':0,'ultimoDia':None}; continue
            if todo:
                if todo['id'] in done: streak[cls]['dias']+=1; streak[cls]['ultimoDia']=iso(d)
                else: streak[cls]['dias']=max(0,streak[cls]['dias']-1)
            elif vote: streak[cls]['dias']+=1; streak[cls]['ultimoDia']=iso(d)
    for cls,s in streak.items(): c.execute('INSERT INTO streaks(user_id,class,days,last_day) VALUES(?,?,?,?) ON CONFLICT(user_id,class) DO UPDATE SET days=excluded.days,last_day=excluded.last_day',(user['id'],cls,s['dias'],s['ultimoDia']))
    c.execute('UPDATE users SET last_processed_day=? WHERE id=?',(iso(yesterday),user['id']))

def current_day_streaks(c,uid,base):
    out={k:dict(v) for k,v in base.items()}; done=completion_set(c,uid,iso(today())); wd=today().weekday(); tasks=get_tasks(c,uid)
    for cls in CLASSES:
        due=[t for t in tasks if t['classe']==cls and wd in t['frequencia']]
        vote=next((t for t in due if t['tipo']=='voto'),None); todo=next((t for t in due if t['tipo']=='todo'),None)
        if not due:
            out[cls]['dias']=int(out[cls]['dias'])+1
        elif vote and vote['id'] in done:
            out[cls]['dias']=int(out[cls]['dias'])+1
        elif not vote and todo and todo['id'] in done:
            out[cls]['dias']=int(out[cls]['dias'])+1
    return out

def user_payload(u):
    c=db(); process_until_yesterday(c,u); tasks=get_tasks(c,u['id']); done=completion_set(c,u['id'],iso(today()))
    for t in tasks:t['concluida']=t['id'] in done
    s={k:dict(v) for k,v in DEFAULT_STREAKS.items()}
    for r in c.execute('SELECT class,days,last_day FROM streaks WHERE user_id=?',(u['id'],)):s[r['class']]={'dias':r['days'],'ultimoDia':r['last_day']}
    s=current_day_streaks(c,u['id'],s)
    ch=c.execute('SELECT * FROM characters WHERE user_id=?',(u['id'],)).fetchone()
    base={'body':float(ch['body'] or 0),'mind':float(ch['mind'] or 0),'soul':float(ch['soul'] or 0)} if ch else {'body':0.0,'mind':0.0,'soul':0.0}
    bonus={x:0.0 for x in CLASSES}
    for r in c.execute('SELECT class,bonus FROM vote_bonuses WHERE user_id=?',(u['id'],)):bonus[r['class']]=float(r['bonus'])
    c.commit(); c.close()
    return {'tarefas':tasks,'streaks':s,'personagem':None if not ch else {'body':base['body'],'mind':base['mind'],'soul':base['soul'],'classe':ch['class_name']},'votoBonus':bonus}

@app.get('/')
def index():return send_file(os.path.join(BASE_DIR,'index.html'))

@app.post('/api/register')
def register():
    d=request.get_json(silent=True) or {}; username=str(d.get('usuario','')).strip(); password=str(d.get('senha',''))
    if not 3<=len(username)<=40:return jsonify(error='O usuário precisa ter entre 3 e 40 caracteres.'),400
    if not all(x.isalnum() or x in '_.-' for x in username):return jsonify(error='Use apenas letras, números, ponto, hífen ou underline.'),400
    if len(password)<4:return jsonify(error='A senha precisa ter pelo menos 4 caracteres.'),400
    c=db()
    try:
        cur=c.execute('INSERT INTO users(username,password_hash,last_processed_day) VALUES(?,?,?)',(username,generate_password_hash(password),iso(today()-timedelta(days=1)))); uid=cur.lastrowid
        for cls in CLASSES:c.execute('INSERT INTO streaks(user_id,class,days,last_day) VALUES(?,?,0,NULL)',(uid,cls))
        c.commit()
    except sqlite3.IntegrityError:c.rollback();c.close();return jsonify(error='Esse usuário já existe.'),409
    c.close();return jsonify(ok=True)

@app.post('/api/login')
def login():
    d=request.get_json(silent=True) or {}; username=str(d.get('usuario','')).strip(); password=str(d.get('senha',''))
    c=db();u=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone();c.close()
    if not u or not check_password_hash(u['password_hash'],password):return jsonify(error='Usuário ou senha incorretos.'),401
    session.clear();session['user_id']=u['id'];session.permanent=True;return jsonify(ok=True,usuario=u['username'])

@app.get('/api/me')
def me():
    u=current_user();return jsonify(autenticado=bool(u),usuario=u['username'] if u else None)
@app.post('/api/logout')
def logout():session.clear();return jsonify(ok=True)
@app.get('/api/data')
def data():
    u,err=require_user();return err if err else jsonify(user_payload(u))

@app.put('/api/tasks')
def save_tasks():
    u,err=require_user()
    if err:return err
    payload=request.get_json(silent=True) or {}; tasks=payload.get('tarefas',[])
    if not isinstance(tasks,list) or len(tasks)>6:return jsonify(error='Limite de 6 tarefas.'),400
    c=db(); existing={r['id'] for r in c.execute('SELECT id FROM tasks WHERE user_id=?',(u['id'],))}; old_votes={r['class'] for r in c.execute("SELECT class FROM tasks WHERE user_id=? AND type='voto'",(u['id'],))}; kept=set()
    for t in tasks:
        text=str(t.get('texto','')).strip(); cls=t.get('classe'); typ=t.get('tipo','todo'); freq=parse_days(t.get('frequencia'))
        if not text or cls not in CLASSES or typ not in ('todo','voto') or not freq:continue
        tid=t.get('id')
        if tid and int(tid) in existing:
            tid=int(tid);kept.add(tid);c.execute('UPDATE tasks SET text=?,class=?,type=?,frequency_json=? WHERE id=? AND user_id=?',(text,cls,typ,json.dumps(freq),tid,u['id']))
        else:
            cur=c.execute('INSERT INTO tasks(user_id,text,class,type,frequency_json) VALUES(?,?,?,?,?)',(u['id'],text,cls,typ,json.dumps(freq)));tid=cur.lastrowid;kept.add(tid)
    for tid in existing-kept:c.execute('DELETE FROM tasks WHERE id=? AND user_id=?',(tid,u['id']))
    new_votes={r['class'] for r in c.execute("SELECT class FROM tasks WHERE user_id=? AND type='voto'",(u['id'],))}
    for cls in CLASSES:
        if cls in new_votes:c.execute('INSERT INTO vote_bonuses(user_id,class,bonus) VALUES(?,?,0.5) ON CONFLICT(user_id,class) DO UPDATE SET bonus=0.5',(u['id'],cls))
        else:c.execute('DELETE FROM vote_bonuses WHERE user_id=? AND class=?',(u['id'],cls))
    c.commit();c.close();return jsonify(ok=True)

@app.post('/api/tasks/<int:task_id>/complete')
def complete_task(task_id):
    u,err=require_user()
    if err:return err
    c=db();t=c.execute('SELECT * FROM tasks WHERE id=? AND user_id=?',(task_id,u['id'])).fetchone()
    if not t:c.close();return jsonify(error='Tarefa não encontrada.'),404
    ds=iso(today());exists=c.execute('SELECT 1 FROM completions WHERE task_id=? AND day=?',(task_id,ds)).fetchone()
    if exists:c.execute('DELETE FROM completions WHERE task_id=? AND day=?',(task_id,ds));done=False
    else:c.execute('INSERT INTO completions(task_id,day) VALUES(?,?)',(task_id,ds));done=True
    c.commit();c.close();return jsonify(ok=True,concluida=done)

@app.put('/api/character')
def save_character():
    u,err=require_user()
    if err:return err
    p=(request.get_json(silent=True) or {}).get('personagem',{}) or {};body=float(p.get('body',0));mind=float(p.get('mind',0));soul=float(p.get('soul',0));cls=str(p.get('classe',''))
    if any(x<0 or x>3 for x in (body,mind,soul)) or abs(body+mind+soul-3)>0.001:return jsonify(error='A distribuição inicial precisa somar exatamente 3 pontos.'),400
    c=db();c.execute('INSERT INTO characters(user_id,body,mind,soul,class_name) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET body=excluded.body,mind=excluded.mind,soul=excluded.soul,class_name=excluded.class_name',(u['id'],body,mind,soul,cls));c.commit();c.close();return jsonify(ok=True)

def attributes_for(c,uid):
    ch=c.execute('SELECT * FROM characters WHERE user_id=?',(uid,)).fetchone();base={'body':0.0,'mind':0.0,'soul':0.0} if not ch else {'body':float(ch['body'] or 0),'mind':float(ch['mind'] or 0),'soul':float(ch['soul'] or 0)};bonus={x:0.0 for x in CLASSES}
    for r in c.execute('SELECT class,bonus FROM vote_bonuses WHERE user_id=?',(uid,)):bonus[r['class']]=float(r['bonus'])
    eff={'body':base['body']+bonus['corpo'],'mind':base['mind']+bonus['mente'],'soul':base['soul']+bonus['alma']}
    return base,bonus,eff,ch

def stats_for(attrs,days):
    days=max(1,int(days or 1));F=lambda a:30/((1+a/10)*days+30);fb,fm,fs=F(attrs['body']),F(attrs['mind']),F(attrs['soul'])
    return {'F':{'corpo':fb,'mente':fm,'alma':fs},'HP':200*(1-fb),'ATK':200*(1-fb)/10,'CE':1000*(1-fs),'CT':1/fm}

@app.get('/api/profile')
def profile():
    u,err=require_user()
    if err:return err
    c=db();process_until_yesterday(c,u);vals={x:{'dias':0,'ultimoDia':None} for x in CLASSES}
    for r in c.execute('SELECT class,days,last_day FROM streaks WHERE user_id=?',(u['id'],)):vals[r['class']]={'dias':int(r['days']),'ultimoDia':r['last_day']}
    vals=current_day_streaks(c,u['id'],vals);days={x:int(vals[x]['dias']) for x in CLASSES};base,bonus,eff,ch=attributes_for(c,u['id']);stats=stats_for(eff,max(days.values()) if max(days.values()) else 1);c.commit();c.close()
    return jsonify(usuario=u['username'],base=base,voto=bonus,atributos=eff,dias=days,stats=stats)

@app.get('/api/skills')
def skills():
    u,err=require_user()
    if err:return err
    c=db(); owned={r['skill_id']:bool(r['equipped']) for r in c.execute('SELECT skill_id,equipped FROM user_skills WHERE user_id=?',(u['id'],))}
    xp=int(u['xp'] or 0); ct=current_ct(c,u['id'])
    out=[]
    for sid,name,cat,skill_ct,ce,effect in SKILLS:
        cost={1:50,2:100,3:175,4:275,5:400}[skill_ct]
        acquired=sid in owned
        out.append({'id':sid,'nome':name,'categoria':cat,'ct':skill_ct,'ce':ce,'efeito':effect,'preco_xp':cost,'adquirida':acquired,'pode_comprar':(not acquired and skill_ct<=ct and xp>=cost),'equipada':owned.get(sid,False)})
    c.close();return jsonify(skills=out,xp=xp,ct=ct)

@app.post('/api/skills/<skill_id>/buy')
def buy_skill(skill_id):
    u,err=require_user()
    if err:return err
    item=next((x for x in SKILLS if x[0]==skill_id),None)
    if not item:return jsonify(error='Skill não encontrada.'),404
    cost={1:50,2:100,3:175,4:275,5:400}[item[3]]
    c=db();
    if c.execute('SELECT 1 FROM user_skills WHERE user_id=? AND skill_id=?',(u['id'],skill_id)).fetchone(): c.close();return jsonify(error='Você já possui essa skill.'),400
    if item[3]>current_ct(c,u['id']): c.close();return jsonify(error='CT insuficiente para comprar essa skill.'),400
    if int(u['xp'] or 0)<cost: c.close();return jsonify(error='XP insuficiente.'),400
    c.execute('UPDATE users SET xp=xp-? WHERE id=?',(cost,u['id']))
    c.execute('INSERT INTO user_skills(user_id,skill_id,equipped) VALUES(?,?,0)',(u['id'],skill_id));c.commit();c.close();return jsonify(ok=True,xp_gasto=cost)

@app.post('/api/skills/<skill_id>/toggle')
def toggle_skill(skill_id):
    u,err=require_user()
    if err:return err
    item=next((x for x in SKILLS if x[0]==skill_id),None)
    if not item:return jsonify(error='Skill não encontrada.'),404
    c=db();row=c.execute('SELECT equipped FROM user_skills WHERE user_id=? AND skill_id=?',(u['id'],skill_id)).fetchone()
    if not row:c.close();return jsonify(error='Compre essa skill primeiro.'),400
    c.execute('UPDATE user_skills SET equipped=? WHERE user_id=? AND skill_id=?',(0 if row['equipped'] else 1,u['id'],skill_id))
    # CT cap
    total=sum(next(x[3] for x in SKILLS if x[0]==r['skill_id']) for r in c.execute('SELECT skill_id FROM user_skills WHERE user_id=? AND equipped=1',(u['id'],)))
    c.rollback() if total>current_ct(c,u['id']) else c.commit()
    if total>current_ct(c,u['id']):c.close();return jsonify(error='Você não possui CT suficiente para equipar essa combinação.'),400
    equipped=[r['skill_id'] for r in c.execute('SELECT skill_id FROM user_skills WHERE user_id=? AND equipped=1',(u['id'],))];c.close();return jsonify(ok=True,equipadas=equipped)

def current_ct(c,uid):
    ch=c.execute('SELECT * FROM characters WHERE user_id=?',(uid,)).fetchone();mind=float(ch['mind'] or 0) if ch else 0;bonus=float(c.execute("SELECT COALESCE(SUM(bonus),0) b FROM vote_bonuses WHERE user_id=? AND class='mente'",(uid,)).fetchone()['b']);attrs={'body':0,'mind':mind+bonus,'soul':0};days=max([int(r['days']) for r in c.execute('SELECT days FROM streaks WHERE user_id=?',(uid,))] or [1]);return stats_for(attrs,days)['CT']

@app.get('/api/leaderboard')
def leaderboard():
    c=db();result=[]
    for u in c.execute('SELECT * FROM users ORDER BY username'):
        process_until_yesterday(c,u);vals={x:{'dias':0} for x in CLASSES}
        for r in c.execute('SELECT class,days FROM streaks WHERE user_id=?',(u['id'],)):vals[r['class']]={'dias':int(r['days'])}
        vals=current_day_streaks(c,u['id'],vals);a=[int(vals[x]['dias']) for x in CLASSES];result.append({'usuario':u['username'],'corpo':a[0],'mente':a[1],'alma':a[2],'total':sum(a)})
    c.commit();c.close();result.sort(key=lambda x:(-x['total'],-max(x['corpo'],x['mente'],x['alma']),x['usuario'].lower()));return jsonify(result)


def skill_dict(skill_id):
    x=next((x for x in SKILLS if x[0]==skill_id),None)
    if not x:return None
    return {'id':x[0],'nome':x[1],'categoria':x[2],'ct':x[3],'ce':x[4],'efeito':x[5]}

def battle_stats(c,uid):
    base,bonus,eff,ch=attributes_for(c,uid)
    days=max([int(r['days']) for r in c.execute('SELECT days FROM streaks WHERE user_id=?',(uid,))] or [1])
    return stats_for(eff,days)

@app.get('/api/entities')
def entities():
    u,err=require_user()
    if err:return err
    c=db(); days=max([int(r['days']) for r in c.execute('SELECT days FROM streaks WHERE user_id=?',(u['id'],))] or [0]); import random
    row=c.execute('SELECT entities_json FROM hunts WHERE user_id=? AND day=?',(u['id'],iso(today()))).fetchone()
    if row:
        out=json.loads(row['entities_json']); c.close(); return jsonify(usou=True,entidades=out,streak=days)
    eligible=[g for g in ENTITY_GRADES if days>=g['min_streak']]
    out=[]
    for g in eligible:
        if g['grade']=='Grade 4' or random.random()<=g['chance']:
            hp=roll_dice(g['hp'][0]+'+'+g['hp'][1]); damage=roll_dice(g['damage'][0]+'+'+g['damage'][1])
            pool=[x for x in SKILLS if x[3]<=g['ct']]
            skills=[]
            if g['ct']==1 and pool: skills=[random.choice(pool)]
            elif g['ct']>=2 and pool:
                skills=random.sample(pool,min(len(pool),random.randint(1,min(3,len(pool)))))
            out.append({'grade':g['grade'],'streak':days,'hp':hp,'damage':damage,'ct':g['ct'],'multiplayer':g['ct']>=3,'skills':[{'id':x[0],'nome':x[1],'ce':x[4],'efeito':x[5]} for x in skills]})
    c.execute('INSERT INTO hunts(user_id,day,entities_json) VALUES(?,?,?)',(u['id'],iso(today()),json.dumps(out,ensure_ascii=False)));c.commit();c.close()
    return jsonify(usou=True,entidades=out,streak=days)

@app.post('/api/hunt')
def hunt():
    u,err=require_user()
    if err:return err
    # Calling this endpoint consumes today's hunt and reveals the persisted list.
    c=db(); row=c.execute('SELECT 1 FROM hunts WHERE user_id=? AND day=?',(u['id'],iso(today()))).fetchone(); c.close()
    if row:return entities()
    return entities()

@app.post('/api/entity-battles')
def start_entity_battle():
    u,err=require_user()
    if err:return err
    d=request.get_json(silent=True) or {}; entity=d.get('entity')
    if not isinstance(entity,dict) or not entity.get('grade'): return jsonify(error='Maldição inválida.'),400
    c=db(); row=c.execute('SELECT entities_json FROM hunts WHERE user_id=? AND day=?',(u['id'],iso(today()))).fetchone()
    if not row:c.close();return jsonify(error='Use CAÇAR MALDIÇÃO primeiro.'),400
    valid=json.loads(row['entities_json']);
    if not any(json.dumps(entity,sort_keys=True)==json.dumps(x,sort_keys=True) for x in valid):c.close();return jsonify(error='Essa maldição não pertence à sua caça de hoje.'),400
    base,bonus,eff,ch=attributes_for(c,u['id']); days=max([int(r['days']) for r in c.execute('SELECT days FROM streaks WHERE user_id=?',(u['id'],))] or [1]); st=stats_for(eff,days)
    cur=c.execute('INSERT INTO entity_battles(user_id,entity_json,hp_player,ce_player,hp_entity,status,turn,log_json) VALUES(?,?,?,?,?,?,?,?)',(u['id'],json.dumps(entity,ensure_ascii=False),st['HP'],st['CE'],float(entity['hp']),'active','player',json.dumps([]))); bid=cur.lastrowid;c.commit();c.close();return jsonify(id=bid)

@app.get('/api/entity-battles/<int:bid>')
def get_entity_battle(bid):
    u,err=require_user()
    if err:return err
    c=db();b=c.execute('SELECT * FROM entity_battles WHERE id=? AND user_id=?',(bid,u['id'])).fetchone()
    if not b:c.close();return jsonify(error='Combate não encontrado.'),404
    e=json.loads(b['entity_json']); log=json.loads(b['log_json']); c.close();return jsonify(id=bid,entity=e,seu_hp=float(b['hp_player']),seu_ce=float(b['ce_player']),inimigo_hp=float(b['hp_entity']),status=b['status'],meu_turno=b['turn']=='player',log=log[-8:])

@app.post('/api/entity-battles/<int:bid>/action')
def entity_battle_action(bid):
    u,err=require_user()
    if err:return err
    import random
    d=request.get_json(silent=True) or {}; c=db(); b=c.execute('SELECT * FROM entity_battles WHERE id=? AND user_id=?',(bid,u['id'])).fetchone()
    if not b:c.close();return jsonify(error='Combate não encontrado.'),404
    if b['status']!='active':c.close();return jsonify(error='Esse combate já terminou.'),400
    if b['turn']!='player':c.close();return jsonify(error='Aguarde o turno da maldição.'),400
    e=json.loads(b['entity_json']); hp=float(b['hp_player']); ce=float(b['ce_player']); ehp=float(b['hp_entity']); log=json.loads(b['log_json']); sid=d.get('skill_id'); dmg=0
    if sid:
        sk=skill_dict(sid); owned=c.execute('SELECT 1 FROM user_skills WHERE user_id=? AND skill_id=? AND equipped=1',(u['id'],sid)).fetchone()
        if not sk or not owned:c.close();return jsonify(error='Skill inválida ou não equipada.'),400
        if ce<sk['ce']:c.close();return jsonify(error='CE insuficiente.'),400
        ce-=sk['ce'];
        if '2d6' in sk['efeito']:dmg=random.randint(1,6)+random.randint(1,6)
        elif '2d4' in sk['efeito']:dmg=random.randint(1,4)+random.randint(1,4)
        elif '1d6' in sk['efeito']:dmg=random.randint(1,6)
        elif '1d4' in sk['efeito']:dmg=random.randint(1,4)
        log.append(f'Você usou {sk["nome"]} e causou {dmg} dano.')
    else:dmg=random.randint(1,4);log.append(f'Você atacou e causou {dmg} dano.')
    ehp=max(0,ehp-dmg)
    if ehp<=0:
        reward=entity_xp_reward(hp,e['hp']); c.execute('UPDATE users SET xp=xp+? WHERE id=?',(reward,u['id'])); log.append(f'Maldição derrotada! +{reward} XP.'); status='finished'; turn='player'
    else:
        edmg=int(e['damage']); hp=max(0,hp-edmg); log.append(f'{e["grade"]} causou {edmg} dano.') ; status='finished' if hp<=0 else 'active'; turn='player'
        if hp<=0: log.append('Você foi derrotado.');
    c.execute('UPDATE entity_battles SET hp_player=?,ce_player=?,hp_entity=?,status=?,turn=?,log_json=? WHERE id=?',(hp,ce,ehp,status,turn,json.dumps(log,ensure_ascii=False),bid));c.commit();c.close();return jsonify(ok=True)

@app.get('/api/battles')
def list_battles():
    u,err=require_user()
    if err:return err
    c=db();out=[]
    for b in c.execute("SELECT * FROM battles WHERE status='active' AND (player1=? OR player2=?) ORDER BY id DESC",(u['id'],u['id'])):
        mine=b['hp1'] if b['player1']==u['id'] else b['hp2']; ce=b['ce1'] if b['player1']==u['id'] else b['ce2']; opp=b['player2'] if b['player1']==u['id'] else b['player1']; on=c.execute('SELECT username FROM users WHERE id=?',(opp,)).fetchone()['username'];out.append({'id':b['id'],'oponente':on,'seu_hp':mine,'seu_ce':ce})
    c.close();return jsonify(out)

@app.post('/api/battles')
def create_battle():
    u,err=require_user()
    if err:return err
    name=str((request.get_json(silent=True) or {}).get('oponente','')).strip();c=db();opp=c.execute('SELECT * FROM users WHERE username=?',(name,)).fetchone()
    if not opp:c.close();return jsonify(error='Adversário não encontrado.'),404
    if opp['id']==u['id']:c.close();return jsonify(error='Você não pode desafiar a si mesmo.'),400
    s1=battle_stats(c,u['id']);s2=battle_stats(c,opp['id'])
    cur=c.execute('INSERT INTO battles(player1,player2,turn_user,status,hp1,ce1,hp2,ce2,log_json) VALUES(?,?,?,?,?,?,?,?,?)',(u['id'],opp['id'],u['id'],'active',s1['HP'],s1['CE'],s2['HP'],s2['CE'],json.dumps([f'{u["username"]} iniciou o combate.'])))
    c.commit();bid=cur.lastrowid;c.close();return jsonify(id=bid)

@app.get('/api/battles/<int:bid>')
def get_battle(bid):
    u,err=require_user()
    if err:return err
    c=db();b=c.execute('SELECT * FROM battles WHERE id=? AND (player1=? OR player2=?)',(bid,u['id'],u['id'])).fetchone()
    if not b:c.close();return jsonify(error='Combate não encontrado.'),404
    me1=b['player1']==u['id']; opp=b['player2'] if me1 else b['player1']; myhp=b['hp1'] if me1 else b['hp2']; myce=b['ce1'] if me1 else b['ce2']; ohp=b['hp2'] if me1 else b['hp1']; names=[c.execute('SELECT username FROM users WHERE id=?',(x,)).fetchone()['username'] for x in (b['player1'],b['player2'])]
    skills=[]
    for r in c.execute('SELECT skill_id FROM user_skills WHERE user_id=? AND equipped=1',(u['id'],)):
        d=skill_dict(r['skill_id']);
        if d:skills.append(d)
    try:log=json.loads(b['log_json'])
    except:log=[]
    c.close();return jsonify(id=bid,jogador1=names[0],jogador2=names[1],status=b['status'],meu_turno=b['turn_user']==u['id'],seu_hp=float(myhp),seu_ce=float(myce),inimigo_hp=float(ohp),skills=skills,log=log[-6:])

@app.post('/api/battles/<int:bid>/action')
def battle_action(bid):
    u,err=require_user()
    if err:return err
    d=request.get_json(silent=True) or {};sid=d.get('skill_id');c=db();b=c.execute('SELECT * FROM battles WHERE id=? AND (player1=? OR player2=?)',(bid,u['id'],u['id'])).fetchone()
    if not b:c.close();return jsonify(error='Combate não encontrado.'),404
    if b['status']!='active':c.close();return jsonify(error='Esse combate já terminou.'),400
    if b['turn_user']!=u['id']:c.close();return jsonify(error='Ainda não é o seu turno.'),400
    me1=b['player1']==u['id']; myhp=float(b['hp1'] if me1 else b['hp2']);myce=float(b['ce1'] if me1 else b['ce2']);ohp=float(b['hp2'] if me1 else b['hp1']);ohp_before=ohp;opp=b['player2'] if me1 else b['player1'];
    import random
    if sid:
        sk=skill_dict(sid)
        if not sk:c.close();return jsonify(error='Skill inválida.'),400
        owned=c.execute('SELECT 1 FROM user_skills WHERE user_id=? AND skill_id=? AND equipped=1',(u['id'],sid)).fetchone()
        if not owned:c.close();return jsonify(error='Essa skill não está equipada.'),400
        if myce<sk['ce']:c.close();return jsonify(error='CE insuficiente.'),400
        myce-=sk['ce'];rolls=[]
        if '2d6' in sk['efeito']:rolls=[random.randint(1,6),random.randint(1,6)]
        elif '2d4' in sk['efeito']:rolls=[random.randint(1,4),random.randint(1,4)]
        elif '1d6' in sk['efeito']:rolls=[random.randint(1,6)]
        elif '1d4' in sk['efeito']:rolls=[random.randint(1,4)]
        dmg=sum(rolls) if rolls else 0;ohp=max(0,ohp-dmg);msg=f'{u["username"]} usou {sk["nome"]} e causou {dmg} dano.'
    else:
        dmg=random.randint(1,4);ohp=max(0,ohp-dmg);msg=f'{u["username"]} atacou e causou {dmg} dano.'
    try:log=json.loads(b['log_json'])
    except:log=[]
    log.append(msg)
    status='active';turn=opp
    if ohp<=0:
        status='finished';turn=u['id'];reward=player_xp_reward(myhp,ohp_before) if ohp_before>0 else 0
        c.execute('UPDATE users SET xp=xp+? WHERE id=?',(reward,u['id']));log.append(f'{u["username"]} venceu o combate e ganhou {reward} XP!')
    if me1:c.execute('UPDATE battles SET hp1=?,ce1=?,hp2=?,turn_user=?,status=?,log_json=? WHERE id=?',(myhp,myce,ohp,turn,status,json.dumps(log),bid))
    else:c.execute('UPDATE battles SET hp2=?,ce2=?,hp1=?,turn_user=?,status=?,log_json=? WHERE id=?',(myhp,myce,ohp,turn,status,json.dumps(log),bid))
    c.commit();c.close();return jsonify(ok=True)

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=True)
