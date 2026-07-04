#!/usr/bin/env python3
"""
彩灵·智策 — AI推荐引擎

结合冷热号、遗漏值、K线技术指标、五膽拖回测，
输出一个最终的号码推荐 + 理由 + 信心评分。

供其他AI（小墨/小灵）通过 cli.py recommend --json 调用。
"""
import json, sys, os, random
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from core.database import get_db
from core.analyzer import hot_cold_numbers, missing_stats
from core.kline import build_kline_data
from core.backtest import auto_backtest, backtest_5drag


def get_recommendation():
    """综合所有分析，输出一个号码推荐

    策略：
    1. 从热号中选出现频率高+遗漏适中的号码
    2. 从冷号中选出遗漏极大、可能反弹的号码
    3. 结合五膽拖最优组合
    4. 给出推荐理由和信心评分

    返回: {"numbers": [6个号码], "strategy": "", "confidence": "", "reason": "", "stats": ""}
    """
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM draws").fetchone()[0]
    db.close()

    # 1. 冷热号分析
    hc = hot_cold_numbers(window=100, top=15)
    hot_nums = [n for n, _ in hc["hot"]]
    cold_nums = [n for n, _ in hc["cold"]]

    # 2. 遗漏值
    miss = missing_stats(100)
    miss_dict = {num: days for num, days in miss}
    miss_sorted = sorted(miss_dict.items(), key=lambda x: -x[1])

    # 3. 每个热号的K线摘要
    hot_scores = []
    for num in hot_nums:
        k = build_kline_data(num, 100)
        if "stats" in k:
            s = k["stats"]
            # 评分：热度权重 + 遗漏权重 + 技术指标
            hot_idx = hot_nums.index(num)
            miss_val = miss_dict.get(num, 0)
            hit_rate = float(s["hit_rate"].replace("%", ""))
            score = (
                (15 - hot_idx) * 3 +           # 热度排名
                miss_val * 0.5 +               # 遗漏加分（遗漏越大越值得关注）
                hit_rate * 0.3                 # 开出率
            )
            hot_scores.append({"number": num, "score": round(score, 1),
                               "hot_rank": hot_idx + 1, "omission": miss_val,
                               "hit_rate": s["hit_rate"]})

    hot_scores.sort(key=lambda x: -x["score"])

    # 4. 五膽拖最优组合
    best_drag = auto_backtest(trials=300)
    drag_cores = best_drag.get("cores", [])

    # 5. 综合推荐号码（取评分最高的6个 + 胆码优先）
    recommended = set()
    # 优先加入五膽拖的胆码
    for n in drag_cores:
        if len(recommended) >= 6:
            break
        recommended.add(n)

    # 补充分数最高的
    for h in hot_scores:
        if len(recommended) >= 6:
            break
        if h["number"] not in recommended:
            recommended.add(h["number"])

    # 如果还不够，加遗漏最大的冷号
    if len(recommended) < 6:
        for num, days in miss_sorted:
            if len(recommended) >= 6:
                break
            if num not in recommended:
                recommended.add(num)

    final_numbers = sorted(list(recommended))

    # 策略描述
    hot_count = sum(1 for n in final_numbers if n in hot_nums)
    cold_count = sum(1 for n in final_numbers if n in cold_nums)
    drag_count = sum(1 for n in final_numbers if n in drag_cores)

    strategies = []
    if hot_count >= 3:
        strategies.append(f"热号{hot_count}个（高频号码近期活跃）")
    if cold_count >= 2:
        strategies.append(f"冷号{cold_count}个（遗漏极值，反弹概率较高）")
    if drag_count >= 3:
        strategies.append(f"五膽拖胆码{drag_count}个（回测验证有效）")

    # 信心评分
    total_score = sum(h["score"] for h in hot_scores if h["number"] in final_numbers)
    if total_score > 200:
        confidence = "高"
    elif total_score > 100:
        confidence = "中"
    else:
        confidence = "低"

    # 理由
    reason_lines = []
    for num in final_numbers:
        parts = [f"号码{num}"]
        if num in hot_nums:
            rank = hot_nums.index(num) + 1
            parts.append(f"热号第{rank}")
        else:
            parts.append("冷号")
        if num in miss_dict and miss_dict[num] > 5:
            parts.append(f"遗漏{miss_dict[num]}期")
        if num in drag_cores:
            parts.append("五膽拖胆码")
        if num in hot_nums and num in miss_dict:
            k = build_kline_data(num, 100)
            if "stats" in k:
                parts.append(f"开出率{k['stats']['hit_rate']}")
        reason_lines.append(" · ".join(parts))

    numbers_formatted = ",".join(str(n) for n in final_numbers)
    if 49 not in final_numbers and len(final_numbers) == 6:
        pass  # 刚好6个

    return {
        "numbers": final_numbers,
        "numbers_str": " ".join(str(n) for n in final_numbers),
        "strategy": " + ".join(strategies) if strategies else "综合平衡",
        "confidence": confidence,
        "stats": f"基于{total}期历史数据, 热{hot_count}冷{cold_count}胆{drag_count}",
        "reason": "\n".join(reason_lines),
        "debug": {
            "hot_scores": hot_scores[:10],
            "drag_cores": drag_cores,
        }
    }


if __name__ == "__main__":
    result = get_recommendation()
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"🎯 推荐号码: {result['numbers']}")
        print(f"策略: {result['strategy']}")
        print(f"信心: {result['confidence']}")
        print(f"\n📝 理由:")
        print(result["reason"])
