"""自动调参——网格搜索最优权重"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db

GRID = {
    "hot_weight": [1, 2, 3, 5],
    "miss_weight": [0.3, 0.5, 0.8, 1.0],
    "seed_base": [42, 99, 123],
}

def grid_search(test_count=30):
    conn = get_db()
    dates = [r["draw_date"] for r in conn.execute("SELECT draw_date FROM draws ORDER BY draw_date").fetchall()]
    conn.close()
    if len(dates) < 200 + test_count:
        return {"error": "数据不足"}

    best = {"rate": 0, "weights": {}}
    for hw in GRID["hot_weight"]:
        for mw in GRID["miss_weight"]:
            for sb in GRID["seed_base"]:
                hits, total = 0, 0
                for i in range(test_count):
                    import random
                    random.seed(sb + i)
                    from core.kline import build_kline_data
                    from core.analyzer import hot_cold_numbers, missing_stats
                    hc = hot_cold_numbers(100, 15)
                    hot_nums = [n for n, _ in hc["hot"]]
                    miss = missing_stats(100)
                    miss_dict = {n: d for n, d in miss}
                    scores = []
                    for num in hot_nums:
                        k = build_kline_data(num, 100)
                        if "stats" not in k: continue
                        hi = hot_nums.index(num)
                        mv = miss_dict.get(num, 0)
                        hr = float(k["stats"]["hit_rate"].replace("%",""))
                        score = (15 - hi) * hw + mv * mw + hr * 0.3
                        scores.append({"n": num, "s": score})
                    scores.sort(key=lambda x: -x["s"])
                    rec = set()
                    for s in scores:
                        rec.add(s["n"])
                        if len(rec) >= 6: break
                    while len(rec) < 6:
                        rec.add(random.randint(1, 49))
                    test_date = dates[-(test_count - i)]
                    conn2 = get_db()
                    actual = conn2.execute("SELECT n1,n2,n3,n4,n5,n6,extra FROM draws WHERE draw_date=?", (test_date,)).fetchone()
                    conn2.close()
                    if actual:
                        an = {actual[c] for c in ["n1","n2","n3","n4","n5","n6","extra"]}
                        if len(rec & an) >= 1: hits += 1
                        total += 1
                rate = hits / max(total, 1)
                if rate > best["rate"]:
                    best = {"rate": rate, "rate_pct": f"{rate*100:.1f}%", "hits": hits, "total": total,
                            "weights": {"hot": hw, "miss": mw, "seed_base": sb}}
    return best

if __name__ == "__main__":
    print(json.dumps(grid_search(30), ensure_ascii=False, indent=2))
