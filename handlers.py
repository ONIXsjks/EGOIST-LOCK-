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

def check_level_up(level, xp):
    # نیاز به XP برای لول آپ: لول * 50
    if xp >= (level * 50):
        return level + 1, 0 # لول جدید، XP ریست میشه
    return level, xp

# ---------- ❓ راهنما (Help) ----------
@router.message(Command("help"))
async def help_command(message: Message):
    help_text = (
        "📖 **راهنمای بازی (نسخه جدید)**\n\n"
        "👤 **پروفایل و کار:**\n"
        "`/profile` - دیدن پروفایل (لول، سکه، بانک)\n"
        "`/work` - کار کردن (XP و سکه می‌دهد)\n"
        "`/rest` - استراحت\n\n"
        "🏦 **بانک و دزدی:**\n"
        "`/bank deposit [مبلغ]` - واریز به بانک\n"
        "`/bank withdraw [مبلغ]` - برداشت از بانک\n"
        "`/steal` - دزدی (روی پیام طرف ریپلای کن)\n\n"
        "🛒 **فروشگاه‌ها:**\n"
        "`/shop` - فروشگاه معمولی (شمشیر و زره)\n"
        "`/blackmarket` - بازار سیاه (خرید چاقوی دزدی)\n"
        "`/buy sword` / `/buy armor` / `/buy dagger`\n\n"
        "⚔️ **ماجراجویی:**\n"
        "`/attack` - حمله (روی پیام طرف ریپلای کن)\n"
        "`/dig` - گنج‌یابی"
    )
    await message.answer(help_text)

# ---------- پروفایل ----------
@router.message(Command("profile"))
async def profile(message: Message):
    try:
        chat_id, user_id = message.chat.id, message.from_user.id
        name = message.from_user.first_name
        with engine.begin() as conn:
            r = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
            if not r:
                conn.execute(text("INSERT INTO players (chat_id, user_id, display_name) VALUES (:c, :u, :n)"), {"c": chat_id, "u": user_id, "n": name})
                r = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
        
        await message.answer(
            f"👤 **{r['display_name']}** (لول {r['level']})\n"
            f"✨ XP: {r['xp']}/{r['level']*50}\n"
            f"💰 سکه (جیب): {r['coins']}\n"
            f"🏦 سکه (بانک): {r['bank_coins']}\n"
            f"⚡ انرژی: {r['energy']}\n"
            f"❤️ سلامتی: {r['health']}\n"
            f"💼 شغل: {r['job'] or 'بیکار'}\n\n"
            f"🗡️ شمشیر: {'✅' if r['has_sword'] else '❌'} | 🛡️ زره: {'✅' if r['has_armor'] else '❌'} | 🔪 چاقو: {'✅' if r['has_dagger'] else '❌'}"
        )
    except Exception as e:
        await message.answer(f"⚠️ خطا:\n{str(e)}")

# ---------- کار ----------
@router.message(Command("work"))
async def work(message: Message):
    chat_id, user_id = message.chat.id, message.from_user.id
    try:
        with engine.begin() as conn:
            p = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
            if not p: return await message.answer("اول /profile")
            if not p["job"]: return await message.answer("/jobs")
            if p["energy"] < 20: return await message.answer("/rest")
            
            npc = conn.execute(text("SELECT id, schedule FROM npcs WHERE id=:i"), {"i": p["employer_npc_id"]}).fetchone()
            if not npc or not is_active(npc[1]): return await message.answer("کارفرما سر کار نیست.")
            
            income = JOBS[p["job"]]["income"] + p["job_level"] * 2
            xp_gain = 15 + (p["level"] * 2)
            
            new_level, new_xp = check_level_up(p["level"], p["xp"] + xp_gain)
            level_msg = f"\n🎉 **تبریک! لولت شد {new_level}**" if new_level > p["level"] else ""

            conn.execute(text("UPDATE players SET coins=coins+:i, energy=energy-15, xp=:xp, level=:lvl, job_level=job_level+1 WHERE id=:p"), 
                         {"i": income, "xp": new_xp, "lvl": new_level, "p": p["id"]})
        await message.answer(f"💼 +{income} سکه | +{xp_gain} XP | -۱۵ انرژی{level_msg}")
    except Exception as e:
        await message.answer(f"⚠️ خطا:\n{str(e)}")

# ---------- استراحت ----------
@router.message(Command("rest"))
async def rest(message: Message):
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET energy=LEAST(100, energy+30) WHERE chat_id=:c AND user_id=:u"), {"c": message.chat.id, "u": message.from_user.id})
    await message.answer("😴 انرژی +۳۰")

# ---------- 🏦 بانک ----------
@router.message(Command("bank"))
async def bank(message: Message):
    args = message.text.split()
    if len(args) < 3 or args[1] not in ["deposit", "withdraw"]:
        return await message.answer("استفاده: `/bank deposit 50` یا `/bank withdraw 50`")
    
    try:
        action, amount = args[1], int(args[2])
    except:
        return await message.answer("عدد نامعتبر است.")

    chat_id, user_id = message.chat.id, message.from_user.id
    
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins, bank_coins FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
        if not p: return await message.answer("اول /profile")
        
        if action == "deposit":
            if p['coins'] < amount: return await message.answer("سکه کافی در جیب نداری.")
            conn.execute(text("UPDATE players SET coins=coins-:a, bank_coins=bank_coins+:a WHERE chat_id=:c AND user_id=:u"), {"a": amount, "c": chat_id, "u": user_id})
            await message.answer(f"🏦 {amount} سکه به بانک واریز شد. (پولت از دزدی در امان است!)")
        else:
            if p['bank_coins'] < amount: return await message.answer("سکه کافی در بانک نداری.")
            conn.execute(text("UPDATE players SET coins=coins+:a, bank_coins=bank_coins-:a WHERE chat_id=:c AND user_id=:u"), {"a": amount, "c": chat_id, "u": user_id})
            await message.answer(f"🏦 {amount} سکه از بانک برداشت شد.")

# ---------- 🥷 دزدی ----------
@router.message(Command("steal"))
async def steal(message: Message):
    if not message.reply_to_message: return await message.answer("روی پیام کسی ریپلای کن.")
    thief_id, target_id, chat_id = message.from_user.id, message.reply_to_message.from_user.id, message.chat.id
    if thief_id == target_id: return await message.answer("خودزنی؟!")
    
    with engine.begin() as conn:
        t = conn.execute(text("SELECT coins, bank_coins, has_dagger, level, display_name FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": thief_id}).mappings().fetchone()
        v = conn.execute(text("SELECT coins, display_name, level FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": target_id}).mappings().fetchone()
        
        if not t or not v: return await message.answer("هر دو باید پروفایل داشته باشید.")
        
        # شانس موفقیت: 40% + 20% اگه چاقو داشته باشه + لول بالاتر
        success_chance = 0.4 + (0.2 if t['has_dagger'] else 0) + (0.1 if t['level'] > v['level'] else 0)
        
        if random.random() < success_chance and v['coins'] > 0:
            # دزدی موفق
            stolen = int(v['coins'] * random.uniform(0.1, 0.3)) # 10% تا 30% پول جیبی
            conn.execute(text("UPDATE players SET coins=coins-:s WHERE chat_id=:c AND user_id=:u"), {"s": stolen, "c": chat_id, "u": target_id})
            conn.execute(text("UPDATE players SET coins=coins+:s WHERE chat_id=:c AND user_id=:u"), {"s": stolen, "c": chat_id, "u": thief_id})
            await message.answer(f"🥷 **دزدی موفق!** {t['display_name']} مبلغ {stolen} سکه از {v['display_name']} دزدید!")
        else:
            # دزدی ناموفق (جریمه)
            penalty = int(t['coins'] * 0.2)
            conn.execute(text("UPDATE players SET coins=GREATEST(0, coins-:p) WHERE chat_id=:c AND user_id=:u"), {"p": penalty, "c": chat_id, "u": thief_id})
            await message.answer(f"🚨 **دزدی ناموفق!** {v['display_name']} متوجه شد و نگهبانان {t['display_name']} را دستگیر کردند. جریمه: {penalty} سکه.")

# ---------- 🛒 فروشگاه‌ها ----------
@router.message(Command("shop"))
async def shop(message: Message):
    await message.answer("🛒 **فروشگاه شهر:**\n🗡️ شمشیر (قدرت حمله): 50 سکه (`/buy sword`)\n🛡️ زره (دفاع): 50 سکه (`/buy armor`)")

@router.message(Command("blackmarket"))
async def blackmarket(message: Message):
    await message.answer("🕶️ **بازار سیاه (سایه):**\n🔪 چاقو (افزایش شانس دزدی): 150 سکه\nبرای خرید: `/buy dagger`\n\n*به کسی نگو اینجا رو بهت نشون دادم...*")

@router.message(Command("buy"))
async def buy(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.answer("مثال: /buy sword")
    item = args[1].strip().lower()
    chat_id, user_id = message.chat.id, message.from_user.id
    
    with engine.begin() as conn:
        p = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
        if not p: return await message.answer("اول /profile")
        
        if item == "sword" and not p['has_sword'] and p['coins'] >= 50:
            conn.execute(text("UPDATE players SET coins=coins-50, has_sword=1 WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}); await message.answer("✅ شمشیر خریدی.")
        elif item == "armor" and not p['has_armor'] and p['coins'] >= 50:
            conn.execute(text("UPDATE players SET coins=coins-50, has_armor=1 WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}); await message.answer("✅ زره خریدی.")
        elif item == "dagger" and not p['has_dagger'] and p['coins'] >= 150:
            conn.execute(text("UPDATE players SET coins=coins-150, has_dagger=1 WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}); await message.answer("✅ چاقو خریدی. حالا دزدی راحت‌تره.")
        else:
            await message.answer("یا پول کافی نداری، یا آیتم نامعتبره، یا از قبل اون رو داری.")

# ---------- ⚔️ حمله ----------
@router.message(Command("attack"))
async def attack(message: Message):
    if not message.reply_to_message: return await message.answer("روی پیام کسی ریپلای کن.")
    a_id, t_id, c_id = message.from_user.id, message.reply_to_message.from_user.id, message.chat.id
    if a_id == t_id: return await message.answer("خودزنی ممنوع!")
    
    with engine.begin() as conn:
        att = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": c_id, "u": a_id}).mappings().fetchone()
        tgt = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": c_id, "u": t_id}).mappings().fetchone()
        if not att or not tgt: return await message.answer("هر دو باید پروفایل داشته باشید.")
        if att['energy'] < 10: return await message.answer("انرژی نداری.")
        
        # لول مهاجم روی قدرت حمله اثر داره
        a_power = random.randint(10, 30) + (15 if att['has_sword'] else 0) + (att['level'] * 2)
        d_power = random.randint(5, 15) + (20 if tgt['has_armor'] else 0) + (tgt['level'] * 2)
        dmg = max(0, a_power - d_power)
        
        new_hp = max(0, tgt['health'] - dmg)
        conn.execute(text("UPDATE players SET health=:h WHERE chat_id=:c AND user_id=:u"), {"h": new_hp, "c": c_id, "u": t_id})
        conn.execute(text("UPDATE players SET energy=energy-10 WHERE chat_id=:c AND user_id=:u"), {"c": c_id, "u": a_id})
        
    if dmg == 0: await message.answer(f"🛡️ حمله {att['display_name']} به {tgt['display_name']} دفع شد!")
    else: await message.answer(f"⚔️ {att['display_name']} به {tgt['display_name']} {dmg} آسیب زد! (سلامتی: {new_hp})")

# ---------- 💎 گنج‌یابی ----------
@router.message(Command("dig"))
async def dig(message: Message):
    if random.random() > 0.3: return await message.answer("⛏️ چیزی پیدا نکردی.")
    r_type, amt = random.choice(["coins", "energy", "health"]), random.randint(20, 50)
    c_id, u_id = message.chat.id, message.from_user.id
    
    with engine.begin() as conn:
        if r_type == "coins":
            conn.execute(text("UPDATE players SET coins=coins+:a WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": c_id, "u": u_id}); await message.answer(f"💎 {amt} سکه پیدا کردی!")
        elif r_type == "energy":
            conn.execute(text("UPDATE players SET energy=LEAST(100, energy+:a) WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": c_id, "u": u_id}); await message.answer(f"💎 {amt} انرژی پیدا کردی!")
        else:
            conn.execute(text("UPDATE players SET health=LEAST(100, health+:a) WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": c_id, "u": u_id}); await message.answer(f"💎 {amt} سلامتی پیدا کردی!")

# ---------- پاسخ NPC ----------
@router.message(F.text)
async def npc_reply(message: Message):
    text, c_id, u_id = message.text, message.chat.id, message.from_user.id
    with engine.begin() as conn:
        npcs = conn.execute(text("SELECT * FROM npcs WHERE chat_id=:c"), {"c": c_id}).fetchall()
        target = next((npc for npc in npcs if npc[2] in text or npc[3] in text), None)
        if not target or not is_active(target[4]): return 
        
        rel = conn.execute(text("SELECT trust, grudge FROM social_edges WHERE from_id=:f AND to_id=:t"), {"f": target[0], "t": u_id}).fetchone()
        trust = rel[0] if rel else 50
        tl = text.lower()
        if any(w in tl for w in ["سلام", "صبح"]):
            await message.answer(f"🍞 {target[2]}: {'سلام! خوش آمدی.' if trust > 60 else 'بله؟'}")
        elif any(w in tl for w in ["بده", "نان"]):
            await message.answer(f"🍞 {target[2]}: نان ۱۰ سکه." if trust >= 30 else f"🍞 {target[2]}: به تو نمی‌فروشم.")

# ---------- ادمین ----------
def is_admin(uid): return uid in ADMIN_IDS

@router.message(Command("admin_stats"))
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id): return
    with engine.begin() as conn:
        p = conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
        n = conn.execute(text("SELECT COUNT(*) FROM npcs")).scalar()
    await message.answer(f"📊 بازیکن‌ها: {p}\n🤖 NPCها: {n}")

@router.message(Command("setcoins"))
async def admin_set_coins(message: Message):
    if not is_admin(message.from_user.id): return
    args = message.text.split()
    if len(args) < 3: return
    try: uid, amt = int(args[1]), int(args[2])
    except: return
    with engine.begin() as conn:
        res = conn.execute(text("UPDATE players SET coins=:a WHERE user_id=:u"), {"a": amt, "u": uid})
    await message.answer(f"✅ {uid} = {amt}" if res.rowcount else f"❌ {uid} پیدا نشد.")

@router.message(Command("broadcast"))
async def admin_broadcast(message: Message):
    if not is_admin(message.from_user.id): return
    msg = message.text.replace("/broadcast", "").strip()
    if not msg: return
    with engine.begin() as conn:
        chats = conn.execute(text("SELECT DISTINCT chat_id FROM players")).fetchall()
    for (cid,) in chats:
        try: await message.bot.send_message(cid, f"📢 {msg}")
        except: pass
    await message.answer("ارسال شد.")

# ---------- 🆙 دستور ادمین برای افزایش لول ----------
@router.message(Command("addlevel"))
async def admin_add_level(message: Message):
    if not is_admin(message.from_user.id): return
    args = message.text.split()
    if len(args) < 3: 
        return await message.answer("استفاده: `/addlevel [آیدی کاربر] [تعداد لول]`")
    
    try: 
        uid, lvl_amount = int(args[1]), int(args[2])
    except: 
        return await message.answer("عدد نامعتبر است.")
        
    try:
        with engine.begin() as conn:
            res = conn.execute(text("UPDATE players SET level=level+:l WHERE user_id=:u"), {"l": lvl_amount, "u": uid})
        if res.rowcount:
            await message.answer(f"✅ لول کاربر {uid} به اندازه {lvl_amount} افزایش یافت.")
        else:
            await message.answer(f"❌ کاربر {uid} پیدا نشد.")
    except Exception as e:
        await message.answer(f"⚠️ خطای لول:\n{str(e)}")