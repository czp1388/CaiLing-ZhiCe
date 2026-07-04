#!/usr/bin/env python3
"""
彩灵·智策 — K线图数据 + 技术指标

基于遗漏值生成K线数据，叠加6项技术指标：
均线(MA/EMA)、布林带(BOLL)、KDJ、MACD、RSI、ADX

参考：奇妙三数字趋势分析系统的设计思路，适配六合彩
"""
import json, sys, os, math
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from core.database import get_db


def get_omission_series(number, window=200):
    """获取指定号码的遗漏值序列（最近N期）

    遗漏值 = 该号码连续未出现的期数
    每期：如果号码开出→遗漏重置为0；未开出→遗漏+1
    返回: [(期次日期, 是否开出, 遗漏值), ...]
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT draw_date,n1,n2,n3,n4,n5,n6,extra FROM draws ORDER BY draw_date DESC LIMIT ?",
        (window,)
    ).fetchall()
    conn.close()

    rows.reverse()  # 按时间正序

    series = []
    omission = 0
    for r in rows:
        nums = {r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"], r["extra"]}
        hit = number in nums
        if hit:
            omission = 0
        else:
            omission += 1
        series.append({
            "date": r["draw_date"],
            "hit": hit,
            "omission": omission,
            "open": max(0, omission - 1),  # K线模拟
            "high": omission,
            "low": max(0, omission - 2),
            "close": omission,
        })

    return series


def calc_ma(series, period=5):
    """普通均线"""
    values = [s["omission"] for s in series]
    ma = []
    for i in range(len(values)):
        if i < period - 1:
            ma.append(None)
        else:
            ma.append(round(sum(values[i - period + 1:i + 1]) / period, 2))
    return ma


def calc_ema(series, period=5):
    """指数均线"""
    values = [s["omission"] for s in series]
    ema = []
    multiplier = 2 / (period + 1)
    for i in range(len(values)):
        if i == 0:
            ema.append(values[i])
        else:
            ema.append(round((values[i] - ema[-1]) * multiplier + ema[-1], 2))
    return ema


def calc_bollinger(series, period=10, num_std=2):
    """布林带"""
    values = [s["omission"] for s in series]
    mid = calc_ma(series, period)
    upper, lower = [], []
    for i in range(len(values)):
        if mid[i] is None:
            upper.append(None)
            lower.append(None)
        else:
            subset = values[max(0, i - period + 1):i + 1]
            std = np.std(subset)
            upper.append(round(mid[i] + num_std * std, 2))
            lower.append(round(mid[i] - num_std * std, 2))
    return upper, mid, lower


def calc_kdj(series, period=9):
    """KDJ随机指标"""
    highs = [s["high"] for s in series]
    lows = [s["low"] for s in series]
    closes = [s["close"] for s in series]
    k_values, d_values, j_values = [], [], []

    for i in range(len(series)):
        if i < period - 1:
            k_values.append(None)
            d_values.append(None)
            j_values.append(None)
        else:
            hh = max(highs[i - period + 1:i + 1])
            ll = min(lows[i - period + 1:i + 1])
            rsv = (closes[i] - ll) / (hh - ll) * 100 if hh != ll else 50
            if i == period - 1:
                k = rsv
                d = rsv
            else:
                k = 2 / 3 * k_values[-1] + 1 / 3 * rsv
                d = 2 / 3 * d_values[-1] + 1 / 3 * k
            j = 3 * k - 2 * d
            k_values.append(round(k, 2))
            d_values.append(round(d, 2))
            j_values.append(round(j, 2))

    return k_values, d_values, j_values


def calc_macd(series, fast=12, slow=26, signal=9):
    """MACD指标"""
    closes = [s["close"] for s in series]
    ema_fast = calc_ema_data(closes, fast)
    ema_slow = calc_ema_data(closes, slow)
    dif = [round(ema_fast[i] - ema_slow[i], 2) if ema_fast[i] is not None and ema_slow[i] is not None else None
           for i in range(len(closes))]
    dea = calc_ema_data(dif, signal)
    macd_hist = [round(dif[i] - dea[i], 2) if dif[i] is not None and dea[i] is not None else None
                 for i in range(len(closes))]
    return dif, dea, macd_hist


def calc_ema_data(values, period):
    """计算EMA序列（通用）"""
    result = []
    multiplier = 2 / (period + 1)
    for i in range(len(values)):
        if values[i] is None:
            result.append(None)
            continue
        if i == 0 or result[-1] is None:
            result.append(values[i])
        else:
            result.append(round((values[i] - result[-1]) * multiplier + result[-1], 2))
    return result


def calc_rsi(series, period=14):
    """RSI相对强弱指标"""
    values = [s["omission"] for s in series]
    rsi = []
    for i in range(len(values)):
        if i < period:
            rsi.append(None)
        else:
            gains, losses = 0, 0
            for j in range(i - period + 1, i + 1):
                diff = values[j] - values[j - 1]
                if diff > 0:
                    gains += diff
                else:
                    losses -= diff
            avg_gain = gains / period
            avg_loss = losses / period
            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi.append(round(100 - 100 / (1 + rs), 2))
    return rsi


def calc_adx(series, period=14):
    """ADX趋势强度指标（简化版）"""
    values = [s["omission"] for s in series]
    adx = []
    for i in range(len(values)):
        if i < period * 2:
            adx.append(None)
        else:
            # 简化计算：用价格变动方向模拟
            up_sum, down_sum = 0, 0
            for j in range(i - period + 1, i + 1):
                diff = values[j] - values[j - 1]
                if diff >= 0:
                    up_sum += diff
                else:
                    down_sum -= diff
            if up_sum + down_sum == 0:
                adx.append(50)
            else:
                adx.append(round(up_sum / (up_sum + down_sum) * 100, 2))
    return adx


def build_kline_data(number, window=200):
    """构建完整K线数据（含所有技术指标）"""
    series = get_omission_series(number, window)

    if not series:
        return {"error": f"号码{number}无数据"}

    dates = [s["date"] for s in series]
    omit = [s["omission"] for s in series]
    hits = [s["hit"] for s in series]
    opens = [s["open"] for s in series]
    highs = [s["high"] for s in series]
    lows = [s["low"] for s in series]
    closes = [s["close"] for s in series]

    result = {
        "number": number,
        "total_periods": len(series),
        "date_range": {"from": series[0]["date"], "to": series[-1]["date"]},
        "kline": series,
        "indicators": {
            "ma5": calc_ma(series, 5),
            "ma10": calc_ma(series, 10),
            "ma20": calc_ma(series, 20),
            "ema5": calc_ema(series, 5),
            "ema10": calc_ema(series, 10),
            "boll": calc_bollinger(series, 10),
            "kdj": calc_kdj(series, 9),
            "macd": calc_macd(series),
            "rsi": calc_rsi(series, 14),
            "adx": calc_adx(series, 14),
        },
        "stats": {
            "current_omission": omit[-1] if omit else 0,
            "max_omission": max(omit) if omit else 0,
            "avg_omission": round(sum(omit) / len(omit), 1) if omit else 0,
            "hit_count": sum(hits),
            "total_draws": len(hits),
            "hit_rate": f"{sum(hits) / len(hits) * 100:.1f}%" if hits else "0%",
        }
    }

    return result


def analyze_number_distribution():
    """号码分布分析：区间/奇偶/大小/和值"""
    conn = get_db()
    rows = conn.execute(
        "SELECT draw_date,n1,n2,n3,n4,n5,n6,extra FROM draws ORDER BY draw_date"
    ).fetchall()
    conn.close()

    result = []
    for r in rows:
        nums = [r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"]]
        extra = r["extra"]
        all_nums = nums + [extra]

        odd_count = sum(1 for n in all_nums if n % 2 == 1)
        big_count = sum(1 for n in all_nums if n > 24)
        total_sum = sum(nums)
        # 区间分布
        zones = [0, 0, 0, 0, 0]
        for n in all_nums:
            if 1 <= n <= 9:
                zones[0] += 1
            elif 10 <= n <= 19:
                zones[1] += 1
            elif 20 <= n <= 29:
                zones[2] += 1
            elif 30 <= n <= 39:
                zones[3] += 1
            elif 40 <= n <= 49:
                zones[4] += 1

        result.append({
            "date": r["draw_date"],
            "odd_even": f"{odd_count}:{len(all_nums) - odd_count}",
            "big_small": f"{big_count}:{len(all_nums) - big_count}",
            "sum": total_sum,
            "zones": zones,
        })

    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="K线数据生成")
    parser.add_argument("--number", type=int, required=True, help="号码 1-49")
    parser.add_argument("--window", type=int, default=200)
    parser.add_argument("--json", action="store_true", help="JSON输出")
    args = parser.parse_args()

    data = build_kline_data(args.number, args.window)
    if "error" in data:
        print(f"❌ {data['error']}")
        sys.exit(1)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        s = data["stats"]
        print(f"📊 号码{args.number} K线分析")
        print(f"  统计期数: {s['total_draws']}")
        print(f"  当前遗漏: {s['current_omission']}期")
        print(f"  最大遗漏: {s['max_omission']}期")
        print(f"  平均遗漏: {s['avg_omission']}期")
        print(f"  开出次数: {s['hit_count']}次 ({s['hit_rate']})")
