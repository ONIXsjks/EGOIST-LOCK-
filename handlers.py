import json, random
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
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
    if xp >= (level * 50):
        return level + 1, 0 
    return level, xp

def get_main_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 پروفایل", callback_data=f"prof_{user_id}"), InlineKeyboardButton(text="💼 شغل‌ها", callback_data=f"jobs_{user_id}")],
        [InlineKeyboardButton(text="🛒 فروشگاه", callback_data=f"shop_{user_id}"), InlineKeyboardButton(text="🕶️ بازار سیاه", callback_data=f"bm_{user_id}")],
        [InlineKeyboardButton(text="🏦 بانک", callback_data=f"bank_{user_id}"), InlineKeyboardButton(text="💎 گنج‌یابی", callback_data=f"dig_{user_id}")],
        [InlineKeyboardButton(text="📖 راهنما", callback_data=f"help_{user_id}")]
    ])
    return keyboard

# ---------- منوی اصلی ----------
@router.message(Command("start"))
async def start_menu(message: Message):
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎮 منوی بازی")]],
        resize_keyboard=True,
        input_field_placeholder="برای بازی دکمه پایین را بزنید..."
    )
    await message.answer("سلام! به شهر خوش آمدی. برای باز کردن منوی بازی، دکمه «🎮 منوی بازی» رو بزن:", reply_markup=reply_keyboard)

@router.message(F.text == "🎮 منوی بازی")
async def open_main_menu(message: Message):
    await message.answer("منوی اصلی:", reply_markup=get_main_keyboard(message.from_user.id))

# ---------- منوی راهنما ----------
@router.message(F.text.lower() == "جوجو راهنما")
async def text_help(message: Message):
    await send_help_message(message, message.from_user.id)

async def send_help_message(call_or_msg, user_id):
    help_text = (
        "📖 **راهنمای کامل شهر جوجو**\n\n"
        "شما می‌توانید از دکمه‌های شیشه‌ای استفاده کنید یا دستورات زیر را تایپ کنید:\n\n"
        "👤 **`جوجو پروفایل`**\nمشاهده سکه‌ها، لول، انرژی و آیتم‌ها.\n\n"
        "💼 **`جوجو شغل`**\nاستخدام شدن (نانوا یا نگهبان).\n\n"
        "🔨 **`جوجو کار`**\nکار کردن برای کارفرما و گرفتن سکه و XP.\n\n"
        "😴 **`جوجو استراحت`**\nپر کردن انرژی.\n\n"
        "🏦 **`جوجو بانک`**\nواریز و برداشت سکه (پولت رو از دزدها دور نگه دار!).\n\n"
        "🛒 **`جوجو فروشگاه`**\nخرید شمشیر و زره.\n\n"
        "🕶️ **`جوجو بازار سیاه`**\nخرید چاقوی دزدی.\n\n"
        "⚔️ **`جوجو حمله`** (روی پیام کسی ریپلای کن)\nحمله به بازیکن‌های دیگه و کم کردن سلامتی‌شون.\n\n"
        "🥷 **`جوجو دزدی`** (روی پیام کسی ریپلای کن)\nدزدیدن پول جیبی بازیکن‌های دیگه.\n\n"
        "💎 **`جوجو گنج`**\nکندن زمین برای پیدا کردن سکه یا انرژی.\n\n"
        "💬 **تعامل با NPCها**\nتوی گروه بنویس: «سلام نانوا» یا «نانوا نان بده»"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{user_id}")]])
    
    if isinstance(call_or_msg, Message):
        await call_or_msg.answer(help_text, reply_markup=keyboard)
    else:
        await call_or_msg.message.edit_text(help_text, reply_markup=keyboard)

# ---------- دستورات متنی با پیشوند "جوجو" ----------
@router.message(F.text.lower() == "جوجو پروفایل")
async def text_profile(message: Message):
    await cb_profile_logic(message, message.from_user.id)

@router.message(F.text.lower() == "جوجو بانک")
async def text_bank(message: Message):
    await cb_bank_logic(message, message.from_user.id)

@router.message(F.text.lower() == "جوجو شغل")
async def text_jobs(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="شاگرد نانوا", callback_data=f"setjob_شاگرد نانوا_{message.from_user.id}")],
        [InlineKeyboardButton(text="نگهبان شب", callback_data=f"setjob_نگهبان شب_{message.from_user.id}")],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{message.from_user.id}")]
    ])
    await message.answer("💼 **لیست شغل‌ها:**\nبرای استخدام یکی را انتخاب کن:", reply_markup=keyboard)

@router.message(F.text.lower() == "جوجو کار")
async def text_work(message: Message):
    chat_id, user_id = message.chat.id, message.from_user.id
    with engine.begin() as conn:
        p = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
        if not p: return await message.answer("اول /start رو بزن.")
        if not p["job"]: return await message.answer("شغلی نداری. اول از منوی شغل‌ها استخدام شو.")
        if p["energy"] < 20: return await message.answer("انرژی نداری. استراحت کن.")
        
        npc = conn.execute(text("SELECT id, schedule FROM npcs WHERE id=:i"), {"i": p["employer_npc_id"]}).fetchone()
        if not npc or not is_active(npc[1]): return await message.answer("کارفرما سر کار نیست.")
        
        income = JOBS[p["job"]]["income"] + p["job_level"] * 2
        xp_gain = 15 + (p["level"] * 2)
        new_level, new_xp = check_level_up(p["level"], p["xp"] + xp_gain)
        
        conn.execute(text("UPDATE players SET coins=coins+:i, energy=energy-15, xp=:xp, level=:lvl, job_level=job_level+1 WHERE id=:p"), 
                     {"i": income, "xp": new_xp, "lvl": new_level, "p": p["id"]})
        
    await message.answer(f"💼 +{income} سکه و +{xp_gain} XP گرفتی. انرژی -۱۵")

@router.message(F.text.lower() == "جوجو استراحت")
async def text_rest(message: Message):
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET energy=LEAST(100, energy+30) WHERE chat_id=:c AND user_id=:u"), {"c": message.chat.id, "u": message.from_user.id})
    await message.answer("😴 انرژی +۳۰")

@router.message(F.text.lower() == "جوجو حمله")
async def text_attack(message: Message):
    if not message.reply_to_message: return await message.answer("روی پیام کسی ریپلای کن و بنویس «جوجو حمله»")
    a_id, t_id, c_id = message.from_user.id, message.reply_to_message.from_user.id, message.chat.id
    if a_id == t_id: return await message.answer("خودزنی ممنوع!")
    
    with engine.begin() as conn:
        att = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": c_id, "u": a_id}).mappings().fetchone()
        tgt = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": c_id, "u": t_id}).mappings().fetchone()
        if not att or not tgt: return await message.answer("هر دو باید پروفایل داشته باشید.")
        if att['energy'] < 10: return await message.answer("انرژی نداری.")
        
        a_power = random.randint(10, 30) + (15 if att['has_sword'] else 0) + (att['level'] * 2)
        d_power = random.randint(5, 15) + (20 if tgt['has_armor'] else 0) + (tgt['level'] * 2)
        dmg = max(0, a_power - d_power)
        
        new_hp = max(0, tgt['health'] - dmg)
        conn.execute(text("UPDATE players SET health=:h WHERE chat_id=:c AND user_id=:u"), {"h": new_hp, "c": c_id, "u": t_id})
        conn.execute(text("UPDATE players SET energy=energy-10 WHERE chat_id=:c AND user_id=:u"), {"c": c_id, "u": a_id})
        
    if dmg == 0: await message.answer(f"🛡️ حمله {att['display_name']} به {tgt['display_name']} دفع شد!")
    else: await message.answer(f"⚔️ {att['display_name']} به {tgt['display_name']} {dmg} آسیب زد! (سلامتی: {new_hp})")

@router.message(F.text.lower() == "جوجو دزدی")
async def text_steal(message: Message):
    if not message.reply_to_message: return await message.answer("روی پیام کسی ریپلای کن و بنویس «جوجو دزدی»")
    thief_id, target_id, chat_id = message.from_user.id, message.reply_to_message.from_user.id, message.chat.id
    if thief_id == target_id: return await message.answer("خودزنی؟!")
    
    with engine.begin() as conn:
        t = conn.execute(text("SELECT coins, has_dagger, level, display_name FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": thief_id}).mappings().fetchone()
        v = conn.execute(text("SELECT coins, display_name, level FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": target_id}).mappings().fetchone()
        
        if not t or not v: return await message.answer("هر دو باید پروفایل داشته باشید.")
        
        success_chance = 0.4 + (0.2 if t['has_dagger'] else 0) + (0.1 if t['level'] > v['level'] else 0)
        
        if random.random() < success_chance and v['coins'] > 0:
            stolen = int(v['coins'] * random.uniform(0.1, 0.3))
            conn.execute(text("UPDATE players SET coins=coins-:s WHERE chat_id=:c AND user_id=:u"), {"s": stolen, "c": chat_id, "u": target_id})
            conn.execute(text("UPDATE players SET coins=coins+:s WHERE chat_id=:c AND user_id=:u"), {"s": stolen, "c": chat_id, "u": thief_id})
            await message.answer(f"🥷 **دزدی موفق!** {t['display_name']} مبلغ {stolen} سکه از {v['display_name']} دزدید!")
        else:
            penalty = int(t['coins'] * 0.2)
            conn.execute(text("UPDATE players SET coins=GREATEST(0, coins-:p) WHERE chat_id=:c AND user_id=:u"), {"p": penalty, "c": chat_id, "u": thief_id})
            await message.answer(f"🚨 **دزدی ناموفق!** {v['display_name']} متوجه شد و جریمه {penalty} سکه دادی.")

@router.message(F.text.lower() == "جوجو گنج")
async def text_dig(message: Message):
    if random.random() > 0.3: return await message.answer("⛏️ زمین را کندی، اما چیزی پیدا نکردی.")
    r_type, amt = random.choice(["coins", "energy", "health"]), random.randint(20, 50)
    c_id, u_id = message.chat.id, message.from_user.id
    
    with engine.begin() as conn:
        if r_type == "coins":
            conn.execute(text("UPDATE players SET coins=coins+:a WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": c_id, "u": u_id})
            await message.answer(f"💎 تبریک! {amt} سکه پیدا کردی!")
        elif r_type == "energy":
            conn.execute(text("UPDATE players SET energy=LEAST(100, energy+:a) WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": c_id, "u": u_id})
            await message.answer(f"💎 تبریک! {amt} انرژی پیدا کردی!")
        else:
            conn.execute(text("UPDATE players SET health=LEAST(100, health+:a) WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": c_id, "u": u_id})
            await message.answer(f"💎 تبریک! {amt} سلامتی پیدا کردی!")

# ---------- هندل کردن دکمه‌ها (شیشه‌ای) ----------
async def cb_profile_logic(call_or_msg, user_id):
    with engine.begin() as conn:
        r = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": call_or_msg.message.chat.id if isinstance(call_or_msg, CallbackQuery) else call_or_msg.chat.id, "u": user_id}).mappings().fetchone()
        if not r:
            chat_id = call_or_msg.message.chat.id if isinstance(call_or_msg, CallbackQuery) else call_or_msg.chat.id
            name = call_or_msg.from_user.first_name
            conn.execute(text("INSERT INTO players (chat_id, user_id, display_name) VALUES (:c, :u, :n)"), {"c": chat_id, "u": user_id, "n": name})
            r = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
    
    text = (f"👤 **{r['display_name']}** (لول {r['level']})\n✨ XP: {r['xp']}/{r['level']*50}\n💰 سکه: {r['coins']} | 🏦 بانک: {r['bank_coins']}\n⚡ انرژی: {r['energy']} | ❤️ سلامتی: {r['health']}\n🗡️ شمشیر: {'✅' if r['has_sword'] else '❌'} | 🛡️ زره: {'✅' if r['has_armor'] else '❌'} | 🔪 چاقو: {'✅' if r['has_dagger'] else '❌'}")
    
    if isinstance(call_or_msg, Message):
        await call_or_msg.answer(text, reply_markup=get_main_keyboard(user_id))
    else:
        await call_or_msg.message.edit_text(text, reply_markup=get_main_keyboard(user_id))

async def cb_bank_logic(call_or_msg, user_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 واریز 50 سکه", callback_data=f"dep_{user_id}_50"), InlineKeyboardButton(text="📤 برداشت 50 سکه", callback_data=f"wd_{user_id}_50")],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{user_id}")]
    ])
    text = "🏦 **منوی بانک:**\nیکی از گزینه‌ها را انتخاب کن:"
    if isinstance(call_or_msg, Message):
        await call_or_msg.answer(text, reply_markup=keyboard)
    else:
        await call_or_msg.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("prof_"))
async def cb_profile(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
    await cb_profile_logic(call, user_id)

@router.callback_query(F.data.startswith("bank_"))
async def cb_bank(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
    await cb_bank_logic(call, user_id)

@router.callback_query(F.data.startswith("help_"))
async def cb_help(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
    await send_help_message(call, user_id)

@router.callback_query(F.data.startswith("dep_") | F.data.startswith("wd_"))
async def cb_transaction(call: CallbackQuery):
    data = call.data.split("_")
    action, user_id, amount = data[0], int(data[1]), int(data[2])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
        
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins, bank_coins FROM players WHERE chat_id=:c AND user_id=:u"), {"c": call.message.chat.id, "u": user_id}).mappings().fetchone()
        if action == "dep":
            if p['coins'] < amount: return await call.answer("❌ سکه کافی در جیب نداری.", show_alert=True)
            conn.execute(text("UPDATE players SET coins=coins-:a, bank_coins=bank_coins+:a WHERE chat_id=:c AND user_id=:u"), {"a": amount, "c": call.message.chat.id, "u": user_id})
            await call.answer(f"✅ {amount} سکه به بانک واریز شد.", show_alert=True)
        else:
            if p['bank_coins'] < amount: return await call.answer("❌ سکه کافی در بانک نداری.", show_alert=True)
            conn.execute(text("UPDATE players SET coins=coins+:a, bank_coins=bank_coins-:a WHERE chat_id=:c AND user_id=:u"), {"a": amount, "c": call.message.chat.id, "u": user_id})
            await call.answer(f"✅ {amount} سکه از بانک برداشت شد.", show_alert=True)
    await cb_bank_logic(call, user_id)

@router.callback_query(F.data.startswith("shop_"))
async def cb_shop(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗡️ خرید شمشیر (50)", callback_data=f"buy_sword_{user_id}"), InlineKeyboardButton(text="🛡️ خرید زره (50)", callback_data=f"buy_armor_{user_id}")],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{user_id}")]
    ])
    await call.message.edit_text("🛒 **فروشگاه شهر:**", reply_markup=keyboard)

@router.callback_query(F.data.startswith("bm_"))
async def cb_blackmarket(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔪 خرید چاقو (150)", callback_data=f"buy_dagger_{user_id}")],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{user_id}")]
    ])
    await call.message.edit_text("🕶️ **بازار سیاه (سایه):**\n*به کسی نگو اینجا رو بهت نشون دادم...*", reply_markup=keyboard)

@router.callback_query(F.data.startswith("buy_"))
async def cb_buy(call: CallbackQuery):
    data = call.data.split("_")
    item, user_id = data[1], int(data[2])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
        
    prices = {"sword": 50, "armor": 50, "dagger": 150}
    price = prices.get(item)
    
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins, has_sword, has_armor, has_dagger FROM players WHERE chat_id=:c AND user_id=:u"), {"c": call.message.chat.id, "u": user_id}).mappings().fetchone()
        if item == "sword" and p['has_sword']: return await call.answer("تو از قبل شمشیر داری!", show_alert=True)
        if item == "armor" and p['has_armor']: return await call.answer("تو از قبل زره داری!", show_alert=True)
        if item == "dagger" and p['has_dagger']: return await call.answer("تو از قبل چاقو داری!", show_alert=True)
        if p['coins'] < price: return await call.answer(f"❌ {price} سکه نیاز داری!", show_alert=True)
        conn.execute(text(f"UPDATE players SET coins=coins-:p, has_{item}=1 WHERE chat_id=:c AND user_id=:u"), {"p": price, "c": call.message.chat.id, "u": user_id})
    await call.answer("✅ خرید با موفقیت انجام شد!", show_alert=True)
    if item == "dagger": await cb_blackmarket(call)
    else: await cb_shop(call)

@router.callback_query(F.data.startswith("dig_"))
async def cb_dig(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
    if random.random() > 0.3: return await call.answer("⛏️ زمین را کندی، اما چیزی پیدا نکردی.", show_alert=True)
        
    r_type, amt = random.choice(["coins", "energy", "health"]), random.randint(20, 50)
    with engine.begin() as conn:
        if r_type == "coins":
            conn.execute(text("UPDATE players SET coins=coins+:a WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": call.message.chat.id, "u": user_id})
            await call.answer(f"💎 تبریک! {amt} سکه پیدا کردی!", show_alert=True)
        elif r_type == "energy":
            conn.execute(text("UPDATE players SET energy=LEAST(100, energy+:a) WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": call.message.chat.id, "u": user_id})
            await call.answer(f"💎 تبریک! {amt} انرژی پیدا کردی!", show_alert=True)
        else:
            conn.execute(text("UPDATE players SET health=LEAST(100, health+:a) WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": call.message.chat.id, "u": user_id})
            await call.answer(f"💎 تبریک! {amt} سلامتی پیدا کردی!", show_alert=True)

@router.callback_query(F.data.startswith("setjob_"))
async def cb_setjob(call: CallbackQuery):
    data = call.data.split("_")
    job, user_id = data[1], int(data[2])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
    
    with engine.begin() as conn:
        npc = conn.execute(text("SELECT id, name FROM npcs WHERE role=:r"), {"r": JOBS[job]["employer_role"]}).fetchone()
        if not npc: return await call.answer("کارفرما در دسترس نیست.", show_alert=True)
        conn.execute(text("UPDATE players SET job=:j, employer_npc_id=:e WHERE chat_id=:c AND user_id=:u"), {"j": job, "e": npc[0], "c": call.message.chat.id, "u": user_id})
    await call.answer(f"✅ شغل تو: {job}", show_alert=True)
    await call.message.delete()

@router.callback_query(F.data.startswith("back_"))
async def cb_back(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
    await call.message.edit_text("منوی اص