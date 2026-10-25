from database import get_db_connection

def seed_characters():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # چک میکنه اگه کاراکترها از قبل وجود دارن، کاری نکنه
    cur.execute("SELECT COUNT(*) as count FROM characters")
    if cur.fetchone()['count'] > 0:
        print("⚠️ کاراکترها از قبل وجود دارند.")
        cur.close()
        conn.close()
        return

    characters_data = [
        # ==========================================
        # ⚪ World Class
        # ==========================================
        ("Noel Noa", "FW", "Machine Dribble", 98, "World Class", False, "noa"),
        ("Julian Loki", "FW", "God Speed", 95, "World Class", False, "loki"),
        ("Leonardo Luna", "FW", "Phantom Shot", 94, "World Class", False, "luna"),
        ("Chris Prince", "FW", "Perfect Body", 94, "World Class", False, "prince"),
        ("Lavinho", "FW", "Brazilian Technique", 93, "World Class", False, "lavinho"),
        ("Mark Snuffy", "MF", "Vision", 85, "World Class", False, "snuffy"), 
        ("Dada Silva", "DF", "Strength", 79, "World Class", False, "dada"), 
        ("Pablo Cavasoz", "FW", "Agility", 84, "World Class", False, "cavasoz"),

        # ==========================================
        # 🔴 Mythic
        # ==========================================
        ("Yoichi Isagi", "FW", "Direct Shot", 92, "Mythic", False, "isagi"),
        ("Michael Kaiser", "FW", "Kaiser Impact", 97, "Mythic", True, "kaiser"),
        ("Sae Itoshi", "MF", "Precision Pass", 96, "Mythic", False, "sae"),
        ("Rin Itoshi", "MF", "Puppet Control", 95, "Mythic", True, "rin"),
        ("Don Lorenzo", "DF", "Zombie Defense", 92, "Mythic", True, "lorenzo"),
        ("Teddy Knight", "DF", "Iron Wall", 86, "Mythic", False, "teddy"),
        ("Ryusei Shidou", "FW", "Bicycle Kick", 96, "Mythic", True, "shidou"),
        ("Bunny Iglesias", "FW", "Acrobatic", 82, "Mythic", False, "bunny"),
        ("Reo Mikage", "MF", "Copycat", 86, "Mythic", False, "mikage"),
        ("Vivian Hugo", "MF", "Pass", 78, "Mythic", False, "hugo"), 

        # ==========================================
        # 🟡 Legendary
        # ==========================================
        ("Seishiro Nagi", "FW", "Trap & Volley", 89, "Legendary", False, "nagi"),
        ("Shoei Barou", "FW", "Chop Dribble", 88, "Legendary", True, "barou"),
        ("Lockhart", "FW", "Iron Knight", 85, "Legendary", False, "lockhart"),
        ("Kenyu Yukimiya", "MF", "Gyro Shot", 84, "Legendary", False, "yukimiya"),
        ("Oliver Aiku", "DF", "Defensive Vision", 88, "Legendary", False, "aiku"),
        ("Rensuke Kunigami", "FW", "Left Leg Shot", 86, "Legendary", False, "kunigami"),
        ("Jin Kiyora", "MF", "Shoot", 80, "Legendary", False, "kiyora"),
        ("Ikki Niko", "DF", "Tactical Foul", 80, "Legendary", False, "niko"),

        # ==========================================
        # 🟣 Epic
        # ==========================================
        ("Meguru Bachira", "FW", "Dribble", 88, "Epic", False, "bachira"),
        ("Hyoma Chigiri", "FW", "Speed Dribble", 87, "Epic", False, "chigiri"),
        ("Tabito Karasu", "MF", "Trap", 86, "Epic", True, "karasu"),
        ("Hiori Yo", "MF", "Meta Vision", 85, "Epic", False, "hiori"),
        ("Jyubei Aryu", "DF", "Long Legs", 82, "Epic", False, "aryu"),
        ("Gin Gagamaru", "GK", "Wild Reflexes", 86, "Epic", False, "gagagmaru"),
        ("Akira Endoji", "GK", "Iron Wall", 84, "Epic", False, "endoji"),

        # ==========================================
        # 🔵 Rare
        # ==========================================
        ("Shuto Sendou", "FW", "Acrobatic Shot", 83, "Rare", False, "sendou"),
        ("Aoshi Tokimitsu", "FW", "Power Shot", 82, "Rare", False, "tokimitsu"),
        ("Gurimu Igarashi", "FW", "Header", 70, "Rare", False, "igarashi"),
        ("Otoya Eita", "MF", "Stealth", 83, "Rare", False, "otoya"),
        ("Tsurugi Zantetsu", "MF", "Speed", 80, "Rare", False, "zantetsu"),
        ("Nijiro Nanase", "MF", "Stamina", 78, "Rare", False, "nanase"),
        ("Kusu", "MF", "Pass", 76, "Rare", False, "kusu"),
        ("Ranze Kurona", "DF", "Agility", 78, "Rare", False, "kurona"),
        ("Sengoku Miroku", "DF", "Block", 75, "Rare", False, "miroku"),
        ("Wataru Kuon", "DF", "Tackle", 75, "Rare", False, "kuon"),
        ("Fukaku", "GK", "Save", 78, "Rare", False, "fukaku"),
        ("Kazuma Nio", "GK", "Reaction", 76, "Rare", False, "nio"),
    ]

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