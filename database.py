from database import get_db_connection

def seed_characters():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # چک می‌کنیم اگه کارت‌ها از قبل توی دیتابیس هستن، دوباره اضافه نشن
    cur.execute("SELECT COUNT(*) FROM characters")
    if cur.fetchone()['count'] > 0:
        print("⚠️ کاراکترها از قبل وجود دارند و نیازی به اضافه کردن مجدد نیست.")
        cur.close()
        conn.close()
        return

    characters_data = [
        # ==========================================
        # ⚽ مهاجمین (Forwards)
        # ==========================================
        # Legendary
        ("Noel Noa", "FW", "Machine Dribble", 98, "Legendary", False, "noa"),
        ("Michael Kaiser", "FW", "Kaiser Impact", 97, "Legendary", True, "kaiser"),
        ("Julian Loki", "FW", "God Speed", 95, "Legendary", False, "loki"),
        ("Leonardo Luna", "FW", "Phantom Shot", 94, "Legendary", False, "luna"),
        ("Chris Prince", "FW", "Perfect Body", 94, "Legendary", False, "prince"),
        ("Lavinho", "FW", "Brazilian Technique", 93, "Legendary", False, "lavinho"),
        ("Yoichi Isagi", "FW", "Direct Shot", 92, "Legendary", False, "isagi"),
        
        # Epic
        ("Ryusei Shidou", "FW", "Bicycle Kick", 96, "Epic", True, "shidou"),
        ("Seishiro Nagi", "FW", "Trap & Volley", 89, "Epic", False, "nagi"),
        ("Meguru Bachira", "FW", "Dribble", 88, "Epic", False, "bachira"),
        ("Shoei Barou", "FW", "Chop Dribble", 88, "Epic", True, "barou"),
        ("Hyoma Chigiri", "FW", "Speed Dribble", 87, "Epic", False, "chigiri"),
        ("Rensuke Kunigami", "FW", "Left Leg Shot", 86, "Epic", False, "kunigami"),
        ("Lockhart", "FW", "Iron Knight", 85, "Epic", False, "lockhart"),
        ("Pablo Cavasoz", "FW", "Agility", 84, "Epic", False, "cavasoz"),
        ("Bunny Iglesias", "FW", "Acrobatic", 82, "Epic", False, "bunny"),
        
        # Rare
        ("Shuto Sendou", "FW", "Acrobatic Shot", 83, "Rare", False, "sendou"),
        ("Aoshi Tokimitsu", "FW", "Power Shot", 82, "Rare", False, "tokimitsu"),
        ("Gurimu Igarashi", "FW", "Header", 70, "Rare", False, "igarashi"),

        # ==========================================
        # 🎯 هافبک‌ها (Midfielders)
        # ==========================================
        # Legendary
        ("Sae Itoshi", "MF", "Precision Pass", 96, "Legendary", False, "sae"),
        ("Rin Itoshi", "MF", "Puppet Control", 95, "Legendary", True, "rin"),
        ("Charles Chevalier", "MF", "Genius Pass", 92, "Legendary", False, "charles"),
        ("Alexis Ness", "MF", "Magic Pass", 90, "Legendary", False, "ness"),
        
        # Epic
        ("Reo Mikage", "MF", "Copycat", 86, "Epic", False, "mikage"),
        ("Tabito Karasu", "MF", "Trap", 86, "Epic", True, "karasu"),
        ("Hiori Yo", "MF", "Meta Vision", 85, "Epic", False, "hiori"),
        ("Mark Snuffy", "MF", "Vision", 85, "Epic", False, "snuffy"), 
        ("Kenyu Yukimiya", "MF", "Gyro Shot", 84, "Epic", False, "yukimiya"),
        ("Vivian Hugo", "MF", "Pass", 78, "Epic", False, "hugo"), 
        
        # Rare
        ("Otoya Eita", "MF", "Stealth", 83, "Rare", False, "otoya"),
        ("Tsurugi Zantetsu", "MF", "Speed", 80, "Rare", False, "zantetsu"),
        ("Jin Kiyora", "MF", "Shoot", 80, "Rare", False, "kiyora"),
        ("Nijiro Nanase", "MF", "Stamina", 78, "Rare", False, "nanase"),
        ("Kusu", "MF", "Pass", 76, "Rare", False, "kusu"),

        # ==========================================
        # 🛡️ مدافعین (Defenders)
        # ==========================================
        # Legendary
        ("Don Lorenzo", "DF", "Zombie Defense", 92, "Legendary", True, "lorenzo"),
        
        # Epic
        ("Oliver Aiku", "DF", "Defensive Vision", 88, "Epic", False, "aiku"),
        ("Teddy Knight", "DF", "Iron Wall", 86, "Epic", False, "teddy"),
        ("Jyubei Aryu", "DF", "Long Legs", 82, "Epic", False, "aryu"),
        ("Dada Silva", "DF", "Strength", 79, "Epic", False, "dada"), 
        
        # Rare
        ("Ikki Niko", "DF", "Tactical Foul", 80, "Rare", False, "niko"),
        ("Ranze Kurona", "DF", "Agility", 78, "Rare", False, "kurona"),
        ("Sengoku Miroku", "DF", "Block", 75, "Rare", False, "miroku"),
        ("Wataru Kuon", "DF", "Tackle", 75, "Rare", False, "kuon"),

        # ==========================================
        # 🧤 دروازه‌بان‌ها (Goalkeepers)
        # ==========================================
        # Epic
        ("Gin Gagamaru", "GK", "Wild Reflexes", 86, "Epic", False, "gagamaru"),
        ("Akira Endoji", "GK", "Iron Wall", 84, "Epic", False, "endoji"),
        
        # Rare
        ("Fukaku", "GK", "Save", 78, "Rare", False, "fukaku"),
        ("Kazuma Nio", "GK", "Reaction", 76, "Rare", False, "nio"),
    ]

    # درج تمام کارت‌ها در دیتابیس
    for char in characters_data:
        cur.execute('''
            INSERT INTO characters (name, position, technique, base_power, rarity, is_cursed, synergy_tag)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', char)
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ {len(characters_data)} کاراکتر با موفقیت وارد دیتابیس شد.")

if __name__ == "__main__":
    seed_characters()