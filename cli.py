#!/usr/bin/env python3
"""
彩灵·智策 — 命令行入口
所有功能通过子命令调用

用法:
  python3 cli.py init       # 初始化数据库
  python3 cli.py fetch      # 拉取数据
  python3 cli.py analyze    # 全面分析
  python3 cli.py hot        # 冷热号
  python3 cli.py missing    # 遗漏值
  python3 cli.py backtest --cores 1 2 3 4 5  # 五膽拖回测
  python3 cli.py ev --calc 1 2 3 4 5 6       # 期望值
  python3 cli.py gui        # 启动图形界面
"""
import sys, os, json

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)


def cmd_init():
    from core.database import init_db
    init_db()
    print("✅ 数据库已初始化")


def cmd_fetch():
    from core.fetcher import fetch_all
    fetch_all()


def cmd_analyze():
    from core.analyzer import analyze
    analyze()


def cmd_hot():
    from core.analyzer import hot_cold_numbers
    hc = hot_cold_numbers()
    if "--json" in sys.argv:
        print(json.dumps(hc, ensure_ascii=False, indent=2))
    else:
        print(f"🔥 热号 Top 10: {hc['hot']}")
        print(f"❄️ 冷号 Top 10: {hc['cold']}")


def cmd_missing():
    from core.analyzer import missing_stats
    m = missing_stats()
    if "--json" in sys.argv:
        print(json.dumps(m, ensure_ascii=False, indent=2))
    else:
        print("📈 遗漏值 (最久未出):")
        for num, days in m[:15]:
            print(f"  {num:2d}: {days}期未出")


def cmd_backtest():
    from core.backtest import backtest_5drag, format_backtest, auto_backtest

    if "--auto" in sys.argv:
        trials = 500
        if "--trials" in sys.argv:
            idx = sys.argv.index("--trials") + 1
            if idx < len(sys.argv):
                trials = int(sys.argv[idx])
        print(f"🔍 自动扫描 {trials} 种组合...")
        best = auto_backtest(trials=trials)
        print(format_backtest(best["result"]))
        print(f"\n推荐胆码: {best['cores']}")
        return

    if "--cores" in sys.argv:
        idx = sys.argv.index("--cores") + 1
        cores = []
        while idx < len(sys.argv) and sys.argv[idx].lstrip('-').isdigit():
            cores.append(int(sys.argv[idx].lstrip('-+')))
            idx += 1
        if len(cores) != 5:
            print("❌ 需要5个胆码: --cores 1 2 3 4 5")
            return
        result = backtest_5drag(cores)
        if "--json" in sys.argv:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_backtest(result))


def cmd_ev():
    from core.ev import calculate_ev, analyze_best_combo

    if "--calc" in sys.argv:
        idx = sys.argv.index("--calc") + 1
        picks = []
        while idx < len(sys.argv) and sys.argv[idx].lstrip('-').isdigit():
            picks.append(int(sys.argv[idx].lstrip('-+')))
            idx += 1
        if len(picks) != 6:
            print("❌ 需要6个号码: --calc 1 2 3 4 5 6")
            return
        result = calculate_ev(picks)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("is_positive"):
            print("\n✅ 正期望值")
        else:
            print(f"\n❌ 负期望值, 每注预期亏损 ${10 - result.get('ev_total', 0):.2f}")

    elif "--best" in sys.argv:
        best = analyze_best_combo()
        print(json.dumps(best, ensure_ascii=False, indent=2))

    else:
        print("用法: python3 cli.py ev --calc 1 2 3 4 5 6")


def cmd_gui():
    """启动PyQt5图形界面"""
    from gui.app import run
    run()


def cmd_kline():
    """K线图数据分析"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", type=int, required=True, help="号码 1-49")
    parser.add_argument("--window", type=int, default=200)
    parser.add_argument("--json", action="store_true")
    args, _ = parser.parse_known_args(sys.argv[2:])
    from core.kline import build_kline_data
    data = build_kline_data(args.number, args.window)
    if "error" in data:
        print(f"❌ {data['error']}")
        return
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        s = data["stats"]
        print(f"📊 号码{args.number} K线分析 ({s['total_draws']}期)")
        print(f"  当前遗漏: {s['current_omission']}期 | 最大遗漏: {s['max_omission']}期 | 平均遗漏: {s['avg_omission']}期")
        print(f"  开出次数: {s['hit_count']}次 ({s['hit_rate']})")
        print(f"  运行 python3 cli.py chart --number {args.number} 生成K线图")


def cmd_chart():
    """生成K线图HTML"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", type=int, default=28)
    parser.add_argument("--window", type=int, default=200)
    parser.add_argument("--indicators", nargs="+",
                       default=["ma5", "ma10", "boll", "kdj", "macd", "rsi", "adx"])
    args, _ = parser.parse_known_args(sys.argv[2:])
    from core.chart import save_kline_chart, render_distribution_html
    path = save_kline_chart(args.number, args.window, args.indicators)
    print(f"  open {path}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    commands = {
        "init": cmd_init, "fetch": cmd_fetch,
        "analyze": cmd_analyze, "hot": cmd_hot,
        "missing": cmd_missing, "backtest": cmd_backtest,
        "ev": cmd_ev, "gui": cmd_gui,
        "kline": cmd_kline, "chart": cmd_chart,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(f"❌ 未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
