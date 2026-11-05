from sqlalchemy import create_engine, text
from config import DATABASE_URL, BAKER_SCHEDULE
import json

# رشته اتصال به Supabase
db_url = DATABASE_URL

# تبدیل postgres:// به postgresql:// (در صورت نیاز)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# 🔴 اجبار SQLAlchemy به استفاده از درایور psycopg2 (رفع خطای ModuleNotFoundError)
if "postgresql://" in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# اضافه کردن SSL برای Supabase
if "sslmode" not in db_url:
    db_url += "?sslmode=require" if "?" not in db_url else "&sslmode=require"

# ساخت موتور دیتابیس
engine = create_engine(
    db_url, 
    pool_pre_ping=True, 
    pool_size=3, 
    max_overflow=2
)

def init_db():
    """ساخت جدول‌ها در دیتابیس و اضافه کردن NPC اولیه"""
    with engine.begin() as conn:
        # جدول بازیکن‌ها
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY, 
            chat_id BIGINT, 
            user_id BIGINT, 
            display_name TEXT,
            coins INTEGER DEFAULT 100, 
            energy INTEGER DEFAULT 100,
            health INTEGER DEFAULT 100, 
            job TEXT, 
            job_level INTEGER DEFAULT 0,
            employer_npc_id INTEGER, 
            UNIQUE(chat_id, user_id)
        );"""))
        
        # جدول NPCها
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS npcs (
            id SERIAL PRIMARY KEY, 
            chat_id BIGINT, 
            name TEXT, 
            role TEXT,
            schedule TEXT, 
            coins INTEGER DEFAULT 500
        );"""))
        
        # جدول روابط (اعتماد و کینه)
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS social_edges (
            id SERIAL PRIMARY KEY, 
            from_id BIGINT, 
            to_id BIGINT,
            trust INTEGER DEFAULT 50, 
            grudge INTEGER DEFAULT 0,
            last_interaction TIMESTAMP, 
            UNIQUE(from_id, to_id)
        );"""))
        
        # چک کردن اینکه آیا نانوا وجود دارد یا نه
        exists = conn.execute(text("SELECT id FROM npcs WHERE role='نانوا' LIMIT 1")).fetchone()
        
        # اگر نانوا نبود، اضافه می‌شود
        if not exists:
            conn.execute(text("""
                INSERT INTO npcs (name, role, schedule, coins)
                VALUES (:name, :role, :schedule, 500)
            """), {
                "name": "نانوا", 
                "role": "نانوا",
                "schedule": json.dumps(BAKER_SCHEDULE, ensure_ascii=False)
            })