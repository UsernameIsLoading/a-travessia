import os, sqlite3, json, secrets
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
from datetime import date, timedelta
from flask import Flask, send_file, request, jsonify, session, Response
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'travessia.db'))
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '1984')
MASTER_USERNAME = '__ADMIN_MASTER__'
if not DATABASE_URL:
    os.makedirs(os.path.dirname(DB_PATH) or BASE_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
CLASSES = ('corpo', 'mente', 'alma')

# Progressão fixa: os números não explodem com o tempo.
GRADE_STATS = [
    ('Grade 4', 0, 70, 250, 3),
    ('Grade 3', 7, 90, 400, 4),
    ('Grade 2', 30, 115, 550, 6),
    ('Grade 1', 90, 150, 750, 8),
    ('Special Grade', 180, 200, 1000, 10),
]

# Identidade visual da Skill Tree. As imagens são referências externas; o site
# continua funcionando mesmo se uma imagem externa estiver indisponível.
TREE_META = {
 'shrine': ('Ryomen Sukuna','Tenha orgulho. Você é forte.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Sukuna.png','Malevolent Shrine'),
 'limitless': ('Satoru Gojo','Através do céu a terra, apenas eu sou o honrado.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Satoru%20Gojo%20%28Anime%29.png','Unlimited Void'),
 'ten-shadows': ('Megumi Fushiguro','Com minha própria vida, salvarei as pessoas de forma desigual.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Megumi%20Fushiguro%20%28Anime%29.png','Chimera Shadow Garden'),
 'cursed-spirit-manipulation': ('Suguru Geto','Você é o mais forte porque é Satoru Gojo? Ou você é Satoru Gojo porque é o mais forte?','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Suguru%20Geto.png','—'),
 'idle-transfiguration': ('Mahito','A vida não tem peso ou valor particular.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Mahito.png','Self-Embodiment of Perfection'),
 'straw-doll': ('Nobara Kugisaki','Eu sou Nobara Kugisaki.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Nobara%20Kugisaki%20%28Anime%29.png','—'),
 'ratio': ('Kento Nanami','Trabalho é uma merda.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Kento%20Nanami.png','—'),
 'projection': ('Naobito Zenin','Eu sou o feiticeiro mais rápido da família Zenin.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Naobito%20Zenin.png','—'),
 'blood': ('Choso','Eu sou seu irmão mais velho.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Choso.png','—'),
 'boogie-woogie': ('Aoi Todo','O ato do aplauso é uma aclamação da alma!','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Aoi%20Todo%20%28Anime%29.png','—'),
 'cursed-speech': ('Toge Inumaki','Salmão.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Toge%20Inumaki%20%28Anime%29.png','—'),
 'copy': ('Yuta Okkotsu','Rika.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Yuta%20Okkotsu%20%28Anime%29.png','Authentic Mutual Love'),
 'construction': ('Yorozu','Eu vou me casar com você.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Yorozu.png','Threefold Affliction'),
 'star-rage': ('Yuki Tsukumo','Que tipo de garota você gosta?','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Yuki%20Tsukumo%20%28Anime%29.png','—'),
 'sky': ('Takako Uro','Eu odeio a luz do sol.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Takako%20Uro.png','—'),
 'granite-blast': ('Ryu Ishigori','A vida não tem sabor.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Ryu%20Ishigori.png','—'),
 'comedian': ('Fumihiko Takaba','Se eu não achar engraçado, não tem graça.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Fumihiko%20Takaba.png','—'),
 'technique-extinguishment': ('Hana Kurusu / Angel','Devolva Megumi para mim!','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Hana%20Kurusu%20%28Anime%29.png','—'),
 'inverse': ('Jiro Awasaka','Eu sou um homem que sobrevive.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Jiro%20Awasaka.png','—'),
 'seance': ('Ogami','Eu trouxe de volta um feiticeiro.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Ogami.png','—'),
 'puppet': ('Kokichi Muta','Encontre sua felicidade.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Kokichi%20Muta%20%28Anime%29.png','—'),
 'auspicious-beasts': ('Takuma Ino','Eu vou dar o meu melhor.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Takuma%20Ino%20%28Anime%29.png','—'),
 'rot': ('Eso','Nós somos irmãos.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Eso.png','—'),
 'cloning': ('Clone User','Uma técnica pode ser usada de muitas formas.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Jujutsu%20Kaisen.png','—'),
 'miracles': ('Haruta Shigemo','Eu sempre tive sorte.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Haruta%20Shigemo.png','—'),
 'ice': ('Uraume','Sukuna-sama.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Uraume%20%28Anime%29.png','—'),
 'disaster-flames': ('Jogo','Eu sou um espírito amaldiçoado.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Jogo.png','Coffin of the Iron Mountain'),
 'disaster-plants': ('Hanami','Os humanos precisam desaparecer.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Hanami.png','—'),
 'disaster-tides': ('Dagon','Eu nasci do medo do mar.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Dagon.png','Horizon of the Captivating Skandha'),
 'contractual-recreation': ('Reggie Star','Eu não sou um homem de promessas vazias.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Reggie%20Star.png','—'),
 'love-rendezvous': ('Kirara Hoshi','Eu não quero perder meu tempo.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Kirara%20Hoshi.png','—'),
 'solo-forbidden-area': ('Utahime Iori','Não subestime os feiticeiros de Kyoto.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Utahime%20Iori%20%28Anime%29.png','—'),
 'black-bird': ('Mei Mei','Dinheiro é tudo que importa.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Mei%20Mei.png','—'),
 'mythical-beast-amber': ('Hajime Kashimo','Eu estava esperando por você.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Hajime%20Kashimo.png','—'),
 'prayer-song': ('Prayer Song User','—','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Jujutsu%20Kaisen.png','—'),
 'antigravity': ('Kenjaku','A evolução humana é fascinante.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Kenjaku.png','Womb Profusion'),
 'light': ('Miguel','Eu não tenho tempo para isso.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Miguel.png','—'),
 'yuji': ('Yuji Itadori','Eu sou só um feiticeiro.','https://jujutsu-kaisen.fandom.com/wiki/Special:Redirect/file/Yuji%20Itadori%20%28Anime%29.png','Domain Expansion'),
}
DOMAIN_ONLY = {'smallpox','deadly-sentencing','idle-death-gamble','womb-profusion','threefold-affliction','authentic-mutual-love','hanami-domain','dabura-domain','yuji-domain'}
SKILL_TREE_NAMES = {k:v[0] for k,v in TREE_META.items()}
SKILL_TREE_OPTIONS_TEXT = {k:v[0] for k,v in TREE_META.items() if k not in DOMAIN_ONLY}
DOMAIN_NODE_NAMES = {
 'smallpox':'Smallpox Deity Domain','deadly-sentencing':'Deadly Sentencing','idle-death-gamble':'Idle Death Gamble',
 'womb-profusion':'Womb Profusion','threefold-affliction':'Threefold Affliction','authentic-mutual-love':'Authentic Mutual Love',
 'hanami-domain':'Hanami Domain','dabura-domain':'Dabura Domain','yuji-domain':'Yuji Domain'
}
DOMAIN_NODE_MAP = {
 'shrine':'Malevolent Shrine','limitless':'Unlimited Void','ten-shadows':'Chimera Shadow Garden',
 'cursed-spirit-manipulation':'—','idle-transfiguration':'Self-Embodiment of Perfection','copy':'Authentic Mutual Love',
 'construction':'Threefold Affliction','technique-extinguishment':'—','disaster-flames':'Coffin of the Iron Mountain',
 'disaster-tides':'Horizon of the Captivating Skandha','antigravity':'Womb Profusion','deadly-sentencing':'Deadly Sentencing',
 'idle-death-gamble':'Idle Death Gamble','hanami-domain':'Hanami Domain','dabura-domain':'Dabura Domain','yuji-domain':'Yuji Domain'
}

# id, name, category, CT, CE, effect, tree
SKILL_DATA = [
('dismantle','Desmantelar','ofensiva',1,5,'Dano baixo: 1 + 1d4.','shrine'),
('cleave','Fatiar','ofensiva',2,20,'Dano comum: 2 + 1d6.','shrine'),
('spiderweb','Teia de Aranha','controle',3,80,'Dano alto: 3 + 2d4 e reduz a precisão do alvo.','shrine'),
('furnace','Fornalha','maxima',4,240,'Dano muito alto: 4 + 2d6; deixa o alvo queimando.','shrine'),
('blue','Azul','espacial',1,5,'Puxa o alvo e causa dano baixo: 1 + 1d4.','limitless'),
('red','Vermelho','espacial',2,20,'Repulsão; dano comum: 2 + 1d6.','limitless'),
('hollow-purple','Vazio Roxo','maxima',4,240,'Dano muito alto: 4 + 2d6 e ignora parte da defesa.','limitless'),
('divine-dogs','Cães Divinos','invocacao',1,5,'Invoca um shikigami para causar dano baixo.','ten-shadows'),
('nue','Nue','invocacao',2,20,'Ataque aéreo; dano comum e chance de atordoar.','ten-shadows'),
('max-elephant','Max Elephant','invocacao',2,20,'Jato de água e pressão; dano comum.','ten-shadows'),
('rabbit-escape','Rabbit Escape','invocacao',1,5,'Cria múltiplas distrações e reduz a precisão do alvo.','ten-shadows'),
('piercing-ox','Piercing Ox','invocacao',3,80,'Investida; dano alto: 3 + 2d4.','ten-shadows'),
('mahoraga','Mahoraga','maxima',4,240,'Adaptação; após sobreviver a um efeito, ganha resistência a ele.','ten-shadows'),
('uzumaki','Uzumaki','maxima',4,240,'Dano muito alto: 4 + 2d6 usando energia de espíritos acumulados.','cursed-spirit-manipulation'),
('curse-command','Espíritos Amaldiçoados','invocacao',1,5,'Invoca um espírito para aplicar um efeito de controle.','cursed-spirit-manipulation'),
('idle-transfiguration','Transfiguração Ociosa','alma',2,20,'Altera a forma da alma; dano comum e pode aplicar técnica bloqueada.','idle-transfiguration'),
('resonance','Ressonância','ofensiva',2,20,'Ataque à distância; dano comum e ignora parte da defesa.','straw-doll'),
('hairpin','Hairpin','ofensiva',3,80,'Explosão retardada; dano alto: 3 + 2d4.','straw-doll'),
('ratio-strike','Golpe de Proporção','ofensiva',1,5,'Dano baixo com chance aumentada de crítico.','ratio'),
('collapse','Colapso','ofensiva',3,80,'Ataca uma proporção marcada; dano alto.','ratio'),
('projection','Feitiçaria de Projeção','controle',2,20,'Acelera o usuário e pode fazer o alvo perder o próximo turno.','projection'),
('blood-formation','Formação de Sangue','ofensiva',1,5,'Dano baixo e aplica sangramento.','blood'),
('piercing-blood','Perfuração de Sangue','ofensiva',3,80,'Dano alto: 3 + 2d4 e sangramento.','blood'),
('supernova','Supernova','maxima',4,240,'Explosão de sangue; dano muito alto.','blood'),
('boogie-woogie','Boogie Woogie','versatil',2,20,'Troca posições; pode anular o próximo ataque recebido.','boogie-woogie'),
('cursed-speech','Fala Amaldiçoada','controle',2,20,'Comando curto; pode impedir a próxima ação do alvo.','cursed-speech'),
('copy','Copy','versatil',3,80,'Replica uma técnica já conhecida por tempo limitado.','copy'),
('construction','Construção','versatil',2,20,'Cria um objeto; pode gerar vantagem defensiva ou ofensiva.','construction'),
('star-rage','Star Rage','ofensiva',3,80,'Massa virtual; dano alto: 3 + 2d4.','star-rage'),
('sky-manipulation','Manipulação do Céu','espacial',2,20,'Distorce o espaço e reduz a precisão do próximo ataque.','sky'),
('granite-blast','Granite Blast','ofensiva',3,80,'Rajada de energia; dano alto: 3 + 2d4.','granite-blast'),
('comedian','Comedian','especial',4,240,'Se o usuário considerar a situação engraçada, pode anular o último efeito sofrido.','comedian'),
('jacobs-ladder','Escada de Jacó','anulacao',4,240,'Apaga técnicas amaldiçoadas ativas; dano muito alto.','technique-extinguishment'),
('inverse','Inverse','defensiva',2,20,'Inverte parte do dano recebido, reduzindo ataques fortes.','inverse'),
('seance','Séance','versatil',3,80,'Assume temporariamente características de um espírito invocado.','seance'),
('puppet-manipulation','Manipulação de Marionetes','invocacao',2,20,'Controla uma marionete para causar dano comum.','puppet'),
('auspicious-beasts','Bestas Auspiciosas','invocacao',2,20,'Invoca uma das Bestas Auspiciosas com efeito variável.','auspicious-beasts'),
('rot-technique','Técnica Rot','ofensiva',2,20,'Aplica decomposição progressiva; dano comum e dano residual.','rot'),
('cloning-technique','Técnica de Clonagem','versatil',2,20,'Cria um clone com parte do poder do usuário.','cloning'),
('miracles','Milagres','especial',2,20,'Armazena pequenos milagres e evita um resultado ruim uma vez.','miracles'),
('ice-formation','Formação de Gelo','controle',2,20,'Congela o alvo e pode impedir sua próxima ação.','ice'),
('maximum-ice','Formação de Gelo Máxima','maxima',4,240,'Dano muito alto e congelamento.','ice'),
('ember-insects','Insetos de Brasa','ofensiva',2,20,'Dano comum e queimadura.','disaster-flames'),
('meteor','Meteoro','maxima',4,240,'Dano muito alto: 4 + 2d6.','disaster-flames'),
('bud-flower','Broto de Flores','controle',2,20,'Cria raízes e reduz a precisão do alvo.','disaster-plants'),
('water-shikigami','Shikigami Aquático','invocacao',2,20,'Dano comum e pressão de água.','disaster-tides'),
('contractual-recreation','Recriação Contratual','versatil',2,20,'Materializa algo representado por um recibo/contrato.','contractual-recreation'),
('love-rendezvous','Love Rendezvous','controle',2,20,'Marca posições e limita como alvos podem se aproximar.','love-rendezvous'),
('solo-forbidden-area','Solo Forbidden Area','reforco',3,80,'Aumenta a eficiência da energia amaldiçoada de aliados próximos.','solo-forbidden-area'),
('bird-strike','Bird Strike','ofensiva',3,80,'Ataque suicida de corvo; dano alto.','black-bird'),
('mythical-beast-amber','Mythical Beast Amber','maxima',4,240,'Descarga de energia; dano muito alto, com alto custo.','mythical-beast-amber'),
('prayer-song','Prayer Song','reforco',2,20,'Aprimora o usuário por meio de um cântico.','prayer-song'),
('antigravity','Antigravity System','defensiva',3,80,'Manipula a gravidade para reduzir dano e controlar o campo.','antigravity'),
('black-flash','Black Flash','ofensiva',3,80,'Golpe de energia precisa; dano alto e grande chance de crítico.','yuji'),
]
SKILLS = [(a,b,c,d,e,f) for a,b,c,d,e,f,_ in SKILL_DATA]
SKILL_TREE_BY_ID = {x[0]:x[6] for x in SKILL_DATA}
SKILL_PREREQS = {
 'cleave':['dismantle'],'spiderweb':['cleave'],'furnace':['dismantle','cleave'],
 'red':['blue'],'hollow-purple':['blue','red'],'mahoraga':['divine-dogs','nue','max-elephant','rabbit-escape','piercing-ox'],
 'uzumaki':['curse-command'],'hairpin':['resonance'],'supernova':['piercing-blood'],
 'meteor':['ember-insects'],'maximum-ice':['ice-formation'],'jacobs-ladder':['copy'],
}
# Trees that can be chosen by players. Domain-only nodes are intentionally absent.
SELECTABLE_TREES = [k for k in TREE_META if k not in DOMAIN_ONLY]


ENTITY_GRADES = [
    {'grade':g,'min_streak':d,'chance':1.0,'hp':hp,'damage':('4','0'),'ce':ce,'ct':ct}
    for g,d,hp,ce,ct in [
        ('Grade 4',0,70,250,3),('Grade 3',7,90,400,4),('Grade 2',30,115,550,6),
        ('Grade 1',90,150,750,8),('Special Grade',180,200,1000,10)
    ]
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


class PostgresDB:
    def __init__(self, conn):
        self.conn=conn
        self.cur=conn.cursor(cursor_factory=RealDictCursor)
    def execute(self, sql, params=()):
        self.cur.execute(sql.replace('?', '%s'), params)
        return self.cur
    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()
    def close(self):
        try: self.cur.close()
        finally: self.conn.close()
    def executescript(self, sql):
        for statement in sql.split(';'):
            statement=statement.strip()
            if statement: self.cur.execute(statement)


def ensure_pvp_challenges(c):
    # SQLite e PostgreSQL usam sintaxes diferentes para colunas auto-incrementais.
    # Além disso, esta tabela referencia users, então ela só deve ser criada
    # depois do schema base (feito em init_db()).
    if DATABASE_URL:
        c.execute('CREATE TABLE IF NOT EXISTS pvp_challenges(id SERIAL PRIMARY KEY,challenger_id INTEGER NOT NULL,challenged_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT \'pending\',created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,battle_id INTEGER,FOREIGN KEY(challenger_id) REFERENCES users(id) ON DELETE CASCADE,FOREIGN KEY(challenged_id) REFERENCES users(id) ON DELETE CASCADE)')
    else:
        c.execute('CREATE TABLE IF NOT EXISTS pvp_challenges(id INTEGER PRIMARY KEY AUTOINCREMENT,challenger_id INTEGER NOT NULL,challenged_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT \'pending\',created_at TEXT DEFAULT CURRENT_TIMESTAMP,battle_id INTEGER,FOREIGN KEY(challenger_id) REFERENCES users(id) ON DELETE CASCADE,FOREIGN KEY(challenged_id) REFERENCES users(id) ON DELETE CASCADE)')
    try: c.execute('CREATE INDEX IF NOT EXISTS pvp_challenges_challenged_status_idx ON pvp_challenges(challenged_id,status)')
    except Exception: pass

def db():
    if DATABASE_URL:
        if psycopg2 is None: raise RuntimeError('DATABASE_URL está configurada, mas psycopg2-binary não está instalado.')
        url=DATABASE_URL
        if 'sslmode=' not in url: url += ('&' if '?' in url else '?') + 'sslmode=require'
        return PostgresDB(psycopg2.connect(url))
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def insert_and_get_id(c, sql, params):
    if DATABASE_URL:
        return c.execute(sql + ' RETURNING id', params).fetchone()['id']
    return c.execute(sql, params).lastrowid

def today(): return date.today()
def iso(d): return d.isoformat()
def parse_days(v):
    try:
        return sorted(set(int(x) for x in (v or []) if 0 <= int(x) <= 6))
    except Exception: return list(range(7))

def init_db():
    c=db()
    if DATABASE_URL:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id SERIAL PRIMARY KEY,username TEXT NOT NULL,password_hash TEXT NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,last_processed_day TEXT,xp INTEGER NOT NULL DEFAULT 0,progress_started_at TEXT);
        CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_idx ON users(LOWER(username));
        CREATE TABLE IF NOT EXISTS characters(user_id INTEGER PRIMARY KEY,body DOUBLE PRECISION NOT NULL DEFAULT 0,mind DOUBLE PRECISION NOT NULL DEFAULT 0,soul DOUBLE PRECISION NOT NULL DEFAULT 0,class_name TEXT,skill_tree TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS tasks(id SERIAL PRIMARY KEY,user_id INTEGER NOT NULL,text TEXT NOT NULL,class TEXT NOT NULL,type TEXT NOT NULL DEFAULT 'todo',frequency_json TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]',FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS completions(task_id INTEGER NOT NULL,day TEXT NOT NULL,PRIMARY KEY(task_id,day),FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS streaks(user_id INTEGER NOT NULL,class TEXT NOT NULL,days INTEGER NOT NULL DEFAULT 0,last_day TEXT,PRIMARY KEY(user_id,class),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS vote_bonuses(user_id INTEGER NOT NULL,class TEXT NOT NULL,bonus DOUBLE PRECISION NOT NULL DEFAULT 0.5,PRIMARY KEY(user_id,class),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS user_skills(user_id INTEGER NOT NULL,skill_id TEXT NOT NULL,equipped INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,skill_id),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS battles(id SERIAL PRIMARY KEY,player1 INTEGER NOT NULL,player2 INTEGER NOT NULL,turn_user INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'active',hp1 DOUBLE PRECISION,ce1 DOUBLE PRECISION,hp2 DOUBLE PRECISION,ce2 DOUBLE PRECISION,log_json TEXT NOT NULL DEFAULT '[]',FOREIGN KEY(player1) REFERENCES users(id),FOREIGN KEY(player2) REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS hunts(user_id INTEGER NOT NULL,day TEXT NOT NULL,entities_json TEXT NOT NULL,PRIMARY KEY(user_id,day),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS entity_battles(id SERIAL PRIMARY KEY,user_id INTEGER NOT NULL,entity_json TEXT NOT NULL,hp_player DOUBLE PRECISION,ce_player DOUBLE PRECISION,hp_entity DOUBLE PRECISION,status TEXT NOT NULL DEFAULT 'active',turn TEXT NOT NULL DEFAULT 'player',log_json TEXT NOT NULL DEFAULT '[]',FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS pvp_daily(user_id INTEGER NOT NULL,day TEXT NOT NULL,count INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,day),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        ''')
        c.execute('ALTER TABLE characters ADD COLUMN IF NOT EXISTS skill_tree TEXT')
        c.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS progress_started_at TEXT')
        c.execute("UPDATE users SET progress_started_at=COALESCE(progress_started_at, TO_CHAR(created_at, 'YYYY-MM-DD')) WHERE progress_started_at IS NULL")
    else:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL UNIQUE COLLATE NOCASE,password_hash TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,last_processed_day TEXT,xp INTEGER NOT NULL DEFAULT 0,progress_started_at TEXT);
        CREATE TABLE IF NOT EXISTS characters(user_id INTEGER PRIMARY KEY,body REAL NOT NULL DEFAULT 0,mind REAL NOT NULL DEFAULT 0,soul REAL NOT NULL DEFAULT 0,class_name TEXT,skill_tree TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,text TEXT NOT NULL,class TEXT NOT NULL,type TEXT NOT NULL DEFAULT 'todo',frequency_json TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]',FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS completions(task_id INTEGER NOT NULL,day TEXT NOT NULL,PRIMARY KEY(task_id,day),FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS streaks(user_id INTEGER NOT NULL,class TEXT NOT NULL,days INTEGER NOT NULL DEFAULT 0,last_day TEXT,PRIMARY KEY(user_id,class),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS vote_bonuses(user_id INTEGER NOT NULL,class TEXT NOT NULL,bonus REAL NOT NULL DEFAULT 0.5,PRIMARY KEY(user_id,class),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS user_skills(user_id INTEGER NOT NULL,skill_id TEXT NOT NULL,equipped INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,skill_id),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS battles(id INTEGER PRIMARY KEY AUTOINCREMENT,player1 INTEGER NOT NULL,player2 INTEGER NOT NULL,turn_user INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'active',hp1 REAL,ce1 REAL,hp2 REAL,ce2 REAL,log_json TEXT NOT NULL DEFAULT '[]',FOREIGN KEY(player1) REFERENCES users(id),FOREIGN KEY(player2) REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS hunts(user_id INTEGER NOT NULL,day TEXT NOT NULL,entities_json TEXT NOT NULL,PRIMARY KEY(user_id,day),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS entity_battles(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,entity_json TEXT NOT NULL,hp_player REAL,ce_player REAL,hp_entity REAL,status TEXT NOT NULL DEFAULT 'active',turn TEXT NOT NULL DEFAULT 'player',log_json TEXT NOT NULL DEFAULT '[]',FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS pvp_daily(user_id INTEGER NOT NULL,day TEXT NOT NULL,count INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,day),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        ''')
        cols=[r['name'] for r in c.execute('PRAGMA table_info(tasks)')]
        if 'frequency_json' not in cols: c.execute("ALTER TABLE tasks ADD COLUMN frequency_json TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]'")
        cols=[r['name'] for r in c.execute('PRAGMA table_info(users)')]
        if 'last_processed_day' not in cols: c.execute('ALTER TABLE users ADD COLUMN last_processed_day TEXT')
        if 'progress_started_at' not in cols: c.execute('ALTER TABLE users ADD COLUMN progress_started_at TEXT')
        c.execute("UPDATE users SET progress_started_at=COALESCE(progress_started_at, substr(created_at,1,10)) WHERE progress_started_at IS NULL")
        for r in c.execute("SELECT DISTINCT user_id,class FROM tasks WHERE type='voto'").fetchall():
            c.execute('INSERT OR IGNORE INTO vote_bonuses(user_id,class,bonus) VALUES (?,?,0.5)',(r['user_id'],r['class']))
    ensure_pvp_challenges(c)
    c.commit(); c.close()
init_db()

DEFAULT_STREAKS={x:{'dias':0,'ultimoDia':None} for x in CLASSES}
def current_user():
    uid=session.get('user_id')
    if not uid:return None
    c=db(); u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone(); c.close(); return u

def ensure_master_player(c):
    row=c.execute('SELECT * FROM users WHERE username=?',(MASTER_USERNAME,)).fetchone()
    if not row:
        uid=insert_and_get_id(c,'INSERT INTO users(username,password_hash,xp) VALUES(?,?,?)',(MASTER_USERNAME,generate_password_hash(secrets.token_hex(24)),180))
    else:
        uid=row['id']; c.execute('UPDATE users SET xp=180 WHERE id=?',(uid,))
    c.execute('INSERT INTO characters(user_id,body,mind,soul,class_name,skill_tree) VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET body=excluded.body,mind=excluded.mind,soul=excluded.soul,class_name=excluded.class_name,skill_tree=excluded.skill_tree',(uid,3.0,3.0,3.0,'Special Grade','shrine'))
    for sid,*_ in SKILLS:
        c.execute('INSERT INTO user_skills(user_id,skill_id,equipped) VALUES(?,?,0) ON CONFLICT(user_id,skill_id) DO UPDATE SET equipped=COALESCE(user_skills.equipped,0)',(uid,sid))
    c.execute('UPDATE users SET progress_started_at=? WHERE id=?', (iso(today()-timedelta(days=180)),uid))
    for cls in CLASSES:
        c.execute('INSERT INTO streaks(user_id,class,days,last_day) VALUES(?,?,180,?) ON CONFLICT(user_id,class) DO UPDATE SET days=180,last_day=excluded.last_day',(uid,cls,iso(today())))
    return uid

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

def _created_date(u):
    raw=str(u['created_at'])[:10]
    try:return date.fromisoformat(raw)
    except Exception:return today()

def _progress_window_start(u):
    raw=u['progress_started_at'] if 'progress_started_at' in u.keys() else None
    if raw:
        try:return date.fromisoformat(str(raw)[:10])
        except Exception:pass
    return _created_date(u)

def _class_consistency(c,uid,start,end):
    tasks=get_tasks(c,uid); out={x:{'due':0,'done':0} for x in CLASSES}
    d=start
    while d<=end:
        wd=d.weekday(); completed=completion_set(c,uid,iso(d))
        for t in tasks:
            if wd not in t['frequencia']: continue
            out[t['classe']]['due']+=1
            if t['id'] in completed: out[t['classe']]['done']+=1
        d+=timedelta(days=1)
    return out

def progression_for(c,u):
    if str(u['username']).upper()==MASTER_USERNAME.upper():
        return {'grade':'Special Grade','score':100.0,'dias':180,'tenure':180,'next':None,'broken_vote':False,'hp':200,'ce':1000,'ct':10,'threshold':None,'remaining_days':0,'attribute_growth':{'corpo':10.0,'mente':10.0,'alma':10.0}}
    start=_progress_window_start(u); elapsed=max(0,(today()-start).days)
    tasks=get_tasks(c,u['id']); end=today()-timedelta(days=1)
    due=done=0; broken_vote=False
    if start<=end:
        d=start
        while d<=end:
            wd=d.weekday(); completed=completion_set(c,u['id'],iso(d))
            for t in tasks:
                if wd not in t['frequencia']: continue
                due+=1
                if t['id'] in completed: done+=1
                elif t['tipo']=='voto': broken_vote=True
            d+=timedelta(days=1)
    # A broken vow is permanent for the current cycle: reset the cycle start
    # so deleting the vow later cannot erase the consequence.
    if broken_vote:
        new_start=iso(today())
        c.execute('UPDATE users SET progress_started_at=? WHERE id=?',(new_start,u['id']))
        c.commit()
        return {'grade':'Grade 4','score':0.0,'dias':0,'tenure':0,'next':'Grade 3','broken_vote':True,'hp':70,'ce':250,'ct':3,'threshold':70,'remaining_days':7,'attribute_growth':{'corpo':0.0,'mente':0.0,'alma':0.0}}
    score=round((done/due)*100,1) if due else 100.0 if elapsed==0 else 0.0
    thresholds={'Grade 4':0,'Grade 3':70,'Grade 2':75,'Grade 1':80,'Special Grade':85}
    grade=GRADE_STATS[0]
    for g,min_days,hp,ce,ct in GRADE_STATS:
        if elapsed>=min_days and score>=thresholds[g]: grade=(g,min_days,hp,ce,ct)
    idx=[x[0] for x in GRADE_STATS].index(grade[0])
    nxt=GRADE_STATS[min(idx+1,len(GRADE_STATS)-1)]
    if grade[0]=='Special Grade': nxt=None
    remaining=max(0,(nxt[1]-elapsed)) if nxt else 0
    threshold=None if not nxt else thresholds[nxt[0]]
    cls=_class_consistency(c,u['id'],start,end) if start<=end else {x:{'due':0,'done':0} for x in CLASSES}
    growth={x:round(min(10.0, (cls[x]['done']/max(1,cls[x]['due']))*10.0),1) for x in CLASSES}
    return {'grade':grade[0],'score':score,'dias':elapsed,'tenure':elapsed,'next':nxt[0] if nxt else None,'broken_vote':False,'hp':grade[2],'ce':grade[3],'ct':grade[4],'threshold':threshold,'remaining_days':remaining,'attribute_growth':growth}

def tree_payload(tree_id):
    m=TREE_META.get(tree_id)
    if not m:return None
    domain=DOMAIN_NODE_MAP.get(tree_id,m[3])
    return {'id':tree_id,'nome':SKILL_TREE_NAMES.get(tree_id,tree_id),'descricao':f'Técnica amaldiçoada associada a {m[0]}.','personagem':m[0],'frase':m[1],'imagem':m[2],'dominio':domain}

def user_payload(u):
    c=db(); process_until_yesterday(c,u)
    tasks=[t for t in get_tasks(c,u['id']) if today().weekday() in t['frequencia']]
    done=completion_set(c,u['id'],iso(today()))
    for t in tasks:t['concluida']=t['id'] in done
    s={k:dict(v) for k,v in DEFAULT_STREAKS.items()}
    for r in c.execute('SELECT class,days,last_day FROM streaks WHERE user_id=?',(u['id'],)):s[r['class']]={'dias':r['days'],'ultimoDia':r['last_day']}
    s=current_day_streaks(c,u['id'],s)
    ch=c.execute('SELECT * FROM characters WHERE user_id=?',(u['id'],)).fetchone()
    base={'body':float(ch['body'] or 0),'mind':float(ch['mind'] or 0),'soul':float(ch['soul'] or 0)} if ch else {'body':0.0,'mind':0.0,'soul':0.0}
    bonus={x:0.0 for x in CLASSES}
    for r in c.execute('SELECT class,bonus FROM vote_bonuses WHERE user_id=?',(u['id'],)):bonus[r['class']]=float(r['bonus'])
    prog=progression_for(c,u)
    growth=prog.get('attribute_growth',{})
    tree_id=(ch['skill_tree'] if ch and 'skill_tree' in ch.keys() else None)
    c.commit();c.close()
    return {'usuario':u['username'],'xp':int(u['xp'] or 0),'tarefas':tasks,'streaks':s,'personagem':None if not ch else {'body':base['body'],'mind':base['mind'],'soul':base['soul'],'classe':ch['class_name'],'skill_tree':tree_id,'crescimento':growth},'votoBonus':bonus,'progresso':prog,'skill_tree':tree_payload(tree_id)}

@app.get('/')
def index():return send_file(os.path.join(BASE_DIR,'index.html'))

@app.post('/api/register')
def register():
    d=request.get_json(silent=True) or {}; username=str(d.get('usuario','')).strip(); password=str(d.get('senha',''))
    if username.upper()=='ADMIN':return jsonify(error='Esse usuário é reservado para o administrador.'),403
    if not 3<=len(username)<=40:return jsonify(error='O usuário precisa ter entre 3 e 40 caracteres.'),400
    if not all(x.isalnum() or x in '_.-' for x in username):return jsonify(error='Use apenas letras, números, ponto, hífen ou underline.'),400
    if len(password)<4:return jsonify(error='A senha precisa ter pelo menos 4 caracteres.'),400
    c=db()
    try:
        uid=insert_and_get_id(c, 'INSERT INTO users(username,password_hash,last_processed_day,progress_started_at) VALUES(?,?,?,?)',(username,generate_password_hash(password),iso(today()-timedelta(days=1)),iso(today())))
        for cls in CLASSES:c.execute('INSERT INTO streaks(user_id,class,days,last_day) VALUES(?,?,0,NULL)',(uid,cls))
        c.commit()
    except Exception as e:
        if (DATABASE_URL and psycopg2 and isinstance(e, psycopg2.IntegrityError)) or (not DATABASE_URL and isinstance(e, sqlite3.IntegrityError)):
            c.rollback();c.close();return jsonify(error='Esse usuário já existe.'),409
        c.rollback();c.close();raise
    c.close();return jsonify(ok=True)

@app.post('/api/login')
def login():
    d=request.get_json(silent=True) or {}; username=str(d.get('usuario','')).strip(); password=str(d.get('senha',''))
    # Acesso administrativo separado da tabela de jogadores.
    if username.upper()=='ADMIN' and password==ADMIN_PASSWORD:
        c=db(); uid=ensure_master_player(c); c.commit(); c.close()
        session.clear();session['admin']=True;session['user_id']=uid;session.permanent=True
        return jsonify(ok=True,usuario='ADMIN',admin=True)
    c=db();u=c.execute('SELECT * FROM users WHERE LOWER(username)=LOWER(?)',(username,)).fetchone();c.close()
    if not u or not check_password_hash(u['password_hash'],password):return jsonify(error='Usuário ou senha incorretos.'),401
    session.clear();session['user_id']=u['id'];session.permanent=True;return jsonify(ok=True,usuario=u['username'],admin=False)

@app.get('/api/me')
def me():
    u=current_user();return jsonify(autenticado=bool(u or session.get('admin')),usuario='ADMIN' if session.get('admin') else (u['username'] if u else None),admin=bool(session.get('admin')))

def require_admin():
    if not session.get('admin'):
        return False,(jsonify(error='Acesso administrativo necessário.'),403)
    return True,None

def admin_delete_user(c, uid):
    c.execute('DELETE FROM battles WHERE player1=? OR player2=?',(uid,uid))
    c.execute('DELETE FROM users WHERE id=?',(uid,))

def sql_literal(v):
    if v is None:return 'NULL'
    if isinstance(v,bool):return 'TRUE' if v else 'FALSE'
    if isinstance(v,(int,float)):return str(v)
    return "'"+str(v).replace("'","''")+"'"

@app.get('/api/admin/users')
def admin_users():
    ok,err=require_admin()
    if not ok:return err
    c=db(); rows=c.execute('SELECT id,username,created_at,xp FROM users ORDER BY username').fetchall();c.close()
    from datetime import datetime
    base=date(2026,9,5)
    today_local=today()
    elapsed=max(0,(today_local-base).days)
    cycles=(elapsed//30)+1 if elapsed>=0 else 0
    next_backup=base+timedelta(days=30*cycles)
    return jsonify({'usuarios':[{'id':r['id'],'usuario':r['username'],'criado_em':str(r['created_at']),'xp':int(r['xp'] or 0)} for r in rows],
                    'backup':{'inicio':'2026-09-05','proximo':iso(next_backup),'ciclo_dias':30,'atrasado':today_local>next_backup,'vence_hoje':today_local==next_backup}})

@app.post('/api/admin/play')
def admin_play():
    ok,err=require_admin()
    if not ok:return err
    c=db(); uid=ensure_master_player(c); c.commit(); c.close()
    session['admin']=True; session['user_id']=uid; session.permanent=True
    return jsonify(ok=True,usuario='ADMIN',modo='master')

@app.delete('/api/admin/users/<int:uid>')
def admin_delete_user_route(uid):
    ok,err=require_admin()
    if not ok:return err
    c=db(); row=c.execute('SELECT username FROM users WHERE id=?',(uid,)).fetchone()
    if not row:c.close();return jsonify(error='Usuário não encontrado.'),404
    if str(row['username']).upper() in ('ADMIN',MASTER_USERNAME.upper()):c.close();return jsonify(error='A conta ADMIN não pode ser apagada.'),400
    admin_delete_user(c,uid);c.commit();c.close();return jsonify(ok=True)

@app.get('/api/admin/export-sql')
def admin_export_sql():
    ok,err=require_admin()
    if not ok:return err
    if not DATABASE_URL:return jsonify(error='Exportação SQL administrativa está disponível para PostgreSQL.'),400
    tables=['users','characters','tasks','completions','streaks','vote_bonuses','user_skills','battles','hunts','entity_battles','pvp_daily','pvp_challenges']
    c=db(); lines=['-- Cursed Mission PostgreSQL backup','-- Gerado pelo painel ADM','-- Importe somente em uma base do Cursed Mission.','','TRUNCATE TABLE '+', '.join(tables)+' CASCADE;']
    for table in tables:
        rows=c.execute(f'SELECT * FROM {table}').fetchall()
        if not rows:continue
        cols=list(rows[0].keys())
        colsql=', '.join(cols)
        for r in rows:
            vals=', '.join(sql_literal(r[col]) for col in cols)
            lines.append(f'INSERT INTO {table} ({colsql}) VALUES ({vals});')
    for table in ['users','tasks','battles','entity_battles']:
        lines.append(f"SELECT setval(pg_get_serial_sequence('{table}','id'), COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM {table};")
    c.close(); sql='\n'.join(lines)+'\n'
    return Response(sql,mimetype='application/sql',headers={'Content-Disposition':'attachment; filename=cursed_mission_backup.sql'})

@app.post('/api/admin/import-sql')
def admin_import_sql():
    ok,err=require_admin()
    if not ok:return err
    if not DATABASE_URL:return jsonify(error='Importação SQL administrativa está disponível para PostgreSQL.'),400
    f=request.files.get('arquivo')
    if not f:return jsonify(error='Selecione um arquivo .sql.'),400
    raw=f.read()
    if len(raw)>20*1024*1024:return jsonify(error='Arquivo SQL grande demais. Limite: 20 MB.'),413
    try: sql=raw.decode('utf-8-sig')
    except UnicodeDecodeError:return jsonify(error='O arquivo precisa estar em UTF-8.'),400
    c=db()
    try:
        c.cur.execute(sql)
        c.commit()
    except Exception as e:
        c.rollback();c.close();return jsonify(error='Falha ao importar SQL: '+str(e)),400
    c.close();return jsonify(ok=True,mensagem='Banco restaurado com sucesso. Atualize a página.')

@app.post('/api/admin/reset-progress')
def admin_reset_progress():
    ok,err=require_admin()
    if not ok:return err
    c=db()
    try:
        # Preserva contas, personagens, missões e votos configurados.
        # Reinicia apenas o progresso/estado derivado dos jogadores.
        c.execute('DELETE FROM completions')
        c.execute('DELETE FROM streaks')
        c.execute('DELETE FROM user_skills')
        c.execute('DELETE FROM battles')
        c.execute('DELETE FROM hunts')
        c.execute('DELETE FROM entity_battles')
        c.execute('DELETE FROM pvp_daily')
        c.execute('DELETE FROM pvp_challenges')
        if DATABASE_URL:
            c.execute("UPDATE users SET xp=0, progress_started_at=created_at")
        else:
            c.execute("UPDATE users SET xp=0, progress_started_at=created_at")
        c.commit(); c.close()
        return jsonify(ok=True,mensagem='Progresso de todos os jogadores foi resetado. Contas, personagens, missões e votos foram preservados.')
    except Exception as e:
        try:c.rollback();c.close()
        except Exception:pass
        return jsonify(error=f'Não foi possível resetar o progresso: {e}'),500

@app.post('/api/admin/reset-db')
def admin_reset_db():
    ok,err=require_admin()
    if err:return err
    c=db()
    try:
        if DATABASE_URL:
            # Mantém o schema e apaga todos os dados. CASCADE cobre as FKs.
            tables=['pvp_challenges','completions','streaks','vote_bonuses','user_skills','entity_battles','hunts','battles','tasks','characters','pvp_daily','users']
            c.execute('TRUNCATE TABLE '+', '.join(tables)+' RESTART IDENTITY CASCADE')
        else:
            # SQLite: remover filhos primeiro por causa das FKs.
            for table in ['pvp_challenges','completions','streaks','vote_bonuses','user_skills','entity_battles','hunts','battles','tasks','characters','pvp_daily','users']:
                c.execute('DELETE FROM '+table)
            try:
                for seq in ['users','tasks','battles','entity_battles','pvp_challenges']:
                    c.execute('DELETE FROM sqlite_sequence WHERE name=?',(seq,))
            except Exception:
                pass
        uid=ensure_master_player(c)
        c.commit();c.close()
        session.clear();session['admin']=True;session['user_id']=uid;session.permanent=True
        return jsonify(ok=True,mensagem='Banco de dados resetado. O jogador ADMIN foi recriado em modo mestre.')
    except Exception as e:
        try:c.rollback();c.close()
        except Exception:pass
        return jsonify(error=f'Não foi possível resetar o banco: {e}'),500

@app.delete('/api/account')
def delete_account():
    u,err=require_user()
    if err:return err
    c=db()
    # Battles reference users without cascading deletes, so remove them explicitly.
    c.execute('DELETE FROM battles WHERE player1=? OR player2=?',(u['id'],u['id']))
    c.execute('DELETE FROM users WHERE id=?',(u['id'],))
    c.commit();c.close();session.clear();return jsonify(ok=True)

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
            tid=insert_and_get_id(c, 'INSERT INTO tasks(user_id,text,class,type,frequency_json) VALUES(?,?,?,?,?)',(u['id'],text,cls,typ,json.dumps(freq)));kept.add(tid)
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
    if today().weekday() not in json.loads(t['frequency_json']):c.close();return jsonify(error='Essa tarefa não está programada para hoje.'),400
    ds=iso(today());exists=c.execute('SELECT 1 FROM completions WHERE task_id=? AND day=?',(task_id,ds)).fetchone()
    if exists:c.execute('DELETE FROM completions WHERE task_id=? AND day=?',(task_id,ds));done=False
    else:c.execute('INSERT INTO completions(task_id,day) VALUES(?,?)',(task_id,ds));done=True
    c.commit();c.close();return jsonify(ok=True,concluida=done)

@app.put('/api/character')
def save_character():
    u,err=require_user()
    if err:return err
    p=(request.get_json(silent=True) or {}).get('personagem',{}) or {};body=float(p.get('body',0));mind=float(p.get('mind',0));soul=float(p.get('soul',0));cls=str(p.get('classe',''));tree=str(p.get('skill_tree',''))
    if any(x<0 or x>3 for x in (body,mind,soul)) or abs(body+mind+soul-3)>0.001:return jsonify(error='A distribuição inicial precisa somar exatamente 3 pontos.'),400
    if tree not in TREE_META:return jsonify(error='Escolha uma Skill Tree válida.'),400
    c=db();old=c.execute('SELECT skill_tree FROM characters WHERE user_id=?',(u['id'],)).fetchone()
    if old and old['skill_tree'] and old['skill_tree']!=tree:c.close();return jsonify(error='A Skill Tree não pode ser trocada depois da criação.'),400
    c.execute('INSERT INTO characters(user_id,body,mind,soul,class_name,skill_tree) VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET body=excluded.body,mind=excluded.mind,soul=excluded.soul,class_name=excluded.class_name,skill_tree=COALESCE(characters.skill_tree,excluded.skill_tree)',(u['id'],body,mind,soul,cls,tree));c.commit();c.close();return jsonify(ok=True)

def attributes_for(c,uid):
    ch=c.execute('SELECT * FROM characters WHERE user_id=?',(uid,)).fetchone()
    base={'body':0.0,'mind':0.0,'soul':0.0} if not ch else {'body':float(ch['body'] or 0),'mind':float(ch['mind'] or 0),'soul':float(ch['soul'] or 0)}
    bonus={x:0.0 for x in CLASSES}
    for r in c.execute('SELECT class,bonus FROM vote_bonuses WHERE user_id=?',(uid,)): bonus[r['class']]=float(r['bonus'])
    u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    prog=progression_for(c,u) if u else {'attribute_growth':{'corpo':0,'mente':0,'alma':0}}
    growth=prog.get('attribute_growth',{})
    eff={'body':base['body']+growth.get('corpo',0)+bonus['corpo'], 'mind':base['mind']+growth.get('mente',0)+bonus['mente'], 'soul':base['soul']+growth.get('alma',0)+bonus['alma']}
    return base,bonus,eff,ch,growth

def stats_for(attrs,days):
    d=max(0,int(days or 0)); g='Special Grade' if d>=180 else 'Grade 1' if d>=90 else 'Grade 2' if d>=30 else 'Grade 3' if d>=7 else 'Grade 4'
    row=next(x for x in GRADE_STATS if x[0]==g)
    return {'F':{},'HP':row[2],'CE':row[3],'CT':row[4]}

def combat_stats_for(c,u):
    prog=progression_for(c,u); grade=prog['grade']; idx=[x[0] for x in GRADE_STATS].index(grade)
    base=GRADE_STATS[idx]; nxt=GRADE_STATS[min(idx+1,len(GRADE_STATS)-1)]; growth=prog.get('attribute_growth',{})
    body=growth.get('corpo',0)/10.0; soul=growth.get('alma',0)/10.0; mind=growth.get('mente',0)/10.0
    hp=round(base[2]+(nxt[2]-base[2])*body,1)
    ce=round(base[3]+(nxt[3]-base[3])*soul,1)
    ct=base[4] if idx>=4 else min(nxt[4], base[4]+int(round((nxt[4]-base[4])*mind)))
    if grade=='Special Grade': hp,ce,ct=200,1000,10
    return {'HP':hp,'CE':ce,'CT':ct,'maxHP':nxt[2],'maxCE':nxt[3],'maxCT':nxt[4]}

@app.get('/api/profile')
def profile():
    u,err=require_user()
    if err:return err
    c=db();process_until_yesterday(c,u);vals={x:{'dias':0,'ultimoDia':None} for x in CLASSES}
    for r in c.execute('SELECT class,days,last_day FROM streaks WHERE user_id=?',(u['id'],)):vals[r['class']]={'dias':int(r['days']),'ultimoDia':r['last_day']}
    vals=current_day_streaks(c,u['id'],vals);days={x:int(vals[x]['dias']) for x in CLASSES};base,bonus,eff,ch,growth=attributes_for(c,u['id']);prog=progression_for(c,u); stats=combat_stats_for(c,u); tree=tree_payload(ch['skill_tree'] if ch and 'skill_tree' in ch.keys() else None);c.commit();c.close()
    return jsonify(usuario=u['username'],base=base,voto=bonus,atributos=eff,dias=days,stats=stats,progresso=prog,skill_tree=tree)

@app.get('/api/skills')
def skills():
    u,err=require_user()
    if err:return err
    c=db(); owned={r['skill_id']:bool(r['equipped']) for r in c.execute('SELECT skill_id,equipped FROM user_skills WHERE user_id=?',(u['id'],))}
    xp=int(u['xp'] or 0); prog=progression_for(c,u); ct=prog['ct']
    ch=c.execute('SELECT skill_tree FROM characters WHERE user_id=?',(u['id'],)).fetchone(); tree_id=ch['skill_tree'] if ch else None
    meta=tree_payload(tree_id); master=str(u['username']).upper()==MASTER_USERNAME.upper()
    rank={'Grade 4':0,'Grade 3':1,'Grade 2':2,'Grade 1':3,'Special Grade':4}.get(prog['grade'],0)
    out=[]
    for sid,name,cat,skill_ct,ce,effect in SKILLS:
        tree=SKILL_TREE_BY_ID.get(sid); cost={1:50,2:100,3:175,4:275}[skill_ct]
        prereq=SKILL_PREREQS.get(sid,[]); acquired=master or sid in owned
        same=tree==tree_id
        prereq_ok=all(pid in owned or master for pid in prereq)
        can=master or (same and not acquired and skill_ct<=ct and xp>=cost and prereq_ok)
        out.append({'id':sid,'nome':name,'categoria':cat,'ct':skill_ct,'ce':ce,'efeito':skill_dict(sid)['efeito'],'preco_xp':cost,'adquirida':acquired,'pode_comprar':can,'equipada':owned.get(sid,False),'mesma_arvore':same,'arvore':tree,'prerequisitos':prereq,'tipo':'normal'})
    domains=[]
    if tree_id and tree_id in DOMAIN_NODE_MAP:
        tree_skills=[x[0] for x in SKILL_DATA if x[6]==tree_id]
        all_mastered=all(x in owned or master for x in tree_skills)
        unlocked=(rank>=3 and all_mastered)
        domains=[{'nome':DOMAIN_NODE_MAP[tree_id],'efeito':'Nó final da Skill Tree. Não é comprado com XP.','requisito':'Grade 1 + todas as técnicas da árvore dominadas','desbloqueada':unlocked,'progresso_tecnicas':sum(1 for x in tree_skills if x in owned or master),'total_tecnicas':len(tree_skills)}]
    power=vote_power_multiplier(c,u['id'])
    c.close();return jsonify(skills=out,xp=xp,ct=ct,skill_tree=tree_id,skill_tree_nome=meta['nome'] if meta else None,skill_tree_descricao=(SKILL_TREE_OPTIONS_TEXT.get(tree_id) if tree_id else None),tree_meta=meta,progresso=prog,domains=domains,poder_voto=power)

@app.post('/api/skills/<skill_id>/buy')
def buy_skill(skill_id):
    u,err=require_user()
    if err:return err
    item=next((x for x in SKILLS if x[0]==skill_id),None)
    if not item:return jsonify(error='Técnica não encontrada.'),404
    tree=SKILL_TREE_BY_ID.get(skill_id); cost={1:50,2:100,3:175,4:275}[item[3]]; c=db()
    if str(u['username']).upper()==MASTER_USERNAME.upper():
        c.execute('INSERT INTO user_skills(user_id,skill_id,equipped) VALUES(?,?,0) ON CONFLICT(user_id,skill_id) DO NOTHING',(u['id'],skill_id));c.commit();c.close();return jsonify(ok=True,master=True)
    ch=c.execute('SELECT skill_tree FROM characters WHERE user_id=?',(u['id'],)).fetchone(); tree_id=ch['skill_tree'] if ch else None
    if tree!=tree_id:c.close();return jsonify(error='Essa técnica pertence a outra Skill Tree.'),400
    if c.execute('SELECT 1 FROM user_skills WHERE user_id=? AND skill_id=?',(u['id'],skill_id)).fetchone(): c.close();return jsonify(error='Você já possui essa técnica.'),400
    if item[3]>current_ct(c,u['id']): c.close();return jsonify(error='CT insuficiente para desbloquear essa técnica.'),400
    if int(u['xp'] or 0)<cost:c.close();return jsonify(error='XP insuficiente.'),400
    missing=[next(x for x in SKILLS if x[0]==pid)[1] for pid in SKILL_PREREQS.get(skill_id,[]) if not c.execute('SELECT 1 FROM user_skills WHERE user_id=? AND skill_id=?',(u['id'],pid)).fetchone()]
    if missing:c.close();return jsonify(error='Pré-requisitos faltando: '+', '.join(missing)),400
    c.execute('UPDATE users SET xp=xp-? WHERE id=?',(cost,u['id']));c.execute('INSERT INTO user_skills(user_id,skill_id,equipped) VALUES(?,?,0)',(u['id'],skill_id));c.commit();c.close();return jsonify(ok=True,xp_gasto=cost)

@app.post('/api/skills/<skill_id>/toggle')
def toggle_skill(skill_id):
    u,err=require_user()
    if err:return err
    item=next((x for x in SKILLS if x[0]==skill_id),None)
    if not item:return jsonify(error='Técnica não encontrada.'),404
    c=db()
    master=str(u['username']).upper()==MASTER_USERNAME.upper()
    row=c.execute('SELECT equipped FROM user_skills WHERE user_id=? AND skill_id=?',(u['id'],skill_id)).fetchone()
    # O ADM mestre possui todas as técnicas virtualmente; crie a linha ao equipar.
    if not row and master:
        c.execute('INSERT INTO user_skills(user_id,skill_id,equipped) VALUES(?,?,0) ON CONFLICT(user_id,skill_id) DO NOTHING',(u['id'],skill_id))
        row=c.execute('SELECT equipped FROM user_skills WHERE user_id=? AND skill_id=?',(u['id'],skill_id)).fetchone()
    if not row:c.close();return jsonify(error='Desbloqueie essa técnica primeiro.'),400
    newv=0 if bool(row['equipped']) else 1
    c.execute('UPDATE user_skills SET equipped=? WHERE user_id=? AND skill_id=?',(newv,u['id'],skill_id))
    total=sum(next(x[3] for x in SKILLS if x[0]==r['skill_id']) for r in c.execute('SELECT skill_id FROM user_skills WHERE user_id=? AND equipped=1',(u['id'],)))
    if total>current_ct(c,u['id']):c.rollback();c.close();return jsonify(error='Você não possui CT suficiente para equipar essa combinação.'),400
    c.commit();equipped=[r['skill_id'] for r in c.execute('SELECT skill_id FROM user_skills WHERE user_id=? AND equipped=1',(u['id'],))];c.close();return jsonify(ok=True,equipadas=equipped,ct_usado=total)

def vote_power_multiplier(c,uid):
    # Cada voto vinculativo ativo aumenta o poder de combate em 10%.
    n=int(c.execute('SELECT COUNT(*) AS n FROM vote_bonuses WHERE user_id=?',(uid,)).fetchone()['n'] or 0)
    return 1.0 + 0.10*min(n,3)

def current_ct(c,uid):
    u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    if not u:return 3
    if str(u['username']).upper()==MASTER_USERNAME.upper(): return 10
    return progression_for(c,u)['ct']

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
    return {'id':x[0],'nome':x[1],'categoria':x[2],'ct':x[3],'ce':x[4],'efeito':(f'Dano = {x[3]} + '+x[5].replace(' de dano.','').replace(' de dano','') if x[2]=='elementar' and 'dano' in x[5].lower() else x[5])}

def battle_stats(c,uid):
    u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    return combat_stats_for(c,u)

@app.get('/api/entities')
def entities():
    u,err=require_user()
    if err:return err
    c=db(); prog=progression_for(c,u); days=prog['dias']; import random
    row=c.execute('SELECT entities_json FROM hunts WHERE user_id=? AND day=?',(u['id'],iso(today()))).fetchone()
    if row:
        out=json.loads(row['entities_json']); c.close(); return jsonify(usou=True,entidades=out,streak=days)
    rank={'Grade 4':0,'Grade 3':1,'Grade 2':2,'Grade 1':3,'Special Grade':4}.get(prog['grade'],0)
    eligible=[g for g in ENTITY_GRADES if {'Grade 4':0,'Grade 3':1,'Grade 2':2,'Grade 1':3,'Special Grade':4}.get(g['grade'],0)<=rank]
    out=[]
    for g in eligible:
        if g['grade']=='Grade 4' or random.random()<=g['chance']:
            hp=int(g['hp']); damage=roll_dice(g['damage'][0]+'+'+g['damage'][1])
            pool=[x for x in SKILLS if x[3]<=g['ct']]
            skills=[]
            if g['ct']==1 and pool: skills=[random.choice(pool)]
            elif g['ct']>=2 and pool:
                skills=random.sample(pool,min(len(pool),random.randint(1,min(3,len(pool)))))
            out.append({'grade':g['grade'],'streak':days,'hp':hp,'damage':damage,'ct':g['ct'],'ce':g['ce'],'multiplayer':g['ct']>=3,'skills':[{'id':x[0],'nome':x[1],'ce':x[4],'efeito':skill_dict(x[0])['efeito']} for x in skills]})
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
    idx=next((i for i,x in enumerate(valid) if json.dumps(entity,sort_keys=True)==json.dumps(x,sort_keys=True)),None)
    if idx is None:c.close();return jsonify(error='Essa maldição não pertence à sua caça de hoje ou já foi enfrentada.'),400
    # Cada maldição só pode ser enfrentada uma vez. Removemos da caça no momento
    # em que o combate é iniciado, então ela não volta a aparecer nem pode ser
    # iniciada novamente, independentemente de vitória ou derrota.
    valid.pop(idx)
    c.execute('UPDATE hunts SET entities_json=? WHERE user_id=? AND day=?',(json.dumps(valid,ensure_ascii=False),u['id'],iso(today())))
    st=combat_stats_for(c,u)
    bid=insert_and_get_id(c, 'INSERT INTO entity_battles(user_id,entity_json,hp_player,ce_player,hp_entity,status,turn,log_json) VALUES(?,?,?,?,?,?,?,?)',(u['id'],json.dumps(entity,ensure_ascii=False),st['HP'],st['CE'],float(entity['hp']),'active','player',json.dumps([])));c.commit();c.close();return jsonify(id=bid)

@app.get('/api/entity-battles/<int:bid>')
def get_entity_battle(bid):
    u,err=require_user()
    if err:return err
    c=db();b=c.execute('SELECT * FROM entity_battles WHERE id=? AND user_id=?',(bid,u['id'])).fetchone()
    if not b:c.close();return jsonify(error='Combate não encontrado.'),404
    e=json.loads(b['entity_json']); log=json.loads(b['log_json'])
    equipped=[]
    for r in c.execute('SELECT skill_id FROM user_skills WHERE user_id=? AND equipped=1',(u['id'],)):
        sk=skill_dict(r['skill_id'])
        if sk: equipped.append(sk)
    c.close();return jsonify(id=bid,entity=e,seu_hp=float(b['hp_player']),seu_ce=float(b['ce_player']),inimigo_hp=float(b['hp_entity']),status=b['status'],meu_turno=b['turn']=='player',log=log[-8:],skills=equipped)

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
        dmg += sk['ct'] if sk['categoria']=='elementar' else 0
        dmg=round(dmg*vote_power_multiplier(c,u['id']))
        log.append(f'Você usou {sk["nome"]} e causou {dmg} dano.')
    else:dmg=round(random.randint(1,4)*vote_power_multiplier(c,u['id']));log.append(f'Você atacou e causou {dmg} dano.')
    ehp=max(0,ehp-dmg)
    if ehp<=0:
        reward=entity_xp_reward(hp,e['hp']); c.execute('UPDATE users SET xp=xp+? WHERE id=?',(reward,u['id'])); log.append(f'Maldição derrotada! +{reward} XP.'); status='finished'; turn='player'
    else:
        edmg=int(e['damage']); hp=max(0,hp-edmg); log.append(f'{e["grade"]} causou {edmg} dano.') ; status='finished' if hp<=0 else 'active'; turn='player'
        if hp<=0: log.append('Você foi derrotado.');
    c.execute('UPDATE entity_battles SET hp_player=?,ce_player=?,hp_entity=?,status=?,turn=?,log_json=? WHERE id=?',(hp,ce,ehp,status,turn,json.dumps(log,ensure_ascii=False),bid));c.commit();c.close();return jsonify(ok=True)

@app.get('/api/pvp-status')
def pvp_status():
    u,err=require_user()
    if err:return err
    c=db(); ensure_pvp_challenges(c)
    row=c.execute('SELECT count FROM pvp_daily WHERE user_id=? AND day=?',(u['id'],iso(today()))).fetchone()
    pending_received=c.execute("SELECT count(*) AS n FROM pvp_challenges WHERE challenged_id=? AND status='pending'",(u['id'],)).fetchone()
    pending_sent=c.execute("SELECT count(*) AS n FROM pvp_challenges WHERE challenger_id=? AND status='pending'",(u['id'],)).fetchone()
    c.close()
    used=int(row['count']) if row else 0
    return jsonify(usados=min(used,2),restantes=max(0,2-used),
                   desafios_recebidos=int(pending_received['n'] or 0),
                   desafios_enviados=int(pending_sent['n'] or 0))

@app.get('/api/pvp-challenges')
def pvp_challenges():
    u,err=require_user()
    if err:return err
    c=db(); ensure_pvp_challenges(c); out=[]
    rows=c.execute("""SELECT pc.*, u1.username AS challenger_name, u2.username AS challenged_name
                      FROM pvp_challenges pc
                      JOIN users u1 ON u1.id=pc.challenger_id
                      JOIN users u2 ON u2.id=pc.challenged_id
                      WHERE (pc.challenger_id=? OR pc.challenged_id=?) AND pc.status='pending'
                      ORDER BY pc.id DESC""",(u['id'],u['id'])).fetchall()
    for r in rows:
        out.append({'id':r['id'],'tipo':'recebido' if r['challenged_id']==u['id'] else 'enviado',
                    'desafiante':r['challenger_name'],'desafiado':r['challenged_name'],'criado_em':str(r['created_at'])})
    c.close(); return jsonify(out)

@app.post('/api/battles')
def create_battle():
    u,err=require_user()
    if err:return err
    name=str((request.get_json(silent=True) or {}).get('oponente','')).strip()
    c=db(); ensure_pvp_challenges(c)
    opp=c.execute('SELECT * FROM users WHERE LOWER(username)=LOWER(?)',(name,)).fetchone()
    if not opp:c.close();return jsonify(error='Adversário não encontrado.'),404
    if opp['id']==u['id']:c.close();return jsonify(error='Você não pode desafiar a si mesmo.'),400
    day=iso(today())
    my_count=c.execute('SELECT count FROM pvp_daily WHERE user_id=? AND day=?',(u['id'],day)).fetchone()
    opp_count=c.execute('SELECT count FROM pvp_daily WHERE user_id=? AND day=?',(opp['id'],day)).fetchone()
    if my_count and int(my_count['count'])>=2:c.close();return jsonify(error='Você já atingiu o limite de 2 combates PvP hoje.'),400
    if opp_count and int(opp_count['count'])>=2:c.close();return jsonify(error='Esse jogador já atingiu o limite de 2 combates PvP hoje.'),400
    active=c.execute("SELECT id FROM battles WHERE status='active' AND (player1=? OR player2=?)",(u['id'],u['id'])).fetchone()
    if active:c.close();return jsonify(error='Você já possui um combate PvP ativo.'),400
    active2=c.execute("SELECT id FROM battles WHERE status='active' AND (player1=? OR player2=?)",(opp['id'],opp['id'])).fetchone()
    if active2:c.close();return jsonify(error='Esse jogador já está em um combate PvP ativo.'),400
    pending=c.execute("SELECT id FROM pvp_challenges WHERE challenger_id=? AND challenged_id=? AND status='pending'",(u['id'],opp['id'])).fetchone()
    if pending:c.close();return jsonify(error='Você já enviou um desafio para esse jogador e está aguardando resposta.'),400
    reverse=c.execute("SELECT id FROM pvp_challenges WHERE challenger_id=? AND challenged_id=? AND status='pending'",(opp['id'],u['id'])).fetchone()
    if reverse:c.close();return jsonify(error='Esse jogador já desafiou você. Responda ao desafio recebido.'),400
    cid=insert_and_get_id(c,'INSERT INTO pvp_challenges(challenger_id,challenged_id,status) VALUES(?,?,?)',(u['id'],opp['id'],'pending'))
    c.commit();c.close()
    return jsonify(id=cid,status='pending',mensagem=f'Desafio enviado para {opp["username"]}. Aguardando aceitação.')

@app.post('/api/pvp-challenges/<int:cid>/respond')
def respond_pvp_challenge(cid):
    u,err=require_user()
    if err:return err
    action=str((request.get_json(silent=True) or {}).get('acao','')).lower()
    if action not in ('aceitar','recusar'): return jsonify(error='Resposta inválida.'),400
    c=db(); ensure_pvp_challenges(c)
    ch=c.execute('SELECT * FROM pvp_challenges WHERE id=? AND challenged_id=?',(cid,u['id'])).fetchone()
    if not ch:c.close();return jsonify(error='Desafio não encontrado.'),404
    if ch['status']!='pending':c.close();return jsonify(error='Esse desafio já foi respondido.'),400
    if action=='recusar':
        c.execute("UPDATE pvp_challenges SET status='declined' WHERE id=?",(cid,)); c.commit(); c.close()
        return jsonify(ok=True,status='declined')
    day=iso(today())
    for uid in (ch['challenger_id'],ch['challenged_id']):
        row=c.execute('SELECT count FROM pvp_daily WHERE user_id=? AND day=?',(uid,day)).fetchone()
        if row and int(row['count'])>=2:
            c.execute("UPDATE pvp_challenges SET status='declined' WHERE id=?",(cid,)); c.commit(); c.close()
            return jsonify(error='Um dos jogadores já atingiu o limite de 2 combates PvP hoje.'),400
    active1=c.execute("SELECT id FROM battles WHERE status='active' AND (player1=? OR player2=?)",(ch['challenger_id'],ch['challenger_id'])).fetchone()
    active2=c.execute("SELECT id FROM battles WHERE status='active' AND (player1=? OR player2=?)",(ch['challenged_id'],ch['challenged_id'])).fetchone()
    if active1 or active2:c.close();return jsonify(error='Um dos jogadores já está em outro combate ativo.'),400
    challenger=c.execute('SELECT username FROM users WHERE id=?',(ch['challenger_id'],)).fetchone()['username']
    challenged=c.execute('SELECT username FROM users WHERE id=?',(ch['challenged_id'],)).fetchone()['username']
    s1=battle_stats(c,ch['challenger_id']); s2=battle_stats(c,ch['challenged_id'])
    starter=ch['challenger_id'] if __import__('random').randint(0,1)==0 else ch['challenged_id']
    log=[f'{challenger} desafiou {challenged}.',f'Desafio aceito. Sorteio 50/50: {challenger if starter==ch["challenger_id"] else challenged} começa.']
    bid=insert_and_get_id(c,'INSERT INTO battles(player1,player2,turn_user,status,hp1,ce1,hp2,ce2,log_json) VALUES(?,?,?,?,?,?,?,?,?)',
                          (ch['challenger_id'],ch['challenged_id'],starter,'active',s1['HP'],s1['CE'],s2['HP'],s2['CE'],json.dumps(log,ensure_ascii=False)))
    for uid in (ch['challenger_id'],ch['challenged_id']):
        c.execute('INSERT INTO pvp_daily(user_id,day,count) VALUES(?,?,1) ON CONFLICT(user_id,day) DO UPDATE SET count=pvp_daily.count+1',(uid,day))
    c.execute("UPDATE pvp_challenges SET status='accepted',battle_id=? WHERE id=?",(bid,cid))
    c.commit();c.close()
    return jsonify(ok=True,status='accepted',battle_id=bid,primeiro=starter)

@app.post('/api/pvp-challenges/<int:cid>/cancel')
def cancel_pvp_challenge(cid):
    u,err=require_user()
    if err:return err
    c=db(); ensure_pvp_challenges(c)
    ch=c.execute("SELECT * FROM pvp_challenges WHERE id=? AND challenger_id=? AND status='pending'",(cid,u['id'])).fetchone()
    if not ch:c.close();return jsonify(error='Desafio enviado não encontrado.'),404
    c.execute("UPDATE pvp_challenges SET status='cancelled' WHERE id=?",(cid,));c.commit();c.close()
    return jsonify(ok=True)

@app.get('/api/battles')
def list_battles():
    u,err=require_user()
    if err:return err
    c=db();out=[]
    for b in c.execute("SELECT * FROM battles WHERE status='active' AND (player1=? OR player2=?) ORDER BY id DESC",(u['id'],u['id'])):
        mine=b['hp1'] if b['player1']==u['id'] else b['hp2']; ce=b['ce1'] if b['player1']==u['id'] else b['ce2']; opp=b['player2'] if b['player1']==u['id'] else b['player1']; on=c.execute('SELECT username FROM users WHERE id=?',(opp,)).fetchone()['username'];out.append({'id':b['id'],'oponente':on,'seu_hp':mine,'seu_ce':ce,'meu_turno':b['turn_user']==u['id']})
    c.close();return jsonify(out)

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
        dmg=(sum(rolls) if rolls else 0) + (sk['ct'] if sk['categoria']=='elementar' else 0);dmg=round(dmg*vote_power_multiplier(c,u['id']));ohp=max(0,ohp-dmg);msg=f'{u["username"]} usou {sk["nome"]} e causou {dmg} dano.'
    else:
        dmg=round(random.randint(1,4)*vote_power_multiplier(c,u['id']));ohp=max(0,ohp-dmg);msg=f'{u["username"]} atacou e causou {dmg} dano.'
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
