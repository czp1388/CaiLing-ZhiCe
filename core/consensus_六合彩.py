#!/usr/bin/env python3
"""
六合彩多策略共识推荐系统

4个独立策略分别推荐号码，只有≥3/4的共识才入选。

策略A: 当前方案(冷热号+遗漏值+K线) — 调用现有recommender
策略B: 纯冷号策略 — 遗漏值最大的6个号
策略C: 纯热号策略 — 历史频率最高的6个号
策略D: 区间分散策略 — 每区间选2个号(1-12,13-24,25-36,37-49)

共识规则:
  - 每个策略推荐6个正选号码
  - 4个策略中≥3个都包含的号码 → 入选
  - 不足6个时从高共识号补
  - 九码复式也从高共识中取前9
"""
import sys, os, json, random
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))
from core.database import get_db, get_number_frequency
from core.analyzer import hot_cold_numbers, missing_stats


def strategy_a():
    """策略A: 当前方案(热号+遗漏+seed)"""
    from core.recommender import get_recommendation
    rec = get_recommendation()
    return set(rec["numbers"]), set(rec.get("plan_c", {}).get("numbers", []))


def strategy_b():
    """策略B: 纯冷号策略 — 遗漏最大的6个号"""
    miss = missing_stats(200)
    cold_set = set(num for num, _ in miss[:6])
    # 九码复式：遗漏最大的9个
    cold9 = set(num for num, _ in miss[:9])
    return cold_set, cold9


def strategy_c():
    """策略C: 纯热号策略 — 历史频率最高的6个号"""
    hc = hot_cold_numbers(window=200, top=15)
    hot_set = set(num for num, _ in hc["hot"][:6])
    hot9 = set(num for num, _ in hc["hot"][:9])
    return hot_set, hot9


def strategy_d():
    """策略D: 区间分散策略 — 每区间选2个"""
    zones = {"1-12": [], "13-24": [], "25-36": [], "37-49": []}
    conn = get_db()
    rows = conn.execute("SELECT n1,n2,n3,n4,n5,n6,extra FROM draws ORDER BY draw_date DESC LIMIT 50").fetchall()
    zone_hits = {k: {} for k in zones}
    for r in rows:
        for n in [r["n1"],r["n2"],r["n3"],r["n4"],r["n5"],r["n6"],r["extra"]]:
            for zname, (zmin, zmax) in [("1-12",(1,12)),("13-24",(13,24)),("25-36",(25,36)),("37-49",(37,49))]:
                if zmin <= n <= zmax:
                    zone_hits[zname][n] = zone_hits[zname].get(n, 0) + 1
                    break
    conn.close()

    selected = []
    for zname in ["1-12","13-24","25-36","37-49"]:
        sorted_nums = sorted(zone_hits[zname].items(), key=lambda x: -x[1])
        picked = [n for n, _ in sorted_nums[:3]]
        selected.extend(picked)
        if len(picked) < 2:
            # 区间内补充随机
            zmin, zmax = {"1-12":(1,12),"13-24":(13,24),"25-36":(25,36),"37-49":(37,49)}[zname]
            while len(picked) < 2:
                n = random.randint(zmin, zmax)
                if n not in picked:
                    picked.append(n)
                    selected.append(n)

    d_set = set(selected[:6])
    d9 = set(selected[:9])
    return d_set, d9


def consensus():
    """
    运行4个策略，取共识

    返回:
        numbers: 6个正选号码(共识≥3/4)
        plan_c: 九码复式(共识排名前9)
        details: 各策略详情
    """
    random.seed(int(datetime.now().strftime("%Y%m%d")))

    strategies = {
        "A-热冷号": strategy_a,
        "B-纯冷号": strategy_b,
        "C-纯热号": strategy_c,
        "D-区间分散": strategy_d,
    }

    results = {}
    all_votes = {}  # {number: [策略名列表]}
    all_plan_c_votes = {}

    for name, func in strategies.items():
        try:
            s6, s9 = func()
            results[name] = {"numbers": sorted(s6), "plan_c": sorted(s9)}
            for n in s6:
                all_votes.setdefault(n, []).append(name)
            for n in s9:
                all_plan_c_votes.setdefault(n, []).append(name)
        except Exception as e:
            results[name] = {"error": str(e)}

    # 共识计票：哪些号码至少被3个策略选中
    threshold = 3
    high_consensus = sorted(
        [(n, len(votes)) for n, votes in all_votes.items() if len(votes) >= threshold],
        key=lambda x: -x[1]
    )
    medium_consensus = sorted(
        [(n, len(votes)) for n, votes in all_votes.items() if len(votes) == 2],
        key=lambda x: -x[1]
    )

    # 选6个正选：高共识优先，不够从中共识补
    final = [n for n, _ in high_consensus[:6]]
    if len(final) < 6:
        for n, _ in medium_consensus:
            if n not in final:
                final.append(n)
            if len(final) >= 6:
                break
    # 还不够就随机
    while len(final) < 6:
        n = random.randint(1, 49)
        if n not in final:
            final.append(n)

    # 九码复式：共识前9
    plan_c_all = sorted(
        [(n, len(votes)) for n, votes in all_plan_c_votes.items()],
        key=lambda x: -x[1]
    )
    plan_c_final = [n for n, _ in plan_c_all[:9]]
    while len(plan_c_final) < 9:
        n = random.randint(1, 49)
        if n not in plan_c_final:
            plan_c_final.append(n)

    return {
        "numbers": sorted(final),
        "plan_c": sorted(plan_c_final[:9]),
        "details": results,
        "votes": {str(n): v for n, v in high_consensus},
    }


if __name__ == "__main__":
    import json
    result = consensus()

    print(f"🎯 六合彩共识推荐")
    print(f"{'='*40}")
    print(f"推荐号码: {result['numbers']}")
    print(f"九码复式: {result['plan_c']}")
    if result.get('votes'):
        print(f"\n高共识号码: {result['votes']}")
    print(f"\n各策略详情:")
    for name, data in result["details"].items():
        if "error" in data:
            print(f"  {name}: ❌ {data['error']}")
        else:
            print(f"  {name}: {data['numbers']}")
    print(f"\n共识规则: 4策略中≥2个同意才入选(候选池扩至10个)")
