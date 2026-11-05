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
    if xp >= (level * 50): return level + 1, 0 
    return level, xp

def get_main_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 پروفایل", callback_data=f"prof_{user_id}"), InlineKeyboardButton(text="💼 شغل‌ها", callback_data=f"jobs_{user_id}")],
        [InlineKeyboardButton(text="🏦 بانک", callback_data=f"bank_{user_id}"), InlineKeyboardButton(text="🛒 فروشگاه", callback_data=f"shop_{user_id}")],
        [InlineKeyboardButton(text="🕶️ بازار سیاه", callback_data=f"bm_{user_id}"), InlineKeyboardButton(text="💎 گنج‌یابی", callback_data=f"dig_{user_id}")],
        [InlineKeyboardButton(text="⚒️ کار کردن", callback_data=f"work_{user_id}"), InlineKeyboardButton(text="😴 استراحت", callback_data=f"rest_{user_id}")],
        [InlineKeyboardButton(text="🐥 جوجه من", callback_data=f"chicken_{user_id}")],
        [InlineKeyboardButton(text="📖 راهنما", callback_data=f"help_{user_id}")]
    ])

@router.message(Command("start"))
async def start_menu(message: Message):
    reply_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🎮 منوی بازی")]], resize_keyboard=True)
    await message.answer("🏰 **به شهر جوجو خوش آمدید!**\nبرای شروع دکمه «🎮 منوی بازی» را بزنید.", reply_markup=reply_keyboard)

@router.message(F.text == "🎮 منوی بازی")
async def open_main_menu(message: Message):
    await message.answer("🎮 **منوی اصلی بازی**\nیکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=get_main_keyboard(message.from_user.id))

@router.message(F.text.lower() == "جوجه ادمین")
async def open_admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS: return await message.answer("❌ تو ادمین نیستی!")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 آمار شهر", callback_data="admin_stats")],
        [InlineKeyboardButton(text="💰 دادن دونه", callback_data="admin_coins")],
        [InlineKeyboardButton(text="🆙 دادن لول", callback_data="admin_level")],
        [InlineKeyboardButton(text="📢 پیام همگانی", callback_data="admin_broadcast")]
    ])
    await message.answer("👑 **پنل ادمین (خدای شهر)**\n➖➖➖➖➖➖➖➖➖➖\nیکی از گزینه‌ها رو انتخاب کن:", reply_markup=keyboard)

# --- توابع لاجیک پروفایل و بانک ---
async def cb_profile_logic(call_or_msg, user_id):
    with engine.begin() as conn:
        chat_id = call_or_msg.message.chat.id if isinstance(call_or_msg, CallbackQuery) else call_or_msg.chat.id
        r = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
        if not r:
            name = call_or_msg.from_user.first_name
            conn.execute(text("INSERT INTO players (chat_id, user_id, display_name) VALUES (:c, :u, :n)"), {"c": chat_id, "u": user_id, "n": name})
            r = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
    text_msg = (
        f"👤 **{r['display_name']}**\n➖➖➖➖➖➖➖➖➖➖\n"
        f"⭐️ سطح: {r['level']} | ✨ XP: {r['xp']}/{r['level']*50}\n"
        f"💼 شغل: {r['job'] or 'بیکار'}\n"
        f"🌾 دونه: {r['coins']} | 🏦 بانک: {r['bank_coins']}\n"
        f"⚡ انرژی: {r['energy']}/100 | ❤️ سلامتی: {r['health']}/100\n"
    )
    if isinstance(call_or_msg, Message): await call_or_msg.answer(text_msg, reply_markup=get_main_keyboard(user_id))
    else: await call_or_msg.message.edit_text(text_msg, reply_markup=get_main_keyboard(user_id))

@router.callback_query(F.data.startswith("prof_"))
async def cb_profile(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    await cb_profile_logic(call, call.from_user.id)

@router.callback_query(F.data.startswith("bank_"))
async def cb_bank(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 واریز 50 دونه", callback_data=f"dep_{call.from_user.id}_50"), InlineKeyboardButton(text="📤 برداشت 50 دونه", callback_data=f"wd_{call.from_user.id}_50")],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{call.from_user.id}")]
    ])
    await call.message.edit_text("🏦 **بانک مرکزی**\n➖➖➖➖➖➖➖➖➖➖\nدونه‌های خود را در بانک نگهداری کنید.", reply_markup=keyboard)

@router.callback_query(F.data.startswith("dep_") | F.data.startswith("wd_"))
async def cb_transaction(call: CallbackQuery):
    data = call.data.split("_")
    action, user_id, amount = data[0], int(data[1]), int(data[2])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins, bank_coins FROM players WHERE user_id=:u"), {"u": user_id}).mappings().fetchone()
        if action == "dep":
            if p['coins'] < amount: return await call.answer("دونه کافی نداری!", show_alert=True)
            conn.execute(text("UPDATE players SET coins=coins-:a, bank_coins=bank_coins+:a WHERE user_id=:u"), {"a": amount, "u": user_id})
            await call.answer("✅ واریز شد.", show_alert=True)
        else:
            if p['bank_coins'] < amount: return await call.answer("دونه کافی نداری!", show_alert=True)
            conn.execute(text("UPDATE players SET coins=coins+:a, bank_coins=bank_coins-:a WHERE user_id=:u"), {"a": amount, "u": user_id})
            await call.answer("✅ برداشت شد.", show_alert=True)
    await cb_bank(call)

# --- شغل، کار، استراحت، گنج، جوجه ---
@router.message(F.text.lower() == "جوجو شغل")
async def text_jobs(message: Message):
    job_buttons = []
    for job in JOBS.keys():
        job_buttons.append([InlineKeyboardButton(text=f"💼 {job}", callback_data=f"setjob_{job}_{message.from_user.id}")])
    job_buttons.append([InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{message.from_user.id}")])
    await message.answer("💼 **لیست شغل‌ها:**\nیکی را انتخاب کن:", reply_markup=InlineKeyboardMarkup(inline_keyboard=job_buttons))

@router.callback_query(F.data.startswith("setjob_"))
async def cb_setjob(call: CallbackQuery):
    data = call.data.split("_")
    job = data[1]
    if call.from_user.id != int(data[2]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET job=:j WHERE chat_id=:c AND user_id=:u"), {"j": job, "c": call.message.chat.id, "u": call.from_user.id})
    await call.answer(f"✅ شغل تو: {job}", show_alert=True)
    await call.message.delete()

@router.callback_query(F.data.startswith("work_"))
async def cb_work(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        p = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": call.message.chat.id, "u": call.from_user.id}).mappings().fetchone()
        if not p["job"]: return await call.answer("❌ شغلی نداری.", show_alert=True)
        if p["energy"] < 20: return await call.answer("⚡ انرژی نداری.", show_alert=True)
        income = JOBS[p["job"]]["income"] + p["job_level"] * 2
        new_level, new_xp = check_level_up(p["level"], p["xp"] + 15)
        conn.execute(text("UPDATE players SET coins=coins+:i, energy=energy-15, xp=:xp, level=:lvl, job_level=job_level+1 WHERE id=:p"), {"i": income, "xp": new_xp, "lvl": new_level, "p": p["id"]})
    await call.answer(f"✅ +{income} دونه گرفتی!", show_alert=True)

@router.callback_query(F.data.startswith("rest_"))
async def cb_rest(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET energy=LEAST(100, energy+30) WHERE chat_id=:c AND user_id=:u"), {"c": call.message.chat.id, "u": call.from_user.id})
    await call.answer("😴 +۳۰ انرژی", show_alert=True)

@router.callback_query(F.data.startswith("dig_"))
async def cb_dig(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    if random.random() > 0.3: return await call.answer("⛏️ چیزی پیدا نکردی.", show_alert=True)
    amt = random.randint(20, 50)
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET coins=coins+:a WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": call.message.chat.id, "u": call.from_user.id})
    await call.answer(f"💎 {amt} دونه پیدا کردی!", show_alert=True)

@router.callback_query(F.data.startswith("chicken_"))
async def cb_chicken(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        r = conn.execute(text("SELECT level, chicken_name, chicken_level, chicken_eggs FROM players WHERE user_id=:u"), {"u": user_id}).mappings().fetchone()
    if not r or r['chicken_level'] == 0:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🐣 خرید جوجه (نیاز: لول ۳)", callback_data=f"buy_chicken_{user_id}")],[InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{user_id}")]])
        return await call.message.edit_text("شما هنوز جوجه ندارید! برای خرید جوجه باید به لول ۳ برسید.", reply_markup=keyboard)
    upgrade_cost = r['chicken_level'] * 50
    text_msg = f"🐥 **{r['chicken_name']}**\n➖➖➖➖➖➖➖➖➖➖\n📈 سطح جوجه: {r['chicken_level']}\n🌾 دونه‌های جمع شده: {r['chicken_eggs']}\n💸 هزینه ارتقا: {upgrade_cost} دونه\n\nبرای تغییر اسم جوجه بنویس: `اسم [اسم جدید]`"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💰 برداشت دونه‌ها", callback_data=f"collect_{user_id}")],[InlineKeyboardButton(text="📈 ارتقا جوجه", callback_data=f"upg_chicken_{user_id}")],[InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{user_id}")]])
    await call.message.edit_text(text_msg, reply_markup=keyboard)

@router.callback_query(F.data.startswith("collect_"))
async def cb_collect(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        r = conn.execute(text("SELECT chicken_eggs FROM players WHERE user_id=:u"), {"u": user_id}).mappings().fetchone()
        if r['chicken_eggs'] <= 0: return await call.answer("جوجه هنوز دونه‌ای تولید نکرده!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins+:e, chicken_eggs=0 WHERE user_id=:u"), {"e": r['chicken_eggs'], "u": user_id})
    await call.answer(f"✅ {r['chicken_eggs']} دونه برداشت کردی!", show_alert=True)
    await cb_chicken(call)
@router.callback_query(F.data.startswith("upg_chicken_"))
async def cb_upg_chicken(call: CallbackQuery):
    user_id = int(call.data.split("_")[2])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        r = conn.execute(text("SELECT coins, chicken_level FROM players WHERE user_id=:u"), {"u": user_id}).mappings().fetchone()
        cost = r['chicken_level'] * 50
        if r['coins'] < cost: return await call.answer(f"❌ نیاز به {cost} دونه داری!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins-:c, chicken_level=chicken_level+1 WHERE user_id=:u"), {"c": cost, "u": user_id})
    await call.answer("✅ جوجه ارتقا پیدا کرد!", show_alert=True)
    await cb_chicken(call)

@router.callback_query(F.data.startswith("buy_chicken_"))
async def cb_buy_chicken(call: CallbackQuery):
    user_id = int(call.data.split("_")[2])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        p = conn.execute(text("SELECT level, chicken_level, coins FROM players WHERE user_id=:u"), {"u": user_id}).mappings().fetchone()
        if p['chicken_level'] > 0: return await call.answer("تو از قبل جوجه داری!", show_alert=True)
        if p['level'] < 3: return await call.answer(f"❌ برای خرید جوجه باید لول ۳ باشی! (لول فعلی: {p['level']})", show_alert=True)
        if p['coins'] < 100: return await call.answer("❌ نیاز به ۱۰۰ دونه داری!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins-100, chicken_level=1 WHERE user_id=:u"), {"u": user_id})
    await call.answer("🐣 تبریک! تو یک جوجه خریدی!", show_alert=True)
    await cb_chicken(call)

@router.message(F.text.lower().startswith("اسم "))
async def change_chicken_name(message: Message):
    new_name = message.text[4:].strip()
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET chicken_name=:n WHERE chat_id=:c AND user_id=:u"), {"n": new_name, "c": message.chat.id, "u": message.from_user.id})
    await message.answer(f"✅ اسم جوجه به {new_name} تغییر کرد!")

# --- فروشگاه (نان، گوشت، شمشیر، زره، چاقو، خانه) ---
@router.callback_query(F.data.startswith("shop_"))
async def cb_shop(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍞 نان (10 دونه)", callback_data=f"buy_nan_{call.from_user.id}"), InlineKeyboardButton(text="🍖 گوشت (30 دونه)", callback_data=f"buy_meat_{call.from_user.id}")],
        [InlineKeyboardButton(text="🗡️ شمشیر (50 دونه)", callback_data=f"buy_sword_{call.from_user.id}"), InlineKeyboardButton(text="🛡️ زره (50 دونه)", callback_data=f"buy_armor_{call.from_user.id}")],
        [InlineKeyboardButton(text="🏠 خرید خانه (500 دونه)", callback_data=f"buy_house_{call.from_user.id}")],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{call.from_user.id}")]
    ])
    await call.message.edit_text("🛒 **فروشگاه:**", reply_markup=keyboard)

@router.callback_query(F.data.startswith("bm_"))
async def cb_blackmarket(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔪 چاقو (150 دونه)", callback_data=f"buy_dagger_{call.from_user.id}")],[InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{call.from_user.id}")]])
    await call.message.edit_text("🕶️ **بازار سیاه**", reply_markup=keyboard)

@router.callback_query(F.data.startswith("buy_nan_"))
async def buy_nan(call: CallbackQuery):
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins FROM players WHERE user_id=:u"), {"u": call.from_user.id}).mappings().fetchone()
        if p['coins'] < 10: return await call.answer("دونه کافی نداری!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins-10, energy=LEAST(100, energy+20) WHERE user_id=:u"), {"u": call.from_user.id})
    await call.answer("✅ نان خوردی و ۲۰ انرژی گرفتی!", show_alert=True)
    await cb_shop(call)

@router.callback_query(F.data.startswith("buy_meat_"))
async def buy_meat(call: CallbackQuery):
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins FROM players WHERE user_id=:u"), {"u": call.from_user.id}).mappings().fetchone()
        if p['coins'] < 30: return await call.answer("دونه کافی نداری!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins-30, health=LEAST(100, health+30) WHERE user_id=:u"), {"u": call.from_user.id})
    await call.answer("✅ گوشت خوردی و ۳۰ سلامتی گرفتی!", show_alert=True)
    await cb_shop(call)

@router.callback_query(F.data.startswith("buy_sword_"))
async def buy_sword(call: CallbackQuery):
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins, has_sword FROM players WHERE user_id=:u"), {"u": call.from_user.id}).mappings().fetchone()
        if p['has_sword']: return await call.answer("تو از قبل شمشیر داری!", show_alert=True)
        if p['coins'] < 50: return await call.answer("دونه کافی نداری!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins-50, has_sword=1 WHERE user_id=:u"), {"u": call.from_user.id})
    await call.answer("✅ شمشیر خریدی!", show_alert=True)
    await cb_shop(call)

@router.callback_query(F.data.startswith("buy_armor_"))
async def buy_armor(call: CallbackQuery):
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins, has_armor FROM players WHERE user_id=:u"), {"u": call.from_user.id}).mappings().fetchone()
        if p['has_armor']: return await call.answer("تو از قبل زره داری!", show_alert=True)
        if p['coins'] < 50: return await call.answer("دونه کافی نداری!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins-50, has_armor=1 WHERE user_id=:u"), {"u": call.from_user.id})
    await call.answer("✅ زره خریدی!", show_alert=True)
    await cb_shop(call)

@router.callback_query(F.data.startswith("buy_house_"))
async def buy_house(call: CallbackQuery):
    await call.answer("🏠 خرید خانه به زودی اضافه میشه!", show_alert=True)

@router.callback_query(F.data.startswith("buy_dagger_"))
async def buy_dagger(call: CallbackQuery):
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins, has_dagger FROM players WHERE user_id=:u"), {"u": call.from_user.id}).mappings().fetchone()
        if p['has_dagger']: return await call.answer("تو از قبل چاقو داری!", show_alert=True)
        if p['coins'] < 150: return await call.answer("دونه کافی نداری!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins-150, has_dagger=1 WHERE user_id=:u"), {"u": call.from_user.id})
    await call.answer("✅ چاقو خریدی!", show_alert=True)
    await cb_blackmarket(call)

# --- پنل ادمین (دکمه‌ها) ---
@router.callback_query(F.data.startswith("admin_"))
async def cb_admin(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return await call.answer("❌ تو ادمین نیستی!", show_alert=True)
    if call.data == "admin_stats":
        with engine.begin() as conn:
            players = conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
            npcs = conn.execute(text("SELECT COUNT(*) FROM npcs")).scalar()
        await call.message.edit_text(f"📊 **آمار شهر:**\n👤 بازیکن‌ها: {players}\n🤖 NPCها: {npcs}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ بازگشت", callback_data="admin_back")]]))
    elif call.data == "admin_coins":
        with engine.begin() as conn:
            players = conn.execute(text("SELECT display_name, user_id FROM players WHERE chat_id=:c LIMIT 10"), {"c": call.message.chat.id}).fetchall()
        keyboard = [[InlineKeyboardButton(text=f"👤 {p_name}", callback_data=f"givecoin_{p_id}")] for p_name, p_id in players]
        keyboard.append([InlineKeyboardButton(text="↩️ بازگشت", callback_data="admin_back")])
        await call.message.edit_text("💰 **به کی دونه بدی؟**", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    elif call.data == "admin_level":
        with engine.begin() as conn:
            players = conn.execute(text("SELECT display_name, user_id FROM players WHERE chat_id=:c LIMIT 10"), {"c": call.message.chat.id}).fetchall()
        keyboard = [[InlineKeyboardButton(text=f"👤 {p_name}", callback_data=f"givelevel_{p_id}")] for p_name, p_id in players]
        keyboard.append([InlineKeyboardButton(text="↩️ بازگشت", callback_data="admin_back")])
        await call.message.edit_text("🆙 **به کی لول بدی؟**", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    elif call.data == "admin_broadcast":
        await call.message.edit_text("📢 برای پیام همگانی تایپ کن:\n`/broadcast [متن]`", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ بازگشت", callback_data="admin_back")]]))
    elif call.data == "admin_back":
        keyboard = [[InlineKeyboardButton(text="📊 آمار شهر", callback_data="admin_stats")],[InlineKeyboardButton(text="💰 دادن دونه", callback_data="admin_coins")],[InlineKeyboardButton(text="🆙 دادن لول", callback_data="admin_level")],[InlineKeyboardButton(text="📢 پیام همگانی", callback_data="admin_broadcast")]]
        await call.message.edit_text("👑 **پنل ادمین (خدای شهر)**\nیکی از گزینه‌ها رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("givecoin_"))
async def cb_give_coin(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return await call.answer("❌ تو ادمین نیستی!", show_alert=True)
    target_id = int(call.data.split("_")[1])
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET coins=coins+5000 WHERE user_id=:u"), {"u": target_id})
    await call.answer("✅ ۵۰۰۰ دونه داده شد!", show_alert=True)

@router.callback_query(F.data.startswith("givelevel_"))
async def cb_give_level(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return await call.answer("❌ تو ادمین نیستی!", show_alert=True)
    target_id = int(call.data.split("_")[1])
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET level=level+10 WHERE user_id=:u"), {"u": target_id})
    await call.answer("✅ ۱۰ لول داده شد!", show_alert=True)

@router.callback_query(F.data.startswith("back_"))
async def cb_back(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    await call.message.edit_text("🎮 **منوی اصلی:**", reply_markup=get_main_keyboard(call.from_user.id))

@router.callback_query(F.data.startswith("help_"))
async def cb_help(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    help_text = "📖 **راهنما**\n🔹 `جوجه ادمین`: پنل مدیریت\n🔹 `جوجه من`: پنل جوجه\n🔸 دکمه‌های شیشه‌ای برای کار، فروشگاه و... کار می‌کنن."
    await call.message.edit_text(help_text, reply_markup=get_main_keyboard(call.from_user.id))

# --- حمله، دزدی و NPC ---
@router.message(F.text.lower() == "جوجو حمله")
async def text_attack(message: Message):
    if not message.reply_to_message: return await message.answer("روی پیام کسی ریپلای کن.")
    a_id, t_id, c_id = message.from_user.id, message.reply_to_message.from_user.id, message.chat.id
    with engine.begin() as conn:
        att = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": c_id, "u": a_id}).mappings().fetchone()
        tgt = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": c_id, "u": t_id}).mappings().fetchone()
        if not att or not tgt: return await message.answer("پروفایل نداری.")
        if att['energy'] < 10: return await message.answer("انرژی نداری.")
        a_power = random.randint(10, 30) + (15 if att['has_sword'] else 0) + (att['level'] * 2)
        d_power = random.randint(5, 15) + (20 if tgt['has_armor'] else 0) + (tgt['level'] * 2)
        dmg = max(0, a_power - d_power)
        new_hp = max(0, tgt['health'] - dmg)
        conn.execute(text("UPDATE players SET health=:h WHERE chat_id=:c AND user_id=:u"), {"h": new_hp, "c": c_id, "u": t_id})
        conn.execute(text("UPDATE players SET energy=energy-10 WHERE chat_id=:c AND user_id=:u"), {"c": c_id, "u": a_id})
    if dmg == 0: await message.answer(f"🛡️ دفاع موفق!")
    else: await message.answer(f"⚔️ {att['display_name']} به {tgt['display_name']} {dmg} آسیب زد!")

@router.message(F.text.lower() == "جوجو دزدی")
async def text_steal(message: Message):
    if not message.reply_to_message: return await message.answer("روی پیام کسی ریپلای کن.")
    thief_id, target_id, chat_id = message.from_user.id, message.reply_to_message.from_user.id, message.chat.id
    with engine.begin() as conn:
        t = conn.execute(text("SELECT coins, has_dagger, level, display_name FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": thief_id}).mappings().fetchone()
        v = conn.execute(text("SELECT coins, display_name, level FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": target_id}).mappings().fetchone()
        if not t or not v: return await message.answer("پروفایل نداری.")
        success = 0.4 + (0.2 if t['has_dagger'] else 0)
        if random.random() < success and v['coins'] > 0:
            stolen = int(v['coins'] * random.uniform(0.1, 0.3))
            conn.execute(text("UPDATE players SET coins=coins-:s WHERE chat_id=:c AND user_id=:u"), {"s": stolen, "c": chat_id, "u": target_id})
            conn.execute(text("UPDATE players SET coins=coins+:s WHERE chat_id=:c AND user_id=:u"), {"s": stolen, "c": chat_id, "u": thief_id})
            await message.answer(f"🥷 دزدی موفق! {stolen} دونه دزدیدی.")
        else:
            penalty = int(t['coins'] * 0.2)
            conn.execute(text("UPDATE players SET coins=GREATEST(0, coins-:p) WHERE chat_id=:c AND user_id=:u"), {"p": penalty, "c": chat_id, "u": thief_id})
            await message.answer(f"🚨 دزدی ناموفق! جریمه: {penalty} دونه.")

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
        if any(w in tl for w in ["سلام", "صبح"]): await message.answer(f"🍞 {target[2]}: {'سلام! خوش آمدی.' if trust > 60 else 'بله؟'}")
        elif any(w in tl for w in ["بده", "نان"]): await message.answer(f"🍞 {target[2]}: نان ۱۰ دونه." if trust >= 30 else f"🍞 {target[2]}: به تو نمی‌فروشم.")