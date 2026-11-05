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
        [InlineKeyboardButton(text="🐥 جوجه من", callback_data=f"chicken_{user_id}"), InlineKeyboardButton(text="🏠 خانه من", callback_data=f"house_{user_id}")],
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

# ---------- پروفایل ----------
@router.callback_query(F.data.startswith("prof_"))
async def cb_profile(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        r = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": call.message.chat.id, "u": user_id}).mappings().fetchone()
        if not r:
            conn.execute(text("INSERT INTO players (chat_id, user_id, display_name) VALUES (:c, :u, :n)"), {"c": call.message.chat.id, "u": user_id, "n": call.from_user.first_name})
            r = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": call.message.chat.id, "u": user_id}).mappings().fetchone()
    text_msg = (
        f"👤 **{r['display_name']}**\n➖➖➖➖➖➖➖➖➖➖\n"
        f"⭐️ سطح: {r['level']} | ✨ XP: {r['xp']}/{r['level']*50}\n"
        f"💼 شغل: {r['job'] or 'بیکار'} | 🏠 خانه: سطح {r['house_level']}\n"
        f"🌾 دونه: {r['coins']} | 🏦 بانک: {r['bank_coins']}\n"
        f"⚡ انرژی: {r['energy']}/100 | ❤️ سلامتی: {r['health']}/100\n"
    )
    await call.message.edit_text(text_msg, reply_markup=get_main_keyboard(user_id))

# ---------- شغل‌ها ----------
@router.callback_query(F.data.startswith("jobs_"))
async def cb_jobs(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    job_buttons = []
    for job in JOBS.keys():
        job_buttons.append([InlineKeyboardButton(text=f"💼 {job}", callback_data=f"setjob_{job}_{call.from_user.id}")])
    job_buttons.append([InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{call.from_user.id}")])
    await call.message.edit_text("💼 **لیست شغل‌ها:**\nیکی را انتخاب کن:", reply_markup=InlineKeyboardMarkup(inline_keyboard=job_buttons))

@router.callback_query(F.data.startswith("setjob_"))
async def cb_setjob(call: CallbackQuery):
    data = call.data.split("_")
    job = data[1]
    if call.from_user.id != int(data[2]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET job=:j WHERE chat_id=:c AND user_id=:u"), {"j": job, "c": call.message.chat.id, "u": call.from_user.id})
    await call.answer(f"✅ شغل تو: {job}", show_alert=True)
    await call.message.delete()

# ---------- کار کردن ----------
@router.callback_query(F.data.startswith("work_"))
async def cb_work(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        p = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": call.message.chat.id, "u": user_id}).mappings().fetchone()
        if not p["job"]: return await call.answer("❌ شغلی نداری.", show_alert=True)
        if p["energy"] < 20: return await call.answer("⚡ انرژی نداری.", show_alert=True)
        income = JOBS[p["job"]]["income"] + p["job_level"] * 2
        new_level, new_xp = check_level_up(p["level"], p["xp"] + 15)
        conn.execute(text("UPDATE players SET coins=coins+:i, energy=energy-15, xp=:xp, level=:lvl, job_level=job_level+1 WHERE id=:p"), {"i": income, "xp": new_xp, "lvl": new_level, "p": p["id"]})
    await call.answer(f"✅ +{income} دونه گرفتی!", show_alert=True)

# ---------- استراحت ----------
@router.callback_query(F.data.startswith("rest_"))
async def cb_rest(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET energy=LEAST(100, energy+30) WHERE chat_id=:c AND user_id=:u"), {"c": call.message.chat.id, "u": user_id})
    await call.answer("😴 +۳۰ انرژی", show_alert=True)

# ---------- گنج‌یابی ----------
@router.callback_query(F.data.startswith("dig_"))
async def cb_dig(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    if random.random() > 0.3: return await call.answer("⛏️ چیزی پیدا نکردی.", show_alert=True)
    amt = random.randint(20, 50)
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET coins=coins+:a WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": call.message.chat.id, "u": user_id})
    await call.answer(f"💎 {amt} دونه پیدا کردی!", show_alert=True)

# ---------- بانک ----------
@router.callback_query(F.data.startswith("bank_"))
async def cb_bank(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 واریز 50 دونه", callback_data=f"dep_{user_id}_50"), InlineKeyboardButton(text="📤 برداشت 50 دونه", callback_data=f"wd_{user_id}_50")],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{user_id}")]
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
# ---------- جوجه ----------
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

# ---------- سیستم خانه ----------
@router.callback_query(F.data.startswith("realestate_"))
async def cb_realestate(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        r = conn.execute(text("SELECT coins, house_level FROM players WHERE user_id=:u"), {"u": call.from_user.id}).mappings().fetchone()
    lvl = r['house_level']
    text_msg = f"🏘️ **املاک و مستغلات**\n➖➖➖➖➖➖➖➖➖➖\n💰 دونه‌های تو: {r['coins']}\n\n"
    keyboard = []
    if lvl == 0:
        text_msg += "تو بی‌خونه‌ای! یک خانه چوبی بخر تا بتوانی استراحت کامل کنی."
        keyboard.append([InlineKeyboardButton(text="🛖 خرید خانه چوبی (500)", callback_data=f"buy_house_1_{call.from_user.id}")])
    elif lvl == 1:
        text_msg += "تو یک **خانه چوبی** داری. می‌توانی آن را ارتقا دهی."
        keyboard.append([InlineKeyboardButton(text="🏡 ارتقا به خانه سنگی (1500)", callback_data=f"buy_house_2_{call.from_user.id}")])
    elif lvl == 2:
        text_msg += "تو یک **خانه سنگی** داری. می‌توانی ارتقا دهی."
        keyboard.append([InlineKeyboardButton(text="🏰 ارتقا به عمارت (5000)", callback_data=f"buy_house_3_{call.from_user.id}")])
    else:
        text_msg += "تو یک **عمارت لاکچری** داری! 🏰\n🌟 **مزیت:** جوجه‌های تو ۲ برابر دونه تولید می‌کنن!"
    keyboard.append([InlineKeyboardButton(text="↩️ بازگشت به فروشگاه", callback_data=f"shop_{call.from_user.id}")])
    await call.message.edit_text(text_msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data.startswith("buy_house_"))
async def buy_house(call: CallbackQuery):
    data = call.data.split("_")
    target_level, user_id = int(data[2]), int(data[3])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    prices = {1: 500, 2: 1500, 3: 5000}
    price = prices[target_level]
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins FROM players WHERE user_id=:u"), {"u": user_id}).mappings().fetchone()
        if p['coins'] < price: return await call.answer(f"❌ نیاز به {price} دونه داری!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins-:c, house_level=:l WHERE user_id=:u"), {"c": price, "l": target_level, "u": user_id})
    await call.answer(f"🏠 تبریک! خونه تو ارتقا پیدا کرد.", show_alert=True)
    await cb_realestate(call)

@router.callback_query(F.data.startswith("house_"))
async def cb_house(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        r = conn.execute(text("SELECT house_level, energy, health FROM players WHERE user_id=:u"), {"u": user_id}).mappings().fetchone()
    if r['house_level'] == 0:
        return await call.answer("🏚️ تو هنوز خونه نداری!", show_alert=True)
    text_msg = f"🏠 **خانه دنج تو (سطح {r['house_level']})**\n➖➖➖➖➖➖➖➖➖➖\nاینجا امن و آرومه.\n⚡ انرژی: {r['energy']}/100\n❤️ سلامتی: {r['health']}/100"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛌 استراحت کامل (فول شدن)", callback_data=f"resthouse_{user_id}")],[InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{user_id}")]])
    await call.message.edit_text(text_msg, reply_markup=keyboard)

@router.callback_query(F.data.startswith("resthouse_"))
async def cb_rest_house(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET energy=100, health=100 WHERE user_id=:u"), {"u": user_id})
    await call.answer("🛌 استراحت کامل انجام شد! انرژی و سلامتی‌ت فول شد.", show_alert=True)
    await cb_house(call)

# ---------- فروشگاه ----------
@router.callback_query(F.data.startswith("shop_"))
async def cb_shop(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍞 نان (10 دونه)", callback_data=f"buy_nan_{call.from_user.id}"), InlineKeyboardButton(text="🍖 گوشت (30 دونه)", callback_data=f"buy_meat_{call.from_user.id}")],
        [InlineKeyboardButton(text="🗡️ شمشیر (50 دونه)", callback_data=f"buy_sword_{call.from_user.id}"), InlineKeyboardButton(text="🛡️ زره (50 دونه)", callback_data=f"buy_armor_{call.from_user.id}")],
        [InlineKeyboardButton(text="🏠 املاک و مستغلات", callback_data=f"realestate_{call.from_user.id}")],
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

@router.callback_query(F.data.startswith("buy_dagger_"))
async def buy_dagger(call: CallbackQuery):
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins, has_dagger FROM players WHERE user_id=:u"), {"u": call.from_user.id}).mappings().fetchone()
        if p['has_dagger']: return await call.answer("تو از قبل چاقو داری!", show_alert=True)
        if p['coins'] < 150: return await call.answer("دونه کافی نداری!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins-150, has_dagger=1 WHERE user_id=:u"), {"u": call.from_user.id})
    await call.answer("✅ چاقو خریدی!", show_alert=True)
    await cb_blackmarket(call)
# ---------- پنل ادمین ----------
@router.callback_query(F.data.startswith("admin_"))
async def cb_admin(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return await call.answer("❌ تو ادمین نیستی!", show_alert=True)
    if call.data == "admin_stats":
        with engine.begin() as conn:
            players = conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
        await call.message.edit_text(f"📊 **آمار:**\n👤 بازیکن‌ها: {players}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ بازگشت", callback_data="admin_back")]]))
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
        await call.message.edit_text("👑 **پنل ادمین**\n➖➖➖➖➖➖➖➖➖➖\nیکی از گزینه‌ها رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

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
    help_text = "📖 **راهنما**\n🔹 `جوجه ادمین`: پنل مدیریت\n🔹 `جوجه من`: پنل جوجه\n🔸 دکمه‌های شیشه‌