import os
import sqlite3
import psycopg2

SOURCE_DB_PATH = os.environ.get('SOURCE_DB_PATH', 'travessia.db')
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
if not DATABASE_URL:
    raise SystemExit('Defina DATABASE_URL apontando para o PostgreSQL.')

url = DATABASE_URL
if 'sslmode=' not in url:
    url += ('&' if '?' in url else '?') + 'sslmode=require'
pg = psycopg2.connect(url)
cur = pg.cursor()

schema = '''
CREATE TABLE IF NOT EXISTS users(id SERIAL PRIMARY KEY,username TEXT NOT NULL,password_hash TEXT NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,last_processed_day TEXT,xp INTEGER NOT NULL DEFAULT 0);
CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_idx ON users(LOWER(username));
CREATE TABLE IF NOT EXISTS characters(user_id INTEGER PRIMARY KEY,body DOUBLE PRECISION NOT NULL DEFAULT 0,mind DOUBLE PRECISION NOT NULL DEFAULT 0,soul DOUBLE PRECISION NOT NULL DEFAULT 0,class_name TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS tasks(id SERIAL PRIMARY KEY,user_id INTEGER NOT NULL,text TEXT NOT NULL,class TEXT NOT NULL,type TEXT NOT NULL DEFAULT 'todo',frequency_json TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]',FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS completions(task_id INTEGER NOT NULL,day TEXT NOT NULL,PRIMARY KEY(task_id,day),FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS streaks(user_id INTEGER NOT NULL,class TEXT NOT NULL,days INTEGER NOT NULL DEFAULT 0,last_day TEXT,PRIMARY KEY(user_id,class),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS vote_bonuses(user_id INTEGER NOT NULL,class TEXT NOT NULL,bonus DOUBLE PRECISION NOT NULL DEFAULT 0.5,PRIMARY KEY(user_id,class),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS user_skills(user_id INTEGER NOT NULL,skill_id TEXT NOT NULL,equipped INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,skill_id),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS battles(id SERIAL PRIMARY KEY,player1 INTEGER NOT NULL,player2 INTEGER NOT NULL,turn_user INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'active',hp1 DOUBLE PRECISION,ce1 DOUBLE PRECISION,hp2 DOUBLE PRECISION,ce2 DOUBLE PRECISION,log_json TEXT NOT NULL DEFAULT '[]',FOREIGN KEY(player1) REFERENCES users(id),FOREIGN KEY(player2) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS hunts(user_id INTEGER NOT NULL,day TEXT NOT NULL,entities_json TEXT NOT NULL,PRIMARY KEY(user_id,day),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS entity_battles(id SERIAL PRIMARY KEY,user_id INTEGER NOT NULL,entity_json TEXT NOT NULL,hp_player DOUBLE PRECISION,ce_player DOUBLE PRECISION,hp_entity DOUBLE PRECISION,status TEXT NOT NULL DEFAULT 'active',turn TEXT NOT NULL DEFAULT 'player',log_json TEXT NOT NULL DEFAULT '[]',FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
'''
for statement in schema.split(';'):
    if statement.strip():
        cur.execute(statement)
pg.commit()

src = sqlite3.connect(SOURCE_DB_PATH)
src.row_factory = sqlite3.Row

def copy_table(name, columns):
    rows = src.execute(f"SELECT {','.join(columns)} FROM {name}").fetchall()
    if not rows:
        return 0
    placeholders = ','.join(['%s'] * len(columns))
    sql = f"INSERT INTO {name} ({','.join(columns)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    for row in rows:
        cur.execute(sql, [row[c] for c in columns])
    return len(rows)

order = [
    ('users', ['id','username','password_hash','created_at','last_processed_day','xp']),
    ('characters', ['user_id','body','mind','soul','class_name']),
    ('tasks', ['id','user_id','text','class','type','frequency_json']),
    ('completions', ['task_id','day']),
    ('streaks', ['user_id','class','days','last_day']),
    ('vote_bonuses', ['user_id','class','bonus']),
    ('user_skills', ['user_id','skill_id','equipped']),
    ('battles', ['id','player1','player2','turn_user','status','hp1','ce1','hp2','ce2','log_json']),
    ('hunts', ['user_id','day','entities_json']),
    ('entity_battles', ['id','user_id','entity_json','hp_player','ce_player','hp_entity','status','turn','log_json']),
]

for table, columns in order:
    n = copy_table(table, columns)
    print(f'{table}: {n} registros processados')
pg.commit()

for table in ('users', 'tasks', 'battles', 'entity_battles'):
    cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}','id'), COALESCE((SELECT MAX(id) FROM {table}),1), true)")
pg.commit()
cur.close()
pg.close()
src.close()
print('Migração concluída.')
