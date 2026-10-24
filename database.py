import json
import random
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://postgres.hjynfqrsyxjibchmghsg:PH6t8bseGQrPp9el@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    print("✅ اتصال به دیتابیس برقرار است.")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS player_damage (
            user_id BIGINT, char_id INTEGER, damage_received INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, char_id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS player_skills (
            user_id BIGINT, skill_name TEXT, is_unlocked BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (user_id, skill_name)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bot_settings (
            setting_key TEXT PRIMARY KEY, setting_value TEXT
        )
    ''')
    conn.commit(); cur.close(); conn.close()

def get_player(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT * FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone(); cur.close(); conn.close()
    return player

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
    res = cur.fetchone(); cur.close(); conn.close()
    return res['setting_value'] if res else None
def resolve_duel(user_id, player_char_name, player_technique, player_power, npc_name, npc_power, action):
    base_damage = player_power - (npc_power * 0.8)
    if action == "shoot": damage_multiplier = 1.5; action_text = "شوت"
    elif action == "pass": damage_multiplier = 0.5; action_text = "پاس"
    else: damage_multiplier = 1.0; action_text = "دریبل"

    final_damage = int(base_damage * damage_multiplier) + random.randint(-10, 10)
    final_damage = max(0, final_damage)
    
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('''
        INSERT INTO player_damage (user_id, char_id, damage_received) 
        VALUES (%s, (SELECT char_id FROM characters WHERE name = %s LIMIT 1), %s)
        ON CONFLICT (user_id, char_id) DO UPDATE SET damage_received = player_damage.damage_received + EXCLUDED.damage_received
    ''', (user_id, npc_name, final_damage))
    conn.commit(); cur.close(); conn.close()

    if final_damage > 0:
        return {
            "success": True,
            "text": (
                f"☠️ **{player_char_name}** ➔ 📍 **{npc_name}**\n"
                f"Lv.1 · 『 {player_technique} 』\n"
                f"💥 -{final_damage} 🔥 **CRIT** 🔥\n"
                f"❤️ {npc_name} 0/2,500\n"
                f"▭▭▭▭▭▭▭▭▭▭▭▭\n"
                f"❤️ {player_char_name} 477/2,500\n"
                f"▭▭▭▭▭▭▭▭▭▭▭▭\n"
                f"⭐ +20 XP · 🪙 +25"
            )
        }
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
    
    match_state = {
        "type": "pvp", "opponent_name": "NPC Legend", "opponent_id": 0,
        "player_star": p1_chars[0]['name'] if p1_chars else "Unknown",
        "player_technique": p1_chars[0]['technique'] if p1_chars else "None",
        "player_power": p1_power, "npc_name": "Strong NPC", "npc_power": random.randint(60, 95),
        "score_player": 0, "score_npc": 0, "turn": 1, "max_turns": 5
    }
    cur.execute('UPDATE players SET current_match_state = %s WHERE user_id = %s', (json.dumps(match_state), user_id))
    conn.commit(); cur.close(); conn.close()
    return match_state

def start_team_battle(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    team_ids = player['team_json'] if player['team_json'] else []
    if len(team_ids) < 3: conn.close(); return "need_3_cards"
    
    cur.execute('SELECT name, technique, base_power FROM characters WHERE char_id = ANY(%s)', (team_ids,))
    chars = cur.fetchall()
    player_power = sum([c['base_power'] for c in chars]) / len(chars)

    match_state = {
        "type": "team_battle", "player_star": chars[0]['name'], "player_technique": chars[0]['technique'],
        "player_power": player_power, "npc_name": "تیم ستارگان اروپا", "npc_power": random.randint(70, 100),
        "score_player": 0, "score_npc": 0, "turn": 1, "max_turns": 4
    }
    cur.execute('UPDATE players SET current_match_state = %s WHERE user_id = %s', (json.dumps(match_state), user_id))
    conn.commit(); cur.close(); conn.close()
    return match_state

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
    conn.commit(); cur.close(); conn.close()
    return result_msg + level_up_msg

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
    conn.commit(); cur.close(); conn.close()
    return dict(char)

def get_player_team(user_id):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or not player['team_json']: conn.close(); return []
    cur.execute('SELECT * FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
    chars = cur.fetchall(); cur.close(); conn.close()
    return [dict(c) for c in chars]

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
    conn.commit(); cur.close(); conn.close()
    return {"status": "success", "xp": 15, "level_up": level_up, "new_level": level}

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

# توابع کمکی
def check_synergy(user_id): return None 
def check_teammate_jealousy(user_id): return "no_team"
def generate_coach_mission(user_id): return {"text": "ماموریتی وجود ندارد."}
def check_coach_mission(user_id, match_result): return "no_mission"
def enter_shadow_league(user_id): pass
def shadow_league_result(user_id, is_win): return "lose"
def use_wild_card(user_id, char_id_to_burn): return "not_in_team"