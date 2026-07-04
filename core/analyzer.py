#!/usr/bin/env python3
"""
彩灵·智策 — 分析引擎
冷热号分析、遗漏值统计、号码走势
"""
import json, sys, os, math
from collections import defaultdict
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from core.database import get_db, get_number_frequency, get_draws


def hot_cold_numbers(window=50, top=10):
    """冷热号分析
    window: 统计最近N期
    top: 显示前N个热号和冷号
    返回: {"hot": [(号码,次数)], "cold": [(号码,次数)]}
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT n1,n2,n3,n4,n5,n6,extra FROM draws ORDER BY draw_date DESC LIMIT ?",
        (window,)
    ).fetchall()
    conn.close()

    freq = defaultdict(int)
    for r in rows:
        for n in [r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"], r["extra"]]:
            if 1 <= n <= 49:
                freq[n] += 1

    # 所有号码的频率
    all_freq = [(i, freq.get(i, 0)) for i in range(1, 50)]
    all_freq.sort(key=lambda x: (-x[1], x[0]))

    hot = all_freq[:top]
    cold = all_freq[-top:]

    return {"hot": hot, "cold": cold}


def missing_stats(window=100):
    """遗漏值统计：每个号码连续未出现的期数"""
    conn = get_db()
    rows = conn.execute(
        "SELECT draw_date,n1,n2,n3,n4,n5,n6,extra FROM draws ORDER BY draw_date DESC LIMIT ?",
        (window,)
    ).fetchall()
    conn.close()

    # 每期出现的号码
    appeared = defaultdict(list)
    for i, r in enumerate(rows):
        for n in [r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"], r["extra"]]:
            if 1 <= n <= 49:
                appeared[n].append(i)

    # 计算每个号码的当前遗漏（最近一次出现到现在经过了几期）
    missing = {}
    for num in range(1, 50):
        if num in appeared:
            last_idx = min(appeared[num])  # 最近的期数索引（DESC排序）
            missing[num] = last_idx
        else:
            missing[num] = window

    # 按遗漏值排序
    ranked = sorted(missing.items(), key=lambda x: (-x[1], x[0]))
    return ranked


def frequency_heatmap():
    """生成号码频率热力图数据（JSON格式，供GUI使用）"""
    freq = get_number_frequency()
    total = sum(freq.values())
    heatmap = []
    for num in range(1, 50):
        count = freq.get(num, 0)
        pct = round(count / total * 100, 2) if total > 0 else 0
        heatmap.append({"number": num, "count": count, "pct": pct})

    # 按号码排序输出
    heatmap.sort(key=lambda x: x["number"])
    return heatmap


def analyze():
    """综合运行所有分析"""
    print("=" * 50)
    print("📊 彩灵·智策 — 号码分析报告")
    print("=" * 50)

    hc = hot_cold_numbers()
    print(f"\n🔥 热号 Top 10:")
    for num, count in hc["hot"]:
        bar = "█" * min(count, 20)
        print(f"  {num:2d}: {count:2d}次 {bar}")

    print(f"\n❄️ 冷号 Top 10:")
    for num, count in hc["cold"]:
        bar = "█" * min(count, 20)
        print(f"  {num:2d}: {count:2d}次 {bar}")

    print(f"\n📈 遗漏值 Top 15 (最久未出):")
    miss = missing_stats()
    for num, days in miss[:15]:
        bar = "█" * min(days, 30)
        print(f"  {num:2d}: {days}期未出 {bar}")

    # 综合推荐（选取热号中遗漏较大的）
    hot_set = {n for n, _ in hc["hot"]}
    print(f"\n💡 推荐关注:")
    recommended = [(n, d) for n, d in miss if n in hot_set][:6]
    for num, days in recommended:
        print(f"  {num:2d}: 热号(前10) + 遗漏{days}期")

    return {"hot_cold": hc, "missing": miss[:15]}


if __name__ == "__main__":
    if "--json" in sys.argv:
        hc = hot_cold_numbers()
        print(json.dumps(hc, ensure_ascii=False, indent=2))
    elif "--missing" in sys.argv:
        m = missing_stats()
        print(json.dumps(m, ensure_ascii=False, indent=2))
    elif "--heatmap" in sys.argv:
        hm = frequency_heatmap()
        print(json.dumps(hm, ensure_ascii=False, indent=2))
    else:
        analyze()
