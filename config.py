import os

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DATABASE_URL = "postgresql://postgres.hjynfqrsyxjibchmghsg:PH6t8bseGQrPp9el@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
ADMIN_IDS = [7023690411]
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

JOBS = {
    "شاگرد نانوا": {"income": 5, "employer_role": "نانوا", "min_trust": 40},
    "نگهبان شب": {"income": 8, "employer_role": "نگهبان", "min_trust": 50},
}

BAKER_SCHEDULE = [
    {"start": 6, "end": 10, "active": True},
    {"start": 10, "end": 12, "active": True},
    {"start": 12, "end": 14, "active": False},
    {"start": 14, "end": 18, "active": True},
    {"start": 18, "end": 6, "active": False},
]

BAKER_TEMPLATES = {
    "greet_high": ["سلام {name}، خوش آمدی! نان تازه دارم.", "سلام! امروز چه خبر؟"],
    "greet_low": ["سلام... چی می‌خواهی؟", "بله؟"],
    "buy_ok": ["بفرما، {price} سکه.", "نان تازه است، {price} سکه."],
    "buy_no_trust": ["به تو جنس نمی‌فروشم.", "پولت را نگه دار."],
    "insult": ["این را یادم می‌ماند.", "دیگر این حرف را نزن."],
    "closed": ["الان وقتم نیست.", "خوابم می‌آید..."],
}