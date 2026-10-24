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
    
    # ساخت جدول بازیکن‌ها با تمام ستون‌های جدید
    cur.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id BIGINT PRIMARY KEY, username TEXT, level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0,
        ego INTEGER DEFAULT 100, sanity INTEGER DEFAULT 100, fatigue INTEGER DEFAULT 0, pressure INTEGER DEFAULT 0,
        black_coins INTEGER DEFAULT 0, normal_coins INTEGER DEFAULT 100, team_json JSONB DEFAULT '[]'::jsonb,
        current_match_state JSONB DEFAULT NULL, in_shadow_league BOOLEAN DEFAULT FALSE, shadow_wins INTEGER DEFAULT 0,
        ego_broken_at TIMESTAMPTZ DEFAULT NULL, last_attack_at TIMESTAMPTZ DEFAULT NULL, 
        last_match_action_at TIMESTAMPTZ DEFAULT NULL, current_ego INTEGER DEFAULT 2000, last_ego_update TIMESTAMPTZ DEFAULT NOW()
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

def unlock_skill_db(user_id, skill_name, currency):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO player_skills (user_id, skill_name, is_unlocked, currency) VALUES (%s, %s, TRUE, %s) ON CONFLICT (user_id, skill_name) DO UPDATE SET is_unlocked = TRUE, currency = EXCLUDED.currency', (user_id, skill_name, currency))
    conn.commit(); cur.close(); conn.close()

def get_unlocked_skills(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT skill_name, currency FROM player_skills WHERE user_id = %s AND is_unlocked = TRUE', (user_id,))
    skills = {row['skill_name']: row['currency'] for row in cur.fetchall()}
    cur.close(); conn.close(); return skills

def get_player_damage(user_id, char_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT damage_received FROM player_damage WHERE user_id = %s AND char_id = %s', (user_id, char_id))
    res = cur.fetchone(); cur.close(); conn.close(); return res['damage_received'] if res else 0

def use_wild_card(user_id, char_id_to_burn):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    team = player['team_json'] if player['team_json'] else []
    if char_id_to_burn not in team: conn.close(); return "not_in_team"
    team.remove(char_id_to_burn)
    cur.execute('SELECT * FROM characters WHERE rarity = "Legendary" ORDER BY RANDOM() LIMIT 1')
    legendary = cur.fetchone()
    if not legendary: conn.close(); return "no_legendary"
    team.append(legendary['char_id'])
    cur.execute('UPDATE players SET team_json = %s WHERE user_id = %s', (json.dumps(team), user_id))
    conn.commit(); cur.close(); conn.close(); return dict(legendary)
def check_ego_recovery(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT current_ego, last_ego_update FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if player['current_ego'] < 2000 and player['last_ego_update']:
        time_passed = datetime.now(player['last_ego_update'].tzinfo) - player['last_ego_update']
        if time_passed >= timedelta(minutes=15):
            cur.execute('UPDATE players SET current_ego = 2000, last_ego_update = NOW() WHERE user_id = %s', (user_id,))
            conn.commit(); cur.close(); conn.close(); return "recovered"
    cur.close(); conn.close(); return "not_recovered"

def check_ego_recovery_all():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('''
        UPDATE players 
        SET current_ego = 2000, last_ego_update = NOW() 
        WHERE current_ego < 2000 
        AND (NOW() - last_ego_update) >= interval '15 minutes'
    ''')
    conn.commit(); cur.close(); conn.close()

def attack_with_technique(user_id, technique_name, opponent_name):
    # چک کردن اینکه آیا کسی ۱۵ دقیقه بدون حمله مونده یا نه
    check_ego_recovery_all()

    conn = get_db_connection(); cur = conn.cursor()
    
    cur.execute('SELECT current_ego, team_json, xp, normal_coins, level, last_attack_at FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    
    if not player or player['current_ego'] <= 0:
        conn.close(); return "ego_broken"

    cur.execute('SELECT name, technique, base_power, rarity FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
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

    cur.execute('SELECT user_id, current_ego FROM players WHERE username = %s LIMIT 1', (opponent_name,))
    opponent_data = cur.fetchone()
    
    opponent_current_ego = 2000
    opponent_user_id = None
    if opponent_data:
        opponent_current_ego = opponent_data['current_ego']
        opponent_user_id = opponent_data['user_id']

    currency_type = "normal"
    if matched_skill_name in unlocked:
        currency_type = unlocked[matched_skill_name]

    rarity = chosen_char['rarity']
    if rarity == 'Legendary': min_dmg, max_dmg = (300, 400) if currency_type == "black" else (200, 250)
    elif rarity == 'Epic': min_dmg, max_dmg = (220, 300) if currency_type == "black" else (150, 190)
    else: min_dmg, max_dmg = (180, 250) if currency_type == "black" else (100, 150)

    if currency_type == "black": cooldown_sec = 30
    elif matched_skill_name != chosen_char['technique']: cooldown_sec = 15
    else: cooldown_sec = 5

    if player['last_attack_at']:
        time_passed = datetime.now(player['last_attack_at'].tzinfo) - player['last_attack_at']
        if time_passed.total_seconds() < cooldown_sec:
            remaining = cooldown_sec - int(time_passed.total_seconds())
            conn.close(); return f"cooldown_{remaining}"

    damage = random.randint(min_dmg, max_dmg)
    
    new_opponent_ego = max(0, opponent_current_ego - damage)
    new_player_ego = max(0, player['current_ego'] - 10)

    cur.execute('UPDATE players SET current_ego = %s, xp = xp + %s, normal_coins = normal_coins + %s, last_attack_at = %s, last_ego_update = %s WHERE user_id = %s', 
                (new_player_ego, random.randint(2, 5), random.randint(2, 5), datetime.now(), datetime.now(), user_id))
    
    if opponent_user_id:
        cur.execute('UPDATE players SET current_ego = %s, last_ego_update = %s WHERE user_id = %s', (new_opponent_ego, datetime.now(), opponent_user_id))

    conn.commit(); cur.close(); conn.close()
    
    return (
        f"☠️ **{chosen_char['name']}** ➔ 📍 **{opponent_name}**\n"
        f"Lv.{player['level']} · 『 {matched_skill_name} 』\n"
        f"💥 -{damage} 🔥 **CRIT** 🔥\n"
        f"🧠 **Ego:** {opponent_name} {new_opponent_ego:,}/2,000\n"
        f"▭▭▭▭▭▭▭▭▭▭▭▭\n"
        f"🧠 **Ego:** {chosen_char['name']} {new_player_ego:,}/2,000\n"
        f"▭▭▭▭▭▭▭▭▭▭▭▭\n"
        f"⭐ +{random.randint(2, 5)} XP · 🪙 +{random.randint(2, 5)}"
    )

def resolve_duel(user_id, player_char_name, player_technique, player_power, npc_name, npc_power, action):
    base_damage = player_power - (npc_power * 0.8)
    if action == "shoot": damage_multiplier = 1.5; action_text = "شوت"
    elif action == "pass": damage_multiplier = 0.5; action_text = "پاس"
    else: damage_multiplier = 1.0; action_text = "دریبل"
    final_damage = max(0, int(base_damage * damage_multiplier) + random.randint(-10, 10))
    
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('INSERT INTO player_damage (user_id, char_id, damage_received) VALUES (%s, (SELECT char_id FROM characters WHERE name = %s LIMIT 1), %s) ON CONFLICT (user_id, char_id) DO UPDATE SET damage_received = player_damage.damage_received + EXCLUDED.damage_received', (user_id, npc_name, final_damage))
    conn.commit(); cur.close(); conn.close()

    if final_damage > 0:
        return {"success": True, "text": f"☠️ **{player_char_name}** ➔ 📍 **{npc_name}**\nLv.1 · 『 {player_technique} 』\n💥 -{final_damage} 🔥 **CRIT** 🔥\n🧠 **Ego:** {npc_name} 0/2,500\n▭▭▭▭▭▭▭▭▭▭▭▭\n🧠 **Ego:** {player_char_name} 477/2,500\n▭▭▭▭▭▭▭▭▭▭▭▭\n⭐ +20 XP · 🪙 +25"}
    else:
        return {"success": False, "text": f"🛡️ **{npc_name}** دفاع کرد! حمله {action_text} شما دفع شد."}

def start_pvp_match(user_id, opponent_id=0):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT username, team_json FROM players WHERE user_id = %s', (user_id,))
    p1 = cur.fetchone()
    if not p1 or not p1['team_json']: conn.close(); return "no_team"
    cur.execute('SELECT name, technique, base_power FROM characters WHERE char_id = ANY(%s)', (p1['team_json'],))
    p1_chars = cur.fetchall()
    p1_power = sum([c['base_power'] for c in p1_chars]) / len(p1_chars) if p1_chars else 50
    match_state = {"type": "pvp", "opponent_name": "NPC Legend", "opponent_id": 0, "player_star": p1_chars[0]['name'] if p1_chars else "Unknown", "player_technique": p1_chars[0]['technique'] if p1_chars else "None", "player_power": p1_power, "npc_name": "Strong NPC", "npc_power": random.randint(60, 95), "score_player": 0, "score_npc": 0, "turn": 1, "max_turns": 5}
    cur.execute('UPDATE players SET current_match_state = %s WHERE user_id = %s', (json.dumps(match_state), user_id))
    conn.commit(); cur.close(); conn.close(); return match_state

def start_team_battle(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    team_ids = player['team_json'] if player['team_json'] else []
    if len(team_ids) < 3: conn.close(); return "need_3_cards"
    cur.execute('SELECT name, technique, base_power FROM characters WHERE char_id = ANY(%s)', (team_ids,))
    chars = cur.fetchall()
    player_power = sum([c['base_power'] for c in chars]) / len(chars)
    match_state = {"type": "team_battle", "player_star": chars[0]['name'], "player_technique": chars[0]['technique'], "player_power": player_power, "npc_name": "تیم ستارگان اروپا", "npc_power": random.randint(70, 100), "score_player": 0, "score_npc": 0, "turn": 1, "max_turns": 4}
    cur.execute('UPDATE players SET current_match_state = %s WHERE user_id = %s', (json.dumps(match_state), user_id))
    conn.commit(); cur.close(); conn.close(); return match_state

def start_2v2_match(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT ego, team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    team_ids = player['team_json'] if player['team_json'] else []
    if len(team_ids) < 2: conn.close(); return "need_2_cards"
    match_team_ids = team_ids[:2]
    cur.execute('SELECT name, technique, base_power, is_cursed FROM characters WHERE char_id = ANY(%s)', (match_team_ids,))
    chars = cur.fetchall()
    player_power = sum([c['base_power'] for c in chars]) / len(chars)
    cursed_count = sum([1 for c in chars if c['is_cursed']])
    if cursed_count > 0: cur.execute('UPDATE players SET sanity = %s WHERE user_id = %s', (max(0, 100 - (cursed_count * 10)), user_id))
    match_state = {"type": "2v2", "player_star": chars[0]['name'], "player_technique": chars[0]['technique'], "player_power": player_power, "npc_name": "تیم دو نفره حریف", "npc_power": random.randint(70, 100), "score_player": 0, "score_npc": 0, "turn": 1, "max_turns": 3}
    cur.execute('UPDATE players SET current_match_state = %s WHERE user_id = %s', (json.dumps(match_state), user_id))
    conn.commit(); cur.close(); conn.close(); return match_state
def enter_shadow_league(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('UPDATE players SET in_shadow_league = TRUE, shadow_wins = 0, sanity = 50 WHERE user_id = %s', (user_id,))
    conn.commit(); cur.close(); conn.close()

def shadow_league_result(user_id, is_win):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT shadow_wins, sanity FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if is_win:
        new_wins = player['shadow_wins'] + 1
        if new_wins >= 3:
            cur.execute('UPDATE players SET in_shadow_league = FALSE, shadow_wins = 0, ego = 100 WHERE user_id = %s', (user_id,))
            conn.commit(); cur.close(); conn.close(); return "freed"
        cur.execute('UPDATE players SET shadow_wins = %s WHERE user_id = %s', (new_wins, user_id))
        conn.commit(); cur.close(); conn.close(); return f"win_{new_wins}"
    else:
        cur.execute('UPDATE players SET shadow_wins = 0, sanity = %s WHERE user_id = %s', (max(0, player['sanity'] - 40), user_id))
        conn.commit(); cur.close(); conn.close(); return "lose"

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
    cur.execute('SELECT * FROM active_events WHERE event_id = %s', (event_id,))
    event = cur.fetchone()
    if not event: conn.close(); return "no_event"
    if player_power + random.randint(-15, 15) > event['boss_power']:
        cur.execute('UPDATE players SET black_coins = black_coins + %s, normal_coins = normal_coins + %s WHERE user_id = %s', (event['reward_black'], event['reward_normal'], user_id))
        conn.commit(); conn.close()
        return {"success": True, "black": event['reward_black'], "normal": event['reward_normal'], "boss_name": event['boss_name'], "boss_power": event['boss_power'], "player_power": player_power}
    else:
        conn.close()
        return {"success": False, "boss_name": event['boss_name'], "boss_power": event['boss_power'], "player_power": player_power}

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

def perform_gacha(user_id, cost=100):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT normal_coins, team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player: conn.close(); return "no_player"
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
    conn.commit(); cur.close(); conn.close(); return dict(char)

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
    cur.execute('UPDATE players SET fatigue = %s, normal_coins = %s, xp = %s, level = %s WHERE user_id = %s', (min(100, player['fatigue'] + 30), player['normal_coins'] - 50, new_xp, level, user_id))
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

def check_synergy(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or not player['team_json']: conn.close(); return None
    cur.execute('SELECT synergy_tag FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
    chars = cur.fetchall(); cur.close(); conn.close()
    tags = [c['synergy_tag'] for c in chars]
    combos = [{"tags": ["isagi", "bachira"], "name": "حمله ترکیبی: ایساگی و باچیرا"}, {"tags": ["sae", "rin"], "name": "حمله ترکیبی: برادران ایتوشی"}, {"tags": ["shidou", "sae"], "name": "حمله ترکیبی: سائه و شیدو"}, {"tags": ["nagi", "mikage"], "name": "حمله ترکیبی: ناگی و میکاگه"}]
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

def generate_coach_mission(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT * FROM coach_missions WHERE player_id = %s AND is_active = TRUE', (user_id,))
    active = cur.fetchone()
    if active: cur.close(); conn.close(); return dict(active)
    missions = [{"type": "lose_on_purpose", "target": "any", "text": "در بازی بعدی بباز."}, {"type": "take_shots", "target": "any", "text": "در بازی بعدی، حداقل ۳ بار خودت شوت بزن."}]
    mission = random.choice(missions)
    cur.execute('INSERT INTO coach_missions (player_id, mission_type, target_name) VALUES (%s, %s, %s)', (user_id, mission['type'], mission['target']))
    conn.commit(); cur.close(); conn.close(); return mission

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