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
    
    # ساخت تمام جدول‌ها (کامل)
    cur.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id BIGINT PRIMARY KEY, username TEXT, level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0,
        ego INTEGER DEFAULT 100, sanity INTEGER DEFAULT 100, fatigue INTEGER DEFAULT 0, pressure INTEGER DEFAULT 0,
        black_coins INTEGER DEFAULT 0, normal_coins INTEGER DEFAULT 100, team_json JSONB DEFAULT '[]'::jsonb,
        current_match_state JSONB DEFAULT NULL, in_shadow_league BOOLEAN DEFAULT FALSE, shadow_wins INTEGER DEFAULT 0,
        ego_broken_at TIMESTAMPTZ DEFAULT NULL
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
    cur.execute('SELECT ego, ego_broken_at FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if player['ego'] <= 0 and player['ego_broken_at']:
        time_passed = datetime.now(player['ego_broken_at'].tzinfo) - player['ego_broken_at']
        if time_passed >= timedelta(minutes=15):
            cur.execute('UPDATE players SET ego = 100, ego_broken_at = NULL WHERE user_id = %s', (user_id,))
            conn.commit(); cur.close(); conn.close(); return "recovered"
    cur.close(); conn.close(); return "not_recovered"

def attack_with_technique(user_id, technique_name, opponent_name):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT ego, team_json, ego_broken_at, xp, normal_coins, level FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if player['ego'] <= 0:
        if check_ego_recovery(user_id) == "not_recovered":
            conn.close(); return "ego_broken"
            
    cur.execute('SELECT name, technique, base_power, rarity FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
    team_chars = cur.fetchall()
    chosen_char = next((c for c in team_chars if c['technique'].lower() == technique_name.lower()), None)
    if not chosen_char: conn.close(); return "no_technique"

    unlocked = get_unlocked_skills(user_id)
    currency_type = unlocked.get(chosen_char['technique'], "normal")
    rarity = chosen_char['rarity']
    if rarity == 'Legendary': max_damage = 400 if currency_type == "black" else 250
    elif rarity == 'Epic': max_damage = 300 if currency_type == "black" else 190
    else: max_damage = 250 if currency_type == "black" else 150
        
    level_bonus = player['level'] * 20
    base_damage = int(chosen_char['base_power'] * 0.2) + level_bonus
    damage = min(base_damage, max_damage)
    new_ego = max(0, player['ego'] - 10)
    reward_xp = random.randint(2, 5) 
    reward_coins = random.randint(2, 5)
    
    cur.execute('UPDATE players SET ego = %s, xp = xp + %s, normal_coins = normal_coins + %s WHERE user_id = %s', (new_ego, reward_xp, reward_coins, user_id))
    if new_ego == 0: cur.execute('UPDATE players SET ego_broken_at = %s WHERE user_id = %s', (datetime.now(), user_id))
    conn.commit(); cur.close(); conn.close()
    
    return (
        f"☠️ **{chosen_char['name']}** ➔ 📍 **{opponent_name}**\n"
        f"Lv.{player['level']} · 『 {chosen_char['technique']} 』\n"
        f"💥 -{damage} 🔥 **CRIT** 🔥\n"
        f"🧠 **Ego:** {opponent_name} {max(0, 3000 - damage)}/3,000\n"
        f"▭▭▭▭▭▭▭▭▭▭▭▭\n"
        f"🧠 **Ego:** {chosen_char['name']} {new_ego}/100\n"
        f"▭▭▭▭▭▭▭▭▭▭▭▭\n"
        f"⭐ +{reward_xp} XP · 🪙 +{reward_coins}"
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
