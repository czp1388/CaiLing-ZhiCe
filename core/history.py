"""推荐历史记录 — 两套方案（A:6正选 + B:旋转矩阵）"""
import json, os, sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db

SCHEMA = """
CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT,
    numbers TEXT,
    confidence TEXT,
    avg_hit_rate TEXT,
    strategy TEXT,
    plan_b_pool TEXT,       -- 方案B号码池（JSON数组）
    plan_b_combos TEXT,     -- 方案B所有组合（JSON二维数组）
    plan_b_count INTEGER,   -- 方案B注数
    plan_b_cost REAL        -- 方案B成本
);
"""

def save_recommendation(rec):
    conn = get_db()
    conn.executescript(SCHEMA)
    plan_b = rec.get("plan_b", {})
    conn.execute("""
        INSERT INTO recommendations
        (created_at, numbers, confidence, avg_hit_rate, strategy,
         plan_b_pool, plan_b_combos, plan_b_count, plan_b_cost)
        VALUES (?,?,?,?,?, ?,?,?,?)
    """, (
        datetime.now().isoformat(),
        json.dumps(rec["numbers"]),
        rec.get("confidence", ""),
        rec.get("avg_hit_rate", ""),
        rec.get("strategy", ""),
        json.dumps(plan_b.get("pool", [])),
        json.dumps(plan_b.get("combos", [])),
        plan_b.get("count", 0),
        plan_b.get("cost", 0),
    ))
    conn.commit()
    conn.close()

def get_history(limit=30):
    conn = get_db()
    conn.executescript(SCHEMA)
    rows = conn.execute("SELECT * FROM recommendations ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        # 解析JSON字段
        if isinstance(d.get("numbers"), str):
            d["numbers"] = json.loads(d["numbers"])
        if isinstance(d.get("plan_b_pool"), str) and d["plan_b_pool"]:
            d["plan_b_pool"] = json.loads(d["plan_b_pool"])
        if isinstance(d.get("plan_b_combos"), str) and d["plan_b_combos"]:
            d["plan_b_combos"] = json.loads(d["plan_b_combos"])
        result.append(d)
    return result

if __name__ == "__main__":
    print(json.dumps(get_history(10), ensure_ascii=False, indent=2, default=str))
