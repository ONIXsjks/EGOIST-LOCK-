import os

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DATABASE_URL = "postgresql://postgres.hjynfqrsyxjibchmghsg:PH6t8bseGQrPp9el@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
ADMIN_IDS = [7023690411]

# شغل‌های جدید با ساعت کاری متفاوت
JOBS = {
    "شاگرد نانوا": {"income": 5, "employer_role": "نانوا"},
    "نگهبان شب": {"income": 8, "employer_role": "نگهبان"},
    "کشاورز": {"income": 6, "employer_role": "کشاورز"},
    "معدن‌کار": {"income": 10, "employer_role": "معدن‌کار"},
    "شکارچی": {"income": 12, "employer_role": "شکارچی"},
    "دکتر": {"income": 15, "employer_role": "دکتر"},
    "معلم": {"income": 7, "employer_role": "معلم"},
    "پلیس": {"income": 9, "employer_role": "پلیس"},
}

# همیشه بیدار برای تست
BAKER_SCHEDULE = [{"start": 0, "end": 24, "active": True}]

BAKER_TEMPLATES = {
    "greet_high": ["سلام {name}، خوش آمدی! نان تازه دارم.", "سلام! امروز چه خبر؟"],
    "greet_low": ["سلام... چی می‌خواهی؟", "بله؟"],
    "buy_ok": ["بفرما، {price} دونه.", "نان تازه است، {price} دونه."],
    "buy_no_trust": ["به تو جنس نمی‌فروشم.", "پولت را نگه دار."],
    "buy_no_stock": ["تمام شد، فردا بیا."],
    "insult": ["این را یادم می‌ماند.", "دیگر این حرف را نزن."],
    "closed": ["الان وقتم نیست.", "خوابم می‌آید..."],
    "tired": ["خیلی خسته‌ام.", "حوصله ندارم."],
    "unknown": ["متوجه نشدم.", "چه می‌گویی؟"],
}