from sqlalchemy import create_engine, text
from config import DATABASE_URL, BAKER_SCHEDULE
import json

# رشته اتصال به Supabase
db_url = DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
if "postgresql://" in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
if "sslmode" not in db_url:
    db_url += "?sslmode=require" if "?" not in db_url else "&sslmode=require"

engine = create_engine(db_url, pool_pre_ping=True, pool_size=3, max_overflow=2)

def init_db():
    with engine.begin() as conn:
        # ۱. ساخت جدول بازیکن‌ها با تمام ستون‌های جدید
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY, 
            chat_id BIGINT, user_id BIGINT, display_name TEXT,
            coins INTEGER DEFAULT 100, bank_coins INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0,
            energy INTEGER DEFAULT 100, health INTEGER DEFAULT 100, 
            job TEXT, job_level INTEGER DEFAULT 0, employer_npc_id INTEGER, 
            has_sword INTEGER DEFAULT 0, has_armor INTEGER DEFAULT 0, has_dagger INTEGER DEFAULT 0,
            UNIQUE(chat_id, user_id)
        );"""))
        
        # ۲. ساخت جدول NPCها
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS npcs (
            id SERIAL PRIMARY KEY, chat_id BIGINT, name TEXT, role TEXT,
            schedule TEXT, coins INTEGER DEFAULT 500
        );"""))
        
        # ۳. ساخت جدول روابط (اعتماد و کینه)
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS social_edges (
            id SERIAL PRIMARY KEY, from_id BIGINT, to_id BIGINT,
            trust INTEGER DEFAULT 50, grudge INTEGER DEFAULT 0,
            last_interaction TIMESTAMP, UNIQUE(from_id, to_id)
        );"""))
        
        # ۴. ساخت NPC نانوا (اگر وجود نداشته باشد)
        exists = conn.execute(text("SELECT id FROM npcs WHERE role='نانوا' LIMIT 1")).fetchone()
        if not exists:
            conn.execute(text("INSERT INTO npcs (name, role, schedule, coins) VALUES (:name, :role, :schedule, 500)"), 
                         {"name": "نانوا", "role": "نانوا", "schedule": json.dumps(BAKER_SCHEDULE, ensure_ascii=False)})
        
        # ۵. ساخت NPC کلاهبردار (اگر وجود نداشته باشد)
        exists_thief = conn.execute(text("SELECT id FROM npcs WHERE role='کلاهبردار' LIMIT 1")).fetchone()
        if not exists_thief:
            conn.execute(text("INSERT INTO npcs (name, role, schedule, coins) VALUES (:name, :role, :schedule, 1000)"), 
                         {"name": "سایه", "role": "کلاهبردار", "schedule": json.dumps([{"start": 0, "end": 24, "active": True}], ensure_ascii=False)})