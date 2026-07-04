#!/usr/bin/env python3
"""
彩灵·智策 — 五膽拖回测引擎

五膽拖玩法：选5个胆码（必中）+ 拖若干个号码
如果胆码中3个以上即有奖。回测用历史数据算命中率。
"""
import json, sys, os, itertools, math
from collections import defaultdict
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from core.database import get_db, get_draws


def backtest_5drag(cores, drags=None, max_window=100):
    """五膽拖回测

    cores: 5个胆码列表
    drags: 拖码列表（None=全部1-49去重）
    max_window: 回测最近N期

    返回: {"total": N, "hits": {等级:次数}, "details": [...]}
    """
    if len(cores) != 5:
        return {"error": "必须选5个胆码"}

    if drags is None:
        drags = [i for i in range(1, 50) if i not in cores]

    conn = get_db()
    rows = conn.execute(
        "SELECT draw_date,n1,n2,n3,n4,n5,n6,extra FROM draws ORDER BY draw_date DESC LIMIT ?",
        (max_window,)
    ).fetchall()
    conn.close()

    results = {
        "total": len(rows),
        "cores": sorted(cores),
        "drags_count": len(drags),
        "hits": {"head_prize": 0, "1st": 0, "2nd": 0, "3rd": 0, "4th": 0, "5th": 0, "6th": 0, "7th": 0},
        "details": []
    }

    for r in rows:
        draw_nums = {r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"]}
        extra = r["extra"]
        core_hits = len(set(cores) & draw_nums)
        drag_hits = len(set(drags) & draw_nums)

        # 计算奖金等级（六合彩规则简化版）
        prize_level = "no_prize"
        if core_hits == 5:
            # 胆码全中 + 至少一个拖码中 = 头奖
            if drag_hits >= 1:
                prize_level = "head_prize"
            else:
                prize_level = "2nd"
        elif core_hits == 4:
            if drag_hits >= 2:
                prize_level = "2nd"
            elif drag_hits == 1:
                prize_level = "3rd"
            else:
                prize_level = "no_prize"  # 拖码全要搭至少一个
        elif core_hits == 3:
            if drag_hits >= 3:
                prize_level = "3rd"
            elif drag_hits == 2:
                prize_level = "4th"
            elif drag_hits == 1:
                prize_level = "5th"
            else:
                prize_level = "no_prize"
        elif core_hits == 2:
            if drag_hits >= 4:
                prize_level = "4th"
            elif drag_hits == 3:
                prize_level = "5th"
            elif drag_hits == 2:
                prize_level = "6th"
            elif drag_hits == 1:
                prize_level = "7th"
            else:
                prize_level = "no_prize"
        elif core_hits <= 1:
            prize_level = "no_prize"

        if prize_level != "no_prize":
            results["hits"][prize_level] = results["hits"].get(prize_level, 0) + 1

        results["details"].append({
            "date": r["draw_date"],
            "core_hits": core_hits,
            "drag_hits": drag_hits,
            "prize": prize_level,
        })

    return results


def auto_backtest(trials=1000, max_window=100):
    """自动扫描最优的五膽拖组合（用小随机采样式）"""
    import random
    conn = get_db()

    # 获取热号作为胆码候选
    from core.analyzer import hot_cold_numbers
    hc = hot_cold_numbers(window=max_window, top=15)
    top_numbers = [n for n, _ in hc["hot"]]

    if len(top_numbers) < 5:
        top_numbers = list(range(1, 50))
        random.shuffle(top_numbers)

    best = {"win_rate": 0, "cores": [], "result": None}

    for _ in range(trials):
        cores = sorted(random.sample(top_numbers, 5))
        result = backtest_5drag(cores, max_window=max_window)
        total_hits = sum(result["hits"].values())
        win_rate = total_hits / max(result["total"], 1)

        if win_rate > best["win_rate"] and total_hits >= 1:
            best = {
                "win_rate": round(win_rate * 100, 1),
                "total_hits": total_hits,
                "cores": cores,
                "result": result,
            }

    conn.close()
    return best


def analyze_drag_efficiency(cores, max_window=100):
    """分析拖码效率：哪些号码作为拖码时中奖率最高"""
    from core.analyzer import hot_cold_numbers

    hc = hot_cold_numbers(window=max_window, top=20)
    candidates = [n for n, _ in hc["hot"] if n not in cores]

    results = []
    for drag in candidates[:10]:
        r = backtest_5drag(cores, drags=[drag], max_window=max_window)
        total_hits = sum(r["hits"].values())
        results.append({"drag": drag, "hits": total_hits, "details": r["hits"]})

    results.sort(key=lambda x: -x["hits"])
    return results


def format_backtest(result):
    """格式化回测结果"""
    lines = []
    lines.append("📊 五膽拖回测结果")
    lines.append(f"  胆码: {result.get('cores', '?')}")
    lines.append(f"  回测期数: {result.get('total', 0)}")
    lines.append("")

    hits = result.get("hits", {})
    total_hits = sum(hits.values())
    win_rate = total_hits / max(result.get("total", 1), 1) * 100
    lines.append(f"  总中奖次数: {total_hits}")
    lines.append(f"  中奖率: {win_rate:.1f}%")
    lines.append("")

    prize_names = {
        "head_prize": "🏆 头奖", "1st": "🥇 一等奖",
        "2nd": "🥈 二等奖", "3rd": "🥉 三等奖",
        "4th": "🎯 四等奖", "5th": "🎯 五等奖",
        "6th": "🎯 六等奖", "7th": "🎯 七等奖",
    }

    for key, name in prize_names.items():
        c = hits.get(key, 0)
        if c > 0:
            lines.append(f"  {name}: {c}次")

    return "\n".join(lines)


if __name__ == "__main__":
    if "--auto" in sys.argv:
        trials = 500
        if "--trials" in sys.argv:
            idx = sys.argv.index("--trials") + 1
            if idx < len(sys.argv):
                trials = int(sys.argv[idx])
        print(f"🔍 自动扫描 {trials} 种组合...")
        best = auto_backtest(trials=trials)
        print(f"\n✅ 最优组合:")
        print(format_backtest(best["result"]))
        print(f"\n推荐胆码: {best['cores']}")

    elif "--test" in sys.argv:
        # 测试指定组合
        cores = []
        if "--cores" in sys.argv:
            idx = sys.argv.index("--cores") + 1
            while idx < len(sys.argv) and sys.argv[idx].isdigit():
                cores.append(int(sys.argv[idx]))
                idx += 1

        if len(cores) != 5:
            print("❌ 需要5个胆码: --cores 1 2 3 4 5")
            sys.exit(1)

        result = backtest_5drag(cores)
        print(format_backtest(result))

        print(f"\n🔍 最佳拖码分析:")
        eff = analyze_drag_efficiency(cores)
        for e in eff[:5]:
            print(f"  拖{e['drag']:2d}: {e['hits']}次中奖")

    elif "--json" in sys.argv:
        cores = list(map(int, sys.argv[sys.argv.index("--json") + 1:sys.argv.index("--json") + 6]))
        result = backtest_5drag(cores)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print("用法:")
        print("  python3 -m core.backtest --auto                 # 自动扫描最优组合")
        print("  python3 -m core.backtest --test --cores 1 2 3 4 5  # 测试指定组合")
        print("  python3 -m core.backtest --json 1 2 3 4 5       # JSON输出")
