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

SKILLS = [
    # id, nome, categoria, CT, CE, dano, efeito, tipo
    ('dismantle','Dismantle','ofensiva',1,20,'2+1d6','Corte à distância.','damage'),
    ('cleave','Cleave','ofensiva',3,80,'3+2d4','Corte adaptativo: +2 dano contra alvos de Defesa muito alta.','damage'),
    ('spiderweb','Spiderweb','ofensiva',3,80,'2+2d4','Cortes em área; -2 Movimento por 2 turnos.','damage'),
    ('furnace','Furnace / Divine Flame','ofensiva',4,240,'4+2d6','Queimadura: 1d4 dano no início de cada rodada por 2 rodadas.','damage'),
    ('blue','Blue','espacial',1,20,'2+1d6','Atração espacial: -2 Defesa e puxa o alvo.','damage'),
    ('red','Cursed Technique Reversal: Red','reversa',2,40,'3+2d4','Repulsão: empurra o alvo e remove sua próxima reação.','damage'),
    ('hollow-purple','Hollow Purple','maxima',4,240,'4+2d6','Ignora 2 pontos de Defesa/mitigação.','damage'),
    ('infinity','Infinity','defensiva',1,20,'0','Barreira espacial: ataques físicos contra o usuário sofrem -5 no acerto. Custa 20 CE por rodada.','defense'),
    ('divine-dogs','Divine Dogs','invocacao',1,5,'1+1d4','Shikigami de combate básico.','damage'),
    ('nue','Nue','invocacao',1,20,'2+1d4','Ataque elétrico/aéreo: -1 Acerto por 1 rodada.','damage'),
    ('great-frog','Great Serpent / Great Frog','invocacao',1,20,'0','Puxa, agarra ou reposiciona um alvo.','control'),
    ('max-elephant','Max Elephant','invocacao',3,80,'2+2d4','Inunda a área; Movimento reduzido pela metade.','damage'),
    ('round-deer','Round Deer','invocacao',3,80,'0','Remove 1 debuff ou recupera 2d6 HP.','heal'),
    ('piercing-ox','Piercing Ox','invocacao',3,80,'3+2d6','Investida; +1 dano se percorreu longa distância.','damage'),
    ('mahoraga','Mahoraga','invocacao',4,240,'4+2d6','Adaptação: após 2 exposições ao mesmo tipo de efeito, ganha resistência; após 3, imunidade.','damage'),
    ('uzumaki','Maximum: Uzumaki','maxima',4,240,'4+2d6','Condensa espíritos amaldiçoados em um ataque máximo.','damage'),
    ('transfiguration','Idle Transfiguration','alma',3,80,'2+1d6','Altera a alma: -2 Defesa por 2 turnos.','damage'),
    ('soul-manipulation','Soul Manipulation','alma',3,80,'3+2d4','Dano à alma: após 2 acertos no mesmo alvo, -2 em testes físicos.','damage'),
    ('nobara-nails','Straw Doll: Nails','ofensiva',1,5,'1+1d4','Pregos amaldiçoados.','damage'),
    ('hairpin','Hairpin','ofensiva',1,20,'2+1d6','Detona pregos já cravados.','damage'),
    ('resonance','Resonance','alma',3,80,'3+2d4','Se possuir parte do alvo, ignora 2 Defesa.','damage'),
    ('ratio','Ratio Technique','ofensiva',1,20,'2+1d6','Ponto fraco 7:3: se acertar o ponto, +2 dano.','damage'),
    ('collapse','Collapse','ofensiva',3,80,'3+2d4','Área; -1 Defesa por 1 rodada.','damage'),
    ('projection','Projection Sorcery','controle',1,20,'0','Movimento em 24 quadros: ganha movimento adicional; alvo pode ficar Imobilizado por 1 rodada.','control'),
    ('piercing-blood','Piercing Blood','ofensiva',2,20,'2+1d6','Disparo de sangue em alta velocidade.','damage'),
    ('flowing-red-scale','Flowing Red Scale','reforco',2,20,'0','+2 Ataque e +2 Defesa por 2 rodadas.','buff'),
    ('supernova','Supernova','ofensiva',3,80,'3+2d4','Projéteis de sangue em área.','damage'),
    ('boogie-woogie','Boogie Woogie','controle',1,20,'0','Troca a posição de dois alvos válidos; +2 no próximo ataque.','control'),
    ('cursed-speech-stop','Cursed Speech: Stop','controle',1,20,'0','O alvo perde a próxima ação.','control'),
    ('cursed-speech-repel','Cursed Speech: Repel','controle',1,20,'0','Empurra o alvo.','control'),
    ('cursed-speech-sleep','Cursed Speech: Sleep','controle',3,80,'0','O alvo fica incapacitado por 1 rodada.','control'),
    ('copy','Copy','versatil',3,20,'0','Copia uma técnica sob as condições da técnica; custo da cópia segue a técnica copiada +20 CE.','special'),
    ('construction','Construction','versatil',1,20,'0','Cria matéria/objetos. Construções complexas custam 80; extremas, 240.','special'),
    ('star-rage','Star Rage','ofensiva',3,80,'3+2d6','Massa virtual: ignora 2 pontos de Defesa.','damage'),
    ('sky-manipulation','Sky Manipulation','espacial',3,80,'2+2d4','Distorce o céu/espaço: -2 Defesa por 2 rodadas.','damage'),
    ('granite-blast','Granite Blast','ofensiva',3,80,'3+2d4','Descarga concentrada de energia amaldiçoada.','damage'),
    ('comedian','Comedian','especial',3,80,'0','Se a situação for genuinamente engraçada para o usuário, o Mestre pode permitir o efeito desejado.','special'),
    ('technique-extinguishment','Technique Extinguishment','anulacao',4,240,'4+2d6','Anula uma técnica amaldiçoada do alvo por 1 rodada; efeitos extremos exigem resistência.','damage'),
    ('inverse','Inverse','defensiva',1,20,'0','Inverte força/efeito: ataques fortes podem virar dano baixo e vice-versa.','defense'),
    ('seance','Séance Technique','especial',2,20,'0','Usa um cadáver para manifestar características de outra pessoa.','special'),
    ('puppet-manipulation','Puppet Manipulation','invocacao',1,5,'1+1d4','Controla bonecos; unidades avançadas custam mais CE.','damage'),
    ('auspicious-beasts','Auspicious Beasts Summon','invocacao',2,20,'2+1d4','Invoca Bestas Auspiciosas com funções diferentes.','damage'),
    ('rot','Rot Technique','ofensiva',1,20,'2+1d6','Sangramento: 1d4 dano no início de cada rodada.','damage'),
    ('cloning','Cloning Technique','especial',3,80,'0','Cria uma cópia com 50% dos atributos do original.','special'),
    ('miracles','Miracles','especial',1,5,'0','Armazena uma chance; pode consumir 1 Milagre para transformar um efeito decisivo em sucesso parcial.','special'),
    ('ice-formation','Ice Formation','controle',3,80,'3+2d4','Lentidão extrema por 2 rodadas; falha em resistência pode causar Imobilização por 1 rodada.','damage'),
    ('disaster-flames','Disaster Flames','ofensiva',1,20,'2+1d6','Queimadura por 1 rodada.','damage'),
    ('meteor','Maximum: Meteor','maxima',4,240,'4+2d6','Área enorme de impacto vulcânico.','damage'),
    ('disaster-plants','Disaster Plants','controle',1,20,'2+1d6','Prende/retarda: -2 Movimento.','damage'),
    ('disaster-tides','Disaster Tides','ofensiva',1,20,'2+1d6','Manipula água e invoca criaturas aquáticas.','damage'),
    ('contractual-recreation','Contractual Re-Creation','especial',1,20,'0','Transforma recibos/contratos em objetos equivalentes temporariamente.','special'),
    ('love-rendezvous','Love Rendezvous','controle',1,20,'0','Impede que alvos designados se aproximem diretamente.','control'),
    ('solo-forbidden-area','Solo Forbidden Area','reforco',1,5,'0','Fortalece uma unidade/corvo dentro das condições da técnica.','buff'),
    ('black-bird-manipulation','Black Bird Manipulation','invocacao',1,5,'1+1d4','Controla corvos e compartilha sua visão.','damage'),
    ('mythical-beast-amber','Mythical Beast Amber','maxima',4,240,'4+2d6','Aumenta velocidade/percepção e permite ataques elétricos. Uso limitado a 1 vez por combate.','damage'),
    ('prayer-song','Prayer Song','reforco',3,80,'0','Fortalece capacidades físicas do usuário.','buff'),
    ('antigravity-system','Antigravity System','defensiva',3,80,'0','Neutraliza efeitos gravitacionais.','defense'),
    ('gravity-reversal','Gravity Reversal','reversa',4,160,'3+2d4','Reversão do Antigravity System: aumenta a gravidade; -2 Movimento e -2 Defesa por 2 rodadas.','damage'),
    ('light','Light','especial',1,20,'2+1d6','Dispara/solidifica luz para ataque e movimentação.','damage'),
    ('darkness','Darkness — Reversal of Light','reversa',1,40,'2+1d6','Reversão de Light: cria escuridão; -2 Visão e -2 Defesa.','damage'),
    # Domínios
    ('domain-malevolent-shrine','Domain Expansion: Malevolent Shrine','dominio',4,240,'3+2d4','Acerto garantido; todos os inimigos sofrem o dano por rodada por 3 rodadas e -2 Defesa.','domain'),
    ('domain-unlimited-void','Domain Expansion: Unlimited Void','dominio',4,240,'0','Acerto garantido; alvo fica Atordoado por 2 rodadas e não pode usar técnicas durante o efeito.','domain'),
    ('domain-self-embodiment','Domain Expansion: Self-Embodiment of Perfection','dominio',4,240,'3+2d6','Acerto garantido; manipulação da alma e -2 Defesa até receber tratamento.','domain'),
    ('domain-coffin-iron-mountain','Domain Expansion: Coffin of the Iron Mountain','dominio',4,240,'4+2d4','Acerto garantido; Queimadura e 1d4 adicional por 2 rodadas.','domain'),
    ('domain-horizon-skandha','Domain Expansion: Horizon of the Captivating Skandha','dominio',4,240,'3+1d6','Acerto garantido; criaturas aquáticas atacam continuamente.','domain'),
    ('domain-smallpox','Domain Expansion: Smallpox Deity','dominio',4,240,'3+2d4','Acerto garantido; caixão/lápide aprisiona o alvo por 1 rodada.','domain'),
    ('domain-deadly-sentencing','Domain Expansion: Deadly Sentencing','dominio',4,240,'0','Julgamento: pode resultar em Confisco (técnica bloqueada por 2 rodadas) ou pena máxima.','domain'),
    ('domain-idle-death-gamble','Domain Expansion: Idle Death Gamble','dominio',4,240,'0','Jogo de azar: Jackpot concede CE ilimitada e regeneração por 4 rodadas.','domain'),
    ('domain-time-cell','Domain Expansion: Time Cell Moon Palace','dominio',4,240,'0','Acerto garantido; regras dos 24 quadros: -2 Defesa, Lentidão e depois Imobilização.','domain'),
    ('domain-womb-profusion','Domain Expansion: Womb Profusion','dominio',4,240,'4+2d4','Acerto garantido; -2 Defesa por 3 rodadas.','domain'),
    ('domain-threefold-affliction','Domain Expansion: Threefold Affliction','dominio',4,240,'3+2d6','Acerto garantido; construção da técnica recebe acerto garantido.','domain'),
    ('domain-authentic-mutual-love','Domain Expansion: Authentic Mutual Love','dominio',4,240,'3+2d4','Acerto garantido; permite técnicas copiadas e escolhe uma para o efeito garantido.','domain'),
    ('domain-yuji','Domain Expansion: Yuji','dominio',4,240,'3+2d4','Acerto garantido; Dismantle direcionado à alma e -2 Defesa.','domain'),
    ('domain-chimera-shadow','Domain Expansion: Chimera Shadow Garden','dominio',4,160,'0','Domínio incompleto: sem acerto garantido; Dez Sombras recebem +2 dano e múltiplas invocações.','domain'),
    ('domain-hanami','Domain Expansion: Hanami','dominio',4,240,'3+2d4','Domínio sem nome conhecido; efeito de natureza vegetal, com acerto garantido nesta adaptação.','domain'),
    ('domain-yuki','Domain Expansion: Yuki','dominio',4,240,'3+2d4','Domínio sem efeito canônico revelado; nesta adaptação recebe impacto de massa virtual.','domain'),
    ('domain-uro','Domain Expansion: Uro','dominio',4,240,'3+2d4','Domínio sem efeito canônico revelado; nesta adaptação distorce o espaço e reduz Defesa em 2.','domain'),
    ('domain-ryu','Domain Expansion: Ryu','dominio',4,240,'4+2d4','Domínio sem efeito canônico revelado; nesta adaptação garante uma descarga de energia.','domain'),
    ('domain-dabura','Otherworld Between Darkness and Light: Reverse Transcendence','dominio',4,240,'3+2d6','Domínio de Dabura; efeito garantido não revelado, então fica deliberadamente aberto para o Mestre.','domain'),
]


# Uma personagem pertence a UMA única árvore de técnica.
# A árvore é escolhida na criação e controla tudo que pode ser aprendido depois.
SKILL_TREES = {
    'shrine': {'nome':'Shrine','descricao':'Cortes, teia e fogo de Sukuna.','skills':['dismantle','cleave','spiderweb','furnace','domain-malevolent-shrine']},
    'limitless': {'nome':'Limitless','descricao':'Manipulação do espaço: Infinity, Blue, Red e Hollow Purple.','skills':['infinity','blue','red','hollow-purple','domain-unlimited-void']},
    'ten-shadows': {'nome':'Ten Shadows Technique','descricao':'Shikigami das Dez Sombras e Chimera Shadow Garden.','skills':['divine-dogs','nue','great-frog','max-elephant','round-deer','piercing-ox','mahoraga','domain-chimera-shadow']},
    'cursed-spirit-manipulation': {'nome':'Cursed Spirit Manipulation','descricao':'Controle e compressão de espíritos amaldiçoados.','skills':['uzumaki']},
    'idle-transfiguration': {'nome':'Idle Transfiguration','descricao':'Manipulação da alma e transformação corporal.','skills':['transfiguration','soul-manipulation','domain-self-embodiment']},
    'straw-doll': {'nome':'Straw Doll Technique','descricao':'Pregos, Hairpin e Resonance.','skills':['nobara-nails','hairpin','resonance']},
    'ratio': {'nome':'Ratio Technique','descricao':'Pontos fracos e colapso estrutural.','skills':['ratio','collapse']},
    'projection': {'nome':'Projection Sorcery','descricao':'Movimento e ação em 24 quadros por segundo.','skills':['projection']},
    'blood': {'nome':'Blood Manipulation','descricao':'Controle do próprio sangue para ataque e reforço.','skills':['piercing-blood','flowing-red-scale','supernova']},
    'boogie-woogie': {'nome':'Boogie Woogie','descricao':'Troca instantânea de posições.','skills':['boogie-woogie']},
    'cursed-speech': {'nome':'Cursed Speech','descricao':'Ordens amaldiçoadas que afetam o alvo.','skills':['cursed-speech-stop','cursed-speech-repel','cursed-speech-sleep']},
    'copy': {'nome':'Copy','descricao':'Cópia de técnicas sob as condições da técnica copiada.','skills':['copy']},
    'construction': {'nome':'Construction','descricao':'Criação de matéria através de energia amaldiçoada.','skills':['construction']},
    'star-rage': {'nome':'Star Rage','descricao':'Massa virtual aplicada ao combate.','skills':['star-rage','domain-yuki']},
    'sky': {'nome':'Sky Manipulation','descricao':'Distorção e manipulação da superfície do céu.','skills':['sky-manipulation','domain-uro']},
    'granite-blast': {'nome':'Granite Blast','descricao':'Descargas concentradas de energia amaldiçoada.','skills':['granite-blast','domain-ryu']},
    'comedian': {'nome':'Comedian','descricao':'A realidade se curva ao que o usuário considera genuinamente engraçado.','skills':['comedian']},
    'technique-extinguishment': {'nome':'Technique Extinguishment','descricao':'Anulação de técnicas amaldiçoadas.','skills':['technique-extinguishment']},
    'inverse': {'nome':'Inverse','descricao':'Inversão da força de ataques recebidos.','skills':['inverse']},
    'seance': {'nome':'Séance Technique','descricao':'Manifestação de características de outra pessoa através de um cadáver.','skills':['seance']},
    'puppet': {'nome':'Puppet Manipulation','descricao':'Controle de marionetes amaldiçoadas.','skills':['puppet-manipulation']},
    'auspicious-beasts': {'nome':'Auspicious Beasts Summon','descricao':'Invocação das Bestas Auspiciosas.','skills':['auspicious-beasts']},
    'rot': {'nome':'Rot Technique','descricao':'Técnica de decomposição e veneno através do sangue.','skills':['rot']},
    'cloning': {'nome':'Cloning Technique','descricao':'Criação de cópias do usuário.','skills':['cloning']},
    'miracles': {'nome':'Miracles','descricao':'Acúmulo e consumo de milagres.','skills':['miracles']},
    'ice': {'nome':'Ice Formation','descricao':'Formação e manipulação de gelo.','skills':['ice-formation','domain-time-cell']},
    'disaster-flames': {'nome':'Disaster Flames','descricao':'Chamas vulcânicas e meteorito máximo.','skills':['disaster-flames','meteor','domain-coffin-iron-mountain']},
    'disaster-plants': {'nome':'Disaster Plants','descricao':'Vegetação amaldiçoada para prender e atacar.','skills':['disaster-plants']},
    'disaster-tides': {'nome':'Disaster Tides','descricao':'Água e criaturas aquáticas amaldiçoadas.','skills':['disaster-tides','domain-horizon-skandha']},
    'contractual-recreation': {'nome':'Contractual Re-Creation','descricao':'Reconstrução de objetos a partir de contratos e recibos.','skills':['contractual-recreation']},
    'love-rendezvous': {'nome':'Love Rendezvous','descricao':'Controle de aproximação entre alvos designados.','skills':['love-rendezvous']},
    'solo-forbidden-area': {'nome':'Solo Forbidden Area','descricao':'Fortalecimento de aliados sob as condições da técnica.','skills':['solo-forbidden-area']},
    'black-bird': {'nome':'Black Bird Manipulation','descricao':'Controle e visão compartilhada através de corvos.','skills':['black-bird-manipulation']},
    'mythical-beast-amber': {'nome':'Mythical Beast Amber','descricao':'Transformação máxima baseada em eletricidade.','skills':['mythical-beast-amber']},
    'prayer-song': {'nome':'Prayer Song','descricao':'Fortalecimento de capacidades físicas através de cântico.','skills':['prayer-song']},
    'antigravity': {'nome':'Antigravity System','descricao':'Manipulação e reversão da gravidade.','skills':['antigravity-system','gravity-reversal']},
    'light': {'nome':'Light','descricao':'Manipulação de luz e sua reversão em escuridão.','skills':['light','darkness']},
    'smallpox': {'nome':'Smallpox Deity','descricao':'Domínio baseado na técnica da Divindade da Varíola.','skills':['domain-smallpox']},
    'deadly-sentencing': {'nome':'Deadly Sentencing','descricao':'Julgamento e confisco através de tribunal amaldiçoado.','skills':['domain-deadly-sentencing']},
    'idle-death-gamble': {'nome':'Idle Death Gamble','descricao':'Expansão baseada em um jogo de azar e Jackpot.','skills':['domain-idle-death-gamble']},
    'womb-profusion': {'nome':'Womb Profusion','descricao':'Expansão de domínio de Kenjaku.','skills':['domain-womb-profusion']},
    'threefold-affliction': {'nome':'Threefold Affliction','descricao':'Expansão de domínio de Yorozu.','skills':['domain-threefold-affliction']},
    'authentic-mutual-love': {'nome':'Authentic Mutual Love','descricao':'Expansão de domínio de Yuta.','skills':['domain-authentic-mutual-love']},
    'hanami-domain': {'nome':'Hanami Domain','descricao':'Expansão de domínio de Hanami.','skills':['domain-hanami']},
    'dabura-domain': {'nome':'Dabura Domain','descricao':'Expansão de domínio de Dabura.','skills':['domain-dabura']},
    'yuji-domain': {'nome':'Yuji Domain','descricao':'Expansão de domínio de Yuji.','skills':['domain-yuji']},
}

SKILL_TREE_BY_ID = {sid: tree_id for tree_id, tree in SKILL_TREES.items() for sid in tree['skills']}
SKILL_PREREQS = {
    'red':['blue'],
    'hollow-purple':['red'],
    'cleave':['dismantle'],
    'spiderweb':['cleave'],
    'furnace':['dismantle','cleave'],
    'resonance':['nobara-nails'],
    'hairpin':['nobara-nails'],
    'supernova':['piercing-blood'],
    'mahoraga':['divine-dogs','nue','great-frog','max-elephant'],
}


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
        CREATE TABLE IF NOT EXISTS battles(id SERIAL PRIMARY KEY,player1 INTEGER NOT NULL,player2 INTEGER NOT NULL,turn_user INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'active',hp1 DOUBLE PRECISION,ce1 DOUBLE PRECISION,hp2 DOUBLE PRECISION,ce2 DOUBLE PRECISION,log_json TEXT NOT NULL DEFAULT '[]',state_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(player1) REFERENCES users(id),FOREIGN KEY(player2) REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS hunts(user_id INTEGER NOT NULL,day TEXT NOT NULL,entities_json TEXT NOT NULL,PRIMARY KEY(user_id,day),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS entity_battles(id SERIAL PRIMARY KEY,user_id INTEGER NOT NULL,entity_json TEXT NOT NULL,hp_player DOUBLE PRECISION,ce_player DOUBLE PRECISION,hp_entity DOUBLE PRECISION,status TEXT NOT NULL DEFAULT 'active',turn TEXT NOT NULL DEFAULT 'player',log_json TEXT NOT NULL DEFAULT '[]',state_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS pvp_daily(user_id INTEGER NOT NULL,day TEXT NOT NULL,count INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,day),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        ''')
    else:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL UNIQUE COLLATE NOCASE,password_hash TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,last_processed_day TEXT,xp INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS characters(user_id INTEGER PRIMARY KEY,body REAL NOT NULL DEFAULT 0,mind REAL NOT NULL DEFAULT 0,soul REAL NOT NULL DEFAULT 0,class_name TEXT,skill_tree TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,text TEXT NOT NULL,class TEXT NOT NULL,type TEXT NOT NULL DEFAULT 'todo',frequency_json TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]',FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS completions(task_id INTEGER NOT NULL,day TEXT NOT NULL,PRIMARY KEY(task_id,day),FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS streaks(user_id INTEGER NOT NULL,class TEXT NOT NULL,days INTEGER NOT NULL DEFAULT 0,last_day TEXT,PRIMARY KEY(user_id,class),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS vote_bonuses(user_id INTEGER NOT NULL,class TEXT NOT NULL,bonus REAL NOT NULL DEFAULT 0.5,PRIMARY KEY(user_id,class),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS user_skills(user_id INTEGER NOT NULL,skill_id TEXT NOT NULL,equipped INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,skill_id),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS battles(id INTEGER PRIMARY KEY AUTOINCREMENT,player1 INTEGER NOT NULL,player2 INTEGER NOT NULL,turn_user INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'active',hp1 REAL,ce1 REAL,hp2 REAL,ce2 REAL,log_json TEXT NOT NULL DEFAULT '[]',state_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(player1) REFERENCES users(id),FOREIGN KEY(player2) REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS hunts(user_id INTEGER NOT NULL,day TEXT NOT NULL,entities_json TEXT NOT NULL,PRIMARY KEY(user_id,day),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS entity_battles(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,entity_json TEXT NOT NULL,hp_player REAL,ce_player REAL,hp_entity REAL,status TEXT NOT NULL DEFAULT 'active',turn TEXT NOT NULL DEFAULT 'player',log_json TEXT NOT NULL DEFAULT '[]',state_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS pvp_daily(user_id INTEGER NOT NULL,day TEXT NOT NULL,count INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,day),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        ''')
        cols=[r['name'] for r in c.execute('PRAGMA table_info(tasks)')]
        if 'frequency_json' not in cols: c.execute("ALTER TABLE tasks ADD COLUMN frequency_json TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]'")
        cols=[r['name'] for r in c.execute('PRAGMA table_info(users)')]
        if 'last_processed_day' not in cols: c.execute('ALTER TABLE users ADD COLUMN last_processed_day TEXT')
        for r in c.execute("SELECT DISTINCT user_id,class FROM tasks WHERE type='voto'").fetchall():
            c.execute('INSERT OR IGNORE INTO vote_bonuses(user_id,class,bonus) VALUES (?,?,0.5)',(r['user_id'],r['class']))
    # Migração da árvore de técnica para bancos já existentes.
    try:
        if DATABASE_URL:
            c.execute('ALTER TABLE characters ADD COLUMN IF NOT EXISTS skill_tree TEXT')
        else:
            cols=[r['name'] for r in c.execute('PRAGMA table_info(characters)')]
            if 'skill_tree' not in cols: c.execute('ALTER TABLE characters ADD COLUMN skill_tree TEXT')
    except Exception:
        pass
    try:
        if DATABASE_URL:
            c.execute("ALTER TABLE battles ADD COLUMN IF NOT EXISTS state_json TEXT NOT NULL DEFAULT '{}'")
            c.execute("ALTER TABLE entity_battles ADD COLUMN IF NOT EXISTS state_json TEXT NOT NULL DEFAULT '{}'")
        else:
            cols=[r['name'] for r in c.execute('PRAGMA table_info(battles)')]
            if 'state_json' not in cols: c.execute("ALTER TABLE battles ADD COLUMN state_json TEXT NOT NULL DEFAULT '{}'")
            cols=[r['name'] for r in c.execute('PRAGMA table_info(entity_battles)')]
            if 'state_json' not in cols: c.execute("ALTER TABLE entity_battles ADD COLUMN state_json TEXT NOT NULL DEFAULT '{}'")
    except Exception:
        pass
    c.commit(); c.close()
init_db()

# A lista de skills foi substituída pelo sistema Jujutsu; remove habilidades antigas que não existem mais.
try:
    _c=db(); _ids={x[0] for x in SKILLS}; _rows=_c.execute('SELECT skill_id FROM user_skills').fetchall(); _valid=[r['skill_id'] for r in _rows if r['skill_id'] in _ids];
    for r in _rows:
        if r['skill_id'] not in _ids: _c.execute('DELETE FROM user_skills WHERE skill_id=?',(r['skill_id'],))
    _c.commit(); _c.close()
except Exception:
    pass

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
    c=db(); process_until_yesterday(c,u); tasks=[t for t in get_tasks(c,u['id']) if today().weekday() in t['frequencia']]; done=completion_set(c,u['id'],iso(today()))
    for t in tasks:t['concluida']=t['id'] in done
    s={k:dict(v) for k,v in DEFAULT_STREAKS.items()}
    for r in c.execute('SELECT class,days,last_day FROM streaks WHERE user_id=?',(u['id'],)):s[r['class']]={'dias':r['days'],'ultimoDia':r['last_day']}
    s=current_day_streaks(c,u['id'],s)
    ch=c.execute('SELECT * FROM characters WHERE user_id=?',(u['id'],)).fetchone()
    base={'body':float(ch['body'] or 0),'mind':float(ch['mind'] or 0),'soul':float(ch['soul'] or 0)} if ch else {'body':0.0,'mind':0.0,'soul':0.0}
    bonus={x:0.0 for x in CLASSES}
    for r in c.execute('SELECT class,bonus FROM vote_bonuses WHERE user_id=?',(u['id'],)):bonus[r['class']]=float(r['bonus'])
    c.commit(); c.close()
    return {'tarefas':tasks,'streaks':s,'personagem':None if not ch else {'body':base['body'],'mind':base['mind'],'soul':base['soul'],'classe':ch['class_name'],'skill_tree':ch['skill_tree']},'votoBonus':bonus}

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
    c=db(); lines=['-- A Travessia PostgreSQL backup','-- Gerado pelo painel ADM','-- Importe somente em uma base do A Travessia.','','TRUNCATE TABLE '+', '.join(tables)+' CASCADE;']
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
    if tree not in SKILL_TREES:return jsonify(error='Escolha uma árvore de técnica válida.'),400
    c=db();existing=c.execute('SELECT skill_tree FROM characters WHERE user_id=?',(u['id'],)).fetchone()
    if existing and existing['skill_tree'] and existing['skill_tree']!=tree:c.close();return jsonify(error='A árvore de técnica só pode ser escolhida uma vez, na criação do personagem.'),400
    c.execute('INSERT INTO characters(user_id,body,mind,soul,class_name,skill_tree) VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET body=excluded.body,mind=excluded.mind,soul=excluded.soul,class_name=excluded.class_name,skill_tree=COALESCE(characters.skill_tree,excluded.skill_tree)',(u['id'],body,mind,soul,cls,tree));c.commit();c.close();return jsonify(ok=True,skill_tree=tree)

def attributes_for(c,uid):
    ch=c.execute('SELECT * FROM characters WHERE user_id=?',(uid,)).fetchone();base={'body':0.0,'mind':0.0,'soul':0.0} if not ch else {'body':float(ch['body'] or 0),'mind':float(ch['mind'] or 0),'soul':float(ch['soul'] or 0)};bonus={x:0.0 for x in CLASSES}
    for r in c.execute('SELECT class,bonus FROM vote_bonuses WHERE user_id=?',(uid,)):bonus[r['class']]=float(r['bonus'])
    eff={'body':base['body']+bonus['corpo'],'mind':base['mind']+bonus['mente'],'soul':base['soul']+bonus['alma']}
    return base,bonus,eff,ch

def stats_for(attrs,days):
    days=max(1,int(days or 1));F=lambda a:30/((1+(a*a)/10)*days+30);fb,fm,fs=F(attrs['body']),F(attrs['mind']),F(attrs['soul'])
    return {'F':{'corpo':fb,'mente':fm,'alma':fs},'HP':200*(1-fb),'CE':1000*(1-fs),'CT':1/fm}

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
    xp=int(u['xp'] or 0); ct=current_ct(c,u['id']); ch=c.execute('SELECT skill_tree FROM characters WHERE user_id=?',(u['id'],)).fetchone(); tree=ch['skill_tree'] if ch else None
    out=[]
    for sid,name,cat,skill_ct,ce,dano,effect,tipo in SKILLS:
        cost={1:50,2:100,3:175,4:275,5:400}[skill_ct]
        acquired=sid in owned
        out.append({'id':sid,'nome':name,'categoria':cat,'ct':skill_ct,'ce':ce,'dano':dano,'efeito':effect,'preco_xp':cost,'adquirida':acquired,'pode_comprar':(not acquired and bool(tree) and SKILL_TREE_BY_ID.get(sid)==tree and skill_ct<=ct and xp>=cost and all(r in owned for r in SKILL_PREREQS.get(sid,[]))),'equipada':owned.get(sid,False)})
    c.close();return jsonify(skills=out,xp=xp,ct=ct,skill_tree=tree,skill_tree_nome=(SKILL_TREES.get(tree,{}).get('nome') if tree else None),skill_tree_descricao=(SKILL_TREES.get(tree,{}).get('descricao') if tree else None))

@app.post('/api/skills/<skill_id>/buy')
def buy_skill(skill_id):
    u,err=require_user()
    if err:return err
    item=next((x for x in SKILLS if x[0]==skill_id),None)
    if not item:return jsonify(error='Skill não encontrada.'),404
    cost={1:50,2:100,3:175,4:275,5:400}[item[3]]
    c=db(); ch=c.execute('SELECT skill_tree FROM characters WHERE user_id=?',(u['id'],)).fetchone(); tree=ch['skill_tree'] if ch else None
    if not tree or SKILL_TREE_BY_ID.get(skill_id)!=tree:c.close();return jsonify(error='Essa técnica pertence a outra árvore. Seu personagem só pode aprender técnicas da árvore escolhida na criação.'),400
    owned_ids={r['skill_id'] for r in c.execute('SELECT skill_id FROM user_skills WHERE user_id=?',(u['id'],))}
    missing=[r for r in SKILL_PREREQS.get(skill_id,[]) if r not in owned_ids]
    if missing:c.close();return jsonify(error='Você precisa desbloquear primeiro: '+', '.join(skill_dict(x)['nome'] for x in missing)),400

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
    c=db(); ch=c.execute('SELECT skill_tree FROM characters WHERE user_id=?',(u['id'],)).fetchone();
    if not ch or SKILL_TREE_BY_ID.get(skill_id)!=ch['skill_tree']:c.close();return jsonify(error='Essa técnica não pertence à árvore do seu personagem.'),400
    row=c.execute('SELECT equipped FROM user_skills WHERE user_id=? AND skill_id=?',(u['id'],skill_id)).fetchone()
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
    return {'id':x[0],'nome':x[1],'categoria':x[2],'ct':x[3],'ce':x[4],'dano':x[5],'efeito':x[6],'tipo':x[7]}

def roll_damage(expr):
    return roll_dice(expr)

import random

def default_combat_state():
    return {'p1':{'defense':0,'attack':0,'skip':0,'lock':0,'burn':0,'bleed':0,'infinity':False,'jackpot':0,'uses':{}},'p2':{'defense':0,'attack':0,'skip':0,'lock':0,'burn':0,'bleed':0,'infinity':False,'jackpot':0,'uses':{}}}

def normalize_combat_state(state):
    base=default_combat_state()
    if not isinstance(state,dict): return base
    for side in ('p1','p2'):
        if isinstance(state.get(side),dict):
            base[side].update(state[side])
            if not isinstance(base[side].get('uses'),dict): base[side]['uses']={}
    return base

def tick_combat_state(state, side, hp, log, name):
    st=state[side]
    dot=0
    if st.get('burn',0)>0:
        d=roll_dice('1d4'); hp=max(0,hp-d); dot+=d; st['burn']=max(0,st['burn']-1); log.append(f'{name} sofreu {d} de queimadura.')
    if st.get('bleed',0)>0:
        d=roll_dice('1d4'); hp=max(0,hp-d); dot+=d; st['bleed']=max(0,st['bleed']-1); log.append(f'{name} sofreu {d} de sangramento.')
    for key in ('defense','attack'):
        if st.get(key,0): st[key]=int(st[key])
    return hp,dot

def apply_skill_effect(skill, actor_side, target_side, actor_hp, target_hp, state, log, actor_name='usuário', target_name='alvo'):
    state=normalize_combat_state(state); a=state[actor_side]; t=state[target_side]
    dmg=roll_damage(skill['dano']) if skill['dano']!='0' else 0
    effect=skill['efeito']
    sid=skill['id']
    # Infinity é uma defesa persistente; domínios e anulação conseguem atravessá-la.
    if dmg and t.get('infinity') and sid not in ('domain-unlimited-void','domain-malevolent-shrine','domain-self-embodiment','domain-coffin-iron-mountain','domain-horizon-skandha','domain-smallpox','domain-deadly-sentencing','domain-idle-death-gamble','domain-time-cell','domain-womb-profusion','domain-threefold-affliction','domain-authentic-mutual-love','domain-threefold-affliction','domain-hanami','domain-yuki','domain-uro','domain-ryu','domain-dabura','domain-yuji','domain-chimera-shadow','technique-extinguishment','hollow-purple'):
        dmg=0; log.append(f'{target_name} bloqueou o ataque com Infinity.')
    else:
        mitigation=max(0,int(t.get('defense',0)))
        dmg=max(0,dmg-mitigation)
    if sid=='infinity':
        a['infinity']=True; log.append(f'{actor_name} ativou Infinity. Ataques comuns terão dificuldade de atravessar a barreira.')
    elif sid=='inverse':
        a['defense']+=2; log.append(f'{actor_name} ativou Inverse: sua defesa foi aumentada em 2.')
    elif sid=='blue':
        t['defense']-=2; log.append(f'{target_name} foi atraído por Blue e perdeu 2 de defesa.')
    elif sid=='red':
        t['skip']=max(t.get('skip',0),1); log.append(f'{target_name} foi repelido por Red e perderá a próxima ação.')
    elif sid=='spiderweb':
        t['defense']-=2; log.append(f'{target_name} ficou preso na Spiderweb e perdeu 2 de defesa por este combate.')
    elif sid in ('furnace','disaster-flames'):
        t['burn']=max(t.get('burn',0),2); log.append(f'{target_name} está queimando por 2 rodadas.')
    elif sid=='rot':
        t['bleed']=max(t.get('bleed',0),3); log.append(f'{target_name} recebeu Sangramento por 3 rodadas.')
    elif sid in ('nue','cursed-speech-stop'):
        t['skip']=max(t.get('skip',0),1); log.append(f'{target_name} perderá a próxima ação.')
    elif sid=='cursed-speech-sleep':
        t['skip']=max(t.get('skip',0),1); log.append(f'{target_name} foi incapacitado por 1 rodada.')
    elif sid=='cursed-speech-repel':
        t['defense']-=1; log.append(f'{target_name} foi empurrado e perdeu 1 de defesa.')
    elif sid=='flowing-red-scale':
        a['attack']+=2; a['defense']+=2; log.append(f'{actor_name} recebeu +2 ataque e +2 defesa.')
    elif sid=='technique-extinguishment':
        t['lock']=max(t.get('lock',0),1); t['infinity']=False; log.append(f'A técnica de {target_name} foi anulada por 1 rodada.')
    elif sid=='domain-unlimited-void':
        t['skip']=max(t.get('skip',0),2); t['lock']=max(t.get('lock',0),2); log.append(f'{target_name} ficou atordoado e sem técnicas por 2 rodadas.')
    elif sid in ('domain-malevolent-shrine','domain-self-embodiment','domain-coffin-iron-mountain','domain-horizon-skandha','domain-smallpox','domain-time-cell','domain-womb-profusion','domain-threefold-affliction','domain-authentic-mutual-love','domain-hanami','domain-yuki','domain-uro','domain-ryu','domain-dabura','domain-yuji','domain-chimera-shadow'):
        t['defense']-=2; log.append(f'O Domínio atingiu {target_name} com acerto garantido.')
        if sid in ('domain-coffin-iron-mountain',): t['burn']=max(t.get('burn',0),2)
        if sid in ('domain-smallpox',): t['skip']=max(t.get('skip',0),1)
    elif sid=='domain-deadly-sentencing':
        t['lock']=max(t.get('lock',0),2); log.append(f'Deadly Sentencing aplicou Confisco: técnicas bloqueadas por 2 rodadas.')
    elif sid=='domain-idle-death-gamble':
        a['jackpot']=4; log.append(f'{actor_name} ativou o Jackpot: CE ilimitada por 4 rodadas.')
    elif sid=='domain-threefold-affliction':
        t['defense']-=2; log.append(f'Threefold Affliction mantém o alvo sob pressão contínua.')
    elif sid=='domain-authentic-mutual-love':
        log.append(f'Authentic Mutual Love permite ao usuário explorar sua técnica copiada dentro do domínio.')
    elif sid=='mahoraga':
        a['defense']+=1; log.append(f'Mahoraga iniciou adaptação: +1 defesa.')
    elif sid=='hollow-purple':
        dmg+=2; log.append(f'Hollow Purple ignorou 2 pontos de defesa e recebeu +2 dano.')
    elif sid=='comedian':
        if random.random()<0.35: dmg=roll_damage('4+2d6'); log.append('Comedian funcionou e produziu um efeito excepcional.')
    # bônus ofensivo
    dmg=max(0,dmg+int(a.get('attack',0)))
    return dmg,state

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
            out.append({'grade':g['grade'],'streak':days,'hp':hp,'damage':damage,'ct':g['ct'],'multiplayer':g['ct']>=3,'skills':[{'id':x[0],'nome':x[1],'ce':x[4],'efeito':skill_dict(x[0])['efeito']} for x in skills]})
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
    bid=insert_and_get_id(c, 'INSERT INTO entity_battles(user_id,entity_json,hp_player,ce_player,hp_entity,status,turn,log_json,state_json) VALUES(?,?,?,?,?,?,?,?,?)',(u['id'],json.dumps(entity,ensure_ascii=False),st['HP'],st['CE'],float(entity['hp']),'active','player',json.dumps([]),json.dumps(default_combat_state())));c.commit();c.close();return jsonify(id=bid)

@app.get('/api/entity-battles/<int:bid>')
def get_entity_battle(bid):
    u,err=require_user()
    if err:return err
    c=db();b=c.execute('SELECT * FROM entity_battles WHERE id=? AND user_id=?',(bid,u['id'])).fetchone()
    if not b:c.close();return jsonify(error='Combate não encontrado.'),404
    e=json.loads(b['entity_json']); log=json.loads(b['log_json']); c.close();
    try: state=normalize_combat_state(json.loads(b['state_json']))
    except: state=default_combat_state()
    return jsonify(id=bid,entity=e,seu_hp=float(b['hp_player']),seu_ce=float(b['ce_player']),inimigo_hp=float(b['hp_entity']),status=b['status'],meu_turno=b['turn']=='player',log=log[-8:],efeitos=state['p1'])

@app.post('/api/entity-battles/<int:bid>/action')
def entity_battle_action(bid):
    u,err=require_user()
    if err:return err
    import random
    d=request.get_json(silent=True) or {}; c=db(); b=c.execute('SELECT * FROM entity_battles WHERE id=? AND user_id=?',(bid,u['id'])).fetchone()
    if not b:c.close();return jsonify(error='Combate não encontrado.'),404
    if b['status']!='active':c.close();return jsonify(error='Esse combate já terminou.'),400
    if b['turn']!='player':c.close();return jsonify(error='Aguarde o turno da maldição.'),400
    e=json.loads(b['entity_json']); hp=float(b['hp_player']); ce=float(b['ce_player']); ehp=float(b['hp_entity']); log=json.loads(b['log_json']); sid=d.get('skill_id')
    try: state=normalize_combat_state(json.loads(b['state_json']))
    except: state=default_combat_state()
    hp,_=tick_combat_state(state,'p1',hp,log,'Você')
    if hp<=0:
        status='finished'; turn='player'; log.append('Você foi derrotado pelos efeitos contínuos.')
    elif state['p1'].get('skip',0)>0:
        state['p1']['skip']-=1; log.append('Você perdeu este turno por um efeito de controle.'); status='active'; turn='player'
    else:
        if sid:
            sk=skill_dict(sid); owned=c.execute('SELECT 1 FROM user_skills WHERE user_id=? AND skill_id=? AND equipped=1',(u['id'],sid)).fetchone()
            if not sk or not owned:c.close();return jsonify(error='Skill inválida ou não equipada.'),400
            if state['p1'].get('lock',0)>0:c.close();return jsonify(error='Sua técnica está bloqueada nesta rodada. Use ataque básico.'),400
            if state['p1'].get('jackpot',0)<=0 and ce<sk['ce']:c.close();return jsonify(error='CE insuficiente.'),400
            if state['p1'].get('jackpot',0)<=0:ce-=sk['ce']
            dmg,state=apply_skill_effect(sk,'p1','p2',hp,ehp,state,log,'Você','a maldição')
            if sk['id']=='round-deer':
                heal=roll_damage('2d6'); hp=min(999,hp+heal); log.append(f'Round Deer recuperou {heal} HP.')
            log.append(f'Você usou {sk["nome"]} e causou {dmg} dano.')
        else:
            dmg=random.randint(1,4)+max(0,int(state['p1'].get('attack',0))); dmg=0 if state['p2'].get('infinity') else max(0,dmg-int(state['p2'].get('defense',0))); log.append(f'Você atacou e causou {dmg} dano.')
        ehp=max(0,ehp-dmg)
        if state['p1'].get('jackpot',0)>0:state['p1']['jackpot']-=1
        if state['p1'].get('lock',0)>0:state['p1']['lock']-=1
        if ehp<=0:
            reward=entity_xp_reward(hp,e['hp']); c.execute('UPDATE users SET xp=xp+? WHERE id=?',(reward,u['id'])); log.append(f'Maldição derrotada! +{reward} XP.'); status='finished'; turn='player'
        else:
            edmg=int(e['damage']);
            if state['p1'].get('infinity'): edmg=0; log.append('Infinity bloqueou o ataque da maldição.')
            else: edmg=max(0,edmg-int(state['p1'].get('defense',0)))
            hp=max(0,hp-edmg); log.append(f'{e["grade"]} causou {edmg} dano.'); status='finished' if hp<=0 else 'active'; turn='player'
            if hp<=0: log.append('Você foi derrotado.')
    c.execute('UPDATE entity_battles SET hp_player=?,ce_player=?,hp_entity=?,status=?,turn=?,log_json=?,state_json=? WHERE id=?',(hp,ce,ehp,status,turn,json.dumps(log,ensure_ascii=False),json.dumps(state,ensure_ascii=False),bid));c.commit();c.close();return jsonify(ok=True)

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
    bid=insert_and_get_id(c, 'INSERT INTO battles(player1,player2,turn_user,status,hp1,ce1,hp2,ce2,log_json,state_json) VALUES(?,?,?,?,?,?,?,?,?,?)',(u['id'],opp['id'],u['id'],'active',s1['HP'],s1['CE'],s2['HP'],s2['CE'],json.dumps([f'{u["username"]} iniciou o combate.']),json.dumps(default_combat_state())))
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
    c.close();
    try: state=normalize_combat_state(json.loads(b['state_json']))
    except Exception: state=default_combat_state()
    mystate=state['p1' if me1 else 'p2']
    return jsonify(id=bid,jogador1=names[0],jogador2=names[1],status=b['status'],meu_turno=b['turn_user']==u['id'],seu_hp=float(myhp),seu_ce=float(myce),inimigo_hp=float(ohp),skills=skills,log=log[-8:],efeitos={'defesa':mystate.get('defense',0),'ataque':mystate.get('attack',0),'pular':mystate.get('skip',0),'tecnicas_bloqueadas':mystate.get('lock',0),'infinity':mystate.get('infinity',False),'queimadura':mystate.get('burn',0),'sangramento':mystate.get('bleed',0)})

@app.post('/api/battles/<int:bid>/action')
def battle_action(bid):
    u,err=require_user()
    if err:return err
    d=request.get_json(silent=True) or {};sid=d.get('skill_id');c=db();b=c.execute('SELECT * FROM battles WHERE id=? AND (player1=? OR player2=?)',(bid,u['id'],u['id'])).fetchone()
    if not b:c.close();return jsonify(error='Combate não encontrado.'),404
    if b['status']!='active':c.close();return jsonify(error='Esse combate já terminou.'),400
    if b['turn_user']!=u['id']:c.close();return jsonify(error='Ainda não é o seu turno.'),400
    me1=b['player1']==u['id']; myhp=float(b['hp1'] if me1 else b['hp2']);myce=float(b['ce1'] if me1 else b['ce2']);ohp=float(b['hp2'] if me1 else b['hp1']);ohp_before=ohp;opp=b['player2'] if me1 else b['player1']; actor_side='p1' if me1 else 'p2'; target_side='p2' if me1 else 'p1'
    try: log=json.loads(b['log_json'])
    except: log=[]
    try: state=normalize_combat_state(json.loads(b['state_json']))
    except: state=default_combat_state()
    actor_name=u['username']; target_row=c.execute('SELECT username FROM users WHERE id=?',(opp,)).fetchone(); target_name=target_row['username'] if target_row else 'adversário'
    a=state[actor_side]; t=state[target_side]
    # Dano contínuo é aplicado no início do turno.
    myhp,_=tick_combat_state(state,actor_side,myhp,log,actor_name)
    if myhp<=0:
        status='finished'; turn=opp; log.append(f'{actor_name} foi derrotado pelos efeitos contínuos.')
    elif a.get('skip',0)>0:
        a['skip']-=1; log.append(f'{actor_name} perdeu este turno por um efeito de controle.'); status='active'; turn=opp
    else:
        import random
        sid=d.get('skill_id'); dmg=0
        if sid:
            sk=skill_dict(sid)
            if not sk:c.close();return jsonify(error='Skill inválida.'),400
            owned=c.execute('SELECT 1 FROM user_skills WHERE user_id=? AND skill_id=? AND equipped=1',(u['id'],sid)).fetchone()
            if not owned:c.close();return jsonify(error='Essa skill não está equipada.'),400
            if a.get('lock',0)>0:
                c.close();return jsonify(error='Sua técnica está bloqueada nesta rodada. Você ainda pode usar ataque básico.'),400
            # Jackpot dispensa o gasto de CE durante sua duração.
            if a.get('jackpot',0)<=0 and myce<sk['ce']:c.close();return jsonify(error='CE insuficiente.'),400
            if a.get('jackpot',0)<=0: myce-=sk['ce']
            dmg,state=apply_skill_effect(sk,actor_side,target_side,myhp,ohp,state,log,actor_name,target_name)
            if sid=='round-deer':
                heal=roll_damage('2d6'); myhp=min(999,myhp+heal); log.append(f'Round Deer recuperou {heal} HP.')
            if sid=='miracles':
                a['uses']['miracles']=int(a['uses'].get('miracles',0))+1; log.append('Um Milagre foi armazenado.')
            log.append(f'{actor_name} usou {sk["nome"]} e causou {dmg} dano.')
        else:
            dmg=random.randint(1,4)+max(0,int(a.get('attack',0)))
            if t.get('infinity'): dmg=0; log.append(f'{target_name} bloqueou o ataque básico com Infinity.')
            else: dmg=max(0,dmg-int(t.get('defense',0)))
            log.append(f'{actor_name} atacou e causou {dmg} dano.')
        ohp=max(0,ohp-dmg)
        if a.get('jackpot',0)>0:a['jackpot']-=1
        if a.get('lock',0)>0:a['lock']-=1
        status='active';turn=opp
        if ohp<=0:
            status='finished';turn=u['id'];reward=player_xp_reward(myhp,ohp_before) if ohp_before>0 else 0
            c.execute('UPDATE users SET xp=xp+? WHERE id=?',(reward,u['id']));log.append(f'{actor_name} venceu o combate e ganhou {reward} XP!')
    if me1:c.execute('UPDATE battles SET hp1=?,ce1=?,hp2=?,turn_user=?,status=?,log_json=?,state_json=? WHERE id=?',(myhp,myce,ohp,turn,status,json.dumps(log,ensure_ascii=False),json.dumps(state,ensure_ascii=False),bid))
    else:c.execute('UPDATE battles SET hp2=?,ce2=?,hp1=?,turn_user=?,status=?,log_json=?,state_json=? WHERE id=?',(myhp,myce,ohp,turn,status,json.dumps(log,ensure_ascii=False),json.dumps(state,ensure_ascii=False),bid))
    c.commit();c.close();return jsonify(ok=True)

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=True)
