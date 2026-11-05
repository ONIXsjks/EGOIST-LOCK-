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
    chat_id = message.chat.id
    user_id = message.from_user.id
    name = message.from_user.first_name
    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT display_name, coins, energy, health, job, job_level
            FROM players WHERE chat_id=:c AND user_id=:u
        """), {"c": chat_id, "u": user_id}).mappings().fetchone()
        if not r:
            conn.execute(text("INSERT INTO players (chat_id, user_id, display_name) VALUES (:c, :u, :n)"),
                         {"c": chat_id, "u": user_id, "n": name})
            r = conn.execute(text("""
                SELECT display_name, coins, energy, health, job, job_level
                FROM players WHERE chat_id=:c AND user_id=:u
            """), {"c": chat_id, "u": user_id}).mappings().fetchone()
    await message.answer(
        f"👤 {r['display_name']}\n💰 سکه: {r['coins']}\n⚡ انرژی: {r['energy']}\n"
        f"❤️ سلامتی: {r['health']}\n💼 شغل: {r['job'] or 'بیکار'} (سطح {r['job_level']})"
    )

# ---------- کار ----------
@router.message(Command("work"))
async def work(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    with engine.begin() as conn:
        p = conn.execute(text("""
            SELECT id, energy, job, job_level, employer_npc_id
            FROM players WHERE chat_id=:c AND user_id=:u
        """), {"c": chat_id, "u": user_id}).mappings().fetchone()
        if not p:
            await message.answer("اول /profile")
            return
        if not p["job"]:
            await message.answer("/jobs")
            return
        if p["energy"] < 20:
            await message.answer("/rest")
            return
        npc = conn.execute(text("SELECT id, schedule FROM npcs WHERE id=:i"),
                           {"i": p["employer_npc_id"]}).fetchone()
        if not npc or not is_active(npc[1]):
            await message.answer("کارفرما سر کار نیست.")
            return
        income = JOBS[p["job"]]["income"] + p["job_level"] * 2
        conn.execute(text("UPDATE players SET coins=coins+:i, energy=energy-15, job_level=job_level+1 WHERE id=:p"),
                     {"i": income, "p": p["id"]})
        conn.execute(text("UPDATE npcs SET coins=GREATEST(0, coins-:i) WHERE id=:n"),
                     {"i": income, "n": npc[0]})
        conn.execute(text("""
            INSERT INTO social_edges (from_id, to_id, trust, last_interaction) VALUES (:f, :t, 53, NOW())
            ON CONFLICT (from_id, to_id) DO UPDATE SET trust=LEAST(100, social_edges.trust+3)
        """), {"f": npc[0], "t": user_id})
    await message.answer(f"💼 +{income} سکه. انرژی -۱۵")

# ---------- استراحت ----------
@router.message(Command("rest"))
async def rest(message: Message):
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET energy=LEAST(100, energy+30) WHERE chat_id=:c AND user_id=:u"),
                     {"c": message.chat.id, "u": message.from_user.id})
    await message.answer("😴 انرژی +۳۰")

# ---------- لیست شغل ----------
@router.message(Command("jobs"))
async def jobs(message: Message):
    lines = ["💼 شغل‌ها:"]
    for name, info in JOBS.items():
        lines.append(f"• {name} — {info['income']} سکه (اعتماد ≥{info['min_trust']})")
    lines.append("\n/set_job نام شغل")
    await message.answer("\n".join(lines))

@router.message(Command("set_job"))
async def set_job(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("/set_job شاگرد نانوا")
        return
    job = args[1].strip()
    if job not in JOBS:
        await message.answer("شغل نامعتبر.")
        return
    chat_id, user_id = message.chat.id, message.from_user.id
    with engine.begin() as conn:
        p = conn.execute(text("SELECT id FROM players WHERE chat_id=:c AND user_id=:u"),
                         {"c": chat_id, "u": user_id}).fetchone()
        if not p:
            await message.answer("اول /profile")
            return
        npc = conn.execute(text("SELECT id, name FROM npcs WHERE role=:r"),
                           {"r": JOBS[job]["employer_role"]}).fetchone()
        if not npc:
            await message.answer("کارفرما نیست.")
            return
        rel = conn.execute(text("SELECT trust FROM social_edges WHERE from_id=:f AND to_id=:t"),
                           {"f": npc[0], "t": user_id}).fetchone()
        if (rel[0] if rel else 50) < JOBS[job]["min_trust"]:
            await message.answer(f"اعتماد {npc[1]} کافی نیست.")
            return
        conn.execute(text("UPDATE players SET job=:j, employer_npc_id=:e WHERE chat_id=:c AND user_id=:u"),
                     {"j": job, "e": npc[0], "c": chat_id, "u": user_id})
    await message.answer(f"✅ {job} (کارفرما: {npc[1]})")

# ---------- پاسخ NPC ----------
@router.message(F.text)
async def npc_reply(message: Message):
    text = message.text
    chat_id, user_id = message.chat.id, message.from_user.id
    with engine.begin() as conn:
        npcs = conn.execute(text("SELECT * FROM npcs WHERE chat_id=:c"), {"c": chat_id}).fetchall()
        target = None
        for npc in npcs:
            if npc[2] in text or npc[3] in text:
                target = npc
                break
        if not target:
            return
        if not is_active(target[4]):
            await message.answer(f"🍞 {target[2]}: {random.choice(BAKER_TEMPLATES['closed'])}")
            return
        rel = conn.execute(text("SELECT trust, grudge FROM social_edges WHERE from_id=:f AND to_id=:t"),
                           {"f": target[0], "t": user_id}).fetchone()
        trust, grudge = (rel[0] if rel else 50), (rel[1] if rel else 0)
        tl = text.lower()
        if any(w in tl for w in ["سلام", "صبح"]):
            tpl = "greet_high" if trust > 60 else "greet_low"
            await message.answer(f"🍞 {target[2]}: {random.choice(BAKER_TEMPLATES[tpl]).format(name=message.from_user.first_name)}")
        elif any(w in tl for w in ["بده", "بخر", "نان"]):
            if trust < 30:
                await message.answer(f"🍞 {target[2]}: {random.choice(BAKER_TEMPLATES['buy_no_trust'])}")
            elif grudge > 50:
                await message.answer(f"🍞 {target[2]}: قیمت برای تو دو برابر است.")
            else:
                await message.answer(f"🍞 {target[2]}: {random.choice(BAKER_TEMPLATES['buy_ok']).format(price=10)}")
                conn.execute(text("UPDATE social_edges SET trust=LEAST(100, trust+2) WHERE from_id=:f AND to_id=:t"),
                             {"f": target[0], "t": user_id})
        elif any(w in tl for w in ["احمق", "بد"]):
            conn.execute(text("UPDATE social_edges SET grudge=LEAST(100, grudge+20), trust=GREATEST(0, trust-10) WHERE from_id=:f AND to_id=:t"),
                         {"f": target[0], "t": user_id})
            await message.answer(f"🍞 {target[2]}: {random.choice(BAKER_TEMPLATES['insult'])}")

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