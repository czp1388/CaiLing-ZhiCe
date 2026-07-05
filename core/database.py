#!/usr/bin/env python3
"""
彩灵·智策 — 数据底座
六合彩历史开奖数据存储 (SQLite)
支持：导入CSV、按日期查询、号码频率统计
"""
import sqlite3, os, csv, json, sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "marksix.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS draws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_date TEXT UNIQUE NOT NULL,   -- YYYY-MM-DD
    draw_no TEXT,                     -- 期号
    n1 INTEGER NOT NULL,
    n2 INTEGER NOT NULL,
    n3 INTEGER NOT NULL,
    n4 INTEGER NOT NULL,
    n5 INTEGER NOT NULL,
    n6 INTEGER NOT NULL,
    extra INTEGER NOT NULL,           -- 特别号码
    total_sales REAL,
    jackpot_1st REAL,
    jackpot_2nd REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_draw_date ON draws(draw_date);
CREATE INDEX IF NOT EXISTS idx_draw_no ON draws(draw_no);
"""



import shutil
def backup_db():
    """自动备份数据库到 backups/ 目录"""
    backup_dir = os.path.join(BASE, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"marksix_{timestamp}.db")
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, backup_path)
        return {"status": "ok", "backup": backup_path}
    return {"error": "数据库不存在"}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    """初始化数据库"""
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"✅ 数据库已初始化: {DB_PATH}")


def import_csv(csv_path):
    """从CSV导入开奖数据"""
    conn = get_db()
    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO draws
                    (draw_date, draw_no, n1, n2, n3, n4, n5, n6, extra, total_sales, jackpot_1st, jackpot_2nd)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get("date", row.get("draw_date", "")),
                    row.get("draw_no", row.get("期号", "")),
                    int(row.get("n1", row.get("num1", 0))),
                    int(row.get("n2", row.get("num2", 0))),
                    int(row.get("n3", row.get("num3", 0))),
                    int(row.get("n4", row.get("num4", 0))),
                    int(row.get("n5", row.get("num5", 0))),
                    int(row.get("n6", row.get("num6", 0))),
                    int(row.get("extra", row.get("特别号码", 0))),
                    float(row.get("total_sales", 0) or 0),
                    float(row.get("jackpot_1st", 0) or 0),
                    float(row.get("jackpot_2nd", 0) or 0),
                ))
                count += 1
            except (ValueError, KeyError) as e:
                print(f"  ⚠️ 跳过异常行: {e}")
    conn.commit()
    conn.close()
    print(f"✅ 已导入 {count} 条记录")


def get_draws(limit=100, offset=0):
    """获取开奖记录"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM draws ORDER BY draw_date DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_number_frequency():
    """统计1-49号出现频率"""
    conn = get_db()
    freq = {i: 0 for i in range(1, 50)}
    rows = conn.execute("SELECT n1,n2,n3,n4,n5,n6,extra FROM draws").fetchall()
    for r in rows:
        for n in [r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"], r["extra"]]:
            if 1 <= n <= 49:
                freq[n] = freq.get(n, 0) + 1
    conn.close()
    return freq


def get_stats():
    """数据库统计"""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM draws").fetchone()[0]
    earliest = conn.execute("SELECT MIN(draw_date) FROM draws").fetchone()[0]
    latest = conn.execute("SELECT MAX(draw_date) FROM draws").fetchone()[0]
    conn.close()
    return {"total_draws": total, "earliest": earliest, "latest": latest}


if __name__ == "__main__":
    if "--init" in sys.argv:
        init_db()
    elif "--import" in sys.argv:
        idx = sys.argv.index("--import") + 1
        import_csv(sys.argv[idx]) if idx < len(sys.argv) else print("❌ 需要CSV路径")
    elif "--stats" in sys.argv:
        stats = get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        freq = get_number_frequency()
        top = sorted(freq.items(), key=lambda x: -x[1])[:10]
        print(f"\n🔥 最热号码 (Top 10): {json.dumps(top, ensure_ascii=False)}")
    else:
        print(f"用法: python3 -m core.database --init|--import <csv>|--stats")
        print(f"数据库: {DB_PATH}")
