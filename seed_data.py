from database import supabase

def seed_characters():
    # چک می‌کنیم اگه کارت‌ها از قبل توی دیتابیس هستن، دوباره اضافه نشن
    existing = supabase.table('characters').select('char_id').limit(1).execute()
    if existing.data:
        print("⚠️ کاراکترها از قبل وجود دارند و نیازی به اضافه کردن مجدد نیست.")
        return

    characters_data = [
        # ==========================================
        # ⚽ مهاجمین (Forwards)
        # ==========================================
        # Legendary
        {"name": "Noel Noa", "position": "FW", "technique": "Machine Dribble", "base_power": 98, "rarity": "Legendary", "is_cursed": False, "synergy_tag": "noa"},
        {"name": "Michael Kaiser", "position": "FW", "technique": "Kaiser Impact", "base_power": 97, "rarity": "Legendary", "is_cursed": True, "synergy_tag": "kaiser"},
        {"name": "Julian Loki", "position": "FW", "technique": "God Speed", "base_power": 95, "rarity": "Legendary", "is_cursed": False, "synergy_tag": "loki"},
        {"name": "Leonardo Luna", "position": "FW", "technique": "Phantom Shot", "base_power": 94, "rarity": "Legendary", "is_cursed": False, "synergy_tag": "luna"},
        {"name": "Chris Prince", "position": "FW", "technique": "Perfect Body", "base_power": 94, "rarity": "Legendary", "is_cursed": False, "synergy_tag": "prince"},
        {"name": "Lavinho", "position": "FW", "technique": "Brazilian Technique", "base_power": 93, "rarity": "Legendary", "is_cursed": False, "synergy_tag": "lavinho"},
        {"name": "Yoichi Isagi", "position": "FW", "technique": "Direct Shot", "base_power": 92, "rarity": "Legendary", "is_cursed": False, "synergy_tag": "isagi"},
        
        # Epic
        {"name": "Ryusei Shidou", "position": "FW", "technique": "Bicycle Kick", "base_power": 96, "rarity": "Epic", "is_cursed": True, "synergy_tag": "shidou"},
        {"name": "Seishiro Nagi", "position": "FW", "technique": "Trap & Volley", "base_power": 89, "rarity": "Epic", "is_cursed": False, "synergy_tag": "nagi"},
        {"name": "Meguru Bachira", "position": "FW", "technique": "Dribble", "base_power": 88, "rarity": "Epic", "is_cursed": False, "synergy_tag": "bachira"},
        {"name": "Shoei Barou", "position": "FW", "technique": "Chop Dribble", "base_power": 88, "rarity": "Epic", "is_cursed": True, "synergy_tag": "barou"},
        {"name": "Hyoma Chigiri", "position": "FW", "technique": "Speed Dribble", "base_power": 87, "rarity": "Epic", "is_cursed": False, "synergy_tag": "chigiri"},
        {"name": "Rensuke Kunigami", "position": "FW", "technique": "Left Leg Shot", "base_power": 86, "rarity": "Epic", "is_cursed": False, "synergy_tag": "kunigami"},
        {"name": "Lockhart", "position": "FW", "technique": "Iron Knight", "base_power": 85, "rarity": "Epic", "is_cursed": False, "synergy_tag": "lockhart"},
        {"name": "Pablo Cavasoz", "position": "FW", "technique": "Agility", "base_power": 84, "rarity": "Epic", "is_cursed": False, "synergy_tag": "cavasoz"},
        {"name": "Bunny Iglesias", "position": "FW", "technique": "Acrobatic", "base_power": 82, "rarity": "Epic", "is_cursed": False, "synergy_tag": "bunny"},
        
        # Rare
        {"name": "Shuto Sendou", "position": "FW", "technique": "Acrobatic Shot", "base_power": 83, "rarity": "Rare", "is_cursed": False, "synergy_tag": "sendou"},
        {"name": "Aoshi Tokimitsu", "position": "FW", "technique": "Power Shot", "base_power": 82, "rarity": "Rare", "is_cursed": False, "synergy_tag": "tokimitsu"},
        {"name": "Gurimu Igarashi", "position": "FW", "technique": "Header", "base_power": 70, "rarity": "Rare", "is_cursed": False, "synergy_tag": "igarashi"},

        # ==========================================
        # 🎯 هافبک‌ها (Midfielders)
        # ==========================================
        # Legendary
        {"name": "Sae Itoshi", "position": "MF", "technique": "Precision Pass", "base_power": 96, "rarity": "Legendary", "is_cursed": False, "synergy_tag": "sae"},
        {"name": "Rin Itoshi", "position": "MF", "technique": "Puppet Control", "base_power": 95, "rarity": "Legendary", "is_cursed": True, "synergy_tag": "rin"},
        {"name": "Charles Chevalier", "position": "MF", "technique": "Genius Pass", "base_power": 92, "rarity": "Legendary", "is_cursed": False, "synergy_tag": "charles"},
        {"name": "Alexis Ness", "position": "MF", "technique": "Magic Pass", "base_power": 90, "rarity": "Legendary", "is_cursed": False, "synergy_tag": "ness"},
        
        # Epic
        {"name": "Reo Mikage", "position": "MF", "technique": "Copycat", "base_power": 86, "rarity": "Epic", "is_cursed": False, "synergy_tag": "mikage"},
        {"name": "Tabito Karasu", "position": "MF", "technique": "Trap", "base_power": 86, "rarity": "Epic", "is_cursed": True, "synergy_tag": "karasu"},
        {"name": "Hiori Yo", "position": "MF", "technique": "Meta Vision", "base_power": 85, "rarity": "Epic", "is_cursed": False, "synergy_tag": "hiori"},
        {"name": "Mark Snuffy", "position": "MF", "technique": "Vision", "base_power": 85, "rarity": "Epic", "is_cursed": False, "synergy_tag": "snuffy"}, 
        {"name": "Kenyu Yukimiya", "position": "MF", "technique": "Gyro Shot", "base_power": 84, "rarity": "Epic", "is_cursed": False, "synergy_tag": "yukimiya"},
        {"name": "Vivian Hugo", "position": "MF", "technique": "Pass", "base_power": 78, "rarity": "Epic", "is_cursed": False, "synergy_tag": "hugo"}, 
        
        # Rare
        {"name": "Otoya Eita", "position": "MF", "technique": "Stealth", "base_power": 83, "rarity": "Rare", "is_cursed": False, "synergy_tag": "otoya"},
        {"name": "Tsurugi Zantetsu", "position": "MF", "technique": "Speed", "base_power": 80, "rarity": "Rare", "is_cursed": False, "synergy_tag": "zantetsu"},
        {"name": "Jin Kiyora", "position": "MF", "technique": "Shoot", "base_power": 80, "rarity": "Rare", "is_cursed": False, "synergy_tag": "kiyora"},
        {"name": "Nijiro Nanase", "position": "MF", "technique": "Stamina", "base_power": 78, "rarity": "Rare", "is_cursed": False, "synergy_tag": "nanase"},
        {"name": "Kusu", "position": "MF", "technique": "Pass", "base_power": 76, "rarity": "Rare", "is_cursed": False, "synergy_tag": "kusu"},

        # ==========================================
        # 🛡️ مدافعین (Defenders)
        # ==========================================
        # Legendary
        {"name": "Don Lorenzo", "position": "DF", "technique": "Zombie Defense", "base_power": 92, "rarity": "Legendary", "is_cursed": True, "synergy_tag": "lorenzo"},
        
        # Epic
        {"name": "Oliver Aiku", "position": "DF", "technique": "Defensive Vision", "base_power": 88, "rarity": "Epic", "is_cursed": False, "synergy_tag": "aiku"},
        {"name": "Teddy Knight", "position": "DF", "technique": "Iron Wall", "base_power": 86, "rarity": "Epic", "is_cursed": False, "synergy_tag": "teddy"},
        {"name": "Jyubei Aryu", "position": "DF", "technique": "Long Legs", "base_power": 82, "rarity": "Epic", "is_cursed": False, "synergy_tag": "aryu"},
        {"name": "Dada Silva", "position": "DF", "technique": "Strength", "base_power": 79, "rarity": "Epic", "is_cursed": False, "synergy_tag": "dada"}, 
        
        # Rare
        {"name": "Ikki Niko", "position": "DF", "technique": "Tactical Foul", "base_power": 80, "rarity": "Rare", "is_cursed": False, "synergy_tag": "niko"},
        {"name": "Ranze Kurona", "position": "DF", "technique": "Agility", "base_power": 78, "rarity": "Rare", "is_cursed": False, "synergy_tag": "kurona"},
        {"name": "Sengoku Miroku", "position": "DF", "technique": "Block", "base_power": 75, "rarity": "Rare", "is_cursed": False, "synergy_tag": "miroku"},
        {"name": "Wataru Kuon", "position": "DF", "technique": "Tackle", "base_power": 75, "rarity": "Rare", "is_cursed": False, "synergy_tag": "kuon"},

        # ==========================================
        # 🧤 دروازه‌بان‌ها (Goalkeepers)
        # ==========================================
        # Epic
        {"name": "Gin Gagamaru", "position": "GK", "technique": "Wild Reflexes", "base_power": 86, "rarity": "Epic", "is_cursed": False, "synergy_tag": "gagamaru"},
        {"name": "Akira Endoji", "position": "GK", "technique": "Iron Wall", "base_power": 84, "rarity": "Epic", "is_cursed": False, "synergy_tag": "endoji"},
        
        # Rare
        {"name": "Fukaku", "position": "GK", "technique": "Save", "base_power": 78, "rarity": "Rare", "is_cursed": False, "synergy_tag": "fukaku"},
        {"name": "Kazuma Nio", "position": "GK", "technique": "Reaction", "base_power": 76, "rarity": "Rare", "is_cursed": False, "synergy_tag": "nio"},
    ]

    # درج تمام کارت‌ها در یک درخواست به Supabase
    response = supabase.table('characters').insert(characters_data).execute()
    print(f"✅ {len(response.data)} کاراکتر با موفقیت وارد دیتابیس شد.")

if __name__ == "__main__":
    seed_characters()