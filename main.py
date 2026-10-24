import asyncio
import logging
import json
import random
import os
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    init_db, get_player, create_player, perform_gacha, 
    start_pvp_match, start_team_battle, resolve_duel,
    check_synergy, check_teammate_jealousy, finish_match_rewards,
    get_player_team, remove_from_team, rest_player, train_player, 
    generate_coach_mission, check_coach_mission, get_leaderboard, 
    get_player_rank, enter_shadow_league, shadow_league_result, 
    use_wild_card, get_db_connection
)
from seed_data import seed_characters

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 7023690411

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# وب‌سرور Flask (برای Render)
# ==========================================
app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# منوها و دکمه‌ها
# ==========================================
def main_menu_keyboard():
    kb = [
        [InlineKeyboardButton(text="🏟️ مسابقه (PvP و تیم بتل)", callback_data="enter_match")],
        [InlineKeyboardButton(text="🎰 بازار گاچا", callback_data="gacha_shop")],
        [InlineKeyboardButton(text="🧠 مدیریت تیم", callback_data="manage_team")],
        [InlineKeyboardButton(text="🌳 بخش آزاد (درخت مهارت)", callback_data="free_mode")],
        [InlineKeyboardButton(text="🏋️ تمرین و ریکاوری", callback_data="training_menu")],
        [InlineKeyboardButton(text="📊 وضعیت من", callback_data="my_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

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
    await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text("🔵 **منوی اصلی بلو لاک**\n\nچه کاری می‌خوای انجام بدی؟", reply_markup=main_menu_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "my_profile")
async def show_profile(callback: types.CallbackQuery):
    player = get_player(callback.from_user.id)
    text = (f"👤 **پروفایل: {player['username']}**\n-------------------------\n"
            f"📈 سطح: {player['level']} | XP: {player['xp']}\n"
            f"🧠 اِگو: {player['ego']}٪ | 🧘 روان: {player['sanity']}٪\n"
            f"⚡ خستگی: {player['fatigue']}٪ | 😰 فشار: {player['pressure']}٪\n"
            f"-------------------------\n🪙 سکه: {player['normal_coins']}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()
# ==========================================
# گاچا و مدیریت تیم
# ==========================================
@dp.callback_query(F.data == "gacha_shop")
async def gacha_shop(callback: types.CallbackQuery):
    text = "🎰 **بازار گاچا**\n\nبا ۱۰۰ سکه شانست رو امتحان کن!\n🔴 Legendary: ۳٪\n🟣 Epic: ۲۲٪\n🔵 Rare: ۷۵٪"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎲 شانس (۱۰۰ سکه)", callback_data="roll_gacha")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "roll_gacha")
async def roll_gacha(callback: types.CallbackQuery):
    result = perform_gacha(callback.from_user.id, cost=100)
    if result == "no_coins": return await callback.answer("❌ سکه کافی نداری!", show_alert=True)
    if result == "no_chars": return await callback.answer("❌ خطا: کارت‌ها در دیتابیس نیستند.", show_alert=True)
        
    emoji = {"Legendary": "🔴", "Epic": "🟣", "Rare": "🔵"}.get(result['rarity'], "⚪")
    caption = f"🎉 **کارت جدید!**\n\n{emoji} **{result['name']}**\n📍 {result['position']}\n⚡ {result['technique']}\n💪 قدرت: {result['base_power']}\n"
    if result['is_cursed']: caption += "\n⚠️ **نفرین‌شده!**"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎲 دوباره", callback_data="roll_gacha")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="gacha_shop")]])
    
    if result.get('image_url'):
        await callback.message.answer_photo(photo=result['image_url'], caption=caption, reply_markup=kb, parse_mode="Markdown")
        await callback.message.delete()
    else:
        await callback.message.edit_text(caption, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "manage_team")
async def manage_team(callback: types.CallbackQuery):
    team = get_player_team(callback.from_user.id)
    if not team:
        text = "🧠 **مدیریت تیم**\n\n❌ تیم خالیه!"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎰 گاچا", callback_data="gacha_shop")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]])
        return await callback.message.edit_text(text, reply_markup=kb)
    kb_buttons = [[InlineKeyboardButton(text=f"{'🔴' if c['rarity']=='Legendary' else '🟣' if c['rarity']=='Epic' else '🔵'} {c['name']} {'⚠️' if c['is_cursed'] else ''}", callback_data=f"view_char_{c['char_id']}")] for c in team]
    kb_buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")])
    await callback.message.edit_text("🧠 **لیست کارت‌های تو:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("view_char_"))
async def view_character(callback: types.CallbackQuery):
    char_id = int(callback.data.split("_")[2])
    team = get_player_team(callback.from_user.id)
    char = next((c for c in team if c['char_id'] == char_id), None)
    if not char: return await callback.answer("پیدا نشد!")
    text = f"🃏 **{char['name']}**\n📍 {char['position']}\n⚡ **تکنیک:** {char['technique']}\n💪 {char['base_power']}\n{'⚠️ **نفرین‌شده!**' if char['is_cursed'] else '✅ سالم'}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗑️ حذف کارت", callback_data=f"delete_char_{char_id}")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="manage_team")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("delete_char_"))
async def delete_character(callback: types.CallbackQuery):
    if remove_from_team(callback.from_user.id, int(callback.data.split("_")[2])):
        await callback.answer("🗑️ حذف شد!", show_alert=True)
        await manage_team(callback)

# ==========================================
# بخش آزاد و تمرین
# ==========================================
@dp.callback_query(F.data == "free_mode")
async def free_mode(callback: types.CallbackQuery):
    text = (
        "🌳 **بخش آزاد - درخت مهارت**\n"
        "-------------------------\n"
        "اینجا می‌تونی مهارت‌های کاراکترت رو ببینی و دمیج‌هایی که بهشون وارد کردی رو مدیریت کنی.\n\n"
        "🌿 **شاخه حمله:** DIRECT SHOT (سطح ۱)\n"
        "🌿 **شاخه دفاع:** METAVISION (سطح ۱)\n"
        "-------------------------\n"
        "برای دیدن دمیج‌های وارد شده، روی کارت‌هات در بخش مدیریت تیم کلیک کن."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "training_menu")
async def training_menu(callback: types.CallbackQuery):
    player = get_player(callback.from_user.id)
    text = f"🏋️ **تمرین**\n-------------------------\n😰 خستگی: {player['fatigue']}٪\n😰 فشار: {player['pressure']}٪\n🧘 روان: {player['sanity']}٪\n🪙 سکه: {player['normal_coins']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛌 استراحت (۳۰)", callback_data="action_rest")], [InlineKeyboardButton(text="🏃 تمرین (۵۰)", callback_data="action_train")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
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
# ==========================================
# مسابقات (PvP و تیم بتل)
# ==========================================
@dp.callback_query(F.data == "enter_match")
async def enter_match(callback: types.CallbackQuery):
    text = "🏟️ **ورود به زمین**\n\nنوع مسابقه رو انتخاب کن:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ PvP (در برابر NPC)", callback_data="start_pvp")],
        [InlineKeyboardButton(text="🛡️ تیم بتل (۳ در ۳)", callback_data="start_team_battle")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "start_pvp")
async def start_pvp(callback: types.CallbackQuery):
    data = start_pvp_match(callback.from_user.id, 0) 
    if data == "no_team": return await callback.answer("❌ اول کارت بگیر!", show_alert=True)
    
    banner = f"⚔️ **مسابقه PvP شروع شد!**\n🆚 حریف: **{data['opponent_name']}**\n⚡ تکنیک ستاره تو: **{data['player_technique']}**\n⏱️ نوبت ۱/{data['max_turns']}\n\nتوپ پیش توست. چه حرکتی می‌زنی؟"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💥 DIRECT SHOT", callback_data="action_shoot")],
        [InlineKeyboardButton(text="🎯 PRECISION PASS", callback_data="action_pass")],
        [InlineKeyboardButton(text="🏃 DRIBBLE", callback_data="action_dribble")]
    ])
    await callback.message.edit_text(banner, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "start_team_battle")
async def start_team_battle_handler(callback: types.CallbackQuery):
    data = start_team_battle(callback.from_user.id)
    if data == "need_3_cards": return await callback.answer("❌ برای تیم بتل حداقل ۳ کارت نیاز داری!", show_alert=True)
    
    banner = f"🛡️ **تیم بتل شروع شد!**\n🆚 حریف: **{data['npc_name']}**\n⚡ تکنیک ستاره تو: **{data['player_technique']}**\n⏱️ نوبت ۱/{data['max_turns']}\n\nتوپ پیش توست. چه حرکتی می‌زنی؟"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💥 DIRECT SHOT", callback_data="action_shoot")],
        [InlineKeyboardButton(text="🎯 PRECISION PASS", callback_data="action_pass")],
        [InlineKeyboardButton(text="🏃 DRIBBLE", callback_data="action_dribble")]
    ])
    await callback.message.edit_text(banner, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.in_(["action_shoot", "action_dribble", "action_pass"]))
async def handle_match_action(callback: types.CallbackQuery):
    action = callback.data.split("_")[1] 
    player = get_player(callback.from_user.id)
    
    duel_result = resolve_duel(
        callback.from_user.id,
        player_char_name=player['current_match_state']['player_star'],
        player_technique=player['current_match_state']['player_technique'],
        player_power=player['current_match_state']['player_power'],
        npc_name=player['current_match_state']['npc_name'],
        npc_power=player['current_match_state']['npc_power'],
        action=action
    )
    
    if duel_result['success']:
        player['current_match_state']['score_player'] += 1
    else:
        player['current_match_state']['score_npc'] += 1

    player['current_match_state']['turn'] += 1
    is_finished = player['current_match_state']['turn'] > player['current_match_state']['max_turns']
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE players SET current_match_state = %s WHERE user_id = %s', (json.dumps(player['current_match_state']), callback.from_user.id))
    conn.commit(); cur.close(); conn.close()
    
    state = player['current_match_state']
    banner = f"🏟️ **{state['type'].upper()}**\n⏱️ نوبت {state['turn']}/{state['max_turns']}\n🔵 {state['score_player']} - {state['score_npc']} 🔴\n-------------------------\n{duel_result['text']}\n\n"
    
    if not is_finished:
        banner += "توپ دوباره به پای توست."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💥 DIRECT SHOT", callback_data="action_shoot")],
            [InlineKeyboardButton(text="🎯 PRECISION PASS", callback_data="action_pass")],
            [InlineKeyboardButton(text="🏃 DRIBBLE", callback_data="action_dribble")]
        ])
    else:
        reward = finish_match_rewards(callback.from_user.id, state['score_player'], state['score_npc'])
        banner += f"\n🏁 **پایان!**\n{reward}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ مجدد", callback_data="enter_match")], [InlineKeyboardButton(text="🔙 منو", callback_data="back_to_main")]])

    await callback.message.edit_text(banner, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# ==========================================
# لیدربورد
# ==========================================
@dp.callback_query(F.data == "leaderboard")
async def show_leaderboard(callback: types.CallbackQuery):
    top = get_leaderboard(10)
    rank = get_player_rank(callback.from_user.id)
    text = "🏆 **جدول رده‌بندی**\n-------------------------\n"
    for i, p in enumerate(top, start=1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} **{p['username']}** | لول {p['level']}\n"
    text += f"-------------------------\n📍 **رتبه تو: {rank}**"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 آپدیت", callback_data="leaderboard")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# ==========================================
# پنل مالک
# ==========================================
class AdminStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_position = State()
    waiting_for_technique = State()
    waiting_for_power = State()
    waiting_for_rarity = State()
    waiting_for_image = State()

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != OWNER_ID: return await message.answer("⛔ دسترسی نداری.")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ کارت جدید", callback_data="admin_add_card")], [InlineKeyboardButton(text="🖼️ تغییر عکس منو", callback_data="admin_set_image")], [InlineKeyboardButton(text="🔙 بستن", callback_data="back_to_main")]])
    await message.answer("👑 **پنل مالک**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "admin_add_card")
async def admin_add_card(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID: return
    await state.set_state(AdminStates.waiting_for_name)
    await callback.message.edit_text("1️⃣ نام کاراکتر:")

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
    await callback.message.edit_text("6️⃣ عکس بفرست (یا کلمه skip):")

@dp.message(AdminStates.waiting_for_image)
async def process_image(message: types.Message, state: FSMContext):
    image_id = message.photo[-1].file_id if message.photo else None
    if not image_id and message.text.lower() != "skip": return await message.answer("⚠️ عکس یا skip.")
    data = await state.get_data()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO characters (name, position, technique, base_power, rarity, is_cursed, synergy_tag, image_url) 
        VALUES (%s, %s, %s, %s, %s, FALSE, 'custom', %s)
    ''', (data['name'], data['position'], data['technique'], data['base_power'], data['rarity'], image_id))
    conn.commit(); cur.close(); conn.close()
    await message.answer(f"✅ **{data['name']}** ساخته شد!")
    await state.clear()

@dp.callback_query(F.data == "admin_set_image")
async def admin_set_image(callback: types.CallbackQuery):
    if callback.from_user.id != OWNER_ID: return
    await callback.message.edit_text("🖼️ برای تغییر عکس منو، باید آیدی عکس (file_id) رو ارسال کنی.\nبرای این کار، عکس رو برام بفرست تا کدش رو بهت بدم.")

# ==========================================
# اجرای نهایی
# ==========================================
async def main():
    init_db()
    seed_characters()
    print("🚀 ربات روشن شد...")
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())