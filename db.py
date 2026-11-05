from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from config import DATABASE_URL
import json

db_url = DATABASE_URL
if db_url.startswith("postgres://"): 
    db_url = db_url.replace("postgres://", "postgresql://", 1)
if "postgresql://" in db_url: 
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
if "sslmode" not in db_url: 
    db_url += "?sslmode=require" if "?" not in db_url else "&sslmode=require"

# استفاده از NullPool برای Transaction Mode (پورت 6543)
engine = create_engine(db_url, poolclass=NullPool)

def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY, 
            chat_id BIGINT, user_id BIGINT, display_name TEXT,
            coins INTEGER DEFAULT 100, bank_coins INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0,
            energy INTEGER DEFAULT 100, health INTEGER DEFAULT 100, 
            job TEXT, job_level INTEGER DEFAULT 0, employer_npc_id INTEGER, 
            has_sword INTEGER DEFAULT 0, has_armor INTEGER DEFAULT 0, has_dagger INTEGER DEFAULT 0,
            chicken_name TEXT DEFAULT 'جوجه', chicken_level INTEGER DEFAULT 1, chicken_eggs INTEGER DEFAULT 0,
            UNIQUE(chat_id, user_id)
        );"""))
        
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS npcs (
            id SERIAL PRIMARY KEY, chat_id BIGINT, name TEXT, role TEXT,
            schedule TEXT, coins INTEGER DEFAULT 500
        );"""))
        
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS social_edges (
            id SERIAL PRIMARY KEY, from_id BIGINT, to_id BIGINT,
            trust INTEGER DEFAULT 50, grudge INTEGER DEFAULT 0,
            last_interaction TIMESTAMP, UNIQUE(from_id, to_id)
        );"""))
        
        npc_list = [
            ("نانوا", "نانوا"), ("نگهبان", "نگهبان"), ("کشاورز", "کشاورز"),
            ("معدن‌کار", "معدن‌کار"), ("شکارچی", "شکارچی"), ("دکتر", "دکتر"),
            ("معلم", "معلم"), ("پلیس", "پلیس"), ("سایه", "کلاهبردار")
        ]
        default_schedule = json.dumps([{"start": 0, "end": 24, "active": True}], ensure_ascii=False)
        
        for name, role in npc_list:
            exists = conn.execute(text("SELECT id FROM npcs WHERE role=:r LIMIT 1"), {"r": role}).fetchone()
            if not exists:
                conn.execute(text("INSERT INTO npcs (name, role, schedule, coins) VALUES (:name, :role, :schedule, 5000)"), 
                             {"name": name, "role": role, "schedule": default_schedule})