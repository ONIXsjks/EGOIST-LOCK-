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

# ایمپورت‌های دیتابیس
from database import (
    init_db, get_player, create_player, perform_gacha, start_new_match, start_2v2_match,
    resolve_turn, check_synergy, check_teammate_jealousy, finish_match_rewards,
    get_player_team, remove_from_team, rest_player, train_player, generate_coach_mission, 
    check_coach_mission, get_leaderboard, get_player_rank, enter_shadow_league, 
    shadow_league_result, use_wild_card, get_db_connection
)

# --- تنظیمات ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "توکن_ربات_خودت_رو_اینجا_بذار")
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
        [InlineKeyboardButton(text="🏟️ ورود به زمین مسابقه", callback_data="enter_match")],
        [InlineKeyboardButton(text="🎰 بازار گاچا (کارت‌ها)", callback_data="gacha_shop")],
        [InlineKeyboardButton(text="🧠 مدیریت تیم", callback_data="manage_team")],
        [InlineKeyboardButton(text="🃏 وایلد کارت (فدا کردن)", callback_data="wild_card_menu")],
        [InlineKeyboardButton(text="🏋️ تمرین و ریکاوری", callback_data="training_menu")],
        [InlineKeyboardButton(text="🕵️‍♂️ توطئه مربی", callback_data="coach_agenda")],
        [InlineKeyboardButton(text="🏆 جدول رده‌بندی", callback_data="leaderboard")],
        [InlineKeyboardButton(text="📊 وضعیت من", callback_data="my_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ==========================================
# هندلرهای اصلی و پروفایل
# ==========================================
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
    text = f"🃏 **{char['name']}**\n📍 {char['position']}\n⚡ {char['technique']}\n💪 {char['base_power']}\n{'⚠️ **نفرین‌شده!**' if char['is_cursed'] else '✅ سالم'}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗑️ حذف کارت", callback_data=f"delete_char_{char_id}")], [InlineKeyboardButton(text="🔙 بازگشت", callback_data="manage_team")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("delete_char_"))
async def delete_character(callback: types.CallbackQuery):
    if remove_from_team(callback.from_user.id, int(callback.data.split("_")[2])):
        await callback.answer("🗑️ حذف شد!", show_alert=True)
        await manage_team(callback)
# ==========================================
# تمرین، استراحت و وایلد کارت
# ==========================================
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

@dp.callback_query(F.data == "wild_card_menu")
async def wild_card_menu(callback: types.CallbackQuery):
    team = get_player_team(callback.from_user.id)
    if not team: return await callback.answer("تیمت خالیه!", show_alert=True)
    text = "🃏 **وایلد کارت**\n\nیک کارت رو فدا کن تا شانس گرفتن یک Legendary رو داشته باشی!\nکدوم کارت رو می‌سوزونی؟"
    kb_buttons = [[InlineKeyboardButton(text=f"🔥 سوزاندن {c['name']}", callback_data=f"burn_card_{c['char_id']}")] for c in team]
    kb_buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("burn_card_"))
async def burn_card(callback: types.CallbackQuery):
    result = use_wild_card(callback.from_user.id, int(callback.data.split("_")[2]))
    if result == "not_in_team": return await callback.answer("کارت پیدا نشد!", show_alert=True)
    text = f"🔥 **کارت سوزانده شد!**\n🎉 یک کارت Legendary جدید:\n\n👤 **{result['name']}**\n⚡ {result['technique']}\n💪 {result['base_power']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# ==========================================
# مسابقات (۱v۱ و ۲v۲) و لیگ سایه
# ==========================================
@dp.callback_query(F.data == "enter_match")
async def enter_match(callback: types.CallbackQuery):
    text = "🏟️ **ورود به زمین**\n\nنوع مسابقه:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 تک‌نفره (۱v۱ - ۵ نوبت)", callback_data="start_match_now")],
        [InlineKeyboardButton(text="👥 دونفره (۲v۲ - ۳ نوبت)", callback_data="start_2v2_now")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "start_match_now")
async def start_match_now(callback: types.CallbackQuery):
    data = start_new_match(callback.from_user.id)
    if data == "no_team": return await callback.answer("❌ اول کارت بگیر!", show_alert=True)
    banner = f"🏟️ **شروع شد!**\n🆚 {data['npc_name']} (قدرت: {data['npc_power']})\n⚡ تیم تو: {data['player_power']:.1f}\n⏱️ نوبت ۱/{data['max_turns']}\n🔵 ۰ - ۰ 🔴\n\nتوپ پیش توست."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚽ شوت", callback_data="action_shoot")], [InlineKeyboardButton(text="🏃 دریبل", callback_data="action_dribble")], [InlineKeyboardButton(text="🎯 پاس", callback_data="action_pass")]])
    await callback.message.edit_text(banner, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "start_2v2_now")
async def start_2v2_now(callback: types.CallbackQuery):
    data = start_2v2_match(callback.from_user.id)
    if data == "need_2_cards": return await callback.answer("❌ حداقل ۲ کارت نیاز داری!", show_alert=True)
    banner = f"👥 **مسابقه ۲ در ۲!**\n🆚 {data['npc_name']}\n⏱️ نوبت ۱/{data['max_turns']}\n🔵 ۰ - ۰ 🔴\n\nتوپ پیش توست. (حمله ترکیبی قوی‌تره!)"
    kb_list = [[InlineKeyboardButton(text="⚽ شوت", callback_data="action_shoot")], [InlineKeyboardButton(text="🏃 دریبل", callback_data="action_dribble")], [InlineKeyboardButton(text="🎯 پاس", callback_data="action_pass")]]
    if check_synergy(callback.from_user.id): kb_list.insert(0, [InlineKeyboardButton(text="🔥 حمله ترکیبی", callback_data="action_combo")])
    await callback.message.edit_text(banner, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.in_(["action_shoot", "action_dribble", "action_pass", "action_combo"]))
async def handle_match_action(callback: types.CallbackQuery):
    action = callback.data.split("_")[1] 
    jealousy = check_teammate_jealousy(callback.from_user.id)
    
    if jealousy != "no_team" and jealousy["status"] == "betrayed":
        text = f"⚠️ **خیانت!** {jealousy['name']} توپ رو لو داد!\n\n"
        conn = get_db_connection()
        state = json.loads(conn.execute('SELECT current_match_state FROM players WHERE user_id = ?', (callback.from_user.id,)).fetchone()['current_match_state'])
        state['score_npc'] += 1; state['turn'] += 1
        conn.execute('UPDATE players SET current_match_state = ? WHERE user_id = ?', (json.dumps(state), callback.from_user.id))
        conn.commit(); conn.close()
        result = {"text": text, "state": state, "is_finished": state['turn'] > state['max_turns']}
    else:
        synergy = check_synergy(callback.from_user.id)
        if action == "combo" and synergy:
            conn = get_db_connection()
            state = json.loads(conn.execute('SELECT current_match_state FROM players WHERE user_id = ?', (callback.from_user.id,)).fetchone()['current_match_state'])
            is_2v2 = state.get("is_2v2", False)
            if random.randint(1, 100) <= (95 if is_2v2 else 80):
                state['score_player'] += 2; text = f"🔥 **{synergy['name']}** فعال شد! (۲ گل)"
            else:
                state['score_npc'] += 1; text = "❌ حمله ترکیبی شکست خورد!"
            state['turn'] += 1
            conn.execute('UPDATE players SET current_match_state = ? WHERE user_id = ?', (json.dumps(state), callback.from_user.id))
            conn.commit(); conn.close()
            result = {"text": text, "state": state, "is_finished": state['turn'] > state['max_turns']}
        else:
            result = resolve_turn(callback.from_user.id, action)
        
    state = result['state']
    banner = f"🏟️ **با {state['npc_name']}**\n⏱️ نوبت {state['turn']}/{state['max_turns']}\n🔵 {state['score_player']} - {state['score_npc']} 🔴\n-------------------------\n{result['text']}\n\n"
    
    if not result['is_finished']:
        banner += "توپ پیش توست."
        kb_list = [[InlineKeyboardButton(text="⚽ شوت", callback_data="action_shoot")], [InlineKeyboardButton(text="🏃 دریبل", callback_data="action_dribble")], [InlineKeyboardButton(text="🎯 پاس", callback_data="action_pass")]]
        if synergy: kb_list.insert(0, [InlineKeyboardButton(text=f"🔥 {synergy['name']}", callback_data="action_combo")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_list)
    else:
        reward = finish_match_rewards(callback.from_user.id, state['score_player'], state['score_npc'])
        match_res = "win" if state['score_player'] > state['score_npc'] else "lose"
        
        if match_res == "lose":
            player = get_player(callback.from_user.id)
            if player['in_shadow_league']:
                shadow_league_result(callback.from_user.id, is_win=False)
                banner += "\n\n🌑 **لیگ سایه:** باختی! روانت آسیب دید."
            else:
                enter_shadow_league(callback.from_user.id)
                banner += "\n\n🌑 **تبعید!** به لیگ سایه فرستاده شدی. باید ۳ بار ببری."
        else:
            player = get_player(callback.from_user.id)
            if player['in_shadow_league']:
                res = shadow_league_result(callback.from_user.id, is_win=True)
                if res == "freed": banner += "\n\n🔥 **آزاد شدی!** اِگوت به ۱۰۰ رسید!"
                else: banner += f"\n\n🌑 **لیگ سایه:** {res.split('_')[1]} از ۳ برد."
                    
        coach = check_coach_mission(callback.from_user.id, match_res)
        if coach == "success": banner += "\n\n🕵️‍♂️ **مربی راضی!** +پاداش"
        elif coach == "failed": banner += "\n\n😡 **مربی ناراضی!** -اِگو"
        
        banner += f"\n🏁 **پایان!**\n{reward}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ مجدد", callback_data="start_match_now")], [InlineKeyboardButton(text="🔙 منو", callback_data="back_to_main")]])

    await callback.message.edit_text(banner, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "coach_agenda")
async def coach_agenda(callback: types.CallbackQuery):
    mission = generate_coach_mission(callback.from_user.id)
    text = f"🕵️‍♂️ **ماموریت مربی:**\n{mission['text']}\n\n⚠️ اگر انجام ندی، جریمه میشی!"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

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
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ کارت جدید", callback_data="admin_add_card")], [InlineKeyboardButton(text="🔙 بستن", callback_data="back_to_main")]])
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
    conn.execute('INSERT INTO characters (name, position, technique, base_power, rarity, is_cursed, synergy_tag, image_url) VALUES (?, ?, ?, ?, ?, 0, ?, ?)', 
                 (data['name'], data['position'], data['technique'], data['base_power'], data['rarity'], 'custom', image_id))
    conn.commit(); conn.close()
    await message.answer(f"✅ **{data['name']}** ساخته شد!")
    await state.clear()

# ==========================================
# اجرای نهایی
# ==========================================
async def main():
    init_db()
    print("🚀 ربات روشن شد...")
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())