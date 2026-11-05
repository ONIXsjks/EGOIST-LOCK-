import json, random
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from db import engine
from config import JOBS, BAKER_TEMPLATES, ADMIN_IDS
from sqlalchemy import text

router = Router()

def is_active(schedule_json):
    schedule = json.loads(schedule_json)
    hour = datetime.now().hour
    for slot in schedule:
        s, e = slot["start"], slot["end"]
        if s <= e and s <= hour < e: return slot["active"]
        if s > e and (hour >= s or hour < e): return slot["active"]
    return False

# ---------- پروفایل ----------
@router.message(Command("profile"))
async def profile(message: Message):
    try:
        chat_id, user_id = message.chat.id, message.from_user.id
        name = message.from_user.first_name
        with engine.begin() as conn:
            r = conn.execute(text("SELECT display_name, coins, energy, health, job, job_level, has_sword, has_armor FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
            if not r:
                conn.execute(text("INSERT INTO players (chat_id, user_id, display_name) VALUES (:c, :u, :n)"), {"c": chat_id, "u": user_id, "n": name})
                r = conn.execute(text("SELECT display_name, coins, energy, health, job, job_level, has_sword, has_armor FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
        
        sword = "🗡️ دارد" if r['has_sword'] else "❌ ندارد"
        armor = "🛡️ دارد" if r['has_armor'] else "❌ ندارد"
        await message.answer(f"👤 {r['display_name']}\n💰 سکه: {r['coins']}\n⚡ انرژی: {r['energy']}\n❤️ سلامتی: {r['health']}\n💼 شغل: {r['job'] or 'بیکار'} (سطح {r['job_level']})\n\n🗡️ شمشیر: {sword}\n🛡️ زره: {armor}")
    except Exception as e:
        await message.answer(f"⚠️ خطای دیتابیس:\n{str(e)}")

# ---------- کار ----------
@router.message(Command("work"))
async def work(message: Message):
    chat_id, user_id = message.chat.id, message.from_user.id
    try:
        with engine.begin() as conn:
            p = conn.execute(text("SELECT id, energy, health, job, job_level, employer_npc_id FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
            if not p: return await message.answer("اول /profile")
            if not p["job"]: return await message.answer("/jobs")
            if p["energy"] < 20: return await message.answer("/rest")
            if p["health"] < 20: return await message.answer("سلامتی‌ت پایینه! برو دکتر.")
            
            npc = conn.execute(text("SELECT id, schedule FROM npcs WHERE id=:i"), {"i": p["employer_npc_id"]}).fetchone()
            if not npc or not is_active(npc[1]): return await message.answer("کارفرما سر کار نیست.")
            
            income = JOBS[p["job"]]["income"] + p["job_level"] * 2
            conn.execute(text("UPDATE players SET coins=coins+:i, energy=energy-15, job_level=job_level+1 WHERE id=:p"), {"i": income, "p": p["id"]})
            conn.execute(text("UPDATE npcs SET coins=GREATEST(0, coins-:i) WHERE id=:n"), {"i": income, "n": npc[0]})
        await message.answer(f"💼 +{income} سکه. انرژی -۱۵")
    except Exception as e:
        await message.answer(f"⚠️ خطای کار:\n{str(e)}")

# ---------- استراحت ----------
@router.message(Command("rest"))
async def rest(message: Message):
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE players SET energy=LEAST(100, energy+30) WHERE chat_id=:c AND user_id=:u"), {"c": message.chat.id, "u": message.from_user.id})
        await message.answer("😴 انرژی +۳۰")
    except Exception as e:
        await message.answer(f"⚠️ خطای استراحت:\n{str(e)}")

# ---------- شغل‌ها ----------
@router.message(Command("jobs"))
async def jobs(message: Message):
    lines = ["💼 شغل‌ها:"]
    for name, info in JOBS.items(): lines.append(f"• {name} — {info['income']} سکه (اعتماد ≥{info['min_trust']})")
    lines.append("\n/set_job نام شغل")
    await message.answer("\n".join(lines))

@router.message(Command("set_job"))
async def set_job(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.answer("/set_job شاگرد نانوا")
    job = args[1].strip()
    if job not in JOBS: return await message.answer("شغل نامعتبر.")
    chat_id, user_id = message.chat.id, message.from_user.id
    try:
        with engine.begin() as conn:
            p = conn.execute(text("SELECT id FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).fetchone()
            if not p: return await message.answer("اول /profile")
            npc = conn.execute(text("SELECT id, name FROM npcs WHERE role=:r"), {"r": JOBS[job]["employer_role"]}).fetchone()
            if not npc: return await message.answer("کارفرما نیست.")
            rel = conn.execute(text("SELECT trust FROM social_edges WHERE from_id=:f AND to_id=:t"), {"f": npc[0], "t": user_id}).fetchone()
            if (rel[0] if rel else 50) < JOBS[job]["min_trust"]: return await message.answer(f"اعتماد {npc[1]} کافی نیست.")
            conn.execute(text("UPDATE players SET job=:j, employer_npc_id=:e WHERE chat_id=:c AND user_id=:u"), {"j": job, "e": npc[0], "c": chat_id, "u": user_id})
        await message.answer(f"✅ {job} (کارفرما: {npc[1]})")
    except Exception as e:
        await message.answer(f"⚠️ خطای استخدام:\n{str(e)}")

# ---------- 🛒 فروشگاه ----------
@router.message(Command("shop"))
async def shop(message: Message):
    await message.answer("🛒 **فروشگاه شهر:**\n\n🗡️ شمشیر (افزایش قدرت حمله): 50 سکه\nبرای خرید: `/buy sword`\n\n🛡️ زره (کاهش آسیب در حمله): 50 سکه\nبرای خرید: `/buy armor`\n\n*برای خرید، پول کافی و جای خالی در کوله‌پشتی نیاز است.*")

@router.message(Command("buy"))
async def buy(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.answer("مثال: /buy sword")
    item = args[1].strip().lower()
    chat_id, user_id = message.chat.id, message.from_user.id
    
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins, has_sword, has_armor FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
        if not p: return await message.answer("اول /profile")
        
        if item == "sword":
            if p['has_sword']: return await message.answer("تو از قبل شمشیر داری!")
            if p['coins'] < 50: return await message.answer("سکه کافی نداری (نیاز: 50).")
            conn.execute(text("UPDATE players SET coins=coins-50, has_sword=1 WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id})
            await message.answer("✅ شمشیر خریدی! حالا در حمله قوی‌تری.")
            
        elif item == "armor":
            if p['has_armor']: return await message.answer("تو از قبل زره داری!")
            if p['coins'] < 50: return await message.answer("سکه کافی نداری (نیاز: 50).")
            conn.execute(text("UPDATE players SET coins=coins-50, has_armor=1 WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id})
            await message.answer("✅ زره خریدی! حالا در حمله آسیب کمتری می‌بینی.")
        else:
            await message.answer("چنین آیتمی وجود ندارد.")

# ---------- ⚔️ حمله به بازیکن ----------
@router.message(Command("attack"))
async def attack(message: Message):
    # پیدا کردن کسی که ریپلای شده
    if not message.reply_to_message:
        return await message.answer("روی پیام کسی ریپلای کن و بنویس /attack")
    
    attacker_id = message.from_user.id
    target_id = message.reply_to_message.from_user.id
    chat_id = message.chat.id
    
    if attacker_id == target_id:
        return await message.answer("خودزنی ممنوع!")
        
    with engine.begin() as conn:
        # چک کردن مهاجم
        att = conn.execute(text("SELECT health, energy, has_sword, display_name FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": attacker_id}).mappings().fetchone()
        if not att: return await message.answer("اول /profile")
        if att['energy'] < 10 or att['health'] < 10: return await message.answer("انرژی یا سلامتی کافی برای حمله نداری.")
        
        # چک کردن هدف
        tgt = conn.execute(text("SELECT health, has_armor, display_name FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": target_id}).mappings().fetchone()
        if not tgt: return await message.answer("هدف هنوز پروفایل نساخته.")
        
        # محاسبات حمله و دفاع
        attack_power = random.randint(10, 30) + (15 if att['has_sword'] else 0)
        defense_power = random.randint(5, 15) + (20 if tgt['has_armor'] else 0)
        
        damage = max(0, attack_power - defense_power)
        
        # اعمال آسیب
        new_health = max(0, tgt['health'] - damage)
        conn.execute(text("UPDATE players SET health=:h WHERE chat_id=:c AND user_id=:u"), {"h": new_health, "c": chat_id, "u": target_id})
        conn.execute(text("UPDATE players SET energy=energy-10 WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": attacker_id})
        
    if damage == 0:
        msg = f"🛡️ {att['display_name']} به {tgt['display_name']} حمله کرد، اما زره هدف جلوی آسیب را گرفت!"
    else:
        msg = f"⚔️ {att['display_name']} به {tgt['display_name']} حمله کرد و {damage} آسیب زد!\n❤️ سلامتی {tgt['display_name']}: {new_health}"
        if new_health <= 0:
            msg += "\n☠️ هدف بیهوش شد! باید بره بیمارستان."
            
    await message.answer(msg)

# ---------- 💎 گنج‌یابی تصادفی ----------
@router.message(Command("dig"))
async def dig(message: Message):
    # 30 درصد شانس پیدا کردن گنج
    if random.random() > 0.3:
        return await message.answer("⛏️ زمین را کندی، اما چیزی پیدا نکردی. شانست رو دوباره امتحان کن.")
        
    reward_type = random.choice(["coins", "energy", "health"])
    amount = random.randint(20, 50)
    chat_id, user_id = message.chat.id, message.from_user.id
    
    with engine.begin() as conn:
        p = conn.execute(text("SELECT id FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).fetchone()
        if not p: return await message.answer("اول /profile")
        
        if reward_type == "coins":
            conn.execute(text("UPDATE players SET coins=coins+:a WHERE chat_id=:c AND user_id=:u"), {"a": amount, "c": chat_id, "u": user_id})
            await message.answer(f"💎 **تبریک!** یک صندوقچه قدیمی پیدا کردی و {amount} سکه به دست آوردی!")
        elif reward_type == "energy":
            conn.execute(text("UPDATE players SET energy=LEAST(100, energy+:a) WHERE chat_id=:c AND user_id=:u"), {"a": amount, "c": chat_id, "u": user_id})
            await message.answer(f"💎 **تبریک!** یک معجون انرژی پیدا کردی و {amount} انرژی گرفتی!")
        elif reward_type == "health":
            conn.execute(text("UPDATE players SET health=LEAST(100, health+:a) WHERE chat_id=:c AND user_id=:u"), {"a": amount, "c": chat_id, "u": user_id})
            await message.answer(f"💎 **تبریک!** یک گیاه دارویی پیدا کردی و {amount} سلامتی گرفتی!")

# ---------- پاسخ NPC ----------
@router.message(F.text)
async def npc_reply(message: Message):
    text = message.text
    chat_id, user_id = message.chat.id, message.from_user.id
    try:
        with engine.begin() as conn:
            npcs = conn.execute(text("SELECT * FROM npcs WHERE chat_id=:c"), {"c": chat_id}).fetchall()
            target = next((npc for npc in npcs if npc[2] in text or npc[3] in text), None)
            if not target: return 
            if not is_active(target[4]): 
                return await message.answer(f"🍞 {target[2]}: {random.choice(BAKER_TEMPLATES['closed'])}")
            
            rel = conn.execute(text("SELECT trust, grudge FROM social_edges WHERE from_id=:f AND to_id=:t"), {"f": target[0], "t": user_id}).fetchone()
            trust, grudge = (rel[0] if rel else 50), (rel[1] if rel else 0)
            tl = text.lower()
            
            if any(w in tl for w in ["سلام", "صبح"]):
                tpl = "greet_high" if trust > 60 else "greet_low"
                answer = random.choice(BAKER_TEMPLATES[tpl]).format(name=message.from_user.first_name)
                await message.answer(f"🍞 {target[2]}: {answer}")
            elif any(w in tl for w in ["بده", "بخر", "نان"]):
                if trust < 30: await message.answer(f"🍞 {target[2]}: {random.choice(BAKER_TEMPLATES['buy_no_trust'])}")
                elif grudge > 50: await message.answer(f"🍞 {target[2]}: قیمت برای تو دو برابر است.")
                else:
                    await message.answer(f"🍞 {target[2]}: {random.choice(BAKER_TEMPLATES['buy_ok']).format(price=10)}")
                    conn.execute(text("UPDATE social_edges SET trust=LEAST(100, trust+2) WHERE from_id=:f AND to_id=:t"), {"f": target[0], "t": user_id})
            elif any(w in tl for w in ["احمق", "بد"]):
                conn.execute(text("UPDATE social_edges SET grudge=LEAST(100, grudge+20), trust=GREATEST(0, trust-10) WHERE from_id=:f AND to_id=:t"), {"f": target[0], "t": user_id})
                await message.answer(f"🍞 {target[2]}: {random.choice(BAKER_TEMPLATES['insult'])}")
    except Exception as e:
        await message.answer(f"⚠️ خطای NPC:\n{str(e)}")

# ---------- ادمین ----------
def is_admin(uid): return uid in ADMIN_IDS

@router.message(Command("admin_stats"))
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id): return
    with engine.begin() as conn:
        p = conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
        n = conn.execute(text("SELECT COUNT(*) FROM npcs")).scalar()
    await message.answer(f"📊 بازیکن‌ها: {p}\n🤖 NPCها: {n}")