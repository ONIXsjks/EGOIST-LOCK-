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
        [InlineKeyboardButton(text="👤 پروفایل", callback_data=f"prof_{user_id}"), 
         InlineKeyboardButton(text="💼 شغل‌ها", callback_data=f"jobs_{user_id}")],
        [InlineKeyboardButton(text="🏦 بانک", callback_data=f"bank_{user_id}"), 
         InlineKeyboardButton(text="🛒 فروشگاه", callback_data=f"shop_{user_id}")],
        [InlineKeyboardButton(text="🕶️ بازار سیاه", callback_data=f"bm_{user_id}"), 
         InlineKeyboardButton(text="💎 گنج‌یابی", callback_data=f"dig_{user_id}")],
        [InlineKeyboardButton(text="📖 راهنما و قوانین", callback_data=f"help_{user_id}")]
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
    text = (
        "🏰 **به شهر جوجو خوش آمدید!**\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        "🌆 اینجا شهری است که در آن می‌توانید کار کنید، دزدی کنید، بجنگید و ثروتمند شوید.\n\n"
        "👇 برای شروع، دکمه «🎮 منوی بازی» را در پایین صفحه بزنید."
    )
    await message.answer(text, reply_markup=reply_keyboard)

@router.message(F.text == "🎮 منوی بازی")
async def open_main_menu(message: Message):
    text = (
        "🎮 **منوی اصلی بازی**\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    await message.answer(text, reply_markup=get_main_keyboard(message.from_user.id))

# ---------- دستورات متنی (جوجو) ----------
@router.message(F.text.lower() == "جوجو پروفایل")
async def text_profile(message: Message):
    await cb_profile_logic(message, message.from_user.id)

@router.message(F.text.lower() == "جوجو بانک")
async def text_bank(message: Message):
    await cb_bank_logic(message, message.from_user.id)

@router.message(F.text.lower() == "جوجو شغل")
async def text_jobs(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍞 شاگرد نانوا (5 سکه)", callback_data=f"setjob_شاگرد نانوا_{message.from_user.id}")],
        [InlineKeyboardButton(text="🛡️ نگهبان شب (8 سکه)", callback_data=f"setjob_نگهبان شب_{message.from_user.id}")],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{message.from_user.id}")]
    ])
    await message.answer("💼 **لیست شغل‌های شهر:**\n➖➖➖➖➖➖➖➖➖➖\nبرای استخدام یکی را انتخاب کن:", reply_markup=keyboard)

@router.message(F.text.lower() == "جوجو کار")
async def text_work(message: Message):
    chat_id, user_id = message.chat.id, message.from_user.id
    with engine.begin() as conn:
        p = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
        if not p: return await message.answer("❌ اول /start رو بزن.")
        if not p["job"]: return await message.answer("❌ شغلی نداری. اول از منوی شغل‌ها استخدام شو.")
        if p["energy"] < 20: return await message.answer("⚡ انرژی نداری. استراحت کن.")
        
        npc = conn.execute(text("SELECT id, schedule FROM npcs WHERE id=:i"), {"i": p["employer_npc_id"]}).fetchone()
        if not npc or not is_active(npc[1]): return await message.answer("🚫 کارفرما الان سر کار نیست.")
        
        income = JOBS[p["job"]]["income"] + p["job_level"] * 2
        xp_gain = 15 + (p["level"] * 2)
        new_level, new_xp = check_level_up(p["level"], p["xp"] + xp_gain)
        
        conn.execute(text("UPDATE players SET coins=coins+:i, energy=energy-15, xp=:xp, level=:lvl, job_level=job_level+1 WHERE id=:p"), 
                     {"i": income, "xp": new_xp, "lvl": new_level, "p": p["id"]})
        
    await message.answer(f"✅ **کار انجام شد!**\n➖➖➖➖➖➖➖➖➖➖\n💰 +{income} سکه\n✨ +{xp_gain} XP\n⚡ -۱۵ انرژی")

@router.message(F.text.lower() == "جوجو استراحت")
async def text_rest(message: Message):
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET energy=LEAST(100, energy+30) WHERE chat_id=:c AND user_id=:u"), {"c": message.chat.id, "u": message.from_user.id})
    await message.answer("😴 **استراحت کردی.**\n➖➖➖➖➖➖➖➖➖➖\n⚡ +۳۰ انرژی")
# ---------- توابع پنل‌ها (دکمه‌های شیشه‌ای) ----------
async def cb_profile_logic(call_or_msg, user_id):
    with engine.begin() as conn:
        chat_id = call_or_msg.message.chat.id if isinstance(call_or_msg, CallbackQuery) else call_or_msg.chat.id
        r = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
        if not r:
            name = call_or_msg.from_user.first_name
            conn.execute(text("INSERT INTO players (chat_id, user_id, display_name) VALUES (:c, :u, :n)"), {"c": chat_id, "u": user_id, "n": name})
            r = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
    
    sword = "✅" if r['has_sword'] else "❌"
    armor = "✅" if r['has_armor'] else "❌"
    dagger = "✅" if r['has_dagger'] else "❌"

    text = (
        f"👤 **کارت شناسایی: {r['display_name']}**\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"⭐️ **سطح:** {r['level']} | ✨ **XP:** {r['xp']}/{r['level']*50}\n"
        f"💼 **شغل:** {r['job'] or 'بیکار'}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💰 **جیب:** {r['coins']} سکه\n"
        f"🏦 **بانک:** {r['bank_coins']} سکه\n"
        f"⚡ **انرژی:** {r['energy']}/100\n"
        f"❤️ **سلامتی:** {r['health']}/100\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🎒 **کوله‌پشتی:**\n"
        f"🗡️ شمشیر: {sword} | 🛡️ زره: {armor} | 🔪 چاقو: {dagger}"
    )
    
    if isinstance(call_or_msg, Message):
        await call_or_msg.answer(text, reply_markup=get_main_keyboard(user_id))
    else:
        await call_or_msg.message.edit_text(text, reply_markup=get_main_keyboard(user_id))

async def cb_bank_logic(call_or_msg, user_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 واریز 50 سکه", callback_data=f"dep_{user_id}_50"), 
         InlineKeyboardButton(text="📤 برداشت 50 سکه", callback_data=f"wd_{user_id}_50")],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{user_id}")]
    ])
    text = (
        "🏦 **بانک مرکزی جوجو**\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        "پول‌های خود را در بانک نگهداری کنید تا از دست دزدها در امان بمانند.\n\n"
        "یک گزینه را انتخاب کنید:"
    )
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

@router.callback_query(F.data.startswith("help_"))
async def cb_help(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
    
    help_text = (
        "📖 **راهنمای بازی**\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        "👤 `جوجو پروفایل` : دیدن کارت شخصیت\n"
        "💼 `جوجو شغل` : استخدام\n"
        "⚒️ `جوجو کار` : درآمدزایی\n"
        "💤 `جوجو استراحت` : شارژ انرژی\n"
        "🏦 `جوجو بانک` : مدیریت پول\n"
        "⚔️ `جوجو حمله` : (ریپلای) دعوا\n"
        "🥷 `جوجو دزدی` : (ریپلای) دزدی\n"
        "💎 `جوجو گنج` : گنج‌یابی"
    )
    await call.message.edit_text(help_text, reply_markup=get_main_keyboard(user_id))

@router.callback_query(F.data.startswith("shop_"))
async def cb_shop(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗡️ خرید شمشیر (50)", callback_data=f"buy_sword_{user_id}"), 
         InlineKeyboardButton(text="🛡️ خرید زره (50)", callback_data=f"buy_armor_{user_id}")],
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

@router.callback_query(F.data.startswith("back_"))
async def cb_back(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ این پنل مخصوص شخص دیگری است!", show_alert=True)
    await call.message.edit_text("🎮 **منوی اصلی بازی**\n➖➖➖➖➖➖➖➖➖➖\nیکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=get_main_keyboard(user_id))

# ---------- حمله، دزدی، گنج (متنی) ----------
@router.message(F.text.lower() == "جوجو حمله")
async def text_attack(message: Message):
    if not message.reply_to_message: return await message.answer("روی پیام کسی ریپلای کن و بنویس «جوجو حمله»")
    a_id, t_id, c_id = message.from_user.id, message.reply_to_message.from_user.id, message.chat.id
    if a_id == t_id: return await message.answer("خودزنی ممنوع! برو دکتر.")
    
    with engine.begin() as conn:
        att = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": c_id, "u": a_id}).mappings().fetchone()
        tgt = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": c_id, "u": t_id}).mappings().fetchone()
        if not att or not tgt: return await message.answer("هر دو باید پروفایل داشته باشید.")
        if att['energy'] < 10: return await message.answer("انرژی نداری. برو استراحت کن.")
        
        a_power = random.randint(10, 30) + (15 if att['has_sword'] else 0) + (att['level'] * 2)
        d_power = random.randint(5, 15) + (20 if tgt['has_armor'] else 0) + (tgt['level'] * 2)
        dmg = max(0, a_power - d_power)
        
        new_hp = max(0, tgt['health'] - dmg)
        conn.execute(text("UPDATE players SET health=:h WHERE chat_id=:c AND user_id=:u"), {"h": new_hp, "c": c_id, "u": t_id})
        conn.execute(text("UPDATE players SET energy=energy-10 WHERE chat_id=:c AND user_id=:u"), {"c": c_id, "u": a_id})
        
    if dmg == 0: await message.answer(f"🛡️ **دفاع موفق!**\n──────────────────\n{att['display_name']} به {tgt['display_name']} حمله کرد، اما زره هدف جلوی ضربه رو گرفت!")
    else: await message.answer(f"⚔️ **دعوا!**\n──────────────────\n{att['display_name']} با تمام قدرت به {tgt['display_name']} زد و **{dmg}** آسیب زد!\n❤️ سلامتی {tgt['display_name']}: {new_hp}")

@router.message(F.text.lower() == "جوجو دزدی")
async def text_steal(message: Message):
    if not message.reply_to_message: return await message.answer("روی پیام کسی ریپلای کن و بنویس «جوجو دزدی»")
    thief_id, target_id, chat_id = message.from_user.id, message.reply_to_message.from_user.id, message.chat.id
    if thief_id == target_id: return await message.answer("خودزنی؟! برو تو خیابون یه نفر پیدا کن.")
    
    with engine.begin() as conn:
        t = conn.execute(text("SELECT coins, has_dagger, level, display_name FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": thief_id}).mappings().fetchone()
        v = conn.execute(text("SELECT coins, display_name, level FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": target_id}).mappings().fetchone()
        
        if not t or not v: return await message.answer("هر دو باید پروفایل داشته باشید.")
        
        success_chance = 0.4 + (0.2 if t['has_dagger'] else 0) + (0.1 if t['level'] > v['level'] else 0)
        
        if random.random() < success_chance and v['coins'] > 0:
            stolen = int(v['coins'] * random.uniform(0.1, 0.3))
            conn.execute(text("UPDATE players SET coins=coins-:s WHERE chat_id=:c AND user_id=:u"), {"s": stolen, "c": chat_id, "u": target_id})
            conn.execute(text("UPDATE players SET coins=coins+:s WHERE chat_id=:c AND user_id=:u"), {"s": stolen, "c": chat_id, "u": thief_id})
            await message.answer(f"🥷 **جیب‌بری موفق!**\n──────────────────\n{t['display_name']} با مهارت تمام، مبلغ **{stolen}** سکه از جیب {v['display_name']} زد و در رفت!")
        else:
            penalty = int(t['coins'] * 0.2)
            conn.execute(text("UPDATE players SET coins=GREATEST(0, coins-:p) WHERE chat_id=:c AND user_id=:u"), {"p": penalty, "c": chat_id, "u": thief_id})
            await message.answer(f"🚨 **دستگیری!**\n──────────────────\n{v['display_name']} متوجه شد و داد زد! نگهبان‌ها {t['display_name']} رو گرفتن.\n💸 جریمه: **{penalty}** سکه")

@router.message(F.text.lower() == "جوجو گنج")
async def text_dig(message: Message):
    if random.random() > 0.3: return await message.answer("⛏️ **تلاش بیهوده**\n──────────────────\nزمین رو کندی، اما فقط یه کرم خاکی پیدا کردی!")
    r_type, amt = random.choice(["coins", "energy", "health"]), random.randint(20, 50)
    c_id, u_id = message.chat.id, message.from_user.id
    
    with engine.begin() as conn:
        if r_type == "coins":
            conn.execute(text("UPDATE players SET coins=coins+:a WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": c_id, "u": u_id})
            await message.answer(f"💎 **گنج پیدا شد!**\n──────────────────\nبا بیل زدی به یه صندوقچه قدیمی و **{amt}** سکه توش پیدا کردی!")
        elif r_type == "energy":
            conn.execute(text("UPDATE players SET energy=LEAST(100, energy+:a) WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": c_id, "u": u_id})
            await message.answer(f"💎 **معجون پیدا شد!**\n──────────────────\nیه شیشه معجون سبز پیدا کردی و خوردی. **{amt}** انرژی گرفتی!")
        else:
            conn.execute(text("UPDATE players SET health=LEAST(100, health+:a) WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": c_id, "u": u_id})
            await message.answer(f"💎 **گیاه دارویی!**\n──────────────────\nیه گیاه عجیب پیدا کردی و خوردی. **{amt}** سلامتی گرفتی!")

# ---------- پاسخ NPC و ادمین ----------
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

def is_admin(uid): return uid in ADMIN_IDS

@router.message(Command("addlevel"))
async def admin_add_level(message: Message):
    if not is_admin(message.from_user.id): return
    args = message.text.split()
    if len(args) < 3: return await message.answer("/addlevel [آیدی] [تعداد]")
    try:
        with engine.begin() as conn:
            res = conn.execute(text("UPDATE players SET level=level+:l WHERE user_id=:u"), {"l": int(args[2]), "u": int(args[1])})
        await message.answer("✅ انجام شد." if res.rowcount else "❌ پیدا نشد.")
    except: pass