#!/usr/bin/env python3
"""开奖核对闭环：抓开奖→核对两套方案→统计→推送"""
import json, logging, os, sys, time, requests
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db
from core.history import get_history

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

SEVENTH = 40   # 七奖
SIXTH = 320    # 六奖
FIFTH = 640    # 五奖
FOURTH = 9600  # 四奖
THIRD = 50000  # 三奖

def _prize_for(m6, me):
    """根据命中数返回奖金"""
    if m6 == 6:               return 10000000  # 头奖
    if m6 == 5 and me:        return 500000    # 二奖
    if m6 == 5:               return 50000     # 三奖
    if m6 == 4:               return 9600      # 四奖
    if m6 == 3 and me:        return 640       # 五奖
    if m6 == 3:               return 320       # 六奖
    if m6 == 2 and me:        return 40        # 七奖
    return 0

def _prize_level_name(m6, me):
    if m6 == 6:               return "🏆头奖"
    if m6 == 5 and me:        return "🥈二奖"
    if m6 == 5:               return "🥉三奖"
    if m6 == 4:               return "💵四奖"
    if m6 == 3 and me:        return "💵五奖"
    if m6 == 3:               return "🎯六奖"
    if m6 == 2 and me:        return "🎯七奖"
    return ""

def check_combo(combo_set, draw_set6, extra):
    """检查一注组合的命中情况"""
    m6 = len(combo_set & draw_set6)
    me = 1 if extra in combo_set else 0
    prize = _prize_for(m6, me)
    return m6, me, prize

def _push_msg(text):
    """推送开奖核对报告（通过统一推送模块）"""
    import sys as _sys
    _notifier_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "彩灵交易系统")
    if _notifier_path not in _sys.path:
        _sys.path.insert(0, _notifier_path)
    from notifier import push
    push("六合彩", "开奖核对", body=text, level="normal")

def fetch_latest_draw():
    """从HKJC官网抓取最新开奖结果（仅限开奖日21:00后执行）

    规则：
      - 开奖日前（<21:00）：返回"待开奖"标记，不写号码
      - 开奖日后（>=21:00）：抓取号码并返回
      - 非开奖日：返回None
    """
    import time as _time
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    # 检查今天是否开奖日（周二/四/六）
    if now.weekday() not in (1, 3, 5):
        _logger.info(f"{date_str} 非开奖日，跳过")
        return None

    # 检查是否已过开奖时间（21:30开奖，21:00后可抓）
    if now.hour < 21:
        _logger.info(f"{date_str} 开奖日但未到21:00，返回待开奖标记")
        return {"draw_date": date_str, "status": "scheduled"}

    # 已过21:00，尝试抓取开奖结果
    for _attempt in range(3):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("https://bet.hkjc.com/marksix/index.aspx?lang=ch", wait_until="domcontentloaded", timeout=30000)
                _time.sleep(3)
                nums = page.evaluate("""() => {
                    try {
                        const body = document.body.innerText;
                        const matches = body.match(/\\b([1-9]|[1-4][0-9])\\b/g);
                        if (matches && matches.length >= 7) {
                            return matches.slice(0, 7).map(Number);
                        }
                        return null;
                    } catch(e) { return null; }
                }
                """)
                browser.close()
                if nums and len(nums) >= 7:
                    main = sorted(nums[:6])
                    extra = nums[6]
                    return {"draw_date": date_str, "n1": main[0], "n2": main[1], "n3": main[2],
                            "n4": main[3], "n5": main[4], "n6": main[5], "extra": extra,
                            "status": "drawn"}
            break
        except Exception as e:
            if _attempt < 2:
                _time.sleep((_attempt + 1) * 30)
                continue
            _logger.warning(f"获取开奖数据失败(重试{_attempt+1}次): {e}")
    return None


def verify_plan_a(rec_nums, draw_set6, extra):
    """方案A：6正选"""
    combo_set = set(rec_nums) if isinstance(rec_nums, (list, set)) else set()
    m6, me, prize = check_combo(combo_set, draw_set6, extra)
    return {
        "hits": m6 + me,
        "hits_6": m6,
        "hits_extra": me,
        "prize": prize,
        "level": _prize_level_name(m6, me),
        "matched": sorted(combo_set & (draw_set6 | {extra})),
    }

def verify_plan_b(combos, draw_set6, extra):
    """方案B：检查所有16注旋转矩阵"""
    total_prize = 0
    winning_combos = []
    for i, combo in enumerate(combos):
        combo_set = set(combo)
        m6, me, prize = check_combo(combo_set, draw_set6, extra)
        if prize > 0:
            total_prize += prize
            winning_combos.append({
                "index": i,
                "combo": sorted(combo),
                "hits_6": m6,
                "hits_extra": me,
                "prize": prize,
                "level": _prize_level_name(m6, me),
            })
    return {
        "total_prize": total_prize,
        "winning_count": len(winning_combos),
        "winning_combos": winning_combos,
        "max_level": max((w["level"] for w in winning_combos), key=lambda x: ["", "🎯七奖", "🎯六奖", "💵五奖", "💵四奖", "🥉三奖", "🥈二奖", "🏆头奖"].index(x) if x in ["", "🎯七奖", "🎯六奖", "💵五奖", "💵四奖", "🥉三奖", "🥈二奖", "🏆头奖"] else 0) if winning_combos else "",
    }


def check_and_update():
    """检查开奖 → 核对双方案 → 推送"""
    conn = get_db()
    latest = conn.execute("SELECT draw_date FROM draws ORDER BY draw_date DESC LIMIT 1").fetchone()
    latest_date = latest[0] if latest else None

    draw = fetch_latest_draw()
    if not draw:
        return {"status": "skipped", "reason": "开奖数据未获取到，请稍后再试"}

    # 如果是"待开奖"状态（开奖日21:00前），插入占位记录但不写号码
    if draw.get("status") == "scheduled":
        dup = conn.execute("SELECT id FROM draws WHERE draw_date=?", (draw["draw_date"],)).fetchone()
        if not dup:
            # 推算期号
            last_no = conn.execute("SELECT draw_no FROM draws WHERE draw_no GLOB '0*' ORDER BY draw_no DESC LIMIT 1").fetchone()
            new_no = str(int(last_no[0]) + 1).zfill(6) if last_no else "000001"
            conn.execute("INSERT INTO draws (draw_date,draw_no,n1,n2,n3,n4,n5,n6,extra,scraped_at) VALUES (?,?,0,0,0,0,0,0,0,datetime('now'))",
                         (draw["draw_date"], new_no))
            conn.commit()
        conn.close()
        _push_msg(f"🎯 今晚六合彩开奖（{draw['draw_date']}），结果将在21:30后更新")
        return {"status": "scheduled", "draw_date": draw["draw_date"]}

    if draw["draw_date"] != latest_date:
        # 双重检查：此日期可能已有占位记录（开奖前插入的scheduled）
        dup = conn.execute("SELECT id, n1 FROM draws WHERE draw_date=?", (draw["draw_date"],)).fetchone()
        if dup:
            if dup["n1"] == 0:
                # 已有占位记录，更新为真实号码
                conn.execute("UPDATE draws SET n1=?,n2=?,n3=?,n4=?,n5=?,n6=?,extra=?,scraped_at=datetime('now') WHERE id=?",
                             (draw["n1"], draw["n2"], draw["n3"], draw["n4"], draw["n5"], draw["n6"], draw["extra"], dup["id"]))
                conn.commit()
                new_draw = True
            else:
                new_draw = False
        else:
            conn.execute("INSERT INTO draws (draw_date,n1,n2,n3,n4,n5,n6,extra,scraped_at) VALUES (?,?,?,?,?,?,?,?,datetime('now'))",
                         (draw["draw_date"], draw["n1"], draw["n2"], draw["n3"], draw["n4"], draw["n5"], draw["n6"], draw["extra"]))
            conn.commit()
            new_draw = True
    else:
        new_draw = False

    draw_set6 = {draw["n1"], draw["n2"], draw["n3"], draw["n4"], draw["n5"], draw["n6"]}
    extra = draw["extra"]
    draw_all7 = draw_set6 | {extra}

    # 读取最近推荐
    history = get_history(5)
    last_rec = history[0] if history else None
    conn.close()

    plan_a_result = {}
    plan_b_result = {}
    report_lines = [f"📊 开奖核对 | {draw['draw_date']}",
                    f"开奖号码：{draw['n1']} {draw['n2']} {draw['n3']} {draw['n4']} {draw['n5']} {draw['n6']} + {draw['extra']}"]

    if last_rec:
        # 方案A核对
        rec_nums = last_rec.get("numbers", [])
        if isinstance(rec_nums, str):
            rec_nums = json.loads(rec_nums)
        plan_a_result = verify_plan_a(rec_nums, draw_set6, extra)
        a_line = f"方案A ({' '.join(str(n) for n in rec_nums)})：中{plan_a_result['hits_6']}个正选"
        if plan_a_result["level"]:
            a_line += f" {plan_a_result['level']} ${plan_a_result['prize']:,}"
        else:
            a_line += " 未中奖"
        report_lines.append(a_line)

        # 方案B核对
        plan_b_combos = last_rec.get("plan_b_combos", [])
        if isinstance(plan_b_combos, str) and plan_b_combos:
            plan_b_combos = json.loads(plan_b_combos)
        if plan_b_combos:
            plan_b_result = verify_plan_b(plan_b_combos, draw_set6, extra)
            pool = last_rec.get("plan_b_pool", "")
            pool_str = ""
            if pool:
                if isinstance(pool, str):
                    pool_list = json.loads(pool)
                else:
                    pool_list = pool
                pool_str = f" ({' '.join(str(n) for n in pool_list)})"
            b_line = f"方案B{pool_str}：17注"
            if plan_b_result["winning_count"] > 0:
                b_line += f" → 中{plan_b_result['winning_count']}注"
                if plan_b_result["max_level"]:
                    b_line += f" {plan_b_result['max_level']}"
                b_line += f" 总奖金${plan_b_result['total_prize']:,}"
            else:
                b_line += " 未中奖"
            report_lines.append(b_line)

    # 累计统计
    all_history = get_history(100)
    stats_a = {"total": 0, "hits_1plus": 0, "total_matches": 0, "max_hits": 0}
    stats_b = {"total": 0, "draws_with_win": 0, "total_prize": 0, "big_win_draws": 0}

    for h in all_history:
        hn = h.get("numbers", [])
        if isinstance(hn, str): hn = json.loads(hn)
        td = h["created_at"][:10] if h.get("created_at") else ""
        conn2 = get_db()
        act = conn2.execute("SELECT n1,n2,n3,n4,n5,n6,extra FROM draws WHERE draw_date < ? ORDER BY draw_date DESC LIMIT 1", (td,)).fetchone()
        conn2.close()
        if act:
            an6 = {act[c] for c in ["n1","n2","n3","n4","n5","n6"]}
            an7 = an6 | {act["extra"]}
            # 方案A
            h6 = len(set(hn) & an6)
            stats_a["total"] += 1
            stats_a["total_matches"] += h6
            stats_a["max_hits"] = max(stats_a["max_hits"], h6)
            if h6 >= 1:
                stats_a["hits_1plus"] += 1

            # 方案B
            b_combos = h.get("plan_b_combos", [])
            if isinstance(b_combos, str) and b_combos:
                b_combos = json.loads(b_combos)
            if b_combos:
                b_res = verify_plan_b(b_combos, an6, act["extra"])
                stats_b["total"] += 1
                if b_res["winning_count"] > 0:
                    stats_b["draws_with_win"] += 1
                stats_b["total_prize"] += b_res["total_prize"]
                # 是否有5+命中（三奖及以上）
                if any(c["hits_6"] >= 5 or c["hits_6"] == 4 and c["hits_extra"] for c in b_res["winning_combos"]):
                    stats_b["big_win_draws"] += 1

    # 累计统计行
    a_hit_rate = f"{stats_a['hits_1plus']/max(stats_a['total'],1)*100:.0f}%" if stats_a["total"] else "0%"
    b_win_rate = f"{stats_b['draws_with_win']/max(stats_b['total'],1)*100:.0f}%" if stats_b["total"] else "0%"
    report_lines.append(f"累计({all_history[0]['created_at'][:10] if all_history else '?'}起)：方案A命中率{a_hit_rate} 方案B中奖率{b_win_rate}")
    report_lines.append("")
    report_lines.append("📌 当前为模拟验证阶段，建议暂不实买")

    report = "\n".join(report_lines)

    can_push = bool(os.getenv("TELEGRAM_BOT_TOKEN", "")) or os.path.exists(os.path.expanduser("~/.hermes/.env"))
    if can_push:
        _push_msg(report)

    return {
        "status": "ok",
        "new_draw": new_draw,
        "draw": draw,
        "plan_a": plan_a_result,
        "plan_b": plan_b_result,
        "stats": {
            "plan_a": {"total": stats_a["total"], "hits_1plus": stats_a["hits_1plus"],
                       "hit_rate": a_hit_rate, "total_matches": stats_a["total_matches"],
                       "max_hits": stats_a["max_hits"]},
            "plan_b": {"total": stats_b["total"], "draws_with_win": stats_b["draws_with_win"],
                       "win_rate": b_win_rate, "total_prize": stats_b["total_prize"],
                       "big_win_draws": stats_b["big_win_draws"]},
        },
        "report": report,
    }


def run_full_backtest():
    """773期完整回测（保留兼容）"""
    import random
    from core.database import get_db
    from core.analyzer import hot_cold_numbers, missing_stats
    from core.kline import build_kline_data

    conn = get_db()
    dates = [r["draw_date"] for r in conn.execute("SELECT draw_date FROM draws ORDER BY draw_date").fetchall()]
    START, STEP = 200, 5
    TEST_DATES = dates[START::STEP]
    ai_total, rand_total = 0, 0
    ai_break = {1:0,2:0,3:0,4:0,5:0,6:0}
    for idx, td in enumerate(TEST_DATES):
        act = conn.execute("SELECT n1,n2,n3,n4,n5,n6,extra FROM draws WHERE draw_date=?", (td,)).fetchone()
        if not act: continue
        actual = {act[c] for c in ["n1","n2","n3","n4","n5","n6","extra"]}
        hc = hot_cold_numbers(100, 15)
        h_nums = [n for n,_ in hc["hot"]]
        m_d = {n:d for n,d in missing_stats(100)}
        scores = []
        for num in h_nums:
            k = build_kline_data(num, 100)
            if "stats" not in k: continue
            hi = h_nums.index(num)
            mv = m_d.get(num, 0)
            hr = float(k["stats"]["hit_rate"].replace("%",""))
            s = (15-hi)*3 + mv*0.5 + hr*0.3
            scores.append({"n": num, "s": s})
        scores.sort(key=lambda x: -x["s"])
        ai = set()
        for s in scores:
            ai.add(s["n"])
            if len(ai) >= 6: break
        while len(ai) < 6:
            ai.add(random.randint(1,49))
        h = len(ai & actual)
        ai_total += h
        if 1 <= h <= 6: ai_break[h] = ai_break.get(h,0)+1
        rand_total += len(set(random.sample(range(1,50),6)) & actual)
    conn.close()
    n = len(TEST_DATES)
    return {"total_tests": n, "ai_avg": round(ai_total/n,3), "rand_avg": round(rand_total/n,3),
            "ai_hit_rate": f"{round((n-sum(v for v in ai_break.values() if v))/n*100,1)}%",
            "breakdown": {str(k):v for k,v in ai_break.items()},
            "conclusion": f"AI推荐平均每期{round(ai_total/n,3)}个, 比随机({round(rand_total/n,3)}个)强{round((ai_total/rand_total-1)*100,1)}%"}

if __name__ == "__main__":
    result = check_and_update()
    print(json.dumps(result, ensure_ascii=False, indent=2))
