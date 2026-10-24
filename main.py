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
    init_db, get_player, create_player, perform_gacha, start_pvp_match, start_team_battle, start_2v2_match,
    finish_match_rewards, get_player_team, remove_from_team, rest_player, train_player, 
    get_leaderboard, get_player_rank, get_db_connection, save_setting, get_setting,
    unlock_skill_db, get_unlocked_skills, create_event, get_active_event, fight_custom_boss,
    enter_shadow_league, shadow_league_result, use_wild_card, get_player_damage,
    check_synergy, check_teammate_jealousy, generate_coach_mission, check_coach_mission,
    attack_with_technique, check_ego_recovery, resolve_duel
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
        [InlineKeyboardButton(text="⚔️ MATCH (PvP / 2v2 / 3v3)", callback_data="enter_match")],
        [InlineKeyboardButton(text="🔥 ACTIVE EVENT", callback_data="active_event_menu")],
        [InlineKeyboardButton(text="🎰 GACHA", callback_data="gacha_shop")],
        [InlineKeyboardButton(text="🧠 MANAGE TEAM", callback_data="manage_team")],
        [InlineKeyboardButton(text="🃏 WILD CARD", callback_data="wild_card_menu")],
        [InlineKeyboardButton(text="🌌 EGO DOMAIN", callback_data="free_mode")],
        [InlineKeyboardButton(text="🕵️‍♂️ COACH AGENDA", callback_data="coach_agenda")],
        [InlineKeyboardButton(text="🏋️ TRAINING", callback_data="training_menu")],
        [InlineKeyboardButton(text="📊 MY PROFILE", callback_data="my_profile")]
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
    menu_image = get_setting("main_menu_image")
    if menu_image:
        await message.answer_photo(photo=menu_image, caption=welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    else:
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
            f"-------------------------\n🪙 سکه: {player['normal_coins']}\n🖤 سکه سیاه: {player['black_coins']}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "coach_agenda")
async def coach_agenda(callback: types.CallbackQuery):
    mission = generate_coach_mission(callback.from_user.id)
    text = f"🕵️‍♂️ **ماموریت مخفی مربی:**\n\n{mission['text']}\n\n⚠️ اگر این ماموریت رو انجام ندی، اِگوت کم میشه و فشار روانی‌ات بالا میره!"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()
@dp.callback_query(F.data == "gacha_shop")
async def gacha_shop(callback: types.CallbackQuery):
    text = "🎰 **بازار گاچا**\n\nبا ۱۰۰ سکه شانست رو امتحان کن!\n🔴 Legendary: ۳٪\n🟣 Epic: ۲۲٪\n🔵 Rare: ۷۵٪"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎲 ROLL GACHA (100 Coins)", callback_data="roll_gacha")], [InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
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
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎲 ROLL AGAIN", callback_data="roll_gacha")], [InlineKeyboardButton(text="🔙 BACK", callback_data="gacha_shop")]])
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
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎰 GACHA", callback_data="gacha_shop")], [InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
        return await callback.message.edit_text(text, reply_markup=kb)
    kb_buttons = [[InlineKeyboardButton(text=f"{'🔴' if c['rarity']=='Legendary' else '🟣' if c['rarity']=='Epic' else '🔵'} {c['name']} {'⚠️' if c['is_cursed'] else ''}", callback_data=f"view_char_{c['char_id']}")] for c in team]
    kb_buttons.append([InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")])
    await callback.message.edit_text("🧠 **لیست کارت‌های تو:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
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
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("delete_char_"))
async def delete_character(callback: types.CallbackQuery):
    if remove_from_team(callback.from_user.id, int(callback.data.split("_")[2])):
        await callback.answer("🗑️ حذف شد!", show_alert=True)
        await manage_team(callback)

@dp.callback_query(F.data == "wild_card_menu")
async def wild_card_menu(callback: types.CallbackQuery):
    team = get_player_team(callback.from_user.id)
    if not team: return await callback.answer("تیمت خالیه!", show_alert=True)
    text = "🃏 **Wild Card**\n\nیک کارت رو فدا کن تا شانس گرفتن یک Legendary رو داشته باشی!\nکدوم کارت رو می‌سوزونی؟"
    kb_buttons = [[InlineKeyboardButton(text=f"🔥 سوزاندن {c['name']}", callback_data=f"burn_card_{c['char_id']}")] for c in team]
    kb_buttons.append([InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("burn_card_"))
async def burn_card(callback: types.CallbackQuery):
    result = use_wild_card(callback.from_user.id, int(callback.data.split("_")[2]))
    if result == "not_in_team": return await callback.answer("کارت پیدا نشد!", show_alert=True)
    text = f"🔥 **کارت سوزانده شد!**\n🎉 یک کارت Legendary جدید:\n\n👤 **{result['name']}**\n⚡ {result['technique']}\n💪 {result['base_power']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "free_mode")
async def free_mode(callback: types.CallbackQuery):
    team = get_player_team(callback.from_user.id)
    if not team: return await callback.answer("❌ اول باید از گاچا کارت بگیری!", show_alert=True)
    text = "🌌 **قلمرو اگو**\n\nمی‌خوای درخت مهارت کدوم کارت رو ببینی؟"
    kb_buttons = [[InlineKeyboardButton(text=f"🃏 {c['name']}", callback_data=f"select_char_{c['char_id']}")] for c in team]
    kb_buttons.append([InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
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
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons), parse_mode="Markdown")
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
@dp.callback_query(F.data == "enter_match")
async def enter_match(callback: types.CallbackQuery):
    text = "🏟️ **ورود به زمین**\n\nنوع مسابقه رو انتخاب کن:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ 1v1 PvP (vs NPC)", callback_data="start_pvp")],
        [InlineKeyboardButton(text="👥 2v2 MATCH", callback_data="start_2v2")],
        [InlineKeyboardButton(text="🛡️ 3v3 TEAM BATTLE", callback_data="start_team_battle")],
        [InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "start_pvp")
async def start_pvp(callback: types.CallbackQuery):
    data = start_pvp_match(callback.from_user.id, 0) 
    if data == "no_team": return await callback.answer("❌ اول کارت بگیر!", show_alert=True)
    banner = f"⚔️ **مسابقه PvP شروع شد!**\n🆚 حریف: **{data['opponent_name']}**\n⚡ تکنیک ستاره تو: **{data['player_technique']}**\n⏱️ نوبت ۱/{data['max_turns']}\n\nتوپ پیش توست. چه حرکتی می‌زنی؟"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💥 DIRECT SHOT", callback_data="action_shoot")], [InlineKeyboardButton(text="🎯 PRECISION PASS", callback_data="action_pass")], [InlineKeyboardButton(text="🏃 DRIBBLE", callback_data="action_dribble")]])
    await callback.message.edit_text(banner, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "start_2v2")
async def start_2v2(callback: types.CallbackQuery):
    data = start_2v2_match(callback.from_user.id)
    if data == "need_2_cards": return await callback.answer("❌ برای مسابقه ۲ در ۲ حداقل به ۲ کارت نیاز داری!", show_alert=True)
    banner = f"👥 **مسابقه ۲ در ۲ شروع شد!**\n🆚 حریف: **{data['npc_name']}**\n⚡ تکنیک ستاره تو: **{data['player_technique']}**\n⏱️ نوبت ۱/{data['max_turns']}\n\nتوپ پیش توست. چه حرکتی می‌زنی؟"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💥 DIRECT SHOT", callback_data="action_shoot")], [InlineKeyboardButton(text="🎯 PRECISION PASS", callback_data="action_pass")], [InlineKeyboardButton(text="🏃 DRIBBLE", callback_data="action_dribble")]])
    await callback.message.edit_text(banner, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "start_team_battle")
async def start_team_battle_handler(callback: types.CallbackQuery):
    data = start_team_battle(callback.from_user.id)
    if data == "need_3_cards": return await callback.answer("❌ برای تیم بتل حداقل ۳ کارت نیاز داری!", show_alert=True)
    banner = f"🛡️ **تیم بتل شروع شد!**\n🆚 حریف: **{data['npc_name']}**\n⚡ تکنیک ستاره تو: **{data['player_technique']}**\n⏱️ نوبت ۱/{data['max_turns']}\n\nتوپ پیش توست. چه حرکتی می‌زنی؟"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💥 DIRECT SHOT", callback_data="action_shoot")], [InlineKeyboardButton(text="🎯 PRECISION PASS", callback_data="action_pass")], [InlineKeyboardButton(text="🏃 DRIBBLE", callback_data="action_dribble")]])
    await callback.message.edit_text(banner, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.in_(["action_shoot", "action_dribble", "action_pass"]))
async def handle_match_action(callback: types.CallbackQuery):
    action = callback.data.split("_")[1] 
    player = get_player(callback.from_user.id)
    state = player['current_match_state']
    
    # چک کردن کول‌داون ۳ ثانیه‌ای
    if player.get('last_match_action_at'):
        time_passed = datetime.now(player['last_match_action_at'].tzinfo) - player['last_match_action_at']
        if time_passed.total_seconds() < 3:
            remaining = 3 - int(time_passed.total_seconds())
            return await callback.answer(f"⏳ صبر کن! {remaining} ثانیه دیگه.", show_alert=True)
    
    synergy = check_synergy(callback.from_user.id)
    action_text = f"🔥 **{synergy['name']}** فعال شد!\n" if (synergy and action == "shoot") else ""
    
    jealousy = check_teammate_jealousy(callback.from_user.id)
    if jealousy != "no_team" and jealousy['status'] == "betrayed":
        banner = f"⚠️ **خیانت!** {jealousy['name']} از حسادت توپ رو ازت گرفت و لو داد!\n\n"
        state['score_npc'] += 1
        state['turn'] += 1
        is_finished = state['turn'] > state['max_turns']
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute('UPDATE players SET current_match_state = %s, last_match_action_at = %s WHERE user_id = %s', (json.dumps(state), datetime.now(), callback.from_user.id))
        conn.commit(); cur.close(); conn.close()
        if not is_finished:
            banner += "توپ دوباره به پای توست."
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💥 DIRECT SHOT", callback_data="action_shoot")], [InlineKeyboardButton(text="🎯 PRECISION PASS", callback_data="action_pass")], [InlineKeyboardButton(text="🏃 DRIBBLE", callback_data="action_dribble")]])
        else:
            reward = finish_match_rewards(callback.from_user.id, state['score_player'], state['score_npc'])
            banner += f"\n🏁 **پایان!**\n{reward}"
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ PLAY AGAIN", callback_data="enter_match")], [InlineKeyboardButton(text="🔙 MAIN MENU", callback_data="back_to_main")]])
        await callback.message.edit_text(banner, reply_markup=kb, parse_mode="Markdown")
        return await callback.answer()

    duel_result = resolve_duel(callback.from_user.id, state['player_star'], state['player_technique'], state['player_power'], state['npc_name'], state['npc_power'], action)
    
    if duel_result['success']: state['score_player'] += 1
    else: state['score_npc'] += 1
    state['turn'] += 1
    is_finished = state['turn'] > state['max_turns']
    
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE players SET current_match_state = %s, last_match_action_at = %s WHERE user_id = %s', (json.dumps(state), datetime.now(), callback.from_user.id))
    conn.commit(); cur.close(); conn.close()
    
    banner = f"🏟️ **{state['type'].upper()}**\n⏱️ نوبت {state['turn']}/{state['max_turns']}\n🔵 {state['score_player']} - {state['score_npc']} 🔴\n-------------------------\n{action_text}\n{duel_result['text']}\n\n"
    
    if not is_finished:
        banner += "توپ دوباره به پای توست."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💥 DIRECT SHOT", callback_data="action_shoot")], [InlineKeyboardButton(text="🎯 PRECISION PASS", callback_data="action_pass")], [InlineKeyboardButton(text="🏃 DRIBBLE", callback_data="action_dribble")]])
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
        banner += f"\n🏁 **پایان!**\n{reward}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ PLAY AGAIN", callback_data="enter_match")], [InlineKeyboardButton(text="🔙 MAIN MENU", callback_data="back_to_main")]])
    await callback.message.edit_text(banner, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()
@dp.message(F.text)
async def text_match_action(message: types.Message):
    if message.text.startswith("/"): return
    if not message.reply_to_message: return
    player = get_player(message.from_user.id)
    if not player: return
    opponent_name = message.reply_to_message.from_user.first_name or "حریف"
    result = attack_with_technique(message.from_user.id, message.text.strip(), opponent_name)
    if result.startswith("cooldown_"):
        remaining = result.split("_")[1]
        return await message.answer(f"⏳ **صبر کن!**\nتا **{remaining}** ثانیه دیگه نمی‌تونی از این تکنیک استفاده کنی.")
    elif result == "ego_broken":
        return await message.answer("💀 **اِگوی تو شکسته شده!**\nباید ۱۵ دقیقه صبر کنی تا اِگوت دوباره پر بشه. تا اون موقع نمی‌تونی حمله کنی.")
    elif result == "no_technique":
        return await message.answer("⚠️ **این تکنیک توی تیم تو نیست!**\nباید اسم دقیق تکنیک یکی از کارت‌هات رو بنویسی.")
    elif result == "no_team":
        return await message.answer("❌ اول باید از گاچا کارت بگیری!")
    else:
        await message.reply(result, parse_mode="Markdown")

@dp.callback_query(F.data == "active_event_menu")
async def active_event_menu(callback: types.CallbackQuery):
    event = get_active_event()
    if not event:
        return await callback.message.edit_text("🔥 **ایونت فعالی وجود ندارد!**\nمنتظر بمانید تا ادمین ایونت جدیدی ایجاد کند.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]]))
    text = f"🔥 **ایونت فعال: {event['boss_name']}**\n-------------------------\n💀 قدرت باس: {event['boss_power']}\n🎁 جایزه: {event['reward_black']} 🖤 و {event['reward_normal']} 🪙\n\nآماده‌ای برای مبارزه؟"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ FIGHT BOSS", callback_data=f"fight_custom_{event['event_id']}")], [InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
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
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

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

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != OWNER_ID: return await message.answer("⛔ دسترسی نداری.")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ ADD NEW CARD", callback_data="admin_add_card")],
        [InlineKeyboardButton(text="🖼️ CHANGE MENU IMAGE", callback_data="admin_set_image")],
        [InlineKeyboardButton(text="🔥 CREATE EVENT", callback_data="admin_create_event")],
        [InlineKeyboardButton(text="🪙 GIVE COINS (Reply)", callback_data="admin_give_coins")],
        [InlineKeyboardButton(text="🚫 BAN USER (Reply)", callback_data="admin_ban")],
        [InlineKeyboardButton(text="🔙 CLOSE", callback_data="back_to_main")]
    ])
    await message.answer("👑 **پنل مالک**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "admin_give_coins")
async def admin_give_coins(callback: types.CallbackQuery):
    if callback.from_user.id != OWNER_ID: return
    await callback.message.edit_text("🪙 روی پیام کاربر مورد نظر **ریپلای** کن و بنویس:\n`give [مقدار]`\nمثال: `give 500`")

@dp.callback_query(F.data == "admin_ban")
async def admin_ban(callback: types.CallbackQuery):
    if callback.from_user.id != OWNER_ID: return
    await callback.message.edit_text("🚫 روی پیام کاربر مورد نظر **ریپلای** کن و بنویس:\n`ban`")

@dp.callback_query(F.data == "admin_set_image")
async def admin_set_image(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID: return
    await state.set_state(AdminStates.waiting_for_menu_image)
    await callback.message.edit_text("🖼️ **لطفاً عکس جدید منو رو ارسال کن:**")

@dp.message(AdminStates.waiting_for_menu_image)
async def process_menu_image(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID: return
    if not message.photo: return await message.answer("⚠️ لطفاً یک عکس ارسال کن.")
    file_id = message.photo[-1].file_id
    save_setting("main_menu_image", file_id)
    await message.answer("✅ **عکس منو با موفقیت تغییر کرد!**")
    await state.clear()

@dp.callback_query(F.data == "admin_create_event")
async def admin_create_event(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID: return
    await state.set_state(AdminStates.waiting_for_event_name)
    await callback.message.edit_text("1️⃣ اسم باس جدید را وارد کن:")

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
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO characters (name, position, technique, base_power, rarity, is_cursed, synergy_tag, image_url) VALUES (%s, %s, %s, %s, %s, FALSE, %s, %s)', (data['name'], data['position'], data['technique'], data['base_power'], data['rarity'], 'custom', image_id))
    conn.commit(); cur.close(); conn.close()
    await message.answer(f"✅ **{data['name']}** ساخته شد!")
    await state.clear()

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
    cur.execute('UPDATE players SET ego = 100, ego_broken_at = NULL WHERE user_id = %s', (target_id,))
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