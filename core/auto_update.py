#!/usr/bin/env python3
"""自动数据更新"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import init_db, get_db
from core.fetcher import fetch_all
def update():
    init_db()
    conn = get_db()
    latest = conn.execute("SELECT MAX(draw_date) FROM draws").fetchone()[0]
    conn.close()
    count = fetch_all(limit=30)
    print(f"✅ 新增{count}期")
    return count
if __name__ == "__main__":
    update()
