#!/usr/bin/env python3
"""
彩灵·智策 — 期望值计算器

计算每注(6个号码)的期望值 EV = Σ(奖金 × 概率)
"""
import json, sys, os, math, itertools
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from core.database import get_db
from core.analyzer import hot_cold_numbers


def combination(n, k):
    """组合数 C(n,k)"""
    if k < 0 or k > n:
        return 0
    return math.comb(n, k)


def calculate_ev(picks, jackpot_1st=10000000, jackpot_2nd=1000000):
    """计算一组号码的期望值

    EV = Σ(奖金_i × 中_i / C(49,6))

    六合彩奖金等级（简化，按$10一注）:
    - 头奖: 6个全中 (1/C(49,6))
    - 二等奖: 中5个+特别号 (C(6,5)*1/C(49,6))
    ...
    """
    n = len(picks)
    if n != 6:
        return {"error": "需要6个号码"}

    # 奖金额（元）
    prizes = {
        "head": jackpot_1st,    # 头奖：6个全中
        "2nd": jackpot_2nd,     # 二等奖：5个半中+特别号
        "3rd": 80000,           # 三等奖：5个半中
        "4th": 9600,            # 四等奖：4个半中+特别号
        "5th": 640,             # 五等奖：4个半中
        "6th": 320,             # 六等奖：3个半中+特别号
        "7th": 40,              # 七等奖：3个半中
    }

    total_combo = combination(49, 6)  # C(49, 6) = 13,983,816

    # 概率计算（简化版）
    # 准确概率应该用超几何分布，这里用近似
    probs = {
        "head": 1 / total_combo,
        "2nd": combination(6, 5) * combination(42, 0) / total_combo,  # 近似
        "3rd": combination(6, 5) * combination(42, 1) / total_combo,
        "4th": combination(6, 4) * combination(42, 1) / total_combo,
        "5th": combination(6, 4) * combination(42, 2) / total_combo,
        "6th": combination(6, 3) * combination(42, 2) / total_combo,
        "7th": combination(6, 3) * combination(42, 3) / total_combo,
    }

    ev = 0
    breakdown = []
    for level, prob in probs.items():
        prize = prizes.get(level, 0)
        expected = prob * prize
        ev += expected
        breakdown.append({
            "level": level,
            "prize": prize,
            "prob": prob,
            "prob_1in": round(1 / prob) if prob > 0 else float('inf'),
            "expected": round(expected, 4),
        })

    # 头奖按今日奖池算
    ev_per_dollar = ev / 10  # 每10元一注的期望回报

    return {
        "picks": sorted(picks),
        "ev_total": round(ev, 2),
        "ev_per_10": round(ev_per_dollar, 2),
        "cost": 10,
        "breakdown": breakdown,
        "is_positive": ev > 10,
    }


def analyze_best_combo(hot_count=7):
    """从热号中找出期望值最高的组合"""
    hc = hot_cold_numbers()
    hot = [n for n, _ in hc["hot"][:hot_count]]

    if len(hot) < 6:
        return {"error": "热号不足"}

    best = {"ev": 0, "picks": []}
    # 从热号中尝试所有6号组合
    for combo in itertools.combinations(hot, 6):
        result = calculate_ev(list(combo))
        if "error" not in result and result["ev_total"] > best["ev"]:
            best = {"ev": result["ev_total"], "picks": sorted(combo)}
            # 限制计算量
            if best["ev"] > 1:
                break

    return best


if __name__ == "__main__":
    if "--calc" in sys.argv:
        idx = sys.argv.index("--calc") + 1
        picks = list(map(int, sys.argv[idx:idx+6]))
        if len(picks) != 6:
            print("❌ 需要6个号码: --calc 1 2 3 4 5 6")
            sys.exit(1)
        result = calculate_ev(picks)
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if result.get("is_positive"):
            print(f"\n✅ 正期望值！理论上长期可盈利")
        else:
            print(f"\n❌ 负期望值，每注预期亏损 ${10 - result.get('ev_total', 0):.2f}")

    elif "--best" in sys.argv:
        best = analyze_best_combo()
        print(json.dumps(best, ensure_ascii=False, indent=2))
        print(f"\n💡 推荐组合: {best.get('picks')} (EV={best.get('ev')})")

    else:
        print("用法:")
        print("  python3 -m core.ev --calc 1 2 3 4 5 6")
        print("  python3 -m core.ev --best")
