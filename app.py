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
 'shrine': ('Ryomen Sukuna','Tenha orgulho, você é forte.','https://static.zerochan.net/Sukuna.full.3814718.jpg','Malevolent Shrine'),
 'limitless': ('Satoru Gojo','No céu e na terra, apenas eu sou o honrado.','https://static.zerochan.net/Gojou.Satoru.full.3974287.jpg','Unlimited Void'),
 'ten-shadows': ('Megumi Fushiguro','Com minha própria vida, salvarei as pessoas de forma desigual.','https://static.zerochan.net/Megumi.Fushiguro.full.3233980.jpg','Chimera Shadow Garden'),
 'cursed-spirit-manipulation': ('Suguru Geto','Você é o mais forte porque é Satoru Gojo?','https://static.zerochan.net/Suguru.Getou.full.3587532.jpg','Womb Profusion'),
 'idle-transfiguration': ('Mahito','A vida não tem peso ou valor particular.','https://static.zerochan.net/Mahito.full.3679477.jpg','Self-Embodiment of Perfection'),
 'straw-doll': ('Nobara Kugisaki','Eu sou Nobara Kugisaki.','https://static.zerochan.net/Kugisaki.Nobara.full.3522408.jpg','—'),
 'ratio': ('Kento Nanami','Trabalho é uma merda.','https://static.zerochan.net/Nanami.Kento.full.3574668.jpg','—'),
 'projection': ('Naobito Zenin','Eu sou o feiticeiro mais rápido da família Zenin.','https://static.zerochan.net/Naobito.Zenin.full.3518074.jpg','—'),
 'blood': ('Choso','Eu sou seu irmão mais velho.','https://static.zerochan.net/Choso.full.3769572.jpg','—'),
 'boogie-woogie': ('Aoi Todo','O ato do aplauso é uma aclamação da alma!','https://static.zerochan.net/Toudou.Aoi.full.3595620.jpg','—'),
 'cursed-speech': ('Toge Inumaki','Salmão.','https://static.zerochan.net/Inumaki.Toge.full.3572672.jpg','—'),
 'copy': ('Yuta Okkotsu','Rika.','https://static.zerochan.net/Okkotsu.Yuuta.full.3814945.jpg','Authentic Mutual Love'),
 'construction': ('Yorozu','Eu vou me casar com você.','https://static.zerochan.net/Yorozu.full.3884581.jpg','Threefold Affliction'),
 'star-rage': ('Yuki Tsukumo','Que tipo de garota você gosta?','https://static.zerochan.net/Tsukumo.Yuki.full.3741404.jpg','—'),
 'sky': ('Takako Uro','Eu odeio a luz do sol.','https://static.zerochan.net/Uro.Takako.full.3895237.jpg','—'),
 'granite-blast': ('Ryu Ishigori','A vida não tem sabor.','https://static.zerochan.net/Ishigori.Ryu.full.3794875.jpg','—'),
 'comedian': ('Fumihiko Takaba','Se eu não achar engraçado, não tem graça.','https://static.zerochan.net/Takaba.Fumihiko.full.3879420.jpg','—'),
 'technique-extinguishment': ('Hana Kurusu / Angel','Devolva Megumi para mim!','https://static.zerochan.net/Kurusu.Hana.full.3825632.jpg','Jacob’s Ladder'),
 'inverse': ('Jiro Awasaka','Eu sou um homem que sobrevive.','https://static.zerochan.net/Awasaka.Jiro.full.3471446.jpg','—'),
 'seance': ('Ogami','Eu trouxe de volta um feiticeiro.','https://static.zerochan.net/Ogami.full.3491297.jpg','—'),
 'puppet': ('Kokichi Muta','Encontre sua felicidade.','https://static.zerochan.net/Muta.Kokichi.full.3478074.jpg','—'),
 'auspicious-beasts': ('Takuma Ino','Eu vou dar o meu melhor.','https://static.zerochan.net/Ino.Takuma.full.3577997.jpg','—'),
 'rot': ('Eso','Nós somos irmãos.','https://static.zerochan.net/Eso.full.3486672.jpg','—'),
 'cloning': ('Bata-bata','Uma técnica pode ser usada de muitas formas.','https://static.zerochan.net/Jujutsu.Kaisen.full.4573758.jpg','—'),
 'miracles': ('Haruta Shigemo','Eu sempre tive sorte.','https://static.zerochan.net/Shigemo.Haruta.full.3513412.jpg','—'),
 'ice': ('Uraume','Sukuna-sama.','https://static.zerochan.net/Uraume.full.3801224.jpg','—'),
 'disaster-flames': ('Jogo','Eu sou um espírito amaldiçoado.','https://static.zerochan.net/Jougo.full.3552467.jpg','Coffin of the Iron Mountain'),
 'disaster-plants': ('Hanami','Os humanos precisam desaparecer.','https://static.zerochan.net/Hanami.full.3485955.jpg','—'),
 'disaster-tides': ('Dagon','Eu nasci do medo do mar.','https://static.zerochan.net/Dagon.full.3550937.jpg','Horizon of the Captivating Skandha'),
 'contractual-recreation': ('Reggie Star','Eu não sou um homem de promessas vazias.','https://static.zerochan.net/Reggie.Star.full.3825626.jpg','—'),
 'love-rendezvous': ('Kirara Hoshi','Eu não quero perder meu tempo.','https://static.zerochan.net/Hoshi.Kirara.full.3840985.jpg','—'),
 'solo-forbidden-area': ('Utahime Iori','Não subestime os feiticeiros de Kyoto.','https://static.zerochan.net/Iori.Utahime.full.3577957.jpg','—'),
 'black-bird': ('Mei Mei','Dinheiro é tudo que importa.','https://static.zerochan.net/Mei.Mei.full.3577958.jpg','—'),
 'mythical-beast-amber': ('Hajime Kashimo','Eu estava esperando por você.','https://static.zerochan.net/Kashimo.Hajime.full.3852290.jpg','—'),
 'prayer-song': ('Yasohachi Bridge User','Oração é a força de uma vontade.','https://static.zerochan.net/Jujutsu.Kaisen.full.4573758.jpg','—'),
 'antigravity': ('Kenjaku','A evolução humana é fascinante.','https://static.zerochan.net/Kenjaku.full.3791075.jpg','Womb Profusion'),
 'light': ('Miguel','Eu não tenho tempo para isso.','https://static.zerochan.net/Miguel.full.3902188.jpg','—'),
 'smallpox': ('Smallpox Deity','—','https://static.zerochan.net/Jujutsu.Kaisen.full.4573758.jpg','Smallpox Deity Domain'),
 'deadly-sentencing': ('Hiromi Higuruma','Confie no julgamento.','https://static.zerochan.net/Higuruma.Hiromi.full.3847165.jpg','Deadly Sentencing'),
 'idle-death-gamble': ('Kinji Hakari','Jackpot!','https://static.zerochan.net/Hakari.Kinji.full.3823831.jpg','Idle Death Gamble'),
 'womb-profusion': ('Kenjaku','A evolução humana é fascinante.','https://static.zerochan.net/Kenjaku.full.3791075.jpg','Womb Profusion'),
 'threefold-affliction': ('Yorozu','Eu vou me casar com você.','https://static.zerochan.net/Yorozu.full.3884581.jpg','Threefold Affliction'),
 'authentic-mutual-love': ('Yuta Okkotsu','Rika.','https://static.zerochan.net/Okkotsu.Yuuta.full.3814945.jpg','Authentic Mutual Love'),
 'hanami-domain': ('Hanami','Os humanos precisam desaparecer.','https://static.zerochan.net/Hanami.full.3485955.jpg','Domain Expansion'),
 'dabura-domain': ('Dabura','Eu sou o rei do submundo.','https://static.zerochan.net/Jujutsu.Kaisen.full.4573758.jpg','Domain Expansion'),
 'yuji-domain': ('Yuji Itadori','Eu sou só um feiticeiro.','https://static.zerochan.net/Itadori.Yuuji.full.3974286.jpg','Domain Expansion'),
}

DOMAIN_TREES = {k:v[3] for k,v in TREE_META.items() if v[3] != '—'}
SKILL_TREE_NAMES = {"antigravity": "Antigravity System", "auspicious-beasts": "Auspicious Beasts Summon", "authentic-mutual-love": "Authentic Mutual Love Domain", "black-bird": "Black Bird Manipulation", "blood": "Blood Manipulation", "boogie-woogie": "Boogie Woogie", "cloning": "Cloning Technique", "comedian": "Comedian", "construction": "Construction", "contractual-recreation": "Contractual Re-Creation", "copy": "Copy", "cursed-speech": "Cursed Speech", "cursed-spirit-manipulation": "Cursed Spirit Manipulation", "dabura-domain": "Dabura Domain", "deadly-sentencing": "Deadly Sentencing Domain", "disaster-flames": "Disaster Flames", "disaster-plants": "Disaster Plants", "disaster-tides": "Disaster Tides", "granite-blast": "Granite Blast", "hanami-domain": "Hanami Domain", "ice": "Ice Formation", "idle-death-gamble": "Idle Death Gamble Domain", "idle-transfiguration": "Idle Transfiguration", "inverse": "Inverse", "light": "Light", "limitless": "Limitless", "love-rendezvous": "Love Rendezvous", "miracles": "Miracles", "mythical-beast-amber": "Mythical Beast Amber", "prayer-song": "Prayer Song", "projection": "Projection Sorcery", "puppet": "Puppet Manipulation", "ratio": "Ratio Technique", "rot": "Rot Technique", "seance": "Séance Technique", "shrine": "Shrine", "sky": "Sky Manipulation", "smallpox": "Smallpox Deity Domain", "solo-forbidden-area": "Solo Forbidden Area", "star-rage": "Star Rage", "straw-doll": "Straw Doll Technique", "technique-extinguishment": "Technique Extinguishment", "ten-shadows": "Ten Shadows Technique", "threefold-affliction": "Threefold Affliction Domain", "womb-profusion": "Womb Profusion Domain", "yuji-domain": "Yuji Domain"}
SKILL_TREE_OPTIONS_TEXT = {k:v for k,v in SKILL_TREE_NAMES.items()}

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
        CREATE TABLE IF NOT EXISTS users(id SERIAL PRIMARY KEY,username TEXT NOT NULL,password_hash TEXT NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,last_processed_day TEXT,xp INTEGER NOT NULL DEFAULT 0);
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
    else:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL UNIQUE COLLATE NOCASE,password_hash TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,last_processed_day TEXT,xp INTEGER NOT NULL DEFAULT 0);
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

def _created_date(u):
    raw=str(u['created_at'])[:10]
    try:return date.fromisoformat(raw)
    except Exception:return today()

def progression_for(c,u):
    created=_created_date(u); elapsed=max(0,(today()-created).days)
    tasks=get_tasks(c,u['id'])
    # Consistência = compromissos realmente assumidos e cumpridos; dias sem
    # compromisso não contam contra o jogador.
    due=done=0
    broken_vote=False
    d=created
    yesterday=today()-timedelta(days=1)
    while d<=yesterday:
        wd=d.weekday(); completed=completion_set(c,u['id'],iso(d))
        for t in tasks:
            if wd not in t['frequencia']: continue
            due+=1
            if t['id'] in completed: done+=1
            elif t['tipo']=='voto': broken_vote=True
        d+=timedelta(days=1)
    score=round((done/due)*100,1) if due else 0.0
    # Quebrar qualquer voto vinculativo concluído/previsto no passado zera o
    # ciclo de progressão. O dia de hoje só é avaliado ao terminar.
    if broken_vote:
        return {'grade':'Grade 4','score':0.0,'dias':0,'tenure':elapsed,'next':'Grade 3','broken_vote':True,'hp':70,'ce':250,'ct':3}
    grade=GRADE_STATS[0]
    for g,min_days,hp,ce,ct in GRADE_STATS:
        if elapsed>=min_days and score >= ({'Grade 4':0,'Grade 3':70,'Grade 2':75,'Grade 1':80,'Special Grade':85}[g]):
            grade=(g,min_days,hp,ce,ct)
    idx=[x[0] for x in GRADE_STATS].index(grade[0]); nxt=GRADE_STATS[min(idx+1,len(GRADE_STATS)-1)]
    return {'grade':grade[0],'score':score,'dias':elapsed,'tenure':elapsed,'next':nxt[0],'broken_vote':False,'hp':grade[2],'ce':grade[3],'ct':grade[4]}

def tree_payload(tree_id):
    m=TREE_META.get(tree_id)
    if not m:return None
    return {'id':tree_id,'nome':SKILL_TREE_NAMES.get(tree_id,tree_id),'descricao':f'Técnica amaldiçoada associada a {m[0]}.','personagem':m[0],'frase':m[1],'imagem':m[2],'dominio':m[3]}

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
    tree_id=(ch['skill_tree'] if ch and 'skill_tree' in ch.keys() else None)
    c.commit();c.close()
    return {'usuario':u['username'],'xp':int(u['xp'] or 0),'tarefas':tasks,'streaks':s,'personagem':None if not ch else {'body':base['body'],'mind':base['mind'],'soul':base['soul'],'classe':ch['class_name'],'skill_tree':tree_id},'votoBonus':bonus,'progresso':prog,'skill_tree':tree_payload(tree_id)}

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
        uid=insert_and_get_id(c, 'INSERT INTO users(username,password_hash,last_processed_day) VALUES(?,?,?)',(username,generate_password_hash(password),iso(today()-timedelta(days=1))))
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
        session.clear();session['admin']=True;session.permanent=True
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
    return jsonify([{'id':r['id'],'usuario':r['username'],'criado_em':str(r['created_at']),'xp':int(r['xp'] or 0)} for r in rows])

@app.delete('/api/admin/users/<int:uid>')
def admin_delete_user_route(uid):
    ok,err=require_admin()
    if not ok:return err
    c=db(); row=c.execute('SELECT username FROM users WHERE id=?',(uid,)).fetchone()
    if not row:c.close();return jsonify(error='Usuário não encontrado.'),404
    if str(row['username']).upper()=='ADMIN':c.close();return jsonify(error='A conta ADMIN não pode ser apagada.'),400
    admin_delete_user(c,uid);c.commit();c.close();return jsonify(ok=True)

@app.get('/api/admin/export-sql')
def admin_export_sql():
    ok,err=require_admin()
    if not ok:return err
    if not DATABASE_URL:return jsonify(error='Exportação SQL administrativa está disponível para PostgreSQL.'),400
    tables=['users','characters','tasks','completions','streaks','vote_bonuses','user_skills','battles','hunts','entity_battles','pvp_daily']
    c=db(); lines=['-- Cursed Mission PostgreSQL backup','-- Gerado pelo painel ADM','-- Importe somente em uma base do A Travessia.','','TRUNCATE TABLE '+', '.join(tables)+' CASCADE;']
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
    return Response(sql,mimetype='application/sql',headers={'Content-Disposition':'attachment; filename=travessia_backup.sql'})

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
    ch=c.execute('SELECT * FROM characters WHERE user_id=?',(uid,)).fetchone();base={'body':0.0,'mind':0.0,'soul':0.0} if not ch else {'body':float(ch['body'] or 0),'mind':float(ch['mind'] or 0),'soul':float(ch['soul'] or 0)};bonus={x:0.0 for x in CLASSES}
    for r in c.execute('SELECT class,bonus FROM vote_bonuses WHERE user_id=?',(uid,)):bonus[r['class']]=float(r['bonus'])
    eff={'body':base['body']+bonus['corpo'],'mind':base['mind']+bonus['mente'],'soul':base['soul']+bonus['alma']}
    return base,bonus,eff,ch

def stats_for(attrs,days):
    # Compatibilidade para chamadas antigas: a escala agora é determinada pelo grau.
    d=max(0,int(days or 0)); g='Special Grade' if d>=180 else 'Grade 1' if d>=90 else 'Grade 2' if d>=30 else 'Grade 3' if d>=7 else 'Grade 4'
    row=next(x for x in GRADE_STATS if x[0]==g)
    return {'F':{},'HP':row[2],'CE':row[3],'CT':row[4]}

@app.get('/api/profile')
def profile():
    u,err=require_user()
    if err:return err
    c=db();process_until_yesterday(c,u);vals={x:{'dias':0,'ultimoDia':None} for x in CLASSES}
    for r in c.execute('SELECT class,days,last_day FROM streaks WHERE user_id=?',(u['id'],)):vals[r['class']]={'dias':int(r['days']),'ultimoDia':r['last_day']}
    vals=current_day_streaks(c,u['id'],vals);days={x:int(vals[x]['dias']) for x in CLASSES};base,bonus,eff,ch=attributes_for(c,u['id']);prog=progression_for(c,u); stats={'HP':prog['hp'],'CE':prog['ce'],'CT':prog['ct']}; tree=tree_payload(ch['skill_tree'] if ch and 'skill_tree' in ch.keys() else None);c.commit();c.close()
    return jsonify(usuario=u['username'],base=base,voto=bonus,atributos=eff,dias=days,stats=stats,progresso=prog,skill_tree=tree)

@app.get('/api/skills')
def skills():
    u,err=require_user()
    if err:return err
    c=db(); owned={r['skill_id']:bool(r['equipped']) for r in c.execute('SELECT skill_id,equipped FROM user_skills WHERE user_id=?',(u['id'],))}
    xp=int(u['xp'] or 0); prog=progression_for(c,u); ct=prog['ct']
    ch=c.execute('SELECT skill_tree FROM characters WHERE user_id=?',(u['id'],)).fetchone(); tree_id=ch['skill_tree'] if ch else None
    meta=tree_payload(tree_id)
    out=[]
    # O catálogo antigo continua disponível para compatibilidade do combate; a
    # interface agora apresenta a identidade da árvore e não transforma domínio em compra.
    for sid,name,cat,skill_ct,ce,effect in SKILLS:
        cost={1:50,2:100,3:175,4:275,5:400}[skill_ct]
        acquired=sid in owned
        out.append({'id':sid,'nome':name,'categoria':cat,'ct':skill_ct,'ce':ce,'efeito':skill_dict(sid)['efeito'],'preco_xp':cost,'adquirida':acquired,'pode_comprar':(not acquired and skill_ct<=ct and xp>=cost),'equipada':owned.get(sid,False)})
    power=vote_power_multiplier(c,u['id'])
    domains=[]
    if meta and meta['dominio']!='—':
        unlocked=prog['grade'] in ('Grade 1','Special Grade')
        domains=[{'nome':meta['dominio'],'efeito':'Nó final da sua Skill Tree. Não é comprado com XP.','requisito':'Grade 1 + domínio das técnicas anteriores','desbloqueada':unlocked}]
    c.close();return jsonify(skills=out,xp=xp,ct=ct,skill_tree=tree_id,skill_tree_nome=meta['nome'] if meta else None,skill_tree_descricao=(SKILL_TREE_OPTIONS_TEXT.get(tree_id) if tree_id else None),tree_meta=meta,progresso=prog,domains=domains,poder_voto=power)

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

def vote_power_multiplier(c,uid):
    # Cada voto vinculativo ativo aumenta o poder de combate em 10%.
    n=int(c.execute('SELECT COUNT(*) AS n FROM vote_bonuses WHERE user_id=?',(uid,)).fetchone()['n'] or 0)
    return 1.0 + 0.10*n

def current_ct(c,uid):
    u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    if not u:return 3
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
    base,bonus,eff,ch=attributes_for(c,uid)
    days=max([int(r['days']) for r in c.execute('SELECT days FROM streaks WHERE user_id=?',(uid,))] or [1])
    return stats_for(eff,days)

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
    base,bonus,eff,ch=attributes_for(c,u['id']); days=max([int(r['days']) for r in c.execute('SELECT days FROM streaks WHERE user_id=?',(u['id'],))] or [1]); st=stats_for(eff,days)
    bid=insert_and_get_id(c, 'INSERT INTO entity_battles(user_id,entity_json,hp_player,ce_player,hp_entity,status,turn,log_json) VALUES(?,?,?,?,?,?,?,?)',(u['id'],json.dumps(entity,ensure_ascii=False),st['HP'],st['CE'],float(entity['hp']),'active','player',json.dumps([])));c.commit();c.close();return jsonify(id=bid)

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
    c=db(); row=c.execute('SELECT count FROM pvp_daily WHERE user_id=? AND day=?',(u['id'],iso(today()))).fetchone(); c.close()
    used=int(row['count']) if row else 0
    return jsonify(usados=min(used,2),restantes=max(0,2-used))

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
    name=str((request.get_json(silent=True) or {}).get('oponente','')).strip();c=db();opp=c.execute('SELECT * FROM users WHERE LOWER(username)=LOWER(?)',(name,)).fetchone()
    if not opp:c.close();return jsonify(error='Adversário não encontrado.'),404
    if opp['id']==u['id']:c.close();return jsonify(error='Você não pode desafiar a si mesmo.'),400
    day=iso(today())
    my_count=c.execute('SELECT count FROM pvp_daily WHERE user_id=? AND day=?',(u['id'],day)).fetchone()
    opp_count=c.execute('SELECT count FROM pvp_daily WHERE user_id=? AND day=?',(opp['id'],day)).fetchone()
    if my_count and int(my_count['count'])>=2:c.close();return jsonify(error='Você já atingiu o limite de 2 combates PvP hoje.'),400
    if opp_count and int(opp_count['count'])>=2:c.close();return jsonify(error='Esse jogador já atingiu o limite de 2 combates PvP hoje.'),400
    s1=battle_stats(c,u['id']);s2=battle_stats(c,opp['id'])
    bid=insert_and_get_id(c, 'INSERT INTO battles(player1,player2,turn_user,status,hp1,ce1,hp2,ce2,log_json) VALUES(?,?,?,?,?,?,?,?,?)',(u['id'],opp['id'],u['id'],'active',s1['HP'],s1['CE'],s2['HP'],s2['CE'],json.dumps([f'{u["username"]} iniciou o combate.'])))
    for uid in (u['id'],opp['id']):
        c.execute('INSERT INTO pvp_daily(user_id,day,count) VALUES(?,?,1) ON CONFLICT(user_id,day) DO UPDATE SET count=pvp_daily.count+1',(uid,day))
    c.commit();c.close();return jsonify(id=bid,combates_restantes=max(0,1-(int(my_count['count']) if my_count else 0)))

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
