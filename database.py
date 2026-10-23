import json
import random
import os
from supadns import create_smart_client as create_client
from supabase import Client

# 🔴 کلیدها از تنظیمات Render (Environment Variables) خوانده می‌شوند
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# اتصال به دیتابیس با استفاده از supadns برای حل مشکل DNS در Render
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_player(user_id):
    response = supabase.table('players').select('*').eq('user_id', user_id).execute()
    return response.data[0] if response.data else None

def create_player(user_id, username):
    data = {'user_id': user_id, 'username': username}
    response = supabase.table('players').select('*').eq('user_id', user_id).execute()
    if not response.data:
        supabase.table('players').insert(data).execute()

def init_db():
    print("✅ اتصال به Supabase برقرار است.")

def perform_gacha(user_id, cost=100):
    player = get_player(user_id)
    if not player: return "no_player"
    if player['normal_coins'] < cost: return "no_coins"

    new_coins = player['normal_coins'] - cost
    supabase.table('players').update({'normal_coins': new_coins}).eq('user_id', user_id).execute()

    roll = random.random()
    if roll <= 0.03: rarity = 'Legendary'
    elif roll <= 0.25: rarity = 'Epic'
    else: rarity = 'Rare'

    char_response = supabase.table('characters').select('*').eq('rarity', rarity).execute()
    if not char_response.data: return "no_chars"
    
    char = random.choice(char_response.data)
    
    team = player['team_json'] if player['team_json'] else []
    team.append(char['char_id'])
    supabase.table('players').update({'team_json': team}).eq('user_id', user_id).execute()
    return char

def rest_player(user_id):
    player = get_player(user_id)
    if player['normal_coins'] < 30: return "no_coins"
    updates = {
        'fatigue': max(0, player['fatigue'] - 40),
        'pressure': max(0, player['pressure'] - 40),
        'sanity': min(100, player['sanity'] + 30),
        'normal_coins': player['normal_coins'] - 30
    }
    supabase.table('players').update(updates).eq('user_id', user_id).execute()
    return "success"

def train_player(user_id):
    player = get_player(user_id)
    if player['normal_coins'] < 50: return "no_coins"
    if player['fatigue'] >= 90: return "too_tired"

    new_xp = player['xp'] + 15
    level = player['level']
    level_up = False
    if new_xp >= 100:
        new_xp -= 100
        level += 1
        level_up = True

    updates = {
        'fatigue': min(100, player['fatigue'] + 30),
        'normal_coins': player['normal_coins'] - 50,
        'xp': new_xp,
        'level': level
    }
    supabase.table('players').update(updates).eq('user_id', user_id).execute()
    return {"status": "success", "xp": 15, "level_up": level_up, "new_level": level}

def start_new_match(user_id):
    player = get_player(user_id)
    if not player or not player['team_json']: return "no_team"
    
    team_ids = player['team_json']
    chars = supabase.table('characters').select('*').in_('char_id', team_ids).execute().data
    
    player_power = sum([c['base_power'] for c in chars]) / len(chars) if chars else 50
    cursed_count = sum([1 for c in chars if c['is_cursed']])
    
    if cursed_count > 0:
        supabase.table('players').update({'sanity': max(0, 100 - (cursed_count * 10))}).eq('user_id', user_id).execute()

    npc_name = random.choice(["Tiger Team", "Kaiser's Team", "Blue Lock 11", "U-20 Japan"])
    npc_power = random.randint(60, 95)
    
    match_state = {
        "npc_name": npc_name, "npc_power": npc_power, "player_power": player_power,
        "score_player": 0, "score_npc": 0, "turn": 1, "max_turns": 5, "is_2v2": False
    }
    
    supabase.table('players').update({'current_match_state': match_state}).eq('user_id', user_id).execute()
    return match_state

def start_2v2_match(user_id):
    player = get_player(user_id)
    if len(player['team_json']) < 2: return "need_2_cards"
    
    match_team_ids = player['team_json'][:2]
    chars = supabase.table('characters').select('*').in_('char_id', match_team_ids).execute().data
    player_power = sum([c['base_power'] for c in chars]) / len(chars)
    cursed_count = sum([1 for c in chars if c['is_cursed']])
    
    if cursed_count > 0:
        supabase.table('players').update({'sanity': max(0, 100 - (cursed_count * 10))}).eq('user_id', user_id).execute()

    npc_name = random.choice(["تیم کایزر و نس", "تیم سائه و شیدو", "تیم ایساگی و باچیرا"])
    npc_power = random.randint(70, 100)
    
    match_state = {
        "npc_name": npc_name, "npc_power": npc_power, "player_power": player_power,
        "score_player": 0, "score_npc": 0, "turn": 1, "max_turns": 3, "is_2v2": True
    }
    
    supabase.table('players').update({'current_match_state': match_state}).eq('user_id', user_id).execute()
    return match_state

def resolve_turn(user_id, action):
    player = get_player(user_id)
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
    supabase.table('players').update({'current_match_state': state}).eq('user_id', user_id).execute()
    return {"success": True, "text": result_text, "state": state, "is_finished": state['turn'] > state['max_turns']}

def check_synergy(user_id):
    player = get_player(user_id)
    if not player or not player['team_json']: return None
    
    chars = supabase.table('characters').select('synergy_tag').in_('char_id', player['team_json']).execute().data
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
    player = get_player(user_id)
    if not player or not player['team_json']: return "no_team"
    
    chars = supabase.table('characters').select('name, synergy_tag').in_('char_id', player['team_json']).execute().data
    jealousy_chance = 30 if player['ego'] > 70 else 15 if player['ego'] > 50 else 0
    for c in chars:
        if c['synergy_tag'] in ['shidou', 'rin', 'kaiser', 'barou', 'karasu', 'lorenzo']:
            jealousy_chance += 15 
            
    if random.randint(1, 100) <= jealousy_chance:
        return {"status": "betrayed", "name": random.choice(chars)['name']}
    return {"status": "loyal"}

def finish_match_rewards(user_id, score_player, score_npc):
    player = get_player(user_id)
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
        
    supabase.table('players').update({
        'normal_coins': player['normal_coins'] + reward_coins, 
        'xp': new_xp, 
        'level': level
    }).eq('user_id', user_id).execute()
    
    return result_msg + level_up_msg

def generate_coach_mission(user_id):
    active = supabase.table('coach_missions').select('*').eq('player_id', user_id).eq('is_active', True).execute().data
    if active: return active[0]
    
    missions = [{"type": "lose_on_purpose", "target": "any", "text": "در بازی بعدی بباز."},
                {"type": "take_shots", "target": "any", "text": "در بازی بعدی، حداقل ۳ بار خودت شوت بزن."}]
    mission = random.choice(missions)
    mission['player_id'] = user_id
    supabase.table('coach_missions').insert(mission).execute()
    return mission

def check_coach_mission(user_id, match_result):
    mission = supabase.table('coach_missions').select('*').eq('player_id', user_id).eq('is_active', True).execute().data
    if not mission: return "no_mission"
    mission = mission[0]
    
    success = (mission['mission_type'] == "lose_on_purpose" and match_result == "lose")
    player = get_player(user_id)
    
    if success:
        supabase.table('players').update({
            'ego': min(100, player['ego'] + 15), 
            'normal_coins': player['normal_coins'] + 100
        }).eq('user_id', user_id).execute()
        supabase.table('coach_missions').update({'is_active': False, 'is_completed': True}).eq('mission_id', mission['mission_id']).execute()
        return "success"
    else:
        supabase.table('players').update({
            'ego': max(0, player['ego'] - 20), 
            'pressure': min(100, player['pressure'] + 30)
        }).eq('user_id', user_id).execute()
        supabase.table('coach_missions').update({'is_active': False}).eq('mission_id', mission['mission_id']).execute()
        return "failed"

def enter_shadow_league(user_id):
    supabase.table('players').update({'in_shadow_league': True, 'shadow_wins': 0, 'sanity': 50}).eq('user_id', user_id).execute()

def shadow_league_result(user_id, is_win):
    player = get_player(user_id)
    if is_win:
        new_wins = player['shadow_wins'] + 1
        if new_wins >= 3:
            supabase.table('players').update({'in_shadow_league': False, 'shadow_wins': 0, 'ego': 100}).eq('user_id', user_id).execute()
            return "freed"
        supabase.table('players').update({'shadow_wins': new_wins}).eq('user_id', user_id).execute()
        return f"win_{new_wins}"
    else:
        supabase.table('players').update({'shadow_wins': 0, 'sanity': max(0, player['sanity'] - 40)}).eq('user_id', user_id).execute()
        return "lose"

def use_wild_card(user_id, char_id_to_burn):
    player = get_player(user_id)
    team = player['team_json'] if player['team_json'] else []
    if char_id_to_burn not in team: return "not_in_team"
    
    team.remove(char_id_to_burn)
    legendary = supabase.table('characters').select('*').eq('rarity', 'Legendary').execute().data
    if not legendary: return "no_legendary"
    
    new_char = random.choice(legendary)
    team.append(new_char['char_id'])
    supabase.table('players').update({'team_json': team}).eq('user_id', user_id).execute()
    return new_char

def get_player_team(user_id):
    player = get_player(user_id)
    if not player or not player['team_json']: return []
    
    chars = supabase.table('characters').select('*').in_('char_id', player['team_json']).execute().data
    return chars

def remove_from_team(user_id, char_id):
    player = get_player(user_id)
    team = player['team_json'] if player['team_json'] else []
    if char_id in team:
        team.remove(char_id)
        supabase.table('players').update({'team_json': team}).eq('user_id', user_id).execute()
        return True
    return False

def get_leaderboard(limit=10):
    response = supabase.table('players').select('username, level, xp').order('level', desc=True).order('xp', desc=True).limit(limit).execute()
    return response.data

def get_player_rank(user_id):
    player = get_player(user_id)
    if not player: return None
    response = supabase.table('players').select('user_id', count='exact').or_(f"level.gt.{player['level']},and(level.eq.{player['level']},xp.gt.{player['xp']})").execute()
    return response.count + 1 if response.count is not None else 1