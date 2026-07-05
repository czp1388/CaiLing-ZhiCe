"""推荐准确率统计看板 — 两套方案对比"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.history import get_history
from core.database import get_db

def accuracy_report():
    history = get_history(200)
    conn = get_db()
    total_recs = len(history)

    stats_a = {"total": 0, "hits_1plus": 0, "total_matches": 0, "max_hits": 0,
               "breakdown": {1:0, 2:0, 3:0, 4:0, 5:0, 6:0}}
    stats_b = {"total": 0, "draws_with_win": 0, "total_prize": 0,
               "big_win_draws": 0, "winning_combos_total": 0}

    per_draw = []

    for h in history:
        td = h["created_at"][:10] if h.get("created_at") else ""
        act = conn.execute("SELECT n1,n2,n3,n4,n5,n6,extra FROM draws WHERE draw_date < ? ORDER BY draw_date DESC LIMIT 1", (td,)).fetchone()
        if not act:
            continue
        an6 = {act[c] for c in ["n1","n2","n3","n4","n5","n6"]}
        extra = act["extra"]

        # 方案A
        nums_a = h.get("numbers", [])
        if isinstance(nums_a, str): nums_a = json.loads(nums_a)
        h6 = len(set(nums_a) & an6)
        stats_a["total"] += 1
        stats_a["total_matches"] += h6
        stats_a["max_hits"] = max(stats_a["max_hits"], h6)
        if h6 >= 1:
            stats_a["hits_1plus"] += 1
        if h6 in stats_a["breakdown"]:
            stats_a["breakdown"][h6] += 1

        # 方案B
        b_combos = h.get("plan_b_combos", [])
        if isinstance(b_combos, str) and b_combos:
            b_combos = json.loads(b_combos)
        b_info = None
        if b_combos:
            from core.verify import verify_plan_b
            b_res = verify_plan_b(b_combos, an6, extra)
            stats_b["total"] += 1
            stats_b["winning_combos_total"] += b_res["winning_count"]
            stats_b["total_prize"] += b_res["total_prize"]
            if b_res["winning_count"] > 0:
                stats_b["draws_with_win"] += 1
            # 大奖判定：5+正选 或 4正选+特别号
            big = any(c["hits_6"] >= 5 or (c["hits_6"] == 4 and c["hits_extra"]) for c in b_res["winning_combos"])
            if big:
                stats_b["big_win_draws"] += 1
            b_info = b_res

        per_draw.append({
            "date": td,
            "plan_a": {"numbers": sorted(nums_a), "hits": h6, "hit_detail": f"中{h6}个"},
            "plan_b": {
                "winning_count": b_res["winning_count"] if b_info else 0,
                "total_prize": b_res["total_prize"] if b_info else 0,
                "max_level": b_res["max_level"] if b_info and b_res["max_level"] else "",
            } if b_info else None,
        })

    conn.close()

    # 命中数分布（方案A）
    dist_a = {str(k): stats_a["breakdown"].get(k, 0) for k in range(1, 7)}
    dist_a_pct = {str(k): round(stats_a["breakdown"].get(k, 0) / max(stats_a["total"], 1) * 100, 1) for k in range(1, 7)}

    return {
        "total_recommendations": stats_a["total"],
        "plan_a": {
            "total": stats_a["total"],
            "hit_rate_1plus": f"{stats_a['hits_1plus']/max(stats_a['total'],1)*100:.1f}%",
            "draws_with_hits": stats_a["hits_1plus"],
            "avg_matches_per_draw": round(stats_a["total_matches"] / max(stats_a["total"], 1), 3),
            "max_hits_in_one_draw": stats_a["max_hits"],
            "hit_distribution": dist_a_pct,
        },
        "plan_b": {
            "total": stats_b["total"],
            "win_rate": f"{stats_b['draws_with_win']/max(stats_b['total'],1)*100:.1f}%",
            "draws_with_win": stats_b["draws_with_win"],
            "total_prize": stats_b["total_prize"],
            "avg_prize_per_draw": round(stats_b["total_prize"] / max(stats_b["total"], 1), 2),
            "winning_combos_total": stats_b["winning_combos_total"],
            "big_win_draws": stats_b["big_win_draws"],  # 5+命中次数
            "has_hit_5plus": stats_b["big_win_draws"] > 0,
        },
        "per_draw": per_draw[-20:],
        "random_baseline": "14.3% (7/49)",
    }

if __name__ == "__main__":
    print(json.dumps(accuracy_report(), ensure_ascii=False, indent=2))
