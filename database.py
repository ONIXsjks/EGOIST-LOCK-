import sqlite3
import json
import random

def get_db_connection():
    conn = sqlite3.connect('blue_lock.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. جدول بازیکن‌ها
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        ego INTEGER DEFAULT 50,         
        sanity INTEGER DEFAULT 100,     
        fatigue INTEGER DEFAULT 0,      
        pressure INTEGER DEFAULT 0,     
        black_coins INTEGER DEFAULT 0,  
        normal_coins INTEGER DEFAULT 100, 
        team_json TEXT DEFAULT '[]',    
        current_match_state TEXT DEFAULT NULL,
        in_shadow_league BOOLEAN DEFAULT 0,
        shadow_wins INTEGER DEFAULT 0
    )
    ''')

    # 2. جدول کارت‌ها
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS characters (
        char_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        position TEXT,                  
        technique TEXT,                 
        base_power INTEGER,             
        rarity TEXT,                    
        is_cursed BOOLEAN DEFAULT 0,    
        synergy_tag TEXT,
        image_url TEXT DEFAULT NULL
    )
    ''')

    # 3. جدول تاریخچه مسابقات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS match_history (
        match_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        opponent_name TEXT,
        result TEXT,                    
        goals_scored INTEGER,
        match_type TEXT,                
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 4. جدول ماموریت‌های مربی
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS coach_missions (
        mission_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        mission_type TEXT,
        target_name TEXT,
        is_active BOOLEAN DEFAULT 1,
        is_completed BOOLEAN DEFAULT 0
    )
    ''')

    conn.commit()
    conn.close()
    print("✅ دیتابیس آماده است.")

def get_player(user_id):
    conn = get_db_connection()
    player = conn.execute('SELECT * FROM players WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return player

def create_player(user_id, username):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO players (user_id, username) VALUES (?, ?)', (user_id, username))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
def perform_gacha(user_id, cost=100):
    conn = get_db_connection()
    player = conn.execute('SELECT normal_coins, team_json FROM players WHERE user_id = ?', (user_id,)).fetchone()
    
    if not player: conn.close(); return "no_player"
    if player['normal_coins'] < cost: conn.close(); return "no_coins"

    new_coins = player['normal_coins'] - cost
    conn.execute('UPDATE players SET normal_coins = ? WHERE user_id = ?', (new_coins, user_id))

    roll = random.random()
    if roll <= 0.03: rarity = 'Legendary'
    elif roll <= 0.25: rarity = 'Epic'
    else: rarity = 'Rare'

    char = conn.execute('SELECT * FROM characters WHERE rarity = ? ORDER BY RANDOM() LIMIT 1', (rarity,)).fetchone()
    
    if not char: conn.close(); return "no_chars"
    
    team = json.loads(player['team_json'])
    team.append(char['char_id'])
    conn.execute('UPDATE players SET team_json = ? WHERE user_id = ?', (json.dumps(team), user_id))
    conn.commit(); conn.close()
    return dict(char)

def rest_player(user_id):
    conn = get_db_connection()
    player = conn.execute('SELECT fatigue, pressure, sanity, normal_coins FROM players WHERE user_id = ?', (user_id,)).fetchone()
    if player['normal_coins'] < 30: conn.close(); return "no_coins"
    conn.execute('UPDATE players SET fatigue = ?, pressure = ?, sanity = ?, normal_coins = ? WHERE user_id = ?',
                 (max(0, player['fatigue'] - 40), max(0, player['pressure'] - 40), min(100, player['sanity'] + 30), player['normal_coins'] - 30, user_id))
    conn.commit(); conn.close()
    return "success"

def train_player(user_id):
    conn = get_db_connection()
    player = conn.execute('SELECT fatigue, normal_coins, xp, level FROM players WHERE user_id = ?', (user_id,)).fetchone()
    if player['normal_coins'] < 50: conn.close(); return "no_coins"
    if player['fatigue'] >= 90: conn.close(); return "too_tired"
        
    new_xp = player['xp'] + 15
    level = player['level']
    level_up = False
    if new_xp >= 100: new_xp -= 100; level += 1; level_up = True
        
    conn.execute('UPDATE players SET fatigue = ?, normal_coins = ?, xp = ?, level = ? WHERE user_id = ?',
                 (min(100, player['fatigue'] + 30), player['normal_coins'] - 50, new_xp, level, user_id))
    conn.commit(); conn.close()
    return {"status": "success", "xp": 15, "level_up": level_up, "new_level": level}

def start_new_match(user_id):
    conn = get_db_connection()
    player = conn.execute('SELECT ego, team_json FROM players WHERE user_id = ?', (user_id,)).fetchone()
    if not player or not json.loads(player['team_json']):
        conn.close(); return "no_team"
        
    team_ids = json.loads(player['team_json'])
    placeholders = ','.join('?' * len(team_ids))
    chars = conn.execute(f'SELECT base_power, is_cursed FROM characters WHERE char_id IN ({placeholders})', team_ids).fetchall()
    
    player_power = sum([c['base_power'] for c in chars]) / len(chars) if chars else 50
    cursed_count = sum([1 for c in chars if c['is_cursed']])
    
    if cursed_count > 0:
        conn.execute('UPDATE players SET sanity = ? WHERE user_id = ?', (max(0, 100 - (cursed_count * 10)), user_id))

    npc_name = random.choice(["Tiger Team", "Kaiser's Team", "Blue Lock 11", "U-20 Japan"])
    npc_power = random.randint(60, 95)
    
    match_state = {"npc_name": npc_name, "npc_power": npc_power, "player_power": player_power,
                   "score_player": 0, "score_npc": 0, "turn": 1, "max_turns": 5, "is_2v2": False}
    
    conn.execute('UPDATE players SET current_match_state = ? WHERE user_id = ?', (json.dumps(match_state), user_id))
    conn.commit(); conn.close()
    return match_state

def start_2v2_match(user_id):
    conn = get_db_connection()
    player = conn.execute('SELECT ego, team_json FROM players WHERE user_id = ?', (user_id,)).fetchone()
    team_ids = json.loads(player['team_json'])
    if len(team_ids) < 2: conn.close(); return "need_2_cards"
        
    match_team_ids = team_ids[:2]
    placeholders = ','.join('?' * len(match_team_ids))
    chars = conn.execute(f'SELECT base_power, is_cursed FROM characters WHERE char_id IN ({placeholders})', match_team_ids).fetchall()
    player_power = sum([c['base_power'] for c in chars]) / len(chars)
    cursed_count = sum([1 for c in chars if c['is_cursed']])
    
    if cursed_count > 0:
        conn.execute('UPDATE players SET sanity = ? WHERE user_id = ?', (max(0, 100 - (cursed_count * 10)), user_id))

    npc_name = random.choice(["تیم کایزر و نس", "تیم سائه و شیدو", "تیم ایساگی و باچیرا"])
    npc_power = random.randint(70, 100)
    
    match_state = {"npc_name": npc_name, "npc_power": npc_power, "player_power": player_power,
                   "score_player": 0, "score_npc": 0, "turn": 1, "max_turns": 3, "is_2v2": True}
    
    conn.execute('UPDATE players SET current_match_state = ? WHERE user_id = ?', (json.dumps(match_state), user_id))
    conn.commit(); conn.close()
    return match_state

def resolve_turn(user_id, action):
    conn = get_db_connection()
    player = conn.execute('SELECT ego, current_match_state FROM players WHERE user_id = ?', (user_id,)).fetchone()
    state = json.loads(player['current_match_state'])
    
    base_chance = (state['player_power'] / (state['player_power'] + state['npc_power'])) * 100
    flow_bonus = 1.5 if player['ego'] >= 90 else 1.0
        
    if action == "shoot": success_chance = (base_chance * 0.6) * flow_bonus; double_chance = 30 if player['ego'] >= 90 else 0
    elif action == "pass": success_chance = base_chance * 1.2; double_chance = 0
    else: success_chance = base_chance * 0.9; double_chance = 0

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
    conn.execute('UPDATE players SET current_match_state = ? WHERE user_id = ?', (json.dumps(state), user_id))
    conn.commit(); conn.close()
    return {"success": True, "text": result_text, "state": state, "is_finished": state['turn'] > state['max_turns']}
def check_synergy(user_id):
    conn = get_db_connection()
    player = conn.execute('SELECT team_json FROM players WHERE user_id = ?', (user_id,)).fetchone()
    if not player or not player['team_json']: conn.close(); return None
    team_ids = json.loads(player['team_json'])
    placeholders = ','.join('?' * len(team_ids))
    chars = conn.execute(f'SELECT synergy_tag FROM characters WHERE char_id IN ({placeholders})', team_ids).fetchall()
    conn.close()
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
    player = conn.execute('SELECT ego, team_json FROM players WHERE user_id = ?', (user_id,)).fetchone()
    if not player or not player['team_json']: conn.close(); return "no_team"
    team_ids = json.loads(player['team_json'])
    placeholders = ','.join('?' * len(team_ids))
    chars = conn.execute(f'SELECT name, synergy_tag FROM characters WHERE char_id IN ({placeholders})', team_ids).fetchall()
    conn.close()
    
    jealousy_chance = 30 if player['ego'] > 70 else 15 if player['ego'] > 50 else 0
    for c in chars:
        if c['synergy_tag'] in ['shidou', 'rin', 'kaiser', 'barou', 'karasu', 'lorenzo']:
            jealousy_chance += 15 
            
    if random.randint(1, 100) <= jealousy_chance:
        return {"status": "betrayed", "name": random.choice(chars)['name']}
    return {"status": "loyal"}

def finish_match_rewards(user_id, score_player, score_npc):
    conn = get_db_connection()
    player = conn.execute('SELECT normal_coins, xp, level FROM players WHERE user_id = ?', (user_id,)).fetchone()
    
    if score_player > score_npc: reward_coins, reward_xp, result_msg = 50, 20, "🎉 **تو بردی!**\n+۵۰ سکه\n+۲۰ XP"
    elif score_player == score_npc: reward_coins, reward_xp, result_msg = 20, 10, "🤝 **مساوی!**\n+۲۰ سکه\n+۱۰ XP"
    else: reward_coins, reward_xp, result_msg = 5, 5, "💀 **باختی!**\n+۵ سکه\n+۵ XP"
        
    new_xp = player['xp'] + reward_xp
    level = player['level']
    level_up_msg = ""
    if new_xp >= 100: new_xp -= 100; level += 1; level_up_msg = f"\n\n🌟 **سطح {level}!**"
        
    conn.execute('UPDATE players SET normal_coins = ?, xp = ?, level = ? WHERE user_id = ?', 
                 (player['normal_coins'] + reward_coins, new_xp, level, user_id))
    conn.commit(); conn.close()
    return result_msg + level_up_msg

def generate_coach_mission(user_id):
    conn = get_db_connection()
    active = conn.execute('SELECT * FROM coach_missions WHERE player_id = ? AND is_active = 1', (user_id,)).fetchone()
    if active: conn.close(); return dict(active)
    missions = [{"type": "lose_on_purpose", "target": "any", "text": "در بازی بعدی بباز."},
                {"type": "take_shots", "target": "any", "text": "در بازی بعدی، حداقل ۳ بار خودت شوت بزن."}]
    mission = random.choice(missions)
    conn.execute('INSERT INTO coach_missions (player_id, mission_type, target_name) VALUES (?, ?, ?)', (user_id, mission['type'], mission['target']))
    conn.commit(); conn.close()
    return mission

def check_coach_mission(user_id, match_result):
    conn = get_db_connection()
    mission = conn.execute('SELECT * FROM coach_missions WHERE player_id = ? AND is_active = 1', (user_id,)).fetchone()
    if not mission: conn.close(); return "no_mission"
    success = (mission['mission_type'] == "lose_on_purpose" and match_result == "lose")
    
    if success:
        player = conn.execute('SELECT ego, normal_coins FROM players WHERE user_id = ?', (user_id,)).fetchone()
        conn.execute('UPDATE players SET ego = ?, normal_coins = ? WHERE user_id = ?', (min(100, player['ego'] + 15), player['normal_coins'] + 100, user_id))
        conn.execute('UPDATE coach_missions SET is_active = 0, is_completed = 1 WHERE mission_id = ?', (mission['mission_id'],))
        conn.commit(); conn.close(); return "success"
    else:
        player = conn.execute('SELECT ego, pressure FROM players WHERE user_id = ?', (user_id,)).fetchone()
        conn.execute('UPDATE players SET ego = ?, pressure = ? WHERE user_id = ?', (max(0, player['ego'] - 20), min(100, player['pressure'] + 30), user_id))
        conn.execute('UPDATE coach_missions SET is_active = 0 WHERE mission_id = ?', (mission['mission_id'],))
        conn.commit(); conn.close(); return "failed"

def enter_shadow_league(user_id):
    conn = get_db_connection()
    conn.execute('UPDATE players SET in_shadow_league = 1, shadow_wins = 0, sanity = 50 WHERE user_id = ?', (user_id,))
    conn.commit(); conn.close()

def shadow_league_result(user_id, is_win):
    conn = get_db_connection()
    player = conn.execute('SELECT shadow_wins, sanity FROM players WHERE user_id = ?', (user_id,)).fetchone()
    if is_win:
        new_wins = player['shadow_wins'] + 1
        if new_wins >= 3:
            conn.execute('UPDATE players SET in_shadow_league = 0, shadow_wins = 0, ego = 100 WHERE user_id = ?', (user_id,))
            conn.commit(); conn.close(); return "freed"
        conn.execute('UPDATE players SET shadow_wins = ? WHERE user_id = ?', (new_wins, user_id))
        conn.commit(); conn.close(); return f"win_{new_wins}"
    else:
        conn.execute('UPDATE players SET shadow_wins = 0, sanity = ? WHERE user_id = ?', (max(0, player['sanity'] - 40), user_id))
        conn.commit(); conn.close(); return "lose"

def use_wild_card(user_id, char_id_to_burn):
    conn = get_db_connection()
    player = conn.execute('SELECT team_json FROM players WHERE user_id = ?', (user_id,)).fetchone()
    team = json.loads(player['team_json'])
    if char_id_to_burn not in team: conn.close(); return "not_in_team"
    team.remove(char_id_to_burn)
    legendary = conn.execute('SELECT * FROM characters WHERE rarity = "Legendary" ORDER BY RANDOM() LIMIT 1').fetchone()
    team.append(legendary['char_id'])
    conn.execute('UPDATE players SET team_json = ? WHERE user_id = ?', (json.dumps(team), user_id))
    conn.commit(); conn.close()
    return dict(legendary)

def get_player_team(user_id):
    conn = get_db_connection()
    player = conn.execute('SELECT team_json FROM players WHERE user_id = ?', (user_id,)).fetchone()
    if not player or not player['team_json']: conn.close(); return []
    team_ids = json.loads(player['team_json'])
    if not team_ids: conn.close(); return []
    placeholders = ','.join('?' * len(team_ids))
    chars = conn.execute(f'SELECT * FROM characters WHERE char_id IN ({placeholders})', team_ids).fetchall()
    conn.close()
    return [dict(c) for c in chars]

def remove_from_team(user_id, char_id):
    conn = get_db_connection()
    player = conn.execute('SELECT team_json FROM players WHERE user_id = ?', (user_id,)).fetchone()
    if player and player['team_json']:
        team = json.loads(player['team_json'])
        if char_id in team:
            team.remove(char_id)
            conn.execute('UPDATE players SET team_json = ? WHERE user_id = ?', (json.dumps(team), user_id))
            conn.commit(); conn.close(); return True
    conn.close(); return False

def get_leaderboard(limit=10):
    conn = get_db_connection()
    players = conn.execute('SELECT username, level, xp FROM players ORDER BY level DESC, xp DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return [dict(p) for p in players]

def get_player_rank(user_id):
    conn = get_db_connection()
    player = conn.execute('SELECT level, xp FROM players WHERE user_id = ?', (user_id,)).fetchone()
    if not player: conn.close(); return None
    rank = conn.execute('SELECT COUNT(*) + 1 FROM players WHERE level > ? OR (level = ? AND xp > ?)', (player['level'], player['level'], player['xp'])).fetchone()[0]
    conn.close(); return rank