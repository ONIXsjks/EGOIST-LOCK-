import json
import random
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# 🔴 رشته اتصال تمیز و استاندارد
DATABASE_URL = "postgresql://postgres.hjynfqrsyxjibchmghsg:PH6t8bseGQrPp9el@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def get_player(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    cur.close(); conn.close()
    return player

def create_player(user_id, username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM players WHERE user_id = %s', (user_id,))
    if not cur.fetchone():
        cur.execute('INSERT INTO players (user_id, username) VALUES (%s, %s)', (user_id, username))
        conn.commit()
    cur.close(); conn.close()

def init_db():
    print("✅ اتصال به Supabase (Pooler) برقرار است.")

def perform_gacha(user_id, cost=100):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT normal_coins, team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player: cur.close(); conn.close(); return "no_player"
    if player['normal_coins'] < cost: cur.close(); conn.close(); return "no_coins"

    new_coins = player['normal_coins'] - cost
    cur.execute('UPDATE players SET normal_coins = %s WHERE user_id = %s', (new_coins, user_id))

    roll = random.random()
    if roll <= 0.03: rarity = 'Legendary'
    elif roll <= 0.25: rarity = 'Epic'
    else: rarity = 'Rare'

    cur.execute('SELECT * FROM characters WHERE rarity = %s ORDER BY RANDOM() LIMIT 1', (rarity,))
    char = cur.fetchone()
    if not char: 
        conn.rollback(); cur.close(); conn.close(); return "no_chars"
    
    team = player['team_json'] if player['team_json'] else []
    team.append(char['char_id'])
    cur.execute('UPDATE players SET team_json = %s WHERE user_id = %s', (json.dumps(team), user_id))
    conn.commit(); cur.close(); conn.close()
    return dict(char)

def rest_player(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT fatigue, pressure, sanity, normal_coins FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if player['normal_coins'] < 30: cur.close(); conn.close(); return "no_coins"
    
    cur.execute('''UPDATE players SET fatigue = %s, pressure = %s, sanity = %s, normal_coins = %s WHERE user_id = %s''',
                 (max(0, player['fatigue'] - 40), max(0, player['pressure'] - 40), min(100, player['sanity'] + 30), player['normal_coins'] - 30, user_id))
    conn.commit(); cur.close(); conn.close()
    return "success"

def train_player(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT fatigue, normal_coins, xp, level FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if player['normal_coins'] < 50: cur.close(); conn.close(); return "no_coins"
    if player['fatigue'] >= 90: cur.close(); conn.close(); return "too_tired"

    new_xp = player['xp'] + 15
    level = player['level']
    level_up = False
    if new_xp >= 100:
        new_xp -= 100
        level += 1
        level_up = True

    cur.execute('''UPDATE players SET fatigue = %s, normal_coins = %s, xp = %s, level = %s WHERE user_id = %s''',
                 (min(100, player['fatigue'] + 30), player['normal_coins'] - 50, new_xp, level, user_id))
    conn.commit(); cur.close(); conn.close()
    return {"status": "success", "xp": 15, "level_up": level_up, "new_level": level}

def start_new_match(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT ego, team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or not player['team_json']:
        cur.close(); conn.close(); return "no_team"
        
    team_ids = player['team_json']
    cur.execute('SELECT base_power, is_cursed FROM characters WHERE char_id = ANY(%s)', (team_ids,))
    chars = cur.fetchall()
    
    player_power = sum([c['base_power'] for c in chars]) / len(chars) if chars else 50
    cursed_count = sum([1 for c in chars if c['is_cursed']])
    
    if cursed_count > 0:
        cur.execute('UPDATE players SET sanity = %s WHERE user_id = %s', (max(0, 100 - (cursed_count * 10)), user_id))

    npc_name = random.choice(["Tiger Team", "Kaiser's Team", "Blue Lock 11", "U-20 Japan"])
    npc_power = random.randint(60, 95)
    
    match_state = {
        "npc_name": npc_name, "npc_power": npc_power, "player_power": player_power,
        "score_player": 0, "score_npc": 0, "turn": 1, "max_turns": 5, "is_2v2": False
    }
    
    cur.execute('UPDATE players SET current_match_state = %s WHERE user_id = %s', (json.dumps(match_state), user_id))
    conn.commit(); cur.close(); conn.close()
    return match_state

def start_2v2_match(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT ego, team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if len(player['team_json']) < 2: cur.close(); conn.close(); return "need_2_cards"
    
    match_team_ids = player['team_json'][:2]
    cur.execute('SELECT base_power, is_cursed FROM characters WHERE char_id = ANY(%s)', (match_team_ids,))
    chars = cur.fetchall()
    player_power = sum([c['base_power'] for c in chars]) / len(chars)
    cursed_count = sum([1 for c in chars if c['is_cursed']])
    
    if cursed_count > 0:
        cur.execute('UPDATE players SET sanity = %s WHERE user_id = %s', (max(0, 100 - (cursed_count * 10)), user_id))

    npc_name = random.choice(["تیم کایزر و نس", "تیم سائه و شیدو", "تیم ایساگی و باچیرا"])
    npc_power = random.randint(70, 100)
    
    match_state = {
        "npc_name": npc_name, "npc_power": npc_power, "player_power": player_power,
        "score_player": 0, "score_npc": 0, "turn": 1, "max_turns": 3, "is_2v2": True
    }
    
    cur.execute('UPDATE players SET current_match_state = %s WHERE user_id = %s', (json.dumps(match_state), user_id))
    conn.commit(); cur.close(); conn.close()
    return match_state

def resolve_turn(user_id, action):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT ego, current_match_state FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    state = player['current_match_state']
    if isinstance(state, str): state = json.loads(state)
    
    base_chance = (state['player_power'] / (state['player_power'] + state['npc_power'])) * 100
    flow_bonus = 1.5 if player['ego'] >= 90 else 1.0
    
    if action == "shoot": 
        success_chance = (base_chance * 0.6) * flow_bonus
        double_chance = 30 if player['ego'] >= 90 else 0
    elif action == "pass": 
        success_chance = base_chance * 1.2
        double_chance = 0
    else: 
        success_chance = base_chance * 0.9
        double_chance = 0

    if random.randint(1, 100) <= success_chance:
        goals = 1
        if double_chance > 0 and random.randint(1, 100) <= double_chance:
            goals = 2
            result_text = "🔥 **حالت فلو! دوبل زدی!** توپ دو بار به تور نشست."
        else:
            result_text = "✅ **موفق بودی!** توپ به تور نشست."
        state['score_player'] += goals
    else:
        state['score_npc'] += 1
        result_text = "❌ **شکست خوردی!** حریف ضدحمله کرد."

    state['turn'] += 1
    cur.execute('UPDATE players SET current_match_state = %s WHERE user_id = %s', (json.dumps(state), user_id))
    conn.commit(); cur.close(); conn.close()
    return {"success": True, "text": result_text, "state": state, "is_finished": state['turn'] > state['max_turns']}

def check_synergy(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or not player['team_json']: cur.close(); conn.close(); return None
    
    cur.execute('SELECT synergy_tag FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
    chars = cur.fetchall()
    cur.close(); conn.close()
    tags = [c['synergy_tag'] for c in chars]
    combos = [
        {"tags": ["isagi", "bachira"], "name": "حمله ترکیبی: ایساگی و باچیرا"},
        {"tags": ["sae", "rin"], "name": "حمله ترکیبی: برادران ایتوشی"},
        {"tags": ["shidou", "sae"], "name": "حمله ترکیبی: سائه و شیدو"},
        {"tags": ["nagi", "mikage"], "name": "حمله ترکیبی: ناگی و میکاگه"}
    ]
    for combo in combos:
        if all(tag in tags for tag in combo["tags"]): return combo
    return None

def check_teammate_jealousy(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT ego, team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or not player['team_json']: cur.close(); conn.close(); return "no_team"
    
    cur.execute('SELECT name, synergy_tag FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
    chars = cur.fetchall()
    cur.close(); conn.close()
    
    jealousy_chance = 30 if player['ego'] > 70 else 15 if player['ego'] > 50 else 0
    for c in chars:
        if c['synergy_tag'] in ['shidou', 'rin', 'kaiser', 'barou', 'karasu', 'lorenzo']:
            jealousy_chance += 15 
            
    if random.randint(1, 100) <= jealousy_chance:
        return {"status": "betrayed", "name": random.choice(chars)['name']}
    return {"status": "loyal"}

def finish_match_rewards(user_id, score_player, score_npc):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT normal_coins, xp, level FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    
    if score_player > score_npc: reward_coins, reward_xp, result_msg = 50, 20, "🎉 **تو بردی!**\n+۵۰ سکه\n+۲۰ XP"
    elif score_player == score_npc: reward_coins, reward_xp, result_msg = 20, 10, "🤝 **مساوی!**\n+۲۰ سکه\n+۱۰ XP"
    else: reward_coins, reward_xp, result_msg = 5, 5, "💀 **باختی!**\n+۵ سکه\n+۵ XP"
        
    new_xp = player['xp'] + reward_xp
    level = player['level']
    level_up_msg = ""
    if new_xp >= 100: 
        new_xp -= 100
        level += 1
        level_up_msg = f"\n\n🌟 **سطح {level}!**"
        
    cur.execute('UPDATE players SET normal_coins = %s, xp = %s, level = %s WHERE user_id = %s', 
                 (player['normal_coins'] + reward_coins, new_xp, level, user_id))
    conn.commit(); cur.close(); conn.close()
    return result_msg + level_up_msg

def generate_coach_mission(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM coach_missions WHERE player_id = %s AND is_active = TRUE', (user_id,))
    active = cur.fetchone()
    if active: cur.close(); conn.close(); return dict(active)
    
    missions = [{"type": "lose_on_purpose", "target": "any", "text": "در بازی بعدی بباز."},
                {"type": "take_shots", "target": "any", "text": "در بازی بعدی، حداقل ۳ بار خودت شوت بزن."}]
    mission = random.choice(missions)
    
    cur.execute('INSERT INTO coach_missions (player_id, mission_type, target_name) VALUES (%s, %s, %s)', (user_id, mission['type'], mission['target']))
    conn.commit(); cur.close(); conn.close()
    return mission

def check_coach_mission(user_id, match_result):
    conn = get_db_connection()
    cur = conn.cursor()
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

def enter_shadow_league(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE players SET in_shadow_league = TRUE, shadow_wins = 0, sanity = 50 WHERE user_id = %s', (user_id,))
    conn.commit(); cur.close(); conn.close()

def shadow_league_result(user_id, is_win):
    conn = get_db_connection()
    cur = conn.cursor()
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

def use_wild_card(user_id, char_id_to_burn):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    team = player['team_json'] if player['team_json'] else []
    if char_id_to_burn not in team: cur.close(); conn.close(); return "not_in_team"
    
    team.remove(char_id_to_burn)
    cur.execute('SELECT * FROM characters WHERE rarity = "Legendary" ORDER BY RANDOM() LIMIT 1')
    legendary = cur.fetchone()
    if not legendary: cur.close(); conn.close(); return "no_legendary"
    
    team.append(legendary['char_id'])
    cur.execute('UPDATE players SET team_json = %s WHERE user_id = %s', (json.dumps(team), user_id))
    conn.commit(); cur.close(); conn.close()
    return dict(legendary)

def get_player_team(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player or not player['team_json']: cur.close(); conn.close(); return []
    
    cur.execute('SELECT * FROM characters WHERE char_id = ANY(%s)', (player['team_json'],))
    chars = cur.fetchall()
    cur.close(); conn.close()
    return [dict(c) for c in chars]

def remove_from_team(user_id, char_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT team_json FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if player and player['team_json']:
        team = player['team_json']
        if char_id in team:
            team.remove(char_id)
            cur.execute('UPDATE players SET team_json = %s WHERE user_id = %s', (json.dumps(team), user_id))
            conn.commit(); cur.close(); conn.close(); return True
    cur.close(); conn.close(); return False

def get_leaderboard(limit=10):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT username, level, xp FROM players ORDER BY level DESC, xp DESC LIMIT %s', (limit,))
    players = cur.fetchall()
    cur.close(); conn.close()
    return [dict(p) for p in players]

def get_player_rank(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT level, xp FROM players WHERE user_id = %s', (user_id,))
    player = cur.fetchone()
    if not player: cur.close(); conn.close(); return None
    cur.execute('SELECT COUNT(*) + 1 FROM players WHERE level > %s OR (level = %s AND xp > %s)', (player['level'], player['level'], player['xp']))
    rank = cur.fetchone()['count']
    cur.close(); conn.close()
    return rank