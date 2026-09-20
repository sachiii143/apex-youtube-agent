"""
character_bible.py — APEX
Original IP: Trishul, Sandy, Libhu — Sunridge Town comedy sketches.
100% owned by channel creator. Locks after episode 1.
"""

import json, sqlite3, hashlib
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "apex_data.db"

CHARACTERS = {
    "Trishul": {
        "version": "1.0", "type": "original", "copyright": "owned by channel creator",
        "age": "12 (appears)", "role": "The overconfident one — always has a plan, plan always goes wrong",
        "personality": "Bold, dramatic, never admits mistakes, secretly kind-hearted",
        "appearance": "Tall for age, spiky hair, homemade red cape",
        "catchphrase": "I TOTALLY meant to do that.",
        "comedy_role": "Instigator — starts the chaos",
        "image_prompt": r"cartoon boy 12 years old, tall, spiky black hair, homemade red cape, confident expression, bright colors, clean animation style, family friendly, original character",
    },
    "Sandy": {
        "version": "1.0", "type": "original", "copyright": "owned by channel creator",
        "age": "11 (appears)", "role": "The logical one — always right, nobody listens to her",
        "personality": "Calm, patient, occasional exasperated outbursts, loves science",
        "appearance": "Medium height, neat ponytail, always carries a small notebook",
        "catchphrase": "I literally just said that.",
        "comedy_role": "Straight-man — reacts to chaos, occasionally joins it",
        "image_prompt": r"cartoon girl 11 years old, neat ponytail brown hair, holding small notebook, slightly exasperated expression, bright colors, clean animation style, family friendly, original character",
    },
    "Libhu": {
        "version": "1.0", "type": "original", "copyright": "owned by channel creator",
        "age": "10 (appears)", "role": "The wildcard — randomly genius or completely clueless, no in-between",
        "personality": "Sweet, unpredictable, takes everything literally, surprisingly wise sometimes",
        "appearance": "Smallest of the three, round face, big eyes, always eating something",
        "catchphrase": "Wait, that was an option?",
        "comedy_role": "Chaos agent — says the unexpected thing at exactly the right/wrong moment",
        "image_prompt": r"cartoon child 10 years old, small round face, big expressive eyes, holding snack food, surprised expression, bright colors, clean animation style, family friendly, original character",
    },
}

WORLD = {
    "name": "Sunridge Town", "version": "1.0", "copyright": "owned by channel creator",
    "setting": "A cheerful small town where slightly weird things happen regularly",
    "tone": "Slapstick comedy, misunderstandings, friendship, family safe",
    "locations": [
        "The Trio's treehouse (their base of operations, always messy)",
        "Sunridge School (where their plans usually start and fail)",
        "Mr. Patel's corner store (long-suffering shopkeeper)",
        "The town park (where things escalate)",
        "Libhu's kitchen (ground zero for food-related chaos)",
    ],
    "rules": [
        "No violence — characters fail through their own mistakes, not harm",
        "No adult themes — family safe",
        "No real brand names — use fictional alternatives",
        "No real people — all characters original",
        "Problems resolve through friendship and honesty",
        "Trishul's plans always fail, always for a funny reason",
        "Sandy is always right about facts, sometimes wrong about people",
        "Libhu's random statements are always accidentally correct by the end",
    ],
    "episode_structure": [
        "1. Trishul has a plan (30-45s)",
        "2. Sandy explains why it won't work — nobody listens (30s)",
        "3. Plan starts going wrong in unexpected way (60s)",
        "4. Libhu says something weird that accidentally makes it worse/better (30s)",
        "5. Crisis peak — all three must work together to fix it (60s)",
        "6. Resolution + Trishul claims he meant for it to happen (30s)",
        "7. Tag scene: hint at next episode (15s)",
    ],
}

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS character_bible (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT NOT NULL, data_hash TEXT NOT NULL,
        data TEXT NOT NULL, locked INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL, locked_at TEXT
    )""")
    conn.commit()
    return conn

def save_bible(locked: bool = False) -> str:
    import audit_log
    data = json.dumps({"characters": CHARACTERS, "world": WORLD}, sort_keys=True)
    h    = hashlib.sha256(data.encode()).hexdigest()[:12]
    version = f"1.0.{h}"
    conn = _conn()
    if not conn.execute("SELECT id FROM character_bible WHERE data_hash=?", (h,)).fetchone():
        conn.execute("INSERT INTO character_bible (version,data_hash,data,locked,created_at) VALUES (?,?,?,?,?)",
                     (version, h, data, 1 if locked else 0, datetime.utcnow().isoformat()))
        conn.commit()
        audit_log.record("VIDEO_SCRIPT_DONE", subject="character_bible", payload={"version": version})
    conn.close()
    return version

def lock_bible():
    import audit_log
    conn = _conn()
    conn.execute("UPDATE character_bible SET locked=1, locked_at=? WHERE locked=0", (datetime.utcnow().isoformat(),))
    conn.commit(); conn.close()
    audit_log.record("VIDEO_APPROVED", subject="character_bible", payload={"action": "locked after episode 1"})

def is_locked() -> bool:
    conn = _conn()
    row = conn.execute("SELECT locked FROM character_bible ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return bool(row and row[0])

def get_prompt_context() -> str:
    lines = ["ORIGINAL CHARACTERS (do not change, do not reference any real cartoon):"]
    for name, c in CHARACTERS.items():
        lines.append(f"  {name}: {c['role']}. Catchphrase: '{c['catchphrase']}'")
    lines.append(f"\nSETTING: {WORLD['name']} — {WORLD['setting']}")
    lines.append(f"TONE: {WORLD['tone']}")
    lines.append("RULES: " + " | ".join(WORLD['rules'][:4]))
    return "\n".join(lines)

def get_image_prompts() -> dict:
    return {name: c["image_prompt"] for name, c in CHARACTERS.items()}
