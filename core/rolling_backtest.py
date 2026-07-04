#!/usr/bin/env python3
"""滚动回测验证"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db
from core.recommender import get_recommendation

def rolling_verify(test_count=30):
    conn = get_db()
    dates = [r["draw_date"] for r in conn.execute("SELECT draw_date FROM draws ORDER BY draw_date").fetchall()]
    conn.close()
    if len(dates) < 200 + test_count:
        return {"error": f"数据不足"}
    hits, total = 0, 0
    for i in range(test_count):
        rec = get_recommendation(seed=i)
        rec_nums = set(rec["numbers"])
        test_date = dates[-(test_count - i)]
        conn = get_db()
        actual = conn.execute("SELECT n1,n2,n3,n4,n5,n6,extra FROM draws WHERE draw_date=?", (test_date,)).fetchone()
        conn.close()
        if actual:
            actual_nums = {actual[c] for c in ["n1","n2","n3","n4","n5","n6","extra"]}
            match = len(rec_nums & actual_nums)
            if match >= 1: hits += 1
            total += 1
    return {"tests": total, "hits": hits, "hit_rate": f"{hits/total*100:.1f}%" if total else "0%"}
if __name__ == "__main__":
    print(json.dumps(rolling_verify(30), ensure_ascii=False, indent=2))
