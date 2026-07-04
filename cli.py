#!/usr/bin/env python3
"""
彩灵·智策 — AI 调用入口

所有命令默认输出 JSON（供其他AI消费）。
添加 --human 参数输出人类可读文本。

用法:
  python3 cli.py init                              # 初始化数据库
  python3 cli.py hot           [--human]            # 冷热号
  python3 cli.py missing       [--human]            # 遗漏值
  python3 cli.py kline --number N [--human]         # K线+技术指标
  python3 cli.py backtest --auto|--cores ...        # 五膽拖回测
  python3 cli.py ev --calc 1 2 3 4 5 6              # 期望值
  python3 cli.py recommend     [--push]  [--human]  # AI推荐（核心）
  python3 cli.py chart --number N                   # 生成K线图
  python3 cli.py analyze       [--human]            # 全面分析
  python3 cli.py gui                                # 图形界面
"""
import sys, os, json

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)


def _is_human():
    """检查是否添加了 --human 参数"""
    return "--human" in sys.argv


def _json(data):
    """输出JSON（默认模式）"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_init():
    """初始化数据库"""
    from core.database import init_db
    init_db()
    _json({"status": "ok", "message": "数据库已初始化"})


def cmd_hot():
    """冷热号分析"""
    from core.analyzer import hot_cold_numbers
    hc = hot_cold_numbers()
    if _is_human():
        print("🔥 热号 Top 10:", hc["hot"])
        print("❄️ 冷号 Top 10:", hc["cold"])
    else:
        _json(hc)


def cmd_missing():
    """遗漏值分析"""
    from core.analyzer import missing_stats
    m = missing_stats()
    if _is_human():
        print("📈 遗漏值 (最久未出):")
        for num, days in m[:15]:
            print(f"  {num:2d}: {days}期未出")
    else:
        _json(m)


def cmd_kline():
    """K线数据+技术指标"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", type=int, required=True)
    parser.add_argument("--window", type=int, default=200)
    args, _ = parser.parse_known_args(sys.argv[2:])
    from core.kline import build_kline_data
    data = build_kline_data(args.number, args.window)
    if "error" in data:
        _json({"error": data["error"]})
        return
    if _is_human():
        s = data["stats"]
        print(f"📊 号码{args.number}: 遗漏{s['current_omission']}期 / 最大{s['max_omission']}期 / 开出{s['hit_rate']}")
    else:
        _json(data)


def cmd_backtest():
    """五膽拖回测"""
    from core.backtest import backtest_5drag, auto_backtest

    if "--auto" in sys.argv:
        trials = 500
        if "--trials" in sys.argv:
            idx = sys.argv.index("--trials") + 1
            if idx < len(sys.argv):
                trials = int(sys.argv[idx])
        best = auto_backtest(trials=trials)
        if _is_human():
            from core.backtest import format_backtest
            print(format_backtest(best["result"]))
            print(f"\n推荐胆码: {best['cores']}")
        else:
            _json(best)
        return

    if "--cores" in sys.argv:
        idx = sys.argv.index("--cores") + 1
        cores = []
        while idx < len(sys.argv) and sys.argv[idx].lstrip('-').isdigit():
            cores.append(int(sys.argv[idx].lstrip('-+')))
            idx += 1
        if len(cores) != 5:
            _json({"error": "需要5个胆码"})
            return
        result = backtest_5drag(cores)
        if _is_human():
            from core.backtest import format_backtest
            print(format_backtest(result))
        else:
            _json(result)


def cmd_ev():
    """期望值计算"""
    from core.ev import calculate_ev
    if "--calc" in sys.argv:
        idx = sys.argv.index("--calc") + 1
        picks = []
        while idx < len(sys.argv) and sys.argv[idx].lstrip('-').isdigit():
            picks.append(int(sys.argv[idx].lstrip('-+')))
            idx += 1
        if len(picks) != 6:
            _json({"error": "需要6个号码"})
            return
        result = calculate_ev(picks)
        _json(result)


def cmd_recommend():
    """AI推荐（核心入口）"""
    from core.recommender import get_recommendation
    result = get_recommendation()

    if _is_human():
        print(f"🎯 彩灵·智策 AI推荐")
        print(f"  推荐号码: {result.get('numbers', [])}")
        print(f"  策略: {result.get('strategy', '')}")
        print(f"  信心: {result.get('confidence', '')}")
        if result.get("reason"):
            print(f"\n📝 理由:")
            for line in result["reason"].split("\n"):
                print(f"  {line}")
        if result.get("stats"):
            print(f"\n📊 参考: {result['stats']}")
    else:
        _json(result)

    # --push 直接推送到Telegram
    if "--push" in sys.argv:
        try:
            text = (
                f"🎯 彩灵·智策 AI推荐\n"
                f"推荐号码: {result.get('numbers', [])}\n"
                f"策略: {result.get('strategy', '')}\n"
                f"信心: {result.get('confidence', '')}\n"
                f"理由: {result.get('reason', '')}"
            )
            for env_path in [
                os.path.expanduser("~/.hermes/.env"),
                os.path.join(BASE, "..", ".env"),
            ]:
                if os.path.exists(env_path):
                    with open(env_path) as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                os.environ.setdefault(k.strip(), v.strip())
            token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            chat = os.getenv("TELEGRAM_CHAT_ID", "") or os.getenv("TELEGRAM_HOME_CHANNEL", "")
            if token and chat:
                import requests as req
                req.post(f"https://api.telegram.org/bot{token}/sendMessage",
                        json={"chat_id": chat, "text": text}, timeout=10)
                print("  📤 已推送Telegram")
        except Exception as e:
            print(f"  ❌ 推送失败: {e}")


def cmd_chart():
    """生成K线图HTML"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", type=int, default=28)
    args, _ = parser.parse_known_args(sys.argv[2:])
    from core.chart import save_kline_chart
    path = save_kline_chart(args.number, 200,
                           ["ma5", "ma10", "boll", "kdj", "macd", "rsi", "adx"])
    _json({"status": "ok", "file": path})


def cmd_analyze():
    """全面分析（JSON聚合）"""
    from core.analyzer import hot_cold_numbers, missing_stats
    from core.kline import build_kline_data

    hc = hot_cold_numbers()
    miss = missing_stats()[:10]

    # 每个热号的K线摘要
    kline_summary = {}
    for num, _ in hc["hot"][:5]:
        k = build_kline_data(num, 100)
        if "stats" in k:
            kline_summary[str(num)] = k["stats"]

    result = {
        "hot_cold": {"hot": hc["hot"][:10], "cold": hc["cold"][:10]},
        "missing_top": miss,
        "kline_top5": kline_summary,
        "total_draws": 755,
    }
    _json(result)


def cmd_gui():
    """启动图形界面"""
    from gui.app import run
    run()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    commands = {
        "init": cmd_init,
        "hot": cmd_hot,
        "missing": cmd_missing,
        "kline": cmd_kline,
        "backtest": cmd_backtest,
        "ev": cmd_ev,
        "recommend": cmd_recommend,
        "chart": cmd_chart,
        "analyze": cmd_analyze,
        "gui": cmd_gui,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        _json({"error": f"未知命令: {cmd}"})


if __name__ == "__main__":
    main()
