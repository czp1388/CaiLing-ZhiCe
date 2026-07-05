#!/usr/bin/env python3
"""
彩灵·智策 — 期望值计算器

计算每注(6个号码)的期望值 EV = Σ(奖金 × 概率)
"""
import json, sys, os, math, itertools

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
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

    # ── 精确概率公式 ──────────────────────────────────────────
    # 超几何分布：C(6,k)*C(43,6-k)/C(49,6) = 恰好中 k 个正选的概率
    # 在恰好中 k 个正选的条件下，剩余 6-k 个未选数中有特别号的概率为 (6-k)/43
    # 因此：
    #   头奖（6正选）        = C(6,6)*C(43,0)/C(49,6)
    #   二奖（5正选+特别号） = C(6,5)*C(43,1)/C(49,6) * 1/43
    #   三奖（5正选）        = C(6,5)*C(43,1)/C(49,6) * 42/43
    #   四奖（4正选+特别号） = C(6,4)*C(43,2)/C(49,6) * 2/43
    #   五奖（4正选）        = C(6,4)*C(43,2)/C(49,6) * 41/43
    #   六奖（3正选+特别号） = C(6,3)*C(43,3)/C(49,6) * 3/43
    #   七奖（3正选）        = C(6,3)*C(43,3)/C(49,6) * 40/43
    probs = {
        "head": combination(6, 6) * combination(43, 0) / total_combo,
        "2nd": combination(6, 5) * combination(43, 1) / total_combo / 43,
        "3rd": combination(6, 5) * combination(43, 1) / total_combo * 42 / 43,
        "4th": combination(6, 4) * combination(43, 2) / total_combo * 2 / 43,
        "5th": combination(6, 4) * combination(43, 2) / total_combo * 41 / 43,
        "6th": combination(6, 3) * combination(43, 3) / total_combo * 3 / 43,
        "7th": combination(6, 3) * combination(43, 3) / total_combo * 40 / 43,
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
