"""版本对比回测——用数据证明哪个版本真的更准"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db

# 不同版本的权重配置
VERSIONS = {
    "v1.0": {"hot_weight": 3, "miss_weight": 0.5, "kdj_weight": 0, "cold_weight": 0, "seed_base": 42},
    "v1.1": {"hot_weight": 3, "miss_weight": 0.5, "kdj_weight": 2, "cold_weight": 3, "seed_base": 42},
    "v1.2": {"hot_weight": 3, "miss_weight": 0.5, "kdj_weight": 5, "cold_weight": 5, "seed_base": 42},
    "v1.3": {"hot_weight": 3, "miss_weight": 0.8, "kdj_weight": 5, "cold_weight": 5, "seed_base": 99},
}

def compare_versions(test_count=50):
    """每个版本跑滚动回测，输出对比表"""
    conn = get_db()
    dates = [r["draw_date"] for r in conn.execute("SELECT draw_date FROM draws ORDER BY draw_date").fetchall()]
    conn.close()
    if len(dates) < 200 + test_count:
        return {"error": f"数据不足"}
    
    results = {}
    for ver, weights in VERSIONS.items():
        hits, total = 0, 0
        for i in range(test_count):
            # 用每个版本的种子和权重生成推荐
            seed = weights["seed_base"] + i
            import random
            random.seed(seed)
            from core.kline import build_kline_data
            from core.analyzer import hot_cold_numbers, missing_stats
            hc = hot_cold_numbers(100, 15)
            hot_nums = [n for n, _ in hc["hot"]]
            miss = missing_stats(100)
            miss_dict = {n: d for n, d in miss}
            
            # 评分
            scores = []
            for num in hot_nums:
                k = build_kline_data(num, 100)
                if "stats" not in k: continue
                hi = hot_nums.index(num)
                mv = miss_dict.get(num, 0)
                hr = float(k["stats"]["hit_rate"].replace("%",""))
                score = (15 - hi) * weights["hot_weight"] + mv * weights["miss_weight"] + hr * 0.3
                scores.append({"n": num, "s": score})
            scores.sort(key=lambda x: -x["s"])
            rec = set()
            for s in scores:
                rec.add(s["n"])
                if len(rec) >= 6: break
            while len(rec) < 6:
                rec.add(random.randint(1, 49))
            
            # 验证
            test_date = dates[-(test_count - i)]
            conn2 = get_db()
            actual = conn2.execute("SELECT n1,n2,n3,n4,n5,n6,extra FROM draws WHERE draw_date=?", (test_date,)).fetchone()
            conn2.close()
            if actual:
                an = {actual[c] for c in ["n1","n2","n3","n4","n5","n6","extra"]}
                if len(rec & an) >= 1: hits += 1
                total += 1
        
        results[ver] = {"hits": hits, "total": total, "rate": f"{hits/max(total,1)*100:.1f}%"}
    return results

if __name__ == "__main__":
    r = compare_versions(30)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    print(f"\n{'='*40}")
    print(f"{'版本':>8s} {'命中':>6s} {'总数':>6s} {'命中率':>8s}")
    print("-" * 30)
    for v, d in sorted(r.items()):
        print(f"{v:>8s} {d['hits']:>6d} {d['total']:>6d} {d['rate']:>8s}")
