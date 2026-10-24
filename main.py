import asyncio
import logging
import json
import random
import os
import threading
from datetime import datetime
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    init_db, get_player, create_player, perform_gacha, 
    finish_match_rewards, get_player_team, remove_from_team, rest_player, train_player, 
    get_leaderboard, get_player_rank, get_db_connection, save_setting, get_setting,
    unlock_skill_db, get_unlocked_skills, create_event, get_active_event, fight_custom_boss,
    use_wild_card, get_player_damage,
    check_synergy, check_teammate_jealousy, generate_coach_mission, check_coach_mission,
    attack_with_technique, check_ego_recovery
)
from seed_data import seed_characters

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 7023690411

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

app = Flask(__name__)
@app.route('/')
def health(): return "Bot is running!"
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def main_menu_keyboard():
    kb = [
        [InlineKeyboardButton(text="🔥 ACTIVE EVENT", callback_data="active_event_menu")],
        [InlineKeyboardButton(text="🎰 GACHA", callback_data="gacha_shop")],
        [InlineKeyboardButton(text="🧠 MANAGE TEAM", callback_data="manage_team")],
        [InlineKeyboardButton(text="🌌 EGO DOMAIN", callback_data="free_mode")],
        [InlineKeyboardButton(text="🕵️‍♂️ COACH AGENDA", callback_data="coach_agenda")],
        [InlineKeyboardButton(text="🎯 SELECT CHARACTER", callback_data="select_main_char")],
        [InlineKeyboardButton(text="🏋️ TRAINING", callback_data="training_menu")],
        [InlineKeyboardButton(text="📊 MY PROFILE", callback_data="my_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ✅ تابع جدید برای جلوگیری از خطای ویرایش عکس
async def safe_edit_message(callback: types.CallbackQuery, text: str, reply_markup=None, parse_mode="Markdown"):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await callback.message.edit_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        try:
            await callback.message.delete()
        except:
            pass
        if callback.message.photo:
            await callback.message.answer_photo(photo=callback.message.photo[-1].file_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    player = get_player(user_id)
    if not player:
        create_player(user_id, username)
        welcome = f"🔵 **به بلو لاک خوش آمدی، {username}!**\n\nاز منوی زیر شروع کن:"
    else:
        welcome = "🔵 **به بلو لاک برگشتی.**\n\nچه کاری می‌خوای انجام بدی؟"
    menu_image = get_setting("main_menu_image")
    if menu_image:
        await message.answer_photo(photo=menu_image, caption=welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    else:
        await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    text = "🔵 **منوی اصلی بلو لاک**\n\nچه کاری می‌خوای انجام بدی؟"
    await safe_edit_message(callback, text, reply_markup=main_menu_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "my_profile")
async def show_profile(callback: types.CallbackQuery):
    try:
        player = get_player(callback.from_user.id)
        if not player: return await callback.answer("❌ ابتدا /start بزنید.", show_alert=True)
        p = dict(player)
        text = (f"👤 پروفایل: {p.get('username', 'Unknown')}\n-------------------------\n"
                f"📈 سطح: {p.get('level', 1)} | XP: {p.get('xp', 0)}\n"
                f"🧠 اِگو: {p.get('current_ego', 2000)}/2000 | 🧘 روان: {p.get('sanity', 100)}\n"
                f"⚡ خستگی: {p.get('fatigue', 0)} | 😰 فشار: {p.get('pressure', 0)}\n"
                f"-------------------------\n🪙 سکه: {p.get('normal_coins', 0)}\n🖤 سکه سیاه: {p.get('black_coins', 0)}")
        
        main_char_id = p.get('main_char_id')
        image_url = None
        if main_char_id:
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute('SELECT image_url FROM characters WHERE char_id = %s', (main_char_id,))
            char = cur.fetchone(); cur.close(); conn.close()
            if char: image_url = char['image_url']

        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
        if image_url:
            try:
                await callback.message.delete()
            except: pass
            await callback.message.answer_photo(photo=image_url, caption=text, reply_markup=kb)
        else:
            await safe_edit_message(callback, text, reply_markup=kb)
    except Exception as e:
        await safe_edit_message(callback, f"⚠️ خطا در دریافت پروفایل.\n(Error: {str(e)})")
    await callback.answer()

@dp.callback_query(F.data == "select_main_char")
async def select_main_char(callback: types.CallbackQuery):
    team = get_player_team(callback.from_user.id)
    if not team: return await callback.answer("❌ اول باید کارت بگیری!", show_alert=True)
    text = "🎯 **انتخاب کاراکتر اصلی**\n\nکدوم کارت توی ریپلای‌ها و پروفایل نمایش داده بشه؟"
    kb_buttons = [[InlineKeyboardButton(text=f"🃏 {c['name']}", callback_data=f"set_main_{c['char_id']}")] for c in team]
    kb_buttons.append([InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")])
    await safe_edit_message(callback, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("set_main_"))
async def set_main_character(callback: types.CallbackQuery):
    char_id = int(callback.data.split("_")[2])
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE players SET main_char_id = %s WHERE user_id = %s', (char_id, callback.from_user.id))
    conn.commit(); cur.close(); conn.close()
    await callback.answer("✅ کاراکتر اصلی انتخاب شد!", show_alert=True)
    await back_to_main(callback)

@dp.callback_query(F.data == "gacha_shop")
async def gacha_shop(callback: types.CallbackQuery):
    text = "🎰 **بازار گاچا**\n\nبا ۱۰۰ سکه شانست رو امتحان کن!\n🔴 Legendary: ۳٪\n🟣 Epic: ۲۲٪\n🔵 Rare: ۷۵٪"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎲 ROLL GACHA (100 Coins)", callback_data="roll_gacha")], [InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
    await safe_edit_message(callback, text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "roll_gacha")
async def roll_gacha(callback: types.CallbackQuery):
    result = perform_gacha(callback.from_user.id, cost=100)
    if result == "no_coins": return await callback.answer("❌ سکه کافی نداری!", show_alert=True)
    if result == "no_chars": return await callback.answer("❌ خطا: کارت‌ها در دیتابیس نیستند.", show_alert=True)
    emoji = {"Legendary": "🔴", "Epic": "🟣", "Rare": "🔵"}.get(result['rarity'], "⚪")
    caption = f"🎉 **کارت جدید!**\n\n{emoji} **{result['name']}**\n📍 {result['position']}\n⚡ {result['technique']}\n💪 قدرت: {result['base_power']}\n"
    if result['is_cursed']: caption += "\n⚠️ **نفرین‌شده!**"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎲 ROLL AGAIN", callback_data="roll_gacha")], [InlineKeyboardButton(text="🔙 BACK", callback_data="gacha_shop")]])
    if result.get('image_url'):
        try:
            await callback.message.delete()
        except: pass
        await callback.message.answer_photo(photo=result['image_url'], caption=caption, reply_markup=kb, parse_mode="Markdown")
    else:
        await safe_edit_message(callback, caption, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "manage_team")
async def manage_team(callback: types.CallbackQuery):
    team = get_player_team(callback.from_user.id)
    if not team:
        text = "🧠 **مدیریت تیم**\n\n❌ تیم خالیه!"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎰 GACHA", callback_data="gacha_shop")], [InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
        return await safe_edit_message(callback, text, reply_markup=kb)
    kb_buttons = [[InlineKeyboardButton(text=f"{'🔴' if c['rarity']=='Legendary' else '🟣' if c['rarity']=='Epic' else '🔵'} {c['name']} {'⚠️' if c['is_cursed'] else ''}", callback_data=f"view_char_{c['char_id']}")] for c in team]
    kb_buttons.append([InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")])
    await safe_edit_message(callback, "🧠 **لیست کارت‌های تو:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("view_char_"))
async def view_character(callback: types.CallbackQuery):
    char_id = int(callback.data.split("_")[2])
    team = get_player_team(callback.from_user.id)
    char = next((c for c in team if c['char_id'] == char_id), None)
    if not char: return await callback.answer("پیدا نشد!")
    dmg = get_player_damage(callback.from_user.id, char_id)
    text = f"🃏 **{char['name']}**\n📍 {char['position']}\n⚡ **تکنیک:** {char['technique']}\n💪 {char['base_power']}\n💥 دمیج دریافتی: **{dmg}**\n{'⚠️ **نفرین‌شده!**' if char['is_cursed'] else '✅ سالم'}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗑️ DELETE CARD", callback_data=f"delete_char_{char_id}")], [InlineKeyboardButton(text="🔙 BACK", callback_data="manage_team")]])
    await safe_edit_message(callback, text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("delete_char_"))
async def delete_character(callback: types.CallbackQuery):
    if remove_from_team(callback.from_user.id, int(callback.data.split("_")[2])):
        await callback.answer("🗑️ حذف شد!", show_alert=True)
        await manage_team(callback)
@dp.callback_query(F.data == "free_mode")
async def free_mode(callback: types.CallbackQuery):
    team = get_player_team(callback.from_user.id)
    if not team: return await callback.answer("❌ اول باید از گاچا کارت بگیری!", show_alert=True)
    text = "🌌 **قلمرو اگو**\n\nمی‌خوای درخت مهارت کدوم کارت رو ببینی؟"
    kb_buttons = [[InlineKeyboardButton(text=f"🃏 {c['name']}", callback_data=f"select_char_{c['char_id']}")] for c in team]
    kb_buttons.append([InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")])
    await safe_edit_message(callback, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("select_char_"))
async def show_char_skills(callback: types.CallbackQuery):
    char_id = int(callback.data.split("_")[2])
    team = get_player_team(callback.from_user.id)
    char = next((c for c in team if c['char_id'] == char_id), None)
    if not char: return await callback.answer("پیدا نشد!")
    char_name = char['name']
    text = f"🌌 **قلمرو اگو - {char_name}**\n-------------------------\nهر مهارت با سکه قابل باز کردنه. مهارت‌های پایین‌تر نیاز به سکه سیاه دارن!\n\n"
    skills = []
    if char_name == "Yoichi Isagi":
        skills = [("DIRECT SHOT", 500, "normal"), ("METAVISION", 500, "normal"), ("OFF THE BALL", 500, "normal"), ("SPATIAL AWARENESS", 800, "normal"), ("PUZZLE SOLVING", 5, "black"), ("PROTAGONIST SYNDROME", 10, "black"), ("FLOW STATE", 15, "black")]
    elif char_name == "Hiori Yo":
        skills = [("GENIUS PASS", 500, "normal"), ("TACTICAL VISION", 500, "normal"), ("QUICK FEET", 500, "normal"), ("PRECISION CROSS", 800, "normal"), ("METAVISION", 5, "black"), ("ZERO LATENCY", 10, "black"), ("GAME MAKER", 15, "black")]
    else:
        tech = char['technique']
        skills = [(tech, 500, "normal"), ("POWER SHOT", 500, "normal"), ("QUICK DRIBBLE", 500, "normal"), ("DEFENSIVE STANCE", 800, "normal"), ("BEAST MODE", 5, "black"), ("ULTIMATE FINISH", 10, "black"), ("DOMAIN EXPANSION", 15, "black")]
    unlocked = get_unlocked_skills(callback.from_user.id)
    kb_buttons = []
    for skill_name, cost, currency in skills:
        if skill_name in unlocked:
            kb_buttons.append([InlineKeyboardButton(text=f"✅ {skill_name} (Unlocked)", callback_data="none")])
        else:
            if currency == "normal":
                kb_buttons.append([InlineKeyboardButton(text=f"UNLOCK: {skill_name} · {cost} 🪙", callback_data=f"unlock_{skill_name.replace(' ', '_')}_{cost}_normal")])
            else:
                kb_buttons.append([InlineKeyboardButton(text=f"🔒 UNLOCK: {skill_name} · {cost} 🖤", callback_data=f"unlock_{skill_name.replace(' ', '_')}_{cost}_black")])
    kb_buttons.append([InlineKeyboardButton(text="🔙 بازگشت به لیست کارت‌ها", callback_data="free_mode")])
    await safe_edit_message(callback, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("unlock_"))
async def unlock_skill(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    cost = int(parts[-2]); currency = parts[-1]
    player = get_player(callback.from_user.id)
    if currency == "normal":
        if player['normal_coins'] < cost: return await callback.answer("❌ سکه عادی کافی نداری!", show_alert=True)
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('UPDATE players SET normal_coins = normal_coins - %s WHERE user_id = %s', (cost, callback.from_user.id))
        conn.commit(); cur.close(); conn.close()
    else:
        if player['black_coins'] < cost: return await callback.answer("❌ سکه سیاه کافی نداری!", show_alert=True)
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('UPDATE players SET black_coins = black_coins - %s WHERE user_id = %s', (cost, callback.from_user.id))
        conn.commit(); cur.close(); conn.close()
    skill_name = "_".join(parts[1:-2]).replace("_", " ")
    unlock_skill_db(callback.from_user.id, skill_name, currency)
    await callback.answer("✅ مهارت باز شد!", show_alert=True)
    await show_char_skills(callback)

@dp.callback_query(F.data == "training_menu")
async def training_menu(callback: types.CallbackQuery):
    player = get_player(callback.from_user.id)
    text = f"🏋️ **تمرین**\n-------------------------\n😰 خستگی: {player['fatigue']}٪\n😰 فشار: {player['pressure']}٪\n🧘 روان: {player['sanity']}٪\n🪙 سکه: {player['normal_coins']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛌 REST (30 Coins)", callback_data="action_rest")], [InlineKeyboardButton(text="🏃 TRAIN (50 Coins)", callback_data="action_train")], [InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
    await safe_edit_message(callback, text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "action_rest")
async def action_rest(callback: types.CallbackQuery):
    if rest_player(callback.from_user.id) == "no_coins": return await callback.answer("❌ سکه نداری!", show_alert=True)
    await callback.answer("🛌 استراحت کردی!", show_alert=True)
    await training_menu(callback)

@dp.callback_query(F.data == "action_train")
async def action_train(callback: types.CallbackQuery):
    res = train_player(callback.from_user.id)
    if res == "no_coins": return await callback.answer("❌ سکه نداری!", show_alert=True)
    if res == "too_tired": return await callback.answer("❌ خیلی خسته‌ای!", show_alert=True)
    msg = f"🏃 +{res['xp']} XP!"
    if res['level_up']: msg += f"\n🌟 لول {res['new_level']}!"
    await callback.answer(msg, show_alert=True)
    await training_menu(callback)

class AdminStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_position = State()
    waiting_for_technique = State()
    waiting_for_power = State()
    waiting_for_rarity = State()
    waiting_for_image = State()
    waiting_for_menu_image = State()
    waiting_for_event_name = State()
    waiting_for_event_power = State()
    waiting_for_event_reward_black = State()
    waiting_for_event_reward_normal = State()
    waiting_for_char_to_change = State()
    waiting_for_char_new_image = State()

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != OWNER_ID: 
        return await message.answer("⛔ دسترسی نداری.")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ ADD NEW CARD", callback_data="admin_add_card")],
        [InlineKeyboardButton(text="🖼️ CHANGE MENU IMAGE", callback_data="admin_set_image")],
        [InlineKeyboardButton(text="🖼️ CHANGE CHARACTER IMAGE", callback_data="admin_change_char_image")],
        [InlineKeyboardButton(text="🔥 CREATE EVENT", callback_data="admin_create_event")],
        [InlineKeyboardButton(text="🪙 GIVE COINS (Reply)", callback_data="admin_give_coins")],
        [InlineKeyboardButton(text="🚫 BAN USER (Reply)", callback_data="admin_ban")],
        [InlineKeyboardButton(text="🔙 CLOSE", callback_data="back_to_main")]
    ])
    await message.answer("👑 **پنل مالک**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "admin_give_coins")
async def admin_give_coins(callback: types.CallbackQuery):
    if callback.from_user.id != OWNER_ID: return
    await safe_edit_message(callback, "🪙 روی پیام کاربر مورد نظر **ریپلای** کن و بنویس:\n`give [مقدار]`\nمثال: `give 500`")

@dp.callback_query(F.data == "admin_ban")
async def admin_ban(callback: types.CallbackQuery):
    if callback.from_user.id != OWNER_ID: return
    await safe_edit_message(callback, "🚫 روی پیام کاربر مورد نظر **ریپلای** کن و بنویس:\n`ban`")

@dp.callback_query(F.data == "admin_set_image")
async def admin_set_image(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID: return
    await state.set_state(AdminStates.waiting_for_menu_image)
    await safe_edit_message(callback, "🖼️ **لطفاً عکس جدید منو رو ارسال کن:**")

@dp.message(AdminStates.waiting_for_menu_image)
async def process_menu_image(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID: return
    if not message.photo: return await message.answer("⚠️ لطفاً یک عکس ارسال کن.")
    file_id = message.photo[-1].file_id
    save_setting("main_menu_image", file_id)
    await message.answer("✅ **عکس منو با موفقیت تغییر کرد!**")
    await state.clear()

@dp.callback_query(F.data == "admin_change_char_image")
async def admin_change_char_image(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID: return
    await state.set_state(AdminStates.waiting_for_char_to_change)
    await safe_edit_message(callback, "🖼️ اسم کاراکتری که می‌خوای عکسش رو عوض کنی بنویس (مثلاً: Michael Kaiser):")

@dp.message(AdminStates.waiting_for_char_to_change)
async def process_char_to_change(message: types.Message, state: FSMContext):
    char_name = message.text.strip()
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT char_id FROM characters WHERE name = %s', (char_name,))
    char = cur.fetchone()
    cur.close(); conn.close()
    if not char: return await message.answer("⚠️ این کاراکتر پیدا نشد!")
    await state.update_data(char_id=char['char_id'])
    await state.set_state(AdminStates.waiting_for_char_new_image)
    await message.answer(f"✅ {char_name} پیدا شد. حالا عکس جدیدش رو بفرست:")

@dp.message(AdminStates.waiting_for_char_new_image)
async def process_char_new_image(message: types.Message, state: FSMContext):
    if not message.photo: return await message.answer("⚠️ لطفاً یک عکس ارسال کن.")
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE characters SET image_url = %s WHERE char_id = %s', (file_id, data['char_id']))
    conn.commit(); cur.close(); conn.close()
    await message.answer("✅ عکس کاراکتر با موفقیت تغییر کرد!")
    await state.clear()

@dp.callback_query(F.data == "admin_create_event")
async def admin_create_event(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID: return
    await state.set_state(AdminStates.waiting_for_event_name)
    await safe_edit_message(callback, "1️⃣ اسم باس جدید را وارد کن:")

@dp.message(AdminStates.waiting_for_event_name)
async def process_event_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text); await state.set_state(AdminStates.waiting_for_event_power)
    await message.answer("2️⃣ قدرت باس (مثلاً 100):")

@dp.message(AdminStates.waiting_for_event_power)
async def process_event_power(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("⚠️ عدد بده.")
    await state.update_data(power=int(message.text)); await state.set_state(AdminStates.waiting_for_event_reward_black)
    await message.answer("3️⃣ جایزه سکه سیاه (🖤):")

@dp.message(AdminStates.waiting_for_event_reward_black)
async def process_event_reward_black(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("⚠️ عدد بده.")
    await state.update_data(reward_black=int(message.text)); await state.set_state(AdminStates.waiting_for_event_reward_normal)
    await message.answer("4️⃣ جایزه سکه عادی (🪙):")

@dp.message(AdminStates.waiting_for_event_reward_normal)
async def process_event_reward_normal(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("⚠️ عدد بده.")
    await state.update_data(reward_normal=int(message.text))
    data = await state.get_data()
    create_event(data['name'], data['power'], data['reward_black'], data['reward_normal'])
    await message.answer(f"✅ **ایونت {data['name']} ساخته شد!**")
    await state.clear()
@dp.callback_query(F.data == "admin_add_card")
async def admin_add_card(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID: return
    await state.set_state(AdminStates.waiting_for_name)
    await safe_edit_message(callback, "1️⃣ نام کاراکتر:")

@dp.message(AdminStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text); await state.set_state(AdminStates.waiting_for_position)
    await message.answer("2️⃣ پست (FW, MF, DF, GK):")

@dp.message(AdminStates.waiting_for_position)
async def process_position(message: types.Message, state: FSMContext):
    await state.update_data(position=message.text.upper()); await state.set_state(AdminStates.waiting_for_technique)
    await message.answer("3️⃣ تکنیک:")

@dp.message(AdminStates.waiting_for_technique)
async def process_tech(message: types.Message, state: FSMContext):
    await state.update_data(technique=message.text); await state.set_state(AdminStates.waiting_for_power)
    await message.answer("4️⃣ قدرت (1-100):")

@dp.message(AdminStates.waiting_for_power)
async def process_power(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("⚠️ عدد بده.")
    await state.update_data(base_power=int(message.text)); await state.set_state(AdminStates.waiting_for_rarity)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Rare", callback_data="rarity_Rare")], [InlineKeyboardButton(text="Epic", callback_data="rarity_Epic")], [InlineKeyboardButton(text="Legendary", callback_data="rarity_Legendary")]])
    await message.answer("5️⃣ ریتی:", reply_markup=kb)

@dp.callback_query(F.data.startswith("rarity_"), AdminStates.waiting_for_rarity)
async def process_rarity(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(rarity=callback.data.split("_")[1]); await state.set_state(AdminStates.waiting_for_image)
    await safe_edit_message(callback, "6️⃣ عکس بفرست (یا کلمه skip):")

@dp.message(AdminStates.waiting_for_image)
async def process_image(message: types.Message, state: FSMContext):
    image_id = message.photo[-1].file_id if message.photo else None
    if not image_id and message.text.lower() != "skip": return await message.answer("⚠️ عکس یا skip.")
    data = await state.get_data()
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO characters (name, position, technique, base_power, rarity, is_cursed, synergy_tag, image_url) VALUES (%s, %s, %s, %s, %s, FALSE, %s, %s)', (data['name'], data['position'], data['technique'], data['base_power'], data['rarity'], 'custom', image_id))
    conn.commit(); cur.close(); conn.close()
    await message.answer(f"✅ **{data['name']}** ساخته شد!")
    await state.clear()

@dp.callback_query(F.data == "coach_agenda")
async def coach_agenda(callback: types.CallbackQuery):
    try:
        mission = generate_coach_mission(callback.from_user.id)
        mission_text = "در بازی بعدی بباز." if mission['mission_type'] == "lose_on_purpose" else "در بازی بعدی، حداقل ۳ بار خودت شوت بزن."
        text = f"🕵️‍♂️ ماموریت مخفی مربی:\n\n{mission_text}\n\n⚠️ اگر این ماموریت رو انجام ندی، اِگوت کم میشه!"
    except Exception as e:
        text = f"⚠️ خطا در دریافت ماموریت.\n(Error: {str(e)})"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
    await safe_edit_message(callback, text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "active_event_menu")
async def active_event_menu(callback: types.CallbackQuery):
    event = get_active_event()
    if not event:
        text = "🔥 **ایونت فعالی وجود ندارد!**\nمنتظر بمانید تا ادمین ایونت جدیدی ایجاد کند."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
        return await safe_edit_message(callback, text, reply_markup=kb)
    text = f"🔥 **ایونت فعال: {event['boss_name']}**\n-------------------------\n💀 قدرت باس: {event['boss_power']}\n🎁 جایزه: {event['reward_black']} 🖤 و {event['reward_normal']} 🪙\n\nآماده‌ای برای مبارزه؟"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ FIGHT BOSS", callback_data=f"fight_custom_{event['event_id']}")], [InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
    await safe_edit_message(callback, text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("fight_custom_"))
async def fight_custom(callback: types.CallbackQuery):
    event_id = int(callback.data.split("_")[2])
    result = fight_custom_boss(callback.from_user.id, event_id)
    if result == "no_team": return await callback.answer("❌ اول کارت بگیر!", show_alert=True)
    if result == "no_event": return await callback.answer("❌ این ایونت منقضی شده!", show_alert=True)
    if result['success']:
        text = f"🎉 **پیروزی بر {result['boss_name']}!**\n-------------------------\nقدرت تیم تو: {result['player_power']:.1f}\nقدرت باس: {result['boss_power']}\n\n🖤 +{result['black']} سکه سیاه\n🪙 +{result['normal']} سکه عادی"
    else:
        text = f"💀 **شکست در برابر {result['boss_name']}!**\n-------------------------\nقدرت تیم تو: {result['player_power']:.1f}\nقدرت باس: {result['boss_power']}\n\nتیمت رو قوی‌تر کن و دوباره برگرد."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ FIGHT AGAIN", callback_data=f"fight_custom_{event_id}")], [InlineKeyboardButton(text="🔙 MAIN MENU", callback_data="back_to_main")]])
    await safe_edit_message(callback, text, reply_markup=kb)
    await callback.answer()

@dp.message(F.text)
async def text_match_action(message: types.Message):
    if message.text.startswith("/"): return
    if not message.reply_to_message: return
    if message.content_type != "text": return
    player = get_player(message.from_user.id)
    if not player: return
    text = message.text.strip().lower()
    team = get_player_team(message.from_user.id)
    if not team: return
    valid_techniques = [char['technique'].lower() for char in team]
    unlocked = get_unlocked_skills(message.from_user.id)
    valid_skills = [skill.lower() for skill in unlocked.keys()]
    if text not in valid_techniques and text not in valid_skills: return
    opponent_name = message.reply_to_message.from_user.first_name or "حریف"
    opponent_id = message.reply_to_message.from_user.id
    result = attack_with_technique(message.from_user.id, text, opponent_name, opponent_id)
    if result.startswith("cooldown_"):
        remaining = result.split("_")[1]
        return await message.answer(f"⏳ **صبر کن!**\nتا **{remaining}** ثانیه دیگه نمی‌تونی از این تکنیک استفاده کنی.")
    elif result == "ego_broken":
        return await message.answer("💀 **اِگوی تو شکسته شده!**\nباید ۱۵ دقیقه صبر کنی تا اِگوت دوباره پر بشه. تا اون موقع نمی‌تونی حمله کنی.")
    elif result == "no_team":
        return await message.answer("❌ اول باید از گاچا کارت بگیری!")
    elif result != "no_technique":
        await message.reply(result, parse_mode="Markdown")

@dp.message(F.text.startswith("give "))
async def handle_give_coins(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    if not message.reply_to_message: return await message.answer("⚠️ باید روی پیام کاربر ریپلای کنی!")
    target_id = message.reply_to_message.from_user.id
    try: amount = int(message.text.split()[1])
    except: return await message.answer("⚠️ مقدار سکه رو درست وارد کن.")
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE players SET normal_coins = normal_coins + %s WHERE user_id = %s', (amount, target_id))
    conn.commit(); cur.close(); conn.close()
    await message.answer(f"✅ {amount} سکه به کاربر داده شد!")

@dp.message(F.text == "ban")
async def handle_ban(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    if not message.reply_to_message: return await message.answer("⚠️ باید روی پیام کاربر ریپلای کنی!")
    target_id = message.reply_to_message.from_user.id
    await message.answer(f"🚫 کاربر {target_id} بن شد!")

@dp.message(F.text.startswith("fill_ego"))
async def admin_fill_ego(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    if not message.reply_to_message: return await message.answer("⚠️ باید روی پیام کاربر ریپلای کنی!")
    target_id = message.reply_to_message.from_user.id
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE players SET current_ego = 2000, last_ego_update = NOW() WHERE user_id = %s', (target_id,))
    conn.commit(); cur.close(); conn.close()
    await message.answer(f"✅ **اِگوی کاربر** با موفقیت پر شد!")

async def main():
    init_db()
    seed_characters()
    print("🚀 ربات روشن شد...")
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())