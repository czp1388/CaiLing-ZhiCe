#!/usr/bin/env python3
"""
彩灵·智策 — AI推荐引擎

结合冷热号、遗漏值、K线技术指标、五膽拖回测，
输出一个最终的号码推荐 + 理由 + 信心评分。

信心评级标准（量化）：
- 高：历史平均开出率 >= 25%
- 中：历史平均开出率 18%-25%
- 低：历史平均开出率 < 18%

供其他AI（小墨/小灵）通过 cli.py recommend --json 调用。
"""
import json, sys, os, random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from core.database import get_db, get_number_frequency
from core.analyzer import hot_cold_numbers, missing_stats
from core.kline import build_kline_data
from core.backtest import auto_backtest
from core.predictor import get_cold_alerts, predict_next_range, predict_hot_zones


def get_recommendation(seed=42, weights=None):
    """综合所有分析，输出一个号码推荐

    固定随机种子(seed=42)，确保同样输入产出同样结果。
    """
    random.seed(seed)

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

    kdj_scores = {}
    cold_alert_nums = cold_alert_nums if 'cold_alert_nums' in dir() else []
    # 3. 每个热号的综合评分
    hot_scores = []
    for num in hot_nums:
        k = build_kline_data(num, 100)
        if "stats" in k:
            s = k["stats"]
            hot_idx = hot_nums.index(num)
            miss_val = miss_dict.get(num, 0)
            hit_rate = float(s["hit_rate"].replace("%", ""))
            kdj_bonus = kdj_scores.get(num, 0)
            cold_bonus = 5 if num in cold_alert_nums else 0
            w = weights or {}
            score = (15 - hot_idx) * w.get("hot", 3) + miss_val * w.get("miss", 0.5) + hit_rate * 0.3 + kdj_bonus + cold_bonus
            hot_scores.append({"number": num, "score": round(score, 1),
                               "hot_rank": hot_idx + 1, "omission": miss_val,
                               "hit_rate": s["hit_rate"]})
    hot_scores.sort(key=lambda x: -x["score"])

    # 4. 冷号反弹预警
    cold_alerts = get_cold_alerts(20)
    cold_alert_nums = [n for n, _ in cold_alerts]

    # 5. 走势预测
    next_sum = predict_next_range()
    hot_zones = predict_hot_zones()
    active_zone = hot_zones["most_active"]

    # 6. 技术指标信号融合（KDJ金叉/死叉）
    kdj_scores = {}
    for num in hot_nums[:10]:
        k = build_kline_data(num, 50)
        if "indicators" in k and k["indicators"].get("kdj"):
            k_arr = k["indicators"]["kdj"][0]
            d_arr = k["indicators"]["kdj"][1]
            if len(k_arr) >= 3 and k_arr[-1] is not None and d_arr[-1] is not None:
                if k_arr[-1] > d_arr[-1] and k_arr[-3] <= d_arr[-3]:
                    kdj_scores[num] = 5  # 金叉加分
                elif k_arr[-1] < d_arr[-1] and k_arr[-3] >= d_arr[-3]:
                    kdj_scores[num] = -3  # 死叉减分

    # 7. 五膽拖最优组合
    random.seed(seed)
    best_drag = auto_backtest(trials=300)
    drag_cores = best_drag.get("cores", [])

    # 5. 综合推荐号码
    recommended = set()
    for n in drag_cores:
        if len(recommended) >= 6:
            break
        recommended.add(n)
    for h in hot_scores:
        if len(recommended) >= 6:
            break
        if h["number"] not in recommended:
            recommended.add(h["number"])
    if len(recommended) < 6:
        for num, days in miss_sorted:
            if len(recommended) >= 6:
                break
            if num not in recommended:
                recommended.add(num)

    final_numbers = sorted(list(recommended))

    # 6. 统计指标
    hot_count = sum(1 for n in final_numbers if n in hot_nums)
    cold_count = sum(1 for n in final_numbers if n in cold_nums)
    drag_count = sum(1 for n in final_numbers if n in drag_cores)

    # 7. 计算每个号码的历史开出率
    # 六合彩每期开7个号(6正选+1特别), 共49个号
    # 单号码理论开出率 = 7/49 ≈ 14.3%
    # 高于14.3% = 热号, 低于14.3% = 冷号
    expected_rate = round(7 / 49 * 100, 1)  # 14.3%
    freq = get_number_frequency()
    number_details = []
    hit_rates = []
    for num in final_numbers:
        hit_count = freq.get(num, 0)
        # 单号码开出率 = 该号码出现次数 / 总期数
        hit_rate_pct = round(hit_count / total * 100, 1)
        hit_rates.append(hit_rate_pct)
        # 相对预期值的偏差
        deviation = round(hit_rate_pct - expected_rate, 1)
        number_details.append({
            "number": num,
            "hit_count": hit_count,
            "hit_rate": f"{hit_rate_pct}%",
            "expected": f"{expected_rate}%",
            "deviation": f"{deviation:+.1f}%",
            "omission": miss_dict.get(num, 0),
            "is_hot": num in hot_nums,
            "is_cold": num in cold_nums,
            "is_drag_core": num in drag_cores,
        })
    avg_hit_rate = round(sum(hit_rates) / len(hit_rates), 1)

    # 8. 信心评级（量化标准，基于相对预期值的偏差）
    # 六合彩单号码理论开出率 = 7/49 ≈ 14.3%
    # 平均偏差 >= +3% = 明显高于随机 → 高
    # 平均偏差 >= 0% = 不低于随机 → 中
    # 平均偏差 < 0% = 低于随机 → 低
    avg_deviation = round(avg_hit_rate - expected_rate, 1)
    if avg_hit_rate >= 15.0:
        confidence = "高"
    elif avg_hit_rate >= 14.0:
        confidence = "中"
    else:
        confidence = "低"

    # 9. 策略描述
    strategies = []
    strategies.append(f"预测和值区间:{next_sum['predicted_range'][0]}-{next_sum['predicted_range'][1]}")
    strategies.append(f"热区:{active_zone}")
    if hot_count >= 3:
        strategies.append(f"热号{hot_count}个（高频号码近期活跃）")
    if cold_count >= 2:
        strategies.append(f"冷号{cold_count}个（遗漏极值，反弹概率较高）")
    if drag_count >= 3:
        strategies.append(f"五膽拖胆码{drag_count}个（回测验证有效）")

    # 10. 推荐理由
    reason_lines = []
    for nd in number_details:
        parts = [f"号码{nd['number']}"]
        if nd["is_hot"]:
            rank = hot_nums.index(nd["number"]) + 1 if nd["number"] in hot_nums else 0
            parts.append(f"热号第{rank}")
        if nd["is_cold"]:
            parts.append("冷号")
        if nd["omission"] > 5:
            parts.append(f"遗漏{nd['omission']}期")
        if nd["is_drag_core"]:
            parts.append("五膽拖胆码")
        parts.append(f"开出率{nd['hit_rate']}({nd['deviation']})")
        reason_lines.append(" · ".join(parts))

    return {
        "numbers": final_numbers,
        "numbers_str": " ".join(str(n) for n in final_numbers),
        "number_details": number_details,
        "avg_hit_rate": f"{avg_hit_rate}%",
        "expected_rate": f"{expected_rate}%",
        "avg_deviation": f"{avg_deviation:+.1f}%",
        "confidence": confidence,
        "confidence_standard": {
            "高": "平均开出率 >= 15.0% (Top热号水平)",
            "中": "平均开出率 >= 14.0% (接近预期14.3%)",
            "低": "平均开出率 < 14.0% (低于随机)",
        },
        "strategy": " + ".join(strategies) if strategies else "综合平衡",
        "stats": f"基于{total}期历史数据, 热{hot_count}冷{cold_count}胆{drag_count}",
        "reason": "\n".join(reason_lines),
        "cold_alerts": cold_alerts[:5],
        "next_sum_range": next_sum["predicted_range"],
        "active_zone": active_zone,
        "debug": {
            "hot_scores": hot_scores[:10],
            "drag_cores": drag_cores,
            "seed": seed,
        }
    }


if __name__ == "__main__":
    result = get_recommendation()
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"🎯 推荐号码: {result['numbers']} (信心:{result['confidence']})")
        print(f"策略: {result['strategy']}")
        print(f"平均开出率: {result['avg_hit_rate']}")
        print(f"\n📝 理由:")
        print(result["reason"])
