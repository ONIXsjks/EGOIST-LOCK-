import json
import random
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

DATABASE_URL = "postgresql://postgres.hjynfqrsyxjibchmghsg:PH6t8bseGQrPp9el@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    print("✅ اتصال به دیتابیس برقرار است.")
    conn = get_db_connection(); cur = conn.cursor()
    
    cur.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id BIGINT PRIMARY KEY, username TEXT, level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0,
        ego INTEGER DEFAULT 100, sanity INTEGER DEFAULT 100, fatigue INTEGER DEFAULT 0, pressure INTEGER DEFAULT 0,
        black_coins INTEGER DEFAULT 0, normal_coins INTEGER DEFAULT 100, team_json JSONB DEFAULT '[]'::jsonb,
        current_match_state JSONB DEFAULT NULL, in_shadow_league BOOLEAN DEFAULT FALSE, shadow_wins INTEGER DEFAULT 0,
        ego_broken_at TIMESTAMPTZ DEFAULT NULL, last_attack_at TIMESTAMPTZ DEFAULT NULL, 
        last_match_action_at TIMESTAMPTZ DEFAULT NULL, current_ego INTEGER DEFAULT 2000, last_ego_update TIMESTAMPTZ DEFAULT NOW(),
        main_char_id INTEGER DEFAULT NULL
    )''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS characters (
        char_id SERIAL PRIMARY KEY, name TEXT, position TEXT, technique TEXT,
        base_power INTEGER, rarity TEXT, is_cursed BOOLEAN DEFAULT FALSE, synergy_tag TEXT, image_url TEXT
    )''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS player_damage (user_id BIGINT, char_id INTEGER, damage_received INTEGER DEFAULT 0, PRIMARY KEY (user_id, char_id))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS player_skills (user_id BIGINT, skill_name TEXT, is_unlocked BOOLEAN DEFAULT FALSE, currency TEXT, PRIMARY KEY (user_id, skill_name))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS bot_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS active_events (event_id SERIAL PRIMARY KEY, boss_name TEXT, boss_power INTEGER, reward_black INTEGER, reward_normal INTEGER, is_active BOOLEAN DEFAULT TRUE)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS coach_missions (mission_id SERIAL PRIMARY KEY, player_id BIGINT, mission_type TEXT, target_name TEXT, is_active BOOLEAN DEFAULT TRUE, is_completed BOOLEAN DEFAULT FALSE)''')
    
    # ستون‌های جدید
    cur.execute('ALTER TABLE players ADD COLUMN IF NOT EXISTS flow_until TIMESTAMPTZ')
    cur.execute('ALTER TABLE players ADD COLUMN IF NOT EXISTS free_gacha_ticket INTEGER DEFAULT 0')
    cur.execute('ALTER TABLE players ADD COLUMN IF NOT EXISTS training_points INTEGER DEFAULT 0')
    cur.execute('ALTER TABLE players ADD COLUMN IF NOT EXISTS skin_inventory JSONB DEFAULT \'{}\'::jsonb')
    cur.execute('ALTER TABLE players ADD COLUMN IF NOT EXISTS active_skin JSONB DEFAULT \'{}\'::jsonb')
    
    cur.execute('ALTER TABLE characters ADD COLUMN IF NOT EXISTS bonus_damage INTEGER DEFAULT 0')
    cur.execute('ALTER TABLE characters ADD COLUMN IF NOT EXISTS cooldown_reduction INTEGER DEFAULT 0')
    
    conn.commit(); cur.close(); conn.close()

def init_new_systems():
    """ساخت جدول‌های مربوط به سیستم‌های جدید (دستاوردها، ترید و...)"""
    conn = get_db_connection(); cur = conn.cursor()
    
    # جدول دستاوردها
    cur.execute('''CREATE TABLE IF NOT EXISTS achievements (
        ach_id TEXT PRIMARY KEY, name TEXT, description TEXT, icon TEXT, target INTEGER DEFAULT 1, reward_coins INTEGER DEFAULT 0
    )''')
    
    # جدول دستاوردهای کاربران
    cur.execute('''CREATE TABLE IF NOT EXISTS player_achievements (
        user_id BIGINT, ach_id TEXT, progress INTEGER DEFAULT 0, completed BOOLEAN DEFAULT FALSE,
        PRIMARY KEY (user_id, ach_id)
    )''')
    
    # جدول پیشنهادات ترید
    cur.execute('''CREATE TABLE IF NOT EXISTS trade_offers (
        offer_id SERIAL PRIMARY KEY, sender_id BIGINT, receiver_id BIGINT,
        sender_char_id INTEGER, receiver_char_id INTEGER, status TEXT DEFAULT 'pending',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )''')
    
    # جدول باس‌های افسانه‌ای
    cur.execute('''CREATE TABLE IF NOT EXISTS legendary_bosses (
        boss_id SERIAL PRIMARY KEY, name TEXT, power INTEGER, hp INTEGER DEFAULT 1000,
        reward_black INTEGER, reward_normal INTEGER, is_active BOOLEAN DEFAULT TRUE,
        spawned_at TIMESTAMPTZ DEFAULT NOW()
    )''')
    
    # اضافه کردن دستاوردهای پیش‌فرض (اگر وجود نداشته باشند)
    default_achievements = [
        ('first_blood', 'اولین خون', 'اولین پیروزی در حمله', '🥇', 1, 100),
        ('boss_hunter', 'شکارچی باس', 'کشتن ۵ باس', '💀', 5, 500),
        ('collector', 'کلکسیونر', 'داشتن ۱۰ کارت', '🎴', 10, 300),
        ('rich_man', 'پولدار', 'رسیدن به ۱۰۰۰ سکه', '💰', 1000, 200),
        ('gacha_addict', 'معتاد گاچا', '۵۰ بار گاچا زدن', '🎰', 50, 250),
    ]
    for ach in default_achievements:
        cur.execute('INSERT INTO achievements (ach_id, name, description, icon, target, reward_coins) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (ach_id) DO NOTHING', ach)
        
    conn.commit(); cur.close(); conn.close()

def get_player(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT * FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone(); cur.close(); conn.close(); return player

def create_player(user_id, username):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT * FROM players WHERE user_id = %s', (user_id,))
    if not cur.fetchone():
        cur.execute('INSERT INTO players (user_id, username) VALUES (%s, %s)', (user_id, username))
        conn.commit()
    cur.close(); conn.close()

def save_setting(key, value):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO bot_settings (setting_key, setting_value) VALUES (%s, %s) ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value', (key, value))
    conn.commit(); cur.close(); conn.close()

def get_setting(key):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT setting_value FROM bot_settings WHERE setting_key = %s', (key,))
    res = cur.fetchone(); cur.close(); conn.close(); return res['setting_value'] if res else None
def add_achievement(user_id, ach_id, progress=1):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT progress, completed FROM player_achievements WHERE user_id = %s AND ach_id = %s', (user_id, ach_id))
    row = cur.fetchone()
    if not row:
        cur.execute('INSERT INTO player_achievements (user_id, ach_id, progress) VALUES (%s, %s, %s)', (user_id, ach_id, progress))
    else:
        new_prog = row['progress'] + progress
        cur.execute('UPDATE player_achievements SET progress = %s WHERE user_id = %s AND ach_id = %s', (new_prog, user_id, ach_id))
    conn.commit(); cur.close(); conn.close()

def update_achievement_progress(user_id, ach_id, amount=1):
    # این تابع برای افزایش پیشرفت است
    add_achievement(user_id, ach_id, amount)
    check_achievement_completion(user_id, ach_id)

def check_achievement_completion(user_id, ach_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT target, reward_coins FROM achievements WHERE ach_id = %s', (ach_id,))
    ach = cur.fetchone()
    cur.execute('SELECT progress, completed FROM player_achievements WHERE user_id = %s AND ach_id = %s', (user_id, ach_id))
    p_ach = cur.fetchone()
    
    if ach and p_ach and not p_ach['completed'] and p_ach['progress'] >= ach['target']:
        cur.execute('UPDATE player_achievements SET completed = TRUE WHERE user_id = %s AND ach_id = %s', (user_id, ach_id))
        cur.execute('UPDATE players SET normal_coins = normal_coins + %s WHERE user_id = %s', (ach['reward_coins'], user_id))
        conn.commit()
    cur.close(); conn.close()

def get_achievements(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('''
        SELECT a.ach_id, a.name, a.icon, a.target, a.reward_coins, 
               COALESCE(pa.progress, 0) as progress, COALESCE(pa.completed, FALSE) as completed
        FROM achievements a
        LEFT JOIN player_achievements pa ON a.ach_id = pa.ach_id AND pa.user_id = %s
    ''', (user_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]

def check_dream_team(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or not player['team_json'] or len(player['team_json']) < 3: 
        conn.close(); return None
        
    cur.execute('SELECT name, synergy_tag FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
    chars = cur.fetchall()
    tags = [c['synergy_tag'] for c in chars]
    cur.close(); conn.close()
    
    # تیم Z
    if tags.count('isagi') >= 2 and 'bachira' in tags and 'nagi' in tags:
        return {"name": "تیم Z (ایساگی، باچیرا، ناگی)", "bonus": 20}
    # تیم باستارد مونشن
    if tags.count('kaiser') >= 1 and tags.count('ness') >= 1:
        return {"name": "باستارد مونشن (کایزر، نس)", "bonus": 15}
    # ترکیب ژاپنی
    if tags.count('isagi') >= 2 or tags.count('bachira') >= 2:
        return {"name": "حمله ترکیبی ژاپنی", "bonus": 10}
    
    return None

def ascend_card(user_id, char_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT team_json, normal_coins FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    
    if not player or char_id not in player['team_json']: conn.close(); return "not_in_team"
    
    cur.execute('SELECT rarity FROM characters WHERE char_id = %s', (char_id,))
    char = cur.fetchone()
    rarity = char['rarity']
    
    if rarity == 'Legendary': conn.close(); return "max_rarity"
    elif rarity == 'Epic': cost = 500; needed_rarity = 'Epic'
    else: cost = 300; needed_rarity = 'Rare'
    
    if player['normal_coins'] < cost: conn.close(); return "no_coins"
    
    # پیدا کردن کارت‌های هم‌رده برای سوزاندن
    cur.execute('SELECT char_id FROM characters WHERE rarity = %s AND char_id != %s AND char_id = ANY(%s) LIMIT 3', (needed_rarity, char_id, player['team_json']))
    burn_cards = [row['char_id'] for row in cur.fetchall()]
    
    if len(burn_cards) < 3: conn.close(); return "no_cards"
    
    # حذف کارت‌های سوخته
    team = player['team_json']
    for c in burn_cards: team.remove(c)
    
    new_rarity = 'Legendary' if rarity == 'Epic' else 'Epic'
    cur.execute('UPDATE characters SET rarity = %s, base_power = base_power + 20 WHERE char_id = %s', (new_rarity, char_id))
    cur.execute('UPDATE players SET team_json = %s, normal_coins = normal_coins - %s WHERE user_id = %s', (json.dumps(team), cost, user_id))
    
    conn.commit(); cur.close(); conn.close()
    return "success"

def add_skin_to_inventory(user_id, char_id, skin_file_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT skin_inventory FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    inv = player['skin_inventory'] if player['skin_inventory'] else {}
    inv[str(char_id)] = skin_file_id
    cur.execute('UPDATE players SET skin_inventory = %s WHERE user_id = %s', (json.dumps(inv), user_id))
    conn.commit(); cur.close(); conn.close()
    return "success"

def set_active_skin(user_id, char_id, skin_file_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT active_skin FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    active = player['active_skin'] if player['active_skin'] else {}
    active[str(char_id)] = skin_file_id
    cur.execute('UPDATE players SET active_skin = %s WHERE user_id = %s', (json.dumps(active), user_id))
    conn.commit(); cur.close(); conn.close()
    return "success"
def upgrade_card_duplicate(user_id, char_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or char_id not in player['team_json']:
        conn.close(); return "not_in_team"
    cur.execute('UPDATE characters SET base_power = base_power + 5 WHERE char_id = %s', (char_id,))
    team = player['team_json']
    team.remove(char_id) 
    cur.execute('UPDATE players SET team_json = %s WHERE user_id = %s', (json.dumps(team), user_id))
    conn.commit(); cur.close(); conn.close()
    return "success"

def buy_from_black_market(user_id, item_type):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT black_coins, team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if item_type == "legendary_ticket":
        cost = 50
        if player['black_coins'] < cost: conn.close(); return "no_coins"
        cur.execute('UPDATE players SET black_coins = black_coins - %s, free_gacha_ticket = free_gacha_ticket + 1 WHERE user_id = %s', (cost, user_id))
        conn.commit(); conn.close(); return "success_legendary_ticket"
    elif item_type == "power_boost":
        cost = 30
        if player['black_coins'] < cost: conn.close(); return "no_coins"
        if player['team_json']:
            cur.execute('UPDATE characters SET base_power = base_power + 10 WHERE char_id = ANY(%s)', (player['team_json'],))
        cur.execute('UPDATE players SET black_coins = black_coins - %s WHERE user_id = %s', (cost, user_id))
        conn.commit(); conn.close(); return "success_power_boost"
    conn.close(); return "invalid_item"

def trigger_flow_state(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE players SET flow_until = NOW() + interval \'30 seconds\' WHERE user_id = %s', (user_id,))
    conn.commit(); cur.close(); conn.close()
    return "flow_activated"

def check_flow_state(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT flow_until FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if player and player['flow_until']:
        if player['flow_until'] > datetime.now(player['flow_until'].tzinfo):
            conn.close(); return True
    conn.close(); return False

def add_training_point(user_id, amount=1):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE players SET training_points = training_points + %s WHERE user_id = %s', (amount, user_id))
    conn.commit(); cur.close(); conn.close()
    return "success"

def upgrade_card_stat(user_id, char_id, stat_type):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT training_points FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or player['training_points'] <= 0: conn.close(); return "no_points"
    if stat_type == "damage":
        cur.execute('UPDATE characters SET bonus_damage = bonus_damage + 10 WHERE char_id = %s', (char_id,))
    elif stat_type == "cooldown":
        cur.execute('UPDATE characters SET cooldown_reduction = cooldown_reduction + 2 WHERE char_id = %s', (char_id,))
    cur.execute('UPDATE players SET training_points = training_points - 1 WHERE user_id = %s', (user_id,))
    conn.commit(); cur.close(); conn.close()
    return "success"

def admin_give_coins(user_id, amount, coin_type="normal"):
    conn = get_db_connection(); cur = conn.cursor()
    if coin_type == "normal":
        cur.execute('UPDATE players SET normal_coins = normal_coins + %s WHERE user_id = %s', (amount, user_id))
    else:
        cur.execute('UPDATE players SET black_coins = black_coins + %s WHERE user_id = %s', (amount, user_id))
    conn.commit(); cur.close(); conn.close()
    return "success"

def set_global_event(event_type, duration_minutes):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO bot_settings (setting_key, setting_value) VALUES ('global_event', %s) ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value", (json.dumps({"type": event_type, "end_time": (datetime.now() + timedelta(minutes=duration_minutes)).isoformat()}),))
    conn.commit(); cur.close(); conn.close()

def get_global_event():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT setting_value FROM bot_settings WHERE setting_key = 'global_event'")
    res = cur.fetchone(); cur.close(); conn.close()
    if res:
        event = json.loads(res['setting_value'])
        if datetime.fromisoformat(event['end_time']) > datetime.now():
            return event
    return None

def start_bet_duel(attacker_id, defender_id, amount):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT normal_coins FROM players WHERE user_id IN (%s, %s)', (attacker_id, defender_id))
    players = cur.fetchall()
    if len(players) < 2 or any(p['normal_coins'] < amount for p in players):
        conn.close(); return "no_coins"
    cur.execute('UPDATE players SET normal_coins = normal_coins - %s WHERE user_id IN (%s, %s)', (amount, attacker_id, defender_id))
    conn.commit(); cur.close(); conn.close()
    return "success"

def resolve_bet_duel(winner_id, loser_id, amount):
    conn = get_db_connection(); cur = conn.cursor()
    total_prize = amount * 2
    cur.execute('UPDATE players SET normal_coins = normal_coins + %s WHERE user_id = %s', (total_prize, winner_id))
    conn.commit(); cur.close(); conn.close()
    return "success"

def attack_with_technique(user_id, technique_name, opponent_name, opponent_id):
    check_ego_recovery_all()
    conn = get_db_connection(); cur = conn.cursor()
    
    cur.execute('SELECT current_ego, team_json, xp, normal_coins, level, last_attack_at FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    
    if not player or player['current_ego'] <= 0:
        conn.close(); return "ego_broken"

    cur.execute('SELECT name, technique, base_power, rarity, bonus_damage, cooldown_reduction FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
    team_chars = cur.fetchall()
    unlocked = get_unlocked_skills(user_id)
    
    chosen_char = None
    matched_skill_name = None
    
    for char in team_chars:
        if char['technique'].lower() == technique_name.lower():
            chosen_char = char; matched_skill_name = char['technique']; break
    if not chosen_char:
        for skill_name, currency in unlocked.items():
            if skill_name.lower() == technique_name.lower():
                chosen_char = team_chars[0]; matched_skill_name = skill_name; break
                
    if not chosen_char:
        conn.close(); return "no_technique"

    cur.execute('SELECT current_ego FROM players WHERE user_id = %s', (opponent_id,))
    opponent_data = cur.fetchone()
    opponent_current_ego = opponent_data['current_ego'] if opponent_data else 2000

    currency_type = "normal"
    if matched_skill_name in unlocked:
        currency_type = unlocked[matched_skill_name]

    rarity = chosen_char['rarity']
    if rarity == 'Legendary': min_dmg, max_dmg = (300, 400) if currency_type == "black" else (200, 250)
    elif rarity == 'Epic': min_dmg, max_dmg = (220, 300) if currency_type == "black" else (150, 190)
    else: min_dmg, max_dmg = (180, 250) if currency_type == "black" else (100, 150)

    # اعمال آپگرید تمرین اختصاصی
    min_dmg += chosen_char['bonus_damage']; max_dmg += chosen_char['bonus_damage']

    # اعمال بونوس تیم رویایی
    dream_bonus = check_dream_team(user_id)
    if dream_bonus:
        min_dmg = int(min_dmg * (1 + dream_bonus['bonus'] / 100))
        max_dmg = int(max_dmg * (1 + dream_bonus['bonus'] / 100))

    # اعمال رویداد دراماتیک
    event = get_global_event()
    if event and event['type'] == 'rain_of_goals':
        min_dmg = int(min_dmg * 1.2); max_dmg = int(max_dmg * 1.2)

    is_flow = check_flow_state(user_id)
    if is_flow:
        min_dmg *= 2; max_dmg *= 2

    if currency_type == "black": cooldown_sec = 30
    elif matched_skill_name != chosen_char['technique']: cooldown_sec = 15
    else: cooldown_sec = 5
    
    cooldown_sec = max(1, cooldown_sec - chosen_char['cooldown_reduction'])

    if player['last_attack_at']:
        time_passed = datetime.now(player['last_attack_at'].tzinfo) - player['last_attack_at']
        if time_passed.total_seconds() < cooldown_sec:
            remaining = cooldown_sec - int(time_passed.total_seconds())
            conn.close(); return f"cooldown_{remaining}"

    damage = random.randint(min_dmg, max_dmg)
    new_opponent_ego = max(0, opponent_current_ego - damage)
    new_player_ego = max(0, player['current_ego'] - 10)

    earned_xp = random.randint(1, 5)
    earned_coins = random.randint(7, 15)

    flow_activated = False
    if new_opponent_ego == 0:
        trigger_flow_state(opponent_id)
        flow_activated = True
        update_achievement_progress(user_id, "first_blood")

    cur.execute('UPDATE players SET current_ego = %s, xp = xp + %s, normal_coins = normal_coins + %s, last_attack_at = %s, last_ego_update = %s WHERE user_id = %s', 
                (new_player_ego, earned_xp, earned_coins, datetime.now(), datetime.now(), user_id))
    
    cur.execute('UPDATE players SET current_ego = %s, last_ego_update = %s WHERE user_id = %s', (new_opponent_ego, datetime.now(), opponent_id))

    conn.commit(); cur.close(); conn.close()
    
    attack_texts = [
        f"⚡ **{chosen_char['name']}** با سرعت برق و باد حرکت کرد!",
        f"🔥 **{chosen_char['name']}** یه حرکت انفجاری زد!",
        f"💨 **{chosen_char['name']}** انگار از قبل می‌دونست کجا می‌خواد بره!",
        f"👁️ **{chosen_char['name']}** با دید مسدودکننده‌اش، دفاع حریف رو شکافت!",
        f"🎯 **{chosen_char['name']}** دقیقاً به نقطه‌ی کور حریف زد!"
    ]
    
    defend_texts = [
        f"💥 **{opponent_name}** کاملاً غافلگیر شد!",
        f"😱 **{opponent_name}** اصلاً فرصت واکنش نداشت!",
        f"🩸 **{opponent_name}** به سختی تعادلش رو حفظ کرد!",
        f"🛡️ دفاع **{opponent_name}** مثل کاغذ پاره شد!",
        f"😵 **{opponent_name}** گیج شد و عقب رفت!"
    ]
    
    flow_text = "\n\n🔥 **FLOW STATE!** 🔥\n" + f"**{opponent_name}** اِگوش شکست و وارد حالت فلو شد!" if flow_activated else ""
    flow_text_attacker = "\n\n🌟 **شما در حالت فلو هستید!** دمیج شما دوبرابر شد!" if is_flow else ""
    event_text = "\n\n🌧️ **باران گل فعال است!** (دمیج ۲۰٪ افزایش یافت)" if event and event['type'] == 'rain_of_goals' else ""
    dream_text = f"\n\n👑 **بونوس تیم رویایی:** {dream_bonus['name']} (+{dream_bonus['bonus']}٪)" if dream_bonus else ""

    return (
        f"{random.choice(attack_texts)}\n"
        f"☠️ **{chosen_char['name']}** ➔ 📍 **{opponent_name}**\n"
        f"Lv.{player['level']} · 『 {matched_skill_name} 』\n"
        f"{random.choice(defend_texts)}\n"
        f"💥 -{damage} 🔥 **CRIT** 🔥\n"
        f"🧠 **Ego:** {opponent_name} {new_opponent_ego:,}/2,000\n"
        f"▭▭▭▭▭▭▭▭▭▭▭▭\n"
        f"🧠 **Ego:** {chosen_char['name']} {new_player_ego:,}/2,000\n"
        f"▭▭▭▭▭▭▭▭▭▭▭▭\n"
        f"⭐ +{earned_xp} XP · 🪙 +{earned_coins}"
        f"{dream_text}{event_text}{flow_text}{flow_text_attacker}"
    )

def perform_gacha(user_id, cost=100):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT normal_coins, team_json, free_gacha_ticket FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player: conn.close(); return "no_player"
    
    if player['free_gacha_ticket'] > 0:
        cur.execute('UPDATE players SET free_gacha_ticket = free_gacha_ticket - 1 WHERE user_id = %s', (user_id,))
    else:
        if player['normal_coins'] < cost: conn.close(); return "no_coins"
        cur.execute('UPDATE players SET normal_coins = %s WHERE user_id = %s', (player['normal_coins'] - cost, user_id))
    
    roll = random.random()
    rarity = 'Legendary' if roll <= 0.03 else 'Epic' if roll <= 0.25 else 'Rare'
    cur.execute('SELECT * FROM characters WHERE rarity = %s ORDER BY RANDOM() LIMIT 1', (rarity,))
    char = cur.fetchone()
    if not char: conn.rollback(); cur.close(); conn.close(); return "no_chars"
    team = player['team_json'] if player['team_json'] else []
    team.append(char['char_id'])
    cur.execute('UPDATE players SET team_json = %s WHERE user_id = %s', (json.dumps(team), user_id))
    conn.commit(); cur.close(); conn.close(); 
    
    update_achievement_progress(user_id, "gacha_addict")
    if len(team) >= 10: update_achievement_progress(user_id, "collector")
    
    return dict(char)

def check_ego_recovery_all():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('''
        UPDATE players 
        SET current_ego = 2000, last_ego_update = NOW() 
        WHERE current_ego <= 0 
        AND (NOW() - last_ego_update) >= interval '15 minutes'
    ''')
    conn.commit(); cur.close(); conn.close()
def get_unlocked_skills(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT skill_name, currency FROM player_skills WHERE user_id = %s AND is_unlocked = TRUE', (user_id,))
    skills = {row['skill_name']: row['currency'] for row in cur.fetchall()}
    cur.close(); conn.close(); return skills

def unlock_skill_db(user_id, skill_name, currency):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO player_skills (user_id, skill_name, is_unlocked, currency) VALUES (%s, %s, TRUE, %s) ON CONFLICT (user_id, skill_name) DO UPDATE SET is_unlocked = TRUE, currency = EXCLUDED.currency', (user_id, skill_name, currency))
    conn.commit(); cur.close(); conn.close()

def get_player_damage(user_id, char_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT damage_received FROM player_damage WHERE user_id = %s AND char_id = %s', (user_id, char_id))
    res = cur.fetchone(); cur.close(); conn.close(); return res['damage_received'] if res else 0

def get_player_team(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or not player['team_json']: conn.close(); return []
    cur.execute('SELECT * FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
    chars = cur.fetchall(); cur.close(); conn.close(); return [dict(c) for c in chars]

def remove_from_team(user_id, char_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if player and player['team_json']:
        team = player['team_json']
        if char_id in team:
            team.remove(char_id)
            cur.execute('UPDATE players SET team_json = %s WHERE user_id = %s', (json.dumps(team), user_id))
            conn.commit(); cur.close(); conn.close(); return True
    cur.close(); conn.close(); return False

def rest_player(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT fatigue, pressure, sanity, normal_coins FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if player['normal_coins'] < 30: conn.close(); return "no_coins"
    cur.execute('UPDATE players SET fatigue = %s, pressure = %s, sanity = %s, normal_coins = %s WHERE user_id = %s', (max(0, player['fatigue'] - 40), max(0, player['pressure'] - 40), min(100, player['sanity'] + 30), player['normal_coins'] - 30, user_id))
    conn.commit(); cur.close(); conn.close(); return "success"

def train_player(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT fatigue, normal_coins, xp, level FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if player['normal_coins'] < 50: conn.close(); return "no_coins"
    if player['fatigue'] >= 90: conn.close(); return "too_tired"
    new_xp = player['xp'] + 15; level = player['level']; level_up = False
    if new_xp >= 100: new_xp -= 100; level += 1; level_up = True
    cur.execute('UPDATE players SET fatigue = %s, normal_coins = %s, xp = %s, level = %s, training_points = training_points + 1 WHERE user_id = %s', (min(100, player['fatigue'] + 30), player['normal_coins'] - 50, new_xp, level, user_id))
    conn.commit(); cur.close(); conn.close(); return {"status": "success", "xp": 15, "level_up": level_up, "new_level": level}

def get_leaderboard(limit=10):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT username, level, xp FROM players ORDER BY level DESC, xp DESC LIMIT %s', (limit,))
    players = cur.fetchall(); cur.close(); conn.close(); return [dict(p) for p in players]

def get_player_rank(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT level, xp FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player: conn.close(); return None
    cur.execute('SELECT COUNT(*) + 1 FROM players WHERE level > %s OR (level = %s AND xp > %s)', (player['level'], player['level'], player['xp']))
    rank = cur.fetchone()['count']; cur.close(); conn.close(); return rank

def create_event(boss_name, boss_power, reward_black, reward_normal):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE active_events SET is_active = FALSE')
    cur.execute('INSERT INTO active_events (boss_name, boss_power, reward_black, reward_normal) VALUES (%s, %s, %s, %s)', (boss_name, boss_power, reward_black, reward_normal))
    conn.commit(); cur.close(); conn.close()

def get_active_event():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT * FROM active_events WHERE is_active = TRUE ORDER BY event_id DESC LIMIT 1')
    event = cur.fetchone(); cur.close(); conn.close(); return event

def fight_custom_boss(user_id, event_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT ego, team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or not player['team_json']: conn.close(); return "no_team"
    cur.execute('SELECT base_power FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
    chars = cur.fetchall()
    player_power = sum([c['base_power'] for c in chars]) / len(chars) if chars else 50
    
    # بونوس تیم رویایی روی باس هم اعمال میشه
    dream_bonus = check_dream_team(user_id)
    if dream_bonus: player_power = player_power * (1 + dream_bonus['bonus'] / 100)
    
    cur.execute('SELECT * FROM active_events WHERE event_id = %s', (event_id,))
    event = cur.fetchone()
    if not event: conn.close(); return "no_event"
    if player_power + random.randint(-15, 15) > event['boss_power']:
        cur.execute('UPDATE players SET black_coins = black_coins + %s, normal_coins = normal_coins + %s WHERE user_id = %s', (event['reward_black'], event['reward_normal'], user_id))
        conn.commit(); conn.close()
        update_achievement_progress(user_id, "boss_hunter")
        return {"success": True, "black": event['reward_black'], "normal": event['reward_normal'], "boss_name": event['boss_name'], "boss_power": event['boss_power'], "player_power": player_power}
    else:
        conn.close()
        return {"success": False, "boss_name": event['boss_name'], "boss_power": event['boss_power'], "player_power": player_power}

def generate_coach_mission(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT * FROM coach_missions WHERE player_id = %s AND is_active = TRUE', (user_id,))
    active = cur.fetchone()
    if active: cur.close(); conn.close(); return dict(active)
    missions = [{"type": "lose_on_purpose", "target": "any", "text": "در بازی بعدی بباز."}, {"type": "take_shots", "target": "any", "text": "در بازی بعدی، حداقل ۳ بار خودت شوت بزن."}]
    mission = random.choice(missions)
    cur.execute('INSERT INTO coach_missions (player_id, mission_type, target_name) VALUES (%s, %s, %s)', (user_id, mission['type'], mission['target']))
    conn.commit(); cur.close(); conn.close(); return mission

# سیستم‌های باقی‌مانده که در main استفاده نشدن هم اینجا برای کامل بودن هستن
def finish_match_rewards(user_id, score_player, score_npc):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT normal_coins, xp, level FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if score_player > score_npc: reward_coins, reward_xp, result_msg = 50, 20, "🎉 **تو بردی!**\n+۵۰ سکه\n+۲۰ XP"
    elif score_player == score_npc: reward_coins, reward_xp, result_msg = 20, 10, "🤝 **مساوی!**\n+۲۰ سکه\n+۱۰ XP"
    else: reward_coins, reward_xp, result_msg = 5, 5, "💀 **باختی!**\n+۵ سکه\n+۵ XP"
    new_xp = player['xp'] + reward_xp; level = player['level']; level_up_msg = ""
    if new_xp >= 100: new_xp -= 100; level += 1; level_up_msg = f"\n\n🌟 **سطح {level}!**"
    cur.execute('UPDATE players SET normal_coins = %s, xp = %s, level = %s WHERE user_id = %s', (player['normal_coins'] + reward_coins, new_xp, level, user_id))
    conn.commit(); cur.close(); conn.close(); return result_msg + level_up_msg

def check_synergy(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or not player['team_json']: conn.close(); return None
    cur.execute('SELECT synergy_tag FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
    chars = cur.fetchall(); cur.close(); conn.close()
    tags = [c['synergy_tag'] for c in chars]
    combos = [{"tags": ["isagi", "bachira"], "name": "حمله ترکیبی: ایساگی و باچیرا"}, {"tags": ["sae", "rin"], "name": "حمله ترکیبی: برادران ایتوشی"}]
    for combo in combos:
        if all(tag in tags for tag in combo["tags"]): return combo
    return None

def check_teammate_jealousy(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT ego, team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or not player['team_json']: conn.close(); return "no_team"
    cur.execute('SELECT name, synergy_tag FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
    chars = cur.fetchall(); cur.close(); conn.close()
    jealousy_chance = 30 if player['ego'] > 70 else 15 if player['ego'] > 50 else 0
    for c in chars:
        if c['synergy_tag'] in ['shidou', 'rin', 'kaiser', 'barou', 'karasu', 'lorenzo']: jealousy_chance += 15 
    if random.randint(1, 100) <= jealousy_chance:
        return {"status": "betrayed", "name": random.choice(chars)['name']}
    return {"status": "loyal"}

def check_coach_mission(user_id, match_result):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT * FROM coach_missions WHERE player_id = %s AND is_active = TRUE', (user_id,))
    mission = cur.fetchone()
    if not mission: cur.close(); conn.close(); return "no_mission"
    success = (mission['mission_type'] == "lose_on_purpose" and match_result == "lose")
    cur.execute('SELECT ego, pressure, normal_coins FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if success:
        cur.execute('UPDATE players SET ego = %s, normal_coins = %s WHERE user_id = %s', (min(100, player['ego'] + 15), player['normal_coins'] + 100, user_id))
        cur.execute('UPDATE coach_missions SET is_active = FALSE, is_completed = TRUE WHERE mission_id = %s', (mission['mission_id'],))
        conn.commit(); cur.close(); conn.close(); return "success"
    else:
        cur.execute('UPDATE players SET ego = %s, pressure = %s WHERE user_id = %s', (max(0, player['ego'] - 20), min(100, player['pressure'] + 30), user_id))
        cur.execute('UPDATE coach_missions SET is_active = FALSE WHERE mission_id = %s', (mission['mission_id'],))
        conn.commit(); cur.close(); conn.close(); return "failed"