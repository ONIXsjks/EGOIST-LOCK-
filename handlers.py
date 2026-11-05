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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 پروفایل", callback_data=f"prof_{user_id}"), 
         InlineKeyboardButton(text="💼 شغل‌ها", callback_data=f"jobs_{user_id}")],
        [InlineKeyboardButton(text="🏦 بانک", callback_data=f"bank_{user_id}"), 
         InlineKeyboardButton(text="🛒 فروشگاه", callback_data=f"shop_{user_id}")],
        [InlineKeyboardButton(text="🕶️ بازار سیاه", callback_data=f"bm_{user_id}"), 
         InlineKeyboardButton(text="💎 گنج‌یابی", callback_data=f"dig_{user_id}")],
        [InlineKeyboardButton(text="⚒️ کار کردن", callback_data=f"work_{user_id}"), 
         InlineKeyboardButton(text="😴 استراحت", callback_data=f"rest_{user_id}")],
        [InlineKeyboardButton(text="🐥 جوجه من", callback_data=f"chicken_{user_id}")],
        [InlineKeyboardButton(text="📖 راهنما و قوانین", callback_data=f"help_{user_id}")]
    ])
    return keyboard

@router.message(Command("start"))
async def start_menu(message: Message):
    reply_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🎮 منوی بازی")]], resize_keyboard=True)
    await message.answer("🏰 **به شهر جوجو خوش آمدید!**\nبرای شروع دکمه «🎮 منوی بازی» را بزنید.", reply_markup=reply_keyboard)

@router.message(F.text == "🎮 منوی بازی")
async def open_main_menu(message: Message):
    await message.answer("🎮 **منوی اصلی بازی**\nیکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=get_main_keyboard(message.from_user.id))

@router.message(F.text.lower() == "جوجو پروفایل")
async def text_profile(message: Message): await cb_profile_logic(message, message.from_user.id)

@router.message(F.text.lower() == "جوجو بانک")
async def text_bank(message: Message): await cb_bank_logic(message, message.from_user.id)

@router.message(F.text.lower() == "جوجه من")
async def text_chicken(message: Message): await cb_chicken_logic(message, message.from_user.id)

@router.message(F.text.lower() == "جوجو شغل")
async def text_jobs(message: Message):
    job_buttons = []
    for job in JOBS.keys():
        job_buttons.append([InlineKeyboardButton(text=f"💼 {job}", callback_data=f"setjob_{job}_{message.from_user.id}")])
    job_buttons.append([InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{message.from_user.id}")])
    await message.answer("💼 **لیست شغل‌ها (بر اساس ساعت کاری):**\nیکی را انتخاب کن:", reply_markup=InlineKeyboardMarkup(inline_keyboard=job_buttons))

@router.message(F.text.lower() == "جوجو کار")
async def text_work(message: Message): await process_work(message.from_user.id, message.chat.id, message)

@router.message(F.text.lower() == "جوجو استراحت")
async def text_rest(message: Message): await process_rest(message.from_user.id, message.chat.id, message)

@router.message(F.text.lower() == "جوجو گنج")
async def text_dig(message: Message): await process_dig(message.from_user.id, message.chat.id, message)

@router.message(F.text.lower() == "خرید جوجه")
async def buy_chicken_text(message: Message):
    await process_buy_chicken(message.from_user.id, message.chat.id, message)

# ---------- توابع لاجیک ----------
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

async def cb_bank_logic(call_or_msg, user_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 واریز 50 دونه", callback_data=f"dep_{user_id}_50"), InlineKeyboardButton(text="📤 برداشت 50 دونه", callback_data=f"wd_{user_id}_50")],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{user_id}")]
    ])
    text_msg = "🏦 **بانک مرکزی**\n➖➖➖➖➖➖➖➖➖➖\nدونه‌های خود را در بانک نگهداری کنید."
    if isinstance(call_or_msg, Message): await call_or_msg.answer(text_msg, reply_markup=keyboard)
    else: await call_or_msg.message.edit_text(text_msg, reply_markup=keyboard)

async def cb_chicken_logic(call_or_msg, user_id):
    with engine.begin() as conn:
        chat_id = call_or_msg.message.chat.id if isinstance(call_or_msg, CallbackQuery) else call_or_msg.chat.id
        r = conn.execute(text("SELECT level, chicken_name, chicken_level, chicken_eggs FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
    
    if not r or r['chicken_level'] == 0:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🐣 خرید جوجه (نیاز: لول ۳)", callback_data=f"buy_chicken_{user_id}")],
            [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{user_id}")]
        ])
        await call_or_msg.message.edit_text("شما هنوز جوجه ندارید! برای خرید جوجه باید به لول ۳ برسید.", reply_markup=keyboard) if isinstance(call_or_msg, CallbackQuery) else await call_or_msg.answer("شما هنوز جوجه ندارید! برای خرید جوجه باید به لول ۳ برسید.", reply_markup=keyboard)
        return

    upgrade_cost = r['chicken_level'] * 50
    text_msg = (
        f"🐥 **{r['chicken_name']}**\n➖➖➖➖➖➖➖➖➖➖\n"
        f"📈 سطح جوجه: {r['chicken_level']}\n"
        f"🌾 دونه‌های جمع شده: {r['chicken_eggs']}\n"
        f"💸 هزینه ارتقا: {upgrade_cost} دونه\n"
        f"*(هر ۵ دقیقه {r['chicken_level'] * 3} دونه تولید میشه)*\n\n"
        f"برای تغییر اسم جوجه بنویس: `اسم [اسم جدید]`"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 برداشت دونه‌ها", callback_data=f"collect_{user_id}")],
        [InlineKeyboardButton(text="📈 ارتقا جوجه", callback_data=f"upg_chicken_{user_id}")],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{user_id}")]
    ])
    if isinstance(call_or_msg, CallbackQuery): await call_or_msg.message.edit_text(text_msg, reply_markup=keyboard)
    else: await call_or_msg.answer(text_msg, reply_markup=keyboard)
# ---------- پردازش دکمه‌ها ----------
@router.callback_query(F.data.startswith("prof_"))
async def cb_profile(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    await cb_profile_logic(call, call.from_user.id)

@router.callback_query(F.data.startswith("bank_"))
async def cb_bank(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    await cb_bank_logic(call, call.from_user.id)

@router.callback_query(F.data.startswith("chicken_"))
async def cb_chicken(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    await cb_chicken_logic(call, call.from_user.id)

@router.callback_query(F.data.startswith("buy_chicken_"))
async def cb_buy_chicken(call: CallbackQuery):
    user_id = int(call.data.split("_")[2])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    await process_buy_chicken(user_id, call.message.chat.id, call)

@router.callback_query(F.data.startswith("collect_"))
async def cb_collect(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    if call.from_user.id != user_id: return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        r = conn.execute(text("SELECT chicken_eggs, chicken_name FROM players WHERE user_id=:u"), {"u": user_id}).mappings().fetchone()
        if r['chicken_eggs'] <= 0: return await call.answer("جوجه هنوز دونهای تولید نکرده!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins+:e, chicken_eggs=0 WHERE user_id=:u"), {"e": r['chicken_eggs'], "u": user_id})
    await call.answer(f"✅ {r['chicken_eggs']} دونه برداشت کردی!", show_alert=True)
    await cb_chicken_logic(call, user_id)

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
    await cb_chicken_logic(call, user_id)

@router.message(F.text.lower().startswith("اسم "))
async def change_chicken_name(message: Message):
    new_name = message.text[4:].strip()
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET chicken_name=:n WHERE chat_id=:c AND user_id=:u"), {"n": new_name, "c": message.chat.id, "u": message.from_user.id})
    await message.answer(f"✅ اسم جوجه به {new_name} تغییر کرد!")

# ---------- فروشگاه و بلک مارکت ----------
@router.callback_query(F.data.startswith("shop_"))
async def cb_shop(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍞 نان (10 دونه)", callback_data=f"buy_nan_{call.from_user.id}")],
        [InlineKeyboardButton(text="🍖 گوشت (30 دونه)", callback_data=f"buy_meat_{call.from_user.id}")],
        [InlineKeyboardButton(text="🗡️ شمشیر (50 دونه)", callback_data=f"buy_sword_{call.from_user.id}")],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=f"back_{call.from_user.id}")]
    ])
    await call.message.edit_text("🛒 **فروشگاه:**", reply_markup=keyboard)

@router.callback_query(F.data.startswith("buy_nan_"))
async def buy_nan(call: CallbackQuery):
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins FROM players WHERE user_id=:u"), {"u": call.from_user.id}).mappings().fetchone()
        if p['coins'] < 10: return await call.answer("دونه کافی نداری!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins-10, energy=LEAST(100, energy+20) WHERE user_id=:u"), {"u": call.from_user.id})
    await call.answer("✅ نان خوردی و ۲۰ انرژی گرفتی!", show_alert=True)

@router.callback_query(F.data.startswith("buy_meat_"))
async def buy_meat(call: CallbackQuery):
    with engine.begin() as conn:
        p = conn.execute(text("SELECT coins FROM players WHERE user_id=:u"), {"u": call.from_user.id}).mappings().fetchone()
        if p['coins'] < 30: return await call.answer("دونه کافی نداری!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins-30, health=LEAST(100, health+30) WHERE user_id=:u"), {"u": call.from_user.id})
    await call.answer("✅ گوشت خوردی و ۳۰ سلامتی گرفتی!", show_alert=True)

# ---------- بقیه توابع (کار، استراحت، بانک و...) ----------
async def process_work(user_id, chat_id, event_obj):
    with engine.begin() as conn:
        p = conn.execute(text("SELECT * FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
        if not p: return await event_obj.answer("❌ اول /start رو بزن.")
        if not p["job"]: return await event_obj.answer("❌ شغلی نداری.")
        if p["energy"] < 20: return await event_obj.answer("⚡ انرژی نداری.")
        income = JOBS[p["job"]]["income"] + p["job_level"] * 2
        new_level, new_xp = check_level_up(p["level"], p["xp"] + 15)
        conn.execute(text("UPDATE players SET coins=coins+:i, energy=energy-15, xp=:xp, level=:lvl, job_level=job_level+1 WHERE id=:p"), 
                     {"i": income, "xp": new_xp, "lvl": new_level, "p": p["id"]})
    if isinstance(event_obj, CallbackQuery): await event_obj.answer(f"✅ +{income} دونه گرفتی!", show_alert=True)
    else: await event_obj.answer(f"✅ +{income} دونه گرفتی!")

async def process_rest(user_id, chat_id, event_obj):
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET energy=LEAST(100, energy+30) WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id})
    if isinstance(event_obj, CallbackQuery): await event_obj.answer("😴 +۳۰ انرژی", show_alert=True)
    else: await event_obj.answer("😴 +۳۰ انرژی")

async def process_dig(user_id, chat_id, event_obj):
    if random.random() > 0.3: return await event_obj.answer("⛏️ چیزی پیدا نکردی.")
    amt = random.randint(20, 50)
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET coins=coins+:a WHERE chat_id=:c AND user_id=:u"), {"a": amt, "c": chat_id, "u": user_id})
    if isinstance(event_obj, CallbackQuery): await event_obj.answer(f"💎 {amt} دونه پیدا کردی!", show_alert=True)
    else: await event_obj.answer(f"💎 {amt} دونه پیدا کردی!")

async def process_buy_chicken(user_id, chat_id, event_obj):
    with engine.begin() as conn:
        p = conn.execute(text("SELECT level, chicken_level, coins FROM players WHERE chat_id=:c AND user_id=:u"), {"c": chat_id, "u": user_id}).mappings().fetchone()
        if p['chicken_level'] > 0: return await event_obj.answer("تو از قبل جوجه داری!", show_alert=True)
        if p['level'] < 3: return await event_obj.answer("❌ برای خرید جوجه باید لول ۳ باشی!", show_alert=True)
        if p['coins'] < 100: return await event_obj.answer("❌ نیاز به ۱۰۰ دونه داری!", show_alert=True)
        conn.execute(text("UPDATE players SET coins=coins-100, chicken_level=1 WHERE user_id=:u"), {"u": user_id})
    await event_obj.answer("🐣 تبریک! تو یک جوجه خریدی!", show_alert=True)

@router.callback_query(F.data.startswith("setjob_"))
async def cb_setjob(call: CallbackQuery):
    data = call.data.split("_")
    job = data[1]
    if call.from_user.id != int(data[2]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    with engine.begin() as conn:
        conn.execute(text("UPDATE players SET job=:j WHERE chat_id=:c AND user_id=:u"), {"j": job, "c": call.message.chat.id, "u": call.from_user.id})
    await call.answer(f"✅ شغل تو: {job}", show_alert=True)
    await call.message.delete()

@router.callback_query(F.data.startswith("back_"))
async def cb_back(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    await call.message.edit_text("🎮 **منوی اصلی:**", reply_markup=get_main_keyboard(call.from_user.id))

@router.callback_query(F.data.startswith("help_"))
async def cb_help(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    help_text = "📖 راهنما:\nجوجو پروفایل | جوجو شغل | جوجو کار | جوجه من | خرید جوجه | اسم [اسم]"
    await call.message.edit_text(help_text, reply_markup=get_main_keyboard(call.from_user.id))

@router.callback_query(F.data.startswith("work_"))
async def cb_work(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    await process_work(call.from_user.id, call.message.chat.id, call)

@router.callback_query(F.data.startswith("rest_"))
async def cb_rest(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    await process_rest(call.from_user.id, call.message.chat.id, call)

@router.callback_query(F.data.startswith("dig_"))
async def cb_dig(call: CallbackQuery):
    if call.from_user.id != int(call.data.split("_")[1]): return await call.answer("❌ پنل شخصی است!", show_alert=True)
    await process_dig(call.from_user.id, call.message.chat.id, call)