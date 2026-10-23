from database import get_db_connection

def seed_characters():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM characters")
    
    characters_data = [
        # مهاجمین
        ("Noel Noa", "FW", "Machine Dribble", 98, "Legendary", 0, "noa"),
        ("Michael Kaiser", "FW", "Kaiser Impact", 97, "Legendary", 1, "kaiser"),
        ("Julian Loki", "FW", "God Speed", 95, "Legendary", 0, "loki"),
        ("Leonardo Luna", "FW", "Phantom Shot", 94, "Legendary", 0, "luna"),
        ("Chris Prince", "FW", "Perfect Body", 94, "Legendary", 0, "prince"),
        ("Lavinho", "FW", "Brazilian Technique", 93, "Legendary", 0, "lavinho"),
        ("Yoichi Isagi", "FW", "Direct Shot", 92, "Legendary", 0, "isagi"),
        ("Ryusei Shidou", "FW", "Bicycle Kick", 96, "Epic", 1, "shidou"),
        ("Seishiro Nagi", "FW", "Trap & Volley", 89, "Epic", 0, "nagi"),
        ("Meguru Bachira", "FW", "Dribble", 88, "Epic", 0, "bachira"),
        ("Shoei Barou", "FW", "Chop Dribble", 88, "Epic", 1, "barou"),
        ("Hyoma Chigiri", "FW", "Speed Dribble", 87, "Epic", 0, "chigiri"),
        ("Rensuke Kunigami", "FW", "Left Leg Shot", 86, "Epic", 0, "kunigami"),
        ("Lockhart", "FW", "Iron Knight", 85, "Epic", 0, "lockhart"),
        ("Pablo Cavasoz", "FW", "Agility", 84, "Epic", 0, "cavasoz"),
        ("Bunny Iglesias", "FW", "Acrobatic", 82, "Epic", 0, "bunny"),
        ("Shuto Sendou", "FW", "Acrobatic Shot", 83, "Rare", 0, "sendou"),
        ("Aoshi Tokimitsu", "FW", "Power Shot", 82, "Rare", 0, "tokimitsu"),
        ("Gurimu Igarashi", "FW", "Header", 70, "Rare", 0, "igarashi"),
        # هافبک‌ها
        ("Sae Itoshi", "MF", "Precision Pass", 96, "Legendary", 0, "sae"),
        ("Rin Itoshi", "MF", "Puppet Control", 95, "Legendary", 1, "rin"),
        ("Charles Chevalier", "MF", "Genius Pass", 92, "Legendary", 0, "charles"),
        ("Alexis Ness", "MF", "Magic Pass", 90, "Legendary", 0, "ness"),
        ("Reo Mikage", "MF", "Copycat", 86, "Epic", 0, "mikage"),
        ("Tabito Karasu", "MF", "Trap", 86, "Epic", 1, "karasu"),
        ("Hiori Yo", "MF", "Meta Vision", 85, "Epic", 0, "hiori"),
        ("Mark Snuffy", "MF", "Vision", 85, "Epic", 0, "snuffy"), 
        ("Kenyu Yukimiya", "MF", "Gyro Shot", 84, "Epic", 0, "yukimiya"),
        ("Vivian Hugo", "MF", "Pass", 78, "Epic", 0, "hugo"), 
        ("Otoya Eita", "MF", "Stealth", 83, "Rare", 0, "otoya"),
        ("Tsurugi Zantetsu", "MF", "Speed", 80, "Rare", 0, "zantetsu"),
        ("Jin Kiyora", "MF", "Shoot", 80, "Rare", 0, "kiyora"),
        ("Nijiro Nanase", "MF", "Stamina", 78, "Rare", 0, "nanase"),
        ("Kusu", "MF", "Pass", 76, "Rare", 0, "kusu"),
        # مدافعین
        ("Don Lorenzo", "DF", "Zombie Defense", 92, "Legendary", 1, "lorenzo"),
        ("Oliver Aiku", "DF", "Defensive Vision", 88, "Epic", 0, "aiku"),
        ("Teddy Knight", "DF", "Iron Wall", 86, "Epic", 0, "teddy"),
        ("Jyubei Aryu", "DF", "Long Legs", 82, "Epic", 0, "aryu"),
        ("Dada Silva", "DF", "Strength", 79, "Epic", 0, "dada"), 
        ("Ikki Niko", "DF", "Tactical Foul", 80, "Rare", 0, "niko"),
        ("Ranze Kurona", "DF", "Agility", 78, "Rare", 0, "kurona"),
        ("Sengoku Miroku", "DF", "Block", 75, "Rare", 0, "miroku"),
        ("Wataru Kuon", "DF", "Tackle", 75, "Rare", 0, "kuon"),
        # دروازه‌بان‌ها
        ("Gin Gagamaru", "GK", "Wild Reflexes", 86, "Epic", 0, "gagamaru"),
        ("Akira Endoji", "GK", "Iron Wall", 84, "Epic", 0, "endoji"),
        ("Fukaku", "GK", "Save", 78, "Rare", 0, "fukaku"),
        ("Kazuma Nio", "GK", "Reaction", 76, "Rare", 0, "nio"),
    ]
    cursor.executemany('''
    INSERT INTO characters (name, position, technique, base_power, rarity, is_cursed, synergy_tag)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', characters_data)
    conn.commit(); conn.close()
    print(f"✅ {len(characters_data)} کاراکتر وارد دیتابیس شد.")

if __name__ == "__main__":
    seed_characters()