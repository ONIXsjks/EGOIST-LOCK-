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
    attack_with_technique, check_ego_recovery,
    upgrade_card_duplicate, buy_from_black_market, check_flow_state,
    add_training_point, upgrade_card_stat, add_skin_to_inventory, set_active_skin,
    set_global_event, get_global_event, start_bet_duel, resolve_bet_duel, admin_give_coins,
    init_new_systems, check_dream_team, ascend_card,
    add_achievement, get_achievements, update_achievement_progress
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
        [InlineKeyboardButton(text="🔥 ACTIVE EVENT", callback_data="active_event_menu"), InlineKeyboardButton(text="🎰 GACHA", callback_data="gacha_shop"), InlineKeyboardButton(text="🧠 MANAGE TEAM", callback_data="manage_team")],
        [InlineKeyboardButton(text="🌌 EGO DOMAIN", callback_data="free_mode"), InlineKeyboardButton(text="🕵️‍♂️ COACH AGENDA", callback_data="coach_agenda"), InlineKeyboardButton(text="🎯 SELECT CHARACTER", callback_data="select_main_char")],
        [InlineKeyboardButton(text="🏋️ TRAINING", callback_data="training_menu"), InlineKeyboardButton(text="🖤 BLACK MARKET", callback_data="black_market"), InlineKeyboardButton(text="🏆 LEADERBOARD", callback_data="leaderboard")],
        [InlineKeyboardButton(text="🏅 ACHIEVEMENTS", callback_data="achievements_menu"), InlineKeyboardButton(text="🔄 TRADE CARDS", callback_data="trade_menu"), InlineKeyboardButton(text="❓ HELP", callback_data="help_menu")],
        [InlineKeyboardButton(text="📊 MY PROFILE", callback_data="my_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def safe_edit_message(callback: types.CallbackQuery, text: str, reply_markup=None, parse_mode="Markdown"):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await callback.message.edit_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        try: await callback.message.delete()
        except: pass
        if callback.message.photo:
            await callback.message.answer_photo(photo=callback.message.photo[-1].file_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    try: init_new_systems()
    except Exception as e: print(f"DB Error: {e}")

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

@dp.callback_query(F.data == "help_menu")
async def help_menu(callback: types.CallbackQuery):
    text = (
        "❓ **راهنمای بازی بلو لاک**\n"
        "-------------------------\n"
        "🔹 **حمله:** روی پیام حریف ریپلای کن و اسم تکنیکت رو بنویس.\n"
        "🔹 **دوئل شرطی:** روی پیام حریف ریپلای کن و بنویس `چالش` (شرط ۵۰ سکه).\n"
        "🔹 **ترید:** روی پیام حریف ریپلای کن و بنویس `ترید` (کارت‌ها معاوضه میشن).\n"
        "🔹 **نبرد دوستانه:** روی پیام حریف ریپلای کن و بنویس `نبرد دوستانه`.\n"
        "🔹 **تیم رویایی:** ۳ کارت از یک تیم خاص توی ترکیب بذار تا بونوس دمیج بگیری.\n"
        "🔹 **لول آپ کارت:** از قلمرو اگو، کارت‌های اضافی رو بسوزون تا رده کارتت بالا بره.\n"
        "🔹 **دستاوردها:** با انجام کارهای خاص، نشان و جایزه بگیر.\n"
        "🔹 **سکه سیاه:** از ایونت‌ها و باس‌ها به دست میاد."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
    await safe_edit_message(callback, text, reply_markup=kb)
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
            try: await callback.message.delete()
            except: pass
            await callback.message.answer_photo(photo=image_url, caption=text, reply_markup=kb)
        else:
            await safe_edit_message(callback, text, reply_markup=kb)
    except Exception as e:
        await safe_edit_message(callback, f"⚠️ خطا در دریافت پروفایل.\n(Error: {str(e)})")
    await callback.answer()

@dp.callback_query(F.data == "leaderboard")
async def show_leaderboard(callback: types.CallbackQuery):
    players = get_leaderboard(10)
    if not players:
        text = "🏆 **تاپ پلیرها**\n\nهنوز هیچ بازیکنی در لیست نیست!"
    else:
        text = "🏆 **۱۰ بازیکن برتر بلو لاک**\n-------------------------\n"
        for i, p in enumerate(players, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            username = p.get('username', 'Unknown')
            level = p.get('level', 1)
            xp = p.get('xp', 0)
            text += f"{medal} **{username}** | Lv.{level} | XP: {xp}\n"
        
        my_rank = get_player_rank(callback.from_user.id)
        if my_rank:
            text += f"\n-------------------------\n📍 رتبه شما: **{my_rank}**"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
    await safe_edit_message(callback, text, reply_markup=kb)
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
    text = "🎰 **بازار گاچا**\n\nبا ۱۰۰ سکه شانست رو امتحان کن!"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎲 ROLL GACHA (100 Coins)", callback_data="roll_gacha")], [InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
    await safe_edit_message(callback, text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "roll_gacha")
async def roll_gacha(callback: types.CallbackQuery):
    result = perform_gacha(callback.from_user.id, cost=100)
    if result == "no_coins": return await callback.answer("❌ سکه کافی نداری!", show_alert=True)
    
    try: update_achievement_progress(callback.from_user.id, "gacha_rolls")
    except: pass
    
    team = get_player_team(callback.from_user.id)
    duplicate = next((c for c in team if c['char_id'] == result['char_id']), None)
    if duplicate:
        caption = f"🔄 **کارت تکراری!**\n\nشما کارت **{result['name']}** رو دوباره گرفتی.\nآیا می‌خوای کارت رو آپگرید کنی؟"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💪 آپگرید (قدرت +5)", callback_data=f"upgrade_card_{result['char_id']}")],
            [InlineKeyboardButton(text="❌ رد کردن", callback_data="gacha_shop")]
        ])
        await safe_edit_message(callback, caption, reply_markup=kb)
        return

    caption = f"🎉 **کارت جدید!**\n\n**{result['name']}**\n📍 {result['position']}\n⚡ {result['technique']}\n💪 قدرت: {result['base_power']}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎲 ROLL AGAIN", callback_data="roll_gacha")], [InlineKeyboardButton(text="🔙 BACK", callback_data="gacha_shop")]])
    if result.get('image_url'):
        try: await callback.message.delete()
        except: pass
        await callback.message.answer_photo(photo=result['image_url'], caption=caption, reply_markup=kb, parse_mode="Markdown")
    else:
        await safe_edit_message(callback, caption, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("upgrade_card_"))
async def upgrade_card(callback: types.CallbackQuery):
    char_id = int(callback.data.split("_")[2])
    result = upgrade_card_duplicate(callback.from_user.id, char_id)
    if result == "success": await callback.answer("✅ کارت با موفقیت آپگرید شد! (قدرت +5)", show_alert=True)
    else: await callback.answer("❌ خطا در آپگرید کارت!", show_alert=True)
    await gacha_shop(callback)

@dp.callback_query(F.data == "manage_team")
async def manage_team(callback: types.CallbackQuery):
    team = get_player_team(callback.from_user.id)
    if not team:
        text = "🧠 **مدیریت تیم**\n\n❌ تیم خالیه!"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎰 GACHA", callback_data="gacha_shop")], [InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
        return await safe_edit_message(callback, text, reply_markup=kb)
    
    try: dream_bonus = check_dream_team(callback.from_user.id)
    except: dream_bonus = None
        
    synergy_text = f"\n\n🔥 **تیم رویایی فعال:** {dream_bonus['name']} (+{dream_bonus['bonus']}٪)" if dream_bonus else ""
    
    kb_buttons = [[InlineKeyboardButton(text=f"{'🔴' if c['rarity']=='Legendary' else '🟣' if c['rarity']=='Epic' else '🔵'} {c['name']}", callback_data=f"view_char_{c['char_id']}")] for c in team]
    kb_buttons.append([InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")])
    await safe_edit_message(callback, f"🧠 **لیست کارت‌های تو:**{synergy_text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("view_char_"))
async def view_character(callback: types.CallbackQuery):
    char_id = int(callback.data.split("_")[2])
    team = get_player_team(callback.from_user.id)
    char = next((c for c in team if c['char_id'] == char_id), None)
    if not char: return await callback.answer("پیدا نشد!")
    dmg = get_player_damage(callback.from_user.id, char_id)
    text = f"🃏 **{char['name']}**\n📍 {char['position']}\n⚡ **تکنیک:** {char['technique']}\n💪 {char['base_power']}\n💥 دمیج دریافتی: **{dmg}**"
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
    
    skills_db = {
        "Noel Noa": [("AMBIDEXTROUS FINISH", 500, "normal"), ("MACHINE DRIBBLE", 500, "normal"), ("TACTICAL GENIUS", 500, "normal"), ("PERFECT EFFICIENCY", 800, "normal"), ("GUN VOLLEY", 5, "black"), ("YOU WILL FOLLOW", 10, "black"), ("BEST STRIKER", 15, "black")],
        "Julian Loki": [("BUT IM FAST", 500, "normal"), ("TORNADO SHOT", 500, "normal"), ("DIVINE SPRINTER", 500, "normal"), ("VELOCITY DASH", 800, "normal"), ("IS THIS OKAY?", 5, "black"), ("GOD SPRINTER", 10, "black"), ("TO SLOW", 15, "black")],
        "Leonardo Luna": [("GOLDEN MIRAGE", 500, "normal"), ("LUNAR IMPACT", 500, "normal"), ("GOLDEN SHIELD", 500, "normal"), ("DOUBLE TOUCH", 800, "normal"), ("GOLDEN DRIBBLE", 5, "black"), ("ROYAL IMPACT", 10, "black"), ("GOO", 15, "black")],
        "Chris Prince": [("MUSCLE DEMON", 500, "normal"), ("DEMON SNIPE", 500, "normal"), ("LOGICAL SHOT", 500, "normal"), ("NO WAY", 800, "normal"), ("ILLOGICAL KNUCKLE BALL", 5, "black"), ("BICYCLE BLOCK", 10, "black"), ("MUSCLE DRIBBLE", 15, "black")],
        "Lavinho": [("RISING DANCE", 500, "normal"), ("BUTTERFLY DRIBBLE", 500, "normal"), ("GINGA STYLE", 500, "normal"), ("GINGA SHOT", 800, "normal"), ("BUTTERFLY COUNTER", 5, "black"), ("BUTTERFLY DANCE", 10, "black"), ("BUTTERFLY INTERCEPT", 15, "black")],
        "Mark Snuffy": [("RATIONAL DEFENSE", 500, "normal"), ("RATIONAL INTERCEPTION", 500, "normal"), ("PHOENIX DRIBBLING", 500, "normal"), ("EAGLE ILLUSION", 800, "normal"), ("TACTICAL VISION", 5, "black"), ("PHOENIX BLOCK", 10, "black"), ("FALL", 15, "black")],
        "Dada Silva": [("STRENGTH", 500, "normal"), ("POWER SHOT", 500, "normal"), ("TACKLE", 500, "normal"), ("AERIAL DUEL", 800, "normal"), ("GIANTS STRENGTH", 5, "black"), ("EARTH SHAKER", 10, "black"), ("TITAN", 15, "black")],
        "Pablo Cavasoz": [("HILUSION SHOT", 500, "normal"), ("RAINBOW PASS", 500, "normal"), ("ILUSION DRIBBLE", 500, "normal"), ("PENJICAL PASS", 800, "normal"), ("BLITZ STRIKE", 5, "black"), ("CURVE ILLUSION", 10, "black"), ("TOUCH COUNTER", 15, "black")],
        "Yoichi Isagi": [("DIRECT SHOT", 500, "normal"), ("FADEAWAY", 500, "normal"), ("META BLOCK", 500, "normal"), ("TWO GUN VOLLEY", 800, "normal"), ("LEFTY SHOT", 5, "black"), ("KING DEMON", 10, "black"), ("LAST PUZZLE", 15, "black")],
        "Vivian Hugo": [("Halu Pass", 500, "normal"), ("Second Best", 500, "normal"), ("Mechanic Dribble", 500, "normal"), ("Halu Block", 800, "normal"), ("Halu shot", 5, "black"), ("Obey Your Destiny", 10, "black"), ("Luck 1%", 15, "black")],
        "Bunny Iglesias": [("RABBIT JUMP", 500, "normal"), ("HE WANNA DIE", 500, "normal"), ("SCISSOR KICK", 500, "normal"), ("LOB PASS", 800, "normal"), ("RABBIT TRAP", 5, "black"), ("BARCHA STRIKER", 10, "black"), ("HERE IN THE AIR", 15, "black")],
        "Reo Mikage": [("PERFECT COPY", 500, "normal"), ("ITOSHI BROTHER COPY", 500, "normal"), ("DEFENSIVE MODE", 500, "normal"), ("OFFENSIVE MODE", 800, "normal"), ("CHAMELEON", 5, "black"), ("COPY", 10, "black"), ("NEO GYRO SHOT", 15, "black")],
        "Michael Kaiser": [("EMPEROR MOVE", 500, "normal"), ("LINGHINTG SHOT", 500, "normal"), ("EMPROR DRIBBLE", 500, "normal"), ("ROSE", 800, "normal"), ("BICYKLE IMPACT", 5, "black"), ("KAISER IMPACT", 10, "black"), ("MEGNUS IMPACT", 15, "black")],
        "Sae Itoshi": [("TURN", 500, "normal"), ("CRUVE PASS", 500, "normal"), ("NUTMEG", 500, "normal"), ("OFF BALANCE", 800, "normal"), ("CORNER SHOT", 5, "black"), ("CROSS MAGIC", 10, "black"), ("PERFECT PASS", 15, "black")],
        "Rin Itoshi": [("WATER DRIBBLE", 500, "normal"), ("CURVE SHOT", 500, "normal"), ("FULL BURST", 500, "normal"), ("BLIND SPOT SHOT", 800, "normal"), ("CRASHOUT", 5, "black"), ("ANHLIOT VOLLEY", 10, "black"), ("ANHILIOT", 15, "black")],
        "Don Lorenzo": [("ZOMBIE DRIBBLE", 500, "normal"), ("ZOMBIE DASH", 500, "normal"), ("ZOMBIE STEAL", 500, "normal"), ("GOLDEN DEFENSE", 800, "normal"), ("YO MICHAEL", 5, "black"), ("COUNTER ATTACK", 10, "black"), ("UNDEAD MODE", 15, "black")],
        "Teddy Knight": [("FLAIR NUTMEG", 500, "normal"), ("PARADO OF KNIGHT", 500, "normal"), ("SWORD CROSS", 500, "normal"), ("KNIGHT GUARD", 800, "normal"), ("DESTROY YOUR FACE", 5, "black"), ("ENGLAND BLITZ", 10, "black"), ("NUTMEG PASS", 15, "black")],
        "Ryusei Shidou": [("Dragon Shot", 500, "normal"), ("Dragon drive", 500, "normal"), ("Dragon Header", 500, "normal"), ("Dragon Run", 800, "normal"), ("Big bang Drive", 5, "black"), ("Demon Drive", 10, "black"), ("BEAST KING", 15, "black")],
        "Seishiro Nagi": [("Perfect Trap", 500, "normal"), ("Fake Shot", 500, "normal"), ("air Dribble", 500, "normal"), ("Juggling shot", 800, "normal"), ("Nice to meet you japan", 5, "black"), ("2 stage Fake volley", 10, "black"), ("5 stage Fake Volley", 15, "black")],
        "Shoei Barou": [("Lion Chop", 500, "normal"), ("King Dribble", 500, "normal"), ("predator Eye", 500, "normal"), ("King Shot", 800, "normal"), ("King Of The Jungle", 5, "black"), ("Your Light Is mine", 10, "black"), ("double Nutmeg", 15, "black")],
        "Lockhart": [("Iron Header", 500, "normal"), ("Iron Body Run", 500, "normal"), ("Body Block", 500, "normal"), ("Power Pass", 800, "normal"), ("Iron Heart", 5, "black"), ("England Striker", 10, "black"), ("Iron Man", 15, "black")],
        "Kenyu Yukimiya": [("LA BOBA", 500, "normal"), ("GOAL IN TIME", 500, "normal"), ("ELASTICO", 500, "normal"), ("GYRO SHOT", 800, "normal"), ("EMPEROR OF 1V1", 5, "black"), ("SWORD SCREW", 10, "black"), ("SWORD SCREW VOLLEY", 15, "black")],
        "Oliver Aiku": [("SNAKE CLEAR", 500, "normal"), ("LAST LINE", 500, "normal"), ("SNAKE BITE", 500, "normal"), ("SENSOR BLOCK", 800, "normal"), ("SNAKE COUNTER", 5, "black"), ("ZIG ZAG CROSS", 10, "black"), ("HEAD BLOCK", 15, "black")],
        "Rensuke Kunigami": [("Body Block", 500, "normal"), ("power Shot", 500, "normal"), ("Cyborg", 500, "normal"), ("Joker Card", 800, "normal"), ("Fallen Hero", 5, "black"), ("RUSH VOLLEY", 10, "black"), ("Joker", 15, "black")],
        "Jin Kiyora": [("BORDELINE PASS", 500, "normal"), ("KAY", 500, "normal"), ("Backspin shot", 500, "normal"), ("TO MAKE HIMSELF", 800, "normal"), ("TWISTER SHOT", 5, "black"), ("TWISTER PASS", 10, "black"), ("ACROBATIC SHOT", 15, "black")],
        "Meguru Bachira": [("Bon", 500, "normal"), ("Monster Dribble", 500, "normal"), ("Curve Pass", 500, "normal"), ("Bee Shot", 800, "normal"), ("Ginga Style x Monser", 5, "black"), ("Monster Trance", 10, "black"), ("I'll Make Dribbling my Ego", 15, "black")],
        "Hyoma Chigiri": [("Speedster", 500, "normal"), ("Accelerate", 500, "normal"), ("match In", 500, "normal"), ("i want to be best striker", 800, "normal"), ("44 panther Zone", 5, "black"), ("The Red Panther", 10, "black"), ("Blitz", 15, "black")],
        "Tabito Karasu": [("HAND DRIBBLE", 500, "normal"), ("CROW THEFT", 500, "normal"), ("RAVEN PASS", 500, "normal"), ("CROW SHOT", 800, "normal"), ("NEW GOAL METHOD", 5, "black"), ("ALRIGHT DATA ENTERED", 10, "black"), ("ALLOW ME TO DELIVER", 15, "black")],
        "Hiori Yo": [("ICE PASS", 500, "normal"), ("RAINBOW FLICK", 500, "normal"), ("SNOW SHOT", 500, "normal"), ("SNOW CUT", 800, "normal"), ("ONE MORE TIME", 5, "black"), ("NO LOOK PASS", 10, "black"), ("ICEVISION", 15, "black")],
        "Jyubei Aryu": [("FLYING CHEST TRAP", 500, "normal"), ("STYLISH BLOCK", 500, "normal"), ("IS MY TERRITORY", 500, "normal"), ("SCRAPTER TACKLE", 800, "normal"), ("AIR MARK", 5, "black"), ("WHAYYY", 10, "black"), ("TWIN TOWER", 15, "black")],
        "Gin Gagamaru": [("Scorpion", 500, "normal"), ("Diving Header", 500, "normal"), ("Fast Reaction", 500, "normal"), ("BEAST REFLEXES", 800, "normal"), ("Handstand", 5, "black"), ("Bear Claw", 10, "black"), ("DIVING SHOT", 15, "black")],
        "Shuto Sendo": [("Second Striker", 500, "normal"), ("Endless Stamina", 500, "normal"), ("Half Space Movement", 500, "normal"), ("Box to Box", 800, "normal"), ("Determination", 5, "black"), ("Sniper shot", 10, "black"), ("Counter Shot", 15, "black")],
        "Aoshi Tokimitsu": [("Agility", 500, "normal"), ("Immovable Physique", 500, "normal"), ("Shoulder Charge", 500, "normal"), ("Unlimited Stamina", 800, "normal"), ("Quickness", 5, "black"), ("Physical Strength", 10, "black"), ("Stamina", 15, "black")],
        "Gurimu Igarashi": [("Diving", 500, "normal"), ("Malicia Dribbling", 500, "normal"), ("Foul Drawing", 500, "normal"), ("Unyielding Spirit", 800, "normal"), ("Full Throttle Scissors", 5, "black"), ("It's Lights Out!", 10, "black"), ("Desperate Look", 15, "black")],
        "Otoya Eita": [("Stealth", 500, "normal"), ("Ninja Dribble", 500, "normal"), ("NINJA Move", 500, "normal"), ("WONG WONG WOHA", 800, "normal"), ("Ninja", 5, "black"), ("Blind-Spot Infiltration", 10, "black"), ("Shadow Striker", 15, "black")],
        "Tsurugi Zantetsu": [("Explosive Acceleration", 500, "normal"), ("Left-Foot Shooting", 500, "normal"), ("Double Wing Boost", 500, "normal"), ("Bullet Train Maglev", 800, "normal"), ("Jet Counter", 5, "black"), ("Quick Reactions", 10, "black"), ("Acceleration", 15, "black")],
        "Fukaku Gen": [("Physique", 500, "normal"), ("Reactions", 500, "normal"), ("Goalkeeping", 500, "normal"), ("Dropkick", 800, "normal"), ("Reflexes", 5, "black"), ("Shot Stopping", 10, "black"), ("Goal Protection", 15, "black")],
        "Kazuma Nio": [("Dominant Physique", 500, "normal"), ("Man Marking", 500, "normal"), ("Physical Defense", 500, "normal"), ("Pressing", 800, "normal"), ("Defensive Duels", 5, "black"), ("Tight Marking", 10, "black"), ("Defensive Positioning", 15, "black")],
        "Nijiro Nanase": [("Ambidexterity", 500, "normal"), ("Mirage Pass", 500, "normal"), ("Mirage Dribble", 500, "normal"), ("Adaptability", 800, "normal"), ("HOLY CRAP", 5, "black"), ("SO CLOSE", 10, "black"), ("DOG RIN", 15, "black")],
        "Ranze Kurona": [("CRODINATE", 500, "normal"), ("ZERO TURN SHOT", 500, "normal"), ("RAZOR CROSS", 500, "normal"), ("RAZOR DRIBBLE", 800, "normal"), ("PLANET HOTLINE", 5, "black"), ("ZERO DEGREE PASS", 10, "black"), ("LETS GO ISAGI", 15, "black")]
    }
    
    # گرفتن مهارت‌های کارت یا حالت پیش‌فرض
    skills = skills_db.get(char_name, [
        (char['technique'], 500, "normal"), ("POWER SHOT", 500, "normal"), 
        ("QUICK DRIBBLE", 500, "normal"), ("DEFENSIVE STANCE", 800, "normal"), 
        ("BEAST MODE", 5, "black"), ("ULTIMATE FINISH", 10, "black"), ("DOMAIN EXPANSION", 15, "black")
    ])
    
    unlocked = get_unlocked_skills(callback.from_user.id)
    
    # باز کردن خودکار ۴ مهارت اول
    for i in range(4):
        if i < len(skills):
            skill_name, cost, currency = skills[i]
            if skill_name not in unlocked:
                unlock_skill_db(callback.from_user.id, skill_name, currency)
                
    unlocked = get_unlocked_skills(callback.from_user.id)
    
    ascend_text = ""
    if char['rarity'] == 'Rare': ascend_text = "\n🔼 **ارتقا به Epic:** نیازمند ۳ کارت Rare + ۳۰۰ سکه"
    elif char['rarity'] == 'Epic': ascend_text = "\n🔼 **ارتقا به Legendary:** نیازمند ۳ کارت Epic + ۵۰۰ سکه"
    
    kb_buttons = []
    for skill_name, cost, currency in skills:
        if skill_name in unlocked:
            kb_buttons.append([InlineKeyboardButton(text=f"✅ {skill_name}", callback_data="none")])
        else:
            if currency == "normal":
                kb_buttons.append([InlineKeyboardButton(text=f"UNLOCK: {skill_name} · {cost} 🪙", callback_data=f"unlock_{skill_name.replace(' ', '_')}_{cost}_normal")])
            else:
                kb_buttons.append([InlineKeyboardButton(text=f"🔒 UNLOCK: {skill_name} · {cost} 🖤", callback_data=f"unlock_{skill_name.replace(' ', '_')}_{cost}_black")])
    
    if ascend_text:
        kb_buttons.append([InlineKeyboardButton(text="🔼 ASCEND CARD", callback_data=f"ascend_{char_id}")])
        
    kb_buttons.append([InlineKeyboardButton(text="🔙 بازگشت به لیست کارت‌ها", callback_data="free_mode")])
    await safe_edit_message(callback, text + ascend_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("ascend_"))
async def do_ascend(callback: types.CallbackQuery):
    char_id = int(callback.data.split("_")[1])
    res = ascend_card(callback.from_user.id, char_id)
    if res == "success": await callback.answer("🎉 کارت با موفقیت ارتقا یافت!", show_alert=True)
    elif res == "no_cards": await callback.answer("❌ کارت کافی برای سوزوندن نداری!", show_alert=True)
    elif res == "no_coins": await callback.answer("❌ سکه کافی نداری!", show_alert=True)
    else: await callback.answer("❌ خطا!", show_alert=True)
    await show_char_skills(callback)

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
    text = (f"🏋️ **تمرین**\n-------------------------\n😰 خستگی: {player['fatigue']}٪\n😰 فشار: {player['pressure']}٪\n🧘 روان: {player['sanity']}٪\n🪙 سکه: {player['normal_coins']}\n🎯 نقاط تمرین: {player.get('training_points', 0)}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛌 REST (30 Coins)", callback_data="action_rest")], 
        [InlineKeyboardButton(text="🏃 TRAIN (50 Coins)", callback_data="action_train")],
        [InlineKeyboardButton(text="🎯 تمرین اختصاصی (صرف نقطه)", callback_data="special_training")],
        [InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]
    ])
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
    msg = f"🏃 +{res['xp']} XP و +۱ نقطه تمرین!"
    if res['level_up']: msg += f"\n🌟 لول {res['new_level']}!"
    try: update_achievement_progress(callback.from_user.id, "train_count")
    except: pass
    await callback.answer(msg, show_alert=True)
    await training_menu(callback)

@dp.callback_query(F.data == "special_training")
async def special_training(callback: types.CallbackQuery):
    team = get_player_team(callback.from_user.id)
    if not team: return await callback.answer("❌ تیم خالیه!", show_alert=True)
    kb_buttons = [[InlineKeyboardButton(text=f"🃏 {c['name']}", callback_data=f"sp_train_{c['char_id']}")] for c in team]
    kb_buttons.append([InlineKeyboardButton(text="🔙 BACK", callback_data="training_menu")])
    await safe_edit_message(callback, "🎯 **کدوم کارت رو می‌خوای تمرین بدی؟**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("sp_train_"))
async def sp_train_char(callback: types.CallbackQuery):
    char_id = int(callback.data.split("_")[2])
    player = get_player(callback.from_user.id)
    if player.get('training_points', 0) <= 0:
        return await callback.answer("❌ نقطه تمرین نداری!", show_alert=True)
    text = "🎯 **نقطه تمرین رو کجا خرج کنم؟**\n(هر بار ۱ نقطه)"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💥 افزایش دمیج (+10)", callback_data=f"up_dmg_{char_id}")],
        [InlineKeyboardButton(text="⏳ کاهش کول‌داون (-2s)", callback_data=f"up_cd_{char_id}")],
        [InlineKeyboardButton(text="🔙 BACK", callback_data="special_training")]
    ])
    await safe_edit_message(callback, text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("up_dmg_"))
async def up_dmg(callback: types.CallbackQuery):
    char_id = int(callback.data.split("_")[2])
    res = upgrade_card_stat(callback.from_user.id, char_id, "damage")
    if res == "success": await callback.answer("✅ دمیج کارت +10 شد!", show_alert=True)
    else: await callback.answer("❌ خطا!", show_alert=True)
    await special_training(callback)

@dp.callback_query(F.data.startswith("up_cd_"))
async def up_cd(callback: types.CallbackQuery):
    char_id = int(callback.data.split("_")[2])
    res = upgrade_card_stat(callback.from_user.id, char_id, "cooldown")
    if res == "success": await callback.answer("✅ کول‌داون کارت -2 ثانیه شد!", show_alert=True)
    else: await callback.answer("❌ خطا!", show_alert=True)
    await special_training(callback)

@dp.callback_query(F.data == "black_market")
async def black_market(callback: types.CallbackQuery):
    player = get_player(callback.from_user.id)
    text = f"🖤 **بازار سیاه**\n\nسکه سیاه شما: {player['black_coins']}\n\nاینجا می‌تونی با سکه سیاه، آیتم‌های خاص بخری:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟️ بلیط گاچا لجندری (50 🖤)", callback_data="buy_legendary_ticket")],
        [InlineKeyboardButton(text="💪 افزایش قدرت کل تیم (+10) (30 🖤)", callback_data="buy_power_boost")],
        [InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]
    ])
    await safe_edit_message(callback, text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "buy_legendary_ticket")
async def buy_legendary_ticket(callback: types.CallbackQuery):
    result = buy_from_black_market(callback.from_user.id, "legendary_ticket")
    if result == "no_coins": return await callback.answer("❌ سکه سیاه کافی نداری!", show_alert=True)
    await callback.answer("✅ بلیط لجندری خریداری شد!", show_alert=True)
    await black_market(callback)

@dp.callback_query(F.data == "buy_power_boost")
async def buy_power_boost(callback: types.CallbackQuery):
    result = buy_from_black_market(callback.from_user.id, "power_boost")
    if result == "no_coins": return await callback.answer("❌ سکه سیاه کافی نداری!", show_alert=True)
    await callback.answer("✅ قدرت تیمت افزایش پیدا کرد!", show_alert=True)
    await black_market(callback)

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

@dp.callback_query(F.data == "achievements_menu")
async def achievements_menu(callback: types.CallbackQuery):
    achs = get_achievements(callback.from_user.id)
    text = "🏅 **دستاوردهای شما**\n-------------------------\n"
    if not achs:
        text += "هنوز هیچ دستاوردی ندارید. بازی کنید تا باز شوند!"
    else:
        for a in achs:
            status = "✅" if a['completed'] else f"⏳ ({a['progress']}/{a['target']})"
            text += f"{a['icon']} {a['name']}: {status}\n"
    
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
        try: update_achievement_progress(callback.from_user.id, "boss_kills")
        except: pass
        text = f"🎉 **پیروزی بر {result['boss_name']}!**\n-------------------------\nقدرت تیم تو: {result['player_power']:.1f}\nقدرت باس: {result['boss_power']}\n\n🖤 +{result['black']} سکه سیاه\n🪙 +{result['normal']} سکه عادی"
    else:
        text = f"💀 **شکست در برابر {result['boss_name']}!**\n-------------------------\nقدرت تیم تو: {result['player_power']:.1f}\nقدرت باس: {result['boss_power']}\n\nتیمت رو قوی‌تر کن و دوباره برگرد."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ FIGHT AGAIN", callback_data=f"fight_custom_{event_id}")], [InlineKeyboardButton(text="🔙 MAIN MENU", callback_data="back_to_main")]])
    await safe_edit_message(callback, text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "trade_menu")
async def trade_menu(callback: types.CallbackQuery):
    text = "🔄 **سیستم ترید**\n\nبرای شروع ترید، روی پیام کاربر مورد نظر **ریپلای** کن و بنویس:\n`ترید`"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_main")]])
    await safe_edit_message(callback, text, reply_markup=kb)
    await callback.answer()

@dp.message(F.text)
async def text_match_action(message: types.Message, state: FSMContext):
    if message.text.startswith("/"): return
    if not message.reply_to_message: return
    if message.content_type != "text": return
    
    text_lower = message.text.strip().lower()
    opponent_name = message.reply_to_message.from_user.first_name or "حریف"
    opponent_id = message.reply_to_message.from_user.id
    
    if text_lower == "چالش":
        player = get_player(message.from_user.id)
        if not player: return
        target = get_player(opponent_id)
        if not target: return
        bet_amount = 50
        res = start_bet_duel(message.from_user.id, opponent_id, bet_amount)
        if res == "no_coins":
            return await message.reply("❌ یکی از طرفین سکه کافی برای شرط‌بندی ۵۰ سکه‌ای رو نداره!")
        text = (f"⚔️ **دوئل شرطی!** ⚔️\n\n**{message.from_user.first_name}** و **{opponent_name}**\nهر کدوم ۵۰ سکه گذاشتن وسط!\n\n🏆 **برنده ۱۰۰ سکه می‌بره!**\n⏳ برای شروع، یکی از شما تکنیک بزنه!")
        await message.reply(text)
        return
        
    if text_lower == "نبرد دوستانه":
        text = (f"🤝 **نبرد دوستانه!** 🤝\n\n**{message.from_user.first_name}** و **{opponent_name}**\nاین یک نبرد تمرینی است. سکه‌ای رد و بدل نمیشه.\nفقط برای اثبات قدرت! 💪")
        await message.reply(text)
        return

    if text_lower == "ترید":
        await message.answer("🔄 سیستم ترید فعلا در حال توسعه است. (به زودی کارت‌ها معاوضه میشن!)")
        return
        
    player = get_player(message.from_user.id)
    if not player: return
    team = get_player_team(message.from_user.id)
    if not team: return
    valid_techniques = [char['technique'].lower() for char in team]
    unlocked = get_unlocked_skills(message.from_user.id)
    valid_skills = [skill.lower() for skill in unlocked.keys()]
    if text_lower not in valid_techniques and text_lower not in valid_skills: return
    
    result = attack_with_technique(message.from_user.id, text_lower, opponent_name, opponent_id)
    if result.startswith("cooldown_"):
        remaining = result.split("_")[1]
        return await message.answer(f"⏳ **صبر کن!**\nتا **{remaining}** ثانیه دیگه نمی‌تونی از این تکنیک استفاده کنی.")
    elif result == "ego_broken":
        return await message.answer("💀 **اِگوی تو شکسته شده!**\nباید ۱۵ دقیقه صبر کنی تا اِگوت دوباره پر بشه.")
    elif result == "no_team":
        return await message.answer("❌ اول باید از گاچا کارت بگیری!")
    elif result != "no_technique":
        try: update_achievement_progress(message.from_user.id, "attack_count")
        except: pass
        await message.reply(result, parse_mode="Markdown")

@dp.message(F.text.startswith("give "))
async def handle_give_coins(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    if not message.reply_to_message: return await message.answer("⚠️ باید روی پیام کاربر ریپلای کنی!")
    target_id = message.reply_to_message.from_user.id
    try: amount = int(message.text.split()[1])
    except: return await message.answer("⚠️ مقدار سکه رو درست وارد کن.")
    admin_give_coins(target_id, amount, "normal")
    await message.answer(f"✅ {amount} سکه عادی به کاربر داده شد!")

@dp.message(F.text.startswith("giveblack "))
async def handle_give_black_coins(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    if not message.reply_to_message: return await message.answer("⚠️ باید روی پیام کاربر ریپلای کنی!")
    target_id = message.reply_to_message.from_user.id
    try: amount = int(message.text.split()[1])
    except: return await message.answer("⚠️ مقدار سکه رو درست وارد کن.")
    admin_give_coins(target_id, amount, "black")
    await message.answer(f"✅ {amount} سکه سیاه به کاربر داده شد!")

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
    waiting_for_skin_char = State()
    waiting_for_skin_image = State()

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != OWNER_ID: 
        return await message.answer("⛔ دسترسی نداری.")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ ADD NEW CARD", callback_data="admin_add_card")],
        [InlineKeyboardButton(text="🖼️ CHANGE MENU IMAGE", callback_data="admin_set_image")],
        [InlineKeyboardButton(text="🖼️ CHANGE CHARACTER IMAGE", callback_data="admin_change_char_image")],
        [InlineKeyboardButton(text="🖼️ ADD SKIN", callback_data="admin_add_skin")],
        [InlineKeyboardButton(text="🔥 CREATE EVENT", callback_data="admin_create_event")],
        [InlineKeyboardButton(text="🌧️ DRAMATIC EVENTS", callback_data="admin_set_event")],
        [InlineKeyboardButton(text="🪙 GIVE COINS (Reply)", callback_data="admin_give_coins")],
        [InlineKeyboardButton(text="🖤 GIVE BLACK COINS (Reply)", callback_data="admin_give_black_coins")],
        [InlineKeyboardButton(text="🚫 BAN USER (Reply)", callback_data="admin_ban")],
        [InlineKeyboardButton(text="🔙 CLOSE", callback_data="back_to_main")]
    ])
    await message.answer("👑 **پنل مالک**", reply_markup=kb, parse_mode="Markdown")

# ... (بقیه کدهای ادمین که توی پیام قبلی فرستادم رو هم همینجا زیرش پیست کن) ...

async def main():
    init_db()
    seed_characters()
    print("🚀 ربات روشن شد...")
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())