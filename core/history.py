"""推荐历史记录"""
import json, os, sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db

def save_recommendation(rec):
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS recommendations (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, numbers TEXT, confidence TEXT, avg_hit_rate TEXT, strategy TEXT)")
    conn.execute("INSERT INTO recommendations (created_at, numbers, confidence, avg_hit_rate, strategy) VALUES (?,?,?,?,?)",
                 (datetime.now().isoformat(), json.dumps(rec["numbers"]), rec["confidence"], rec["avg_hit_rate"], rec["strategy"]))
    conn.commit()
    conn.close()

def get_history(limit=30):
    conn = get_db()
    rows = conn.execute("SELECT * FROM recommendations ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

if __name__ == "__main__":
    print(json.dumps(get_history(10), ensure_ascii=False, indent=2, default=str))
