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


def cmd_daily_run():
    """🌟 一键日常：检查更新→分析→推荐→推送"""
    quiet = "--quiet" in sys.argv
    push = "--push" in sys.argv
    from core.logging_util import get_logger
    log = get_logger("daily_run")
    log.info("daily-run started")
    try:
        from core.auto_update import update
        updated = update()
        log.info(f"update: {updated}")
    except Exception as e:
        log.error(f"update failed: {e}")
    if not quiet:
        print(json.dumps({"step": "update", "status": "ok"}))
    try:
        from core.recommender import get_recommendation
        rec = get_recommendation()
        if "error" in rec:
            if not quiet:
                _json({"status": "skipped", "reason": rec["error"]})
            return
        if not quiet:
            _json(rec)
        log.info(f"recommend: {rec['numbers']} confidence={rec['confidence']}")
        if push:
            token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            chat = os.getenv("TELEGRAM_CHAT_ID", "") or os.getenv("TELEGRAM_HOME_CHANNEL", "")
            for p in [os.path.expanduser("~/.hermes/.env"), os.path.join(BASE, ".env")]:
                if os.path.exists(p):
                    with open(p) as f:
                        for line in f:
                            if "=" in line and not line.startswith("#"):
                                k, v = line.strip().split("=", 1)
                                os.environ.setdefault(k.strip(), v.strip())
            token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
            chat = chat or os.getenv("TELEGRAM_CHAT_ID", "") or os.getenv("TELEGRAM_HOME_CHANNEL", "")
            if token and chat:
                import requests as req
                nums_display = " ".join(str(n) for n in rec['numbers'])
                reasons_short = []
                for nd in rec['number_details']:
                    tags = []
                    if nd['omission'] > 5: tags.append(f"遗漏{nd['omission']}期")
                    if nd['deviation']: tags.append(nd['deviation'])
                    reasons_short.append(f"#{nd['number']} {' '.join(tags)}")
                text = f"🎯 彩灵智策 · {rec['confidence']} \n推荐: {nums_display}\n{rec['avg_hit_rate']} | {' | '.join(reasons_short)}"
                req.post(f"https://api.telegram.org/bot{token}/sendMessage",
                        json={"chat_id": chat, "text": text}, timeout=10)
                log.info("telegram pushed")
                if not quiet:
                    print("  📤 Telegram已推送")
    except Exception as e:
        log.error(f"recommend failed: {e}")
        if not quiet:
            _json({"error": str(e)})
    log.info("daily-run completed")


def cmd_report():
    """📊 生成HTML分析报告"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default=None)
    args, _ = parser.parse_known_args(sys.argv[2:])
    from core.report import save_report
    path = save_report(args.output)
    _json({"status": "ok", "file": path})


def cmd_cooccur():
    """🔗 号码共现分析"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", type=int, default=None)
    args, _ = parser.parse_known_args(sys.argv[2:])
    from core.cooccurrence import analyze_cooccurrence
    result = analyze_cooccurrence(args.number)
    _json(result)



def cmd_compare():
    """📊 多期推荐对比"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    args, _ = parser.parse_known_args(sys.argv[2:])
    from core.history import get_history
    h = get_history(args.days)
    if not h:
        _json({"error": "无推荐历史"})
        return
    result = []
    for r in h:
        nums = json.loads(r["numbers"]) if isinstance(r["numbers"], str) else r["numbers"]
        result.append({"date": r["created_at"][:10], "numbers": nums, "confidence": r["confidence"]})
    _json(result)


def cmd_predict():
    """🔮 走势预测：冷号预警+和值区间+热区"""
    from core.predictor import get_cold_alerts, predict_next_range, predict_hot_zones
    result = {"cold_alerts": get_cold_alerts(), "next_sum": predict_next_range(), "hot_zones": predict_hot_zones()}
    if "--human" in sys.argv:
        print("❄️ 冷号反弹预警:")
        for n, d in result["cold_alerts"][:5]:
            print(f"  号码{n}: 遗漏{d}期")
        print(f"\n📊 下期和值预测: {result['next_sum']['predicted_range']}")
        print(f"🔥 热区: {result['hot_zones']['most_active']} ({result['hot_zones']['zones']})")
    else:
        _json(result)


def cmd_strategies():
    """🎯 多策略输出"""
    from core.recommender import get_recommendation
    from core.backtest import auto_backtest
    result = {"current": get_recommendation()}
    # 冷号策略：用不同seed
    result["cold_focus"] = get_recommendation(seed=99)
    result["balanced"] = get_recommendation(seed=123)
    if "--human" in sys.argv:
        for k, v in result.items():
            print(f"\n{'='*30}\n{k}: {v['numbers']} (信心:{v['confidence']})")
    else:
        _json(result)

def cmd_pattern():
    """🔍 历史模式匹配"""
    from core.pattern_matcher import find_similar_patterns
    result = find_similar_patterns()
    _json(result)



def cmd_accuracy():
    """📊 推荐准确率统计"""
    from core.stats import accuracy_report
    _json(accuracy_report())

def cmd_weekly():
    """📅 周报"""
    from core.weekly import generate_weekly
    if "--human" in sys.argv:
        w = generate_weekly()
        print(f"📅 周报: {w['period']}")
        print(f"推荐次数: {w['total_recommendations']}")
        print(f"本周推荐: {w['weekly_pick']}")
        print(f"冷号预警: {w['cold_alerts']}")
    else:
        _json(generate_weekly())

def cmd_backup():
    """💾 备份数据库"""
    from core.database import backup_db
    _json(backup_db())

def cmd_missing_chart():
    """📈 遗漏值走势图/区间热度图"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", type=int, default=28)
    parser.add_argument("--window", type=int, default=100)
    args, _ = parser.parse_known_args(sys.argv[2:])
    from core.chart import render_omission_chart, render_zone_heatmap
    base = os.path.dirname(os.path.abspath(__file__))
    if "--zone" in sys.argv:
        html = render_zone_heatmap(args.window)
        path = os.path.join(base, "output", "zones.html")
    else:
        html = render_omission_chart(args.number, args.window)
        path = os.path.join(base, "output", f"omission_{args.number}.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    _json({"status": "ok", "file": path})
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    commands = {
        "init": cmd_init, "hot": cmd_hot, "missing": cmd_missing,
        "kline": cmd_kline, "backtest": cmd_backtest, "ev": cmd_ev,
        "recommend": cmd_recommend, "chart": cmd_chart, "analyze": cmd_analyze,
        "gui": cmd_gui, "daily-run": cmd_daily_run, "report": cmd_report, "compare": cmd_compare, "predict": cmd_predict, "strategies": cmd_strategies,
        "cooccur": cmd_cooccur, "pattern": cmd_pattern, "accuracy": cmd_accuracy, "weekly": cmd_weekly, "backup": cmd_backup, "missing-chart": cmd_missing_chart, "compare-versions": cmd_compare_versions, "tune": cmd_tune, "rotate": cmd_rotate,
    }

    if cmd in ("--help", "-h"):
        print(__doc__)
    elif cmd in commands:
        commands[cmd]()
    else:
        _json({"error": f"未知命令: {cmd}"})




def cmd_compare_versions():
    """📊 版本对比回测"""
    from core.version_compare import compare_versions
    r = compare_versions(30)
    if "--human" in sys.argv:
        print(f"{'版本':>8s} {'命中':>6s} {'总数':>6s} {'命中率':>8s}")
        print("-" * 35)
        for v, d in sorted(r.items()):
            print(f"{v:>8s} {d['hits']:>6d} {d['total']:>6d} {d['rate']:>8s}")
    else:
        _json(r)


def cmd_tune():
    """🔧 自动调参-网格搜索最优权重"""
    from core.tuner import grid_search
    result = grid_search(30)
    if "--human" in sys.argv:
        print(f"最优权重: {result.get('weights', {})}")
        print(f"命中率: {result.get('rate_pct', '?')}")
    else:
        _json(result)


def cmd_rotate():
    """🔄 号码去重与轮换建议"""
    from core.history import get_history
    h = get_history(10)
    from collections import Counter
    all_nums = []
    for r in h:
        nums = __import__('json').loads(r["numbers"]) if isinstance(r["numbers"], str) else r["numbers"]
        all_nums.extend(nums)
    freq = Counter(all_nums)
    warnings = [{"number": n, "count": c, "suggestion": "建议轮换" if c >= 3 else ""} for n, c in freq.most_common(10)]
    import json as _json_mod
    print(_json_mod.dumps({"frequencies": warnings[:6], "total_history": len(h)}, ensure_ascii=False, indent=2))

    main()


def cmd_compare_versions():
    """📊 版本对比回测"""
    from core.version_compare import compare_versions
    r = compare_versions(30)
    if "--human" in sys.argv:
        print(f"{'版本':>8s} {'命中':>6s} {'总数':>6s} {'命中率':>8s}")
        print("-" * 35)
        for v, d in sorted(r.items()):
            print(f"{v:>8s} {d['hits']:>6d} {d['total']:>6d} {d['rate']:>8s}")
    else:
        _json(r)


def cmd_tune():
    """🔧 自动调参-网格搜索最优权重"""
    from core.tuner import grid_search
    result = grid_search(30)
    if "--human" in sys.argv:
        print(f"最优权重: {result.get('weights', {})}")
        print(f"命中率: {result.get('rate_pct', '?')}")
    else:
        _json(result)


def cmd_rotate():
    """🔄 号码去重与轮换建议"""
    from core.history import get_history
    h = get_history(10)
    from collections import Counter
    all_nums = []
    for r in h:
        nums = __import__('json').loads(r["numbers"]) if isinstance(r["numbers"], str) else r["numbers"]
        all_nums.extend(nums)
    freq = Counter(all_nums)
    warnings = [{"number": n, "count": c, "suggestion": "建议轮换" if c >= 3 else ""} for n, c in freq.most_common(10)]
    import json as _json_mod
    print(_json_mod.dumps({"frequencies": warnings[:6], "total_history": len(h)}, ensure_ascii=False, indent=2))

    main()
