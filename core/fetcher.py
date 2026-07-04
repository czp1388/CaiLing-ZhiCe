#!/usr/bin/env python3
"""
彩灵·智策 — 数据采集
从bet.hkjc.com获取六合彩历史开奖数据（Playwright）
"""
import sys, os, json
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from core.database import get_db, init_db


def fetch_marksix_results(target_date, max_retries=2):
    """用Playwright爬取六合彩开奖结果"""
    for attempt in range(max_retries):
        try:
            from playwright.sync_api import sync_playwright
            date_str = target_date.strftime("%Y-%m-%d")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                url = f"https://bet.hkjc.com/marksix/index.aspx?lang=ch&date={date_str}"
                page.goto(url, wait_until="domcontentloaded", timeout=30000)

                import time
                time.sleep(3)

                # 尝试提取开奖结果
                result = page.evaluate("""
                () => {
                    try {
                        // 找开奖号码元素
                        const elements = document.querySelectorAll('.markSixBall, .ball, [class*=ball], [class*=number]');
                        const nums = [];
                        for (const el of elements) {
                            const text = el.innerText.trim();
                            if (text && !isNaN(parseInt(text)) && parseInt(text) >= 1 && parseInt(text) <= 49) {
                                nums.push(parseInt(text));
                            }
                        }
                        if (nums.length >= 7) return nums.slice(0, 7);

                        // 备选：从页面文本找号码
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

                if result and len(result) >= 7:
                    draw_date = target_date.strftime("%Y-%m-%d")
                    main = sorted(result[:6])
                    extra = result[6]
                    return {
                        "draw_date": draw_date,
                        "draw_no": str(target_date.year) + target_date.strftime("%m%d"),
                        "n1": main[0], "n2": main[1], "n3": main[2],
                        "n4": main[3], "n5": main[4], "n6": main[5],
                        "extra": extra,
                    }
                return None

        except Exception as e:
            if attempt < max_retries - 1:
                import time
                time.sleep(2)
                continue
            return None
    return None


def generate_sample_data():
    """生成模拟数据用于开发和测试（六合彩历史开奖结果近似数据）"""
    import random
    random.seed(42)
    conn = get_db()
    count = 0
    today = datetime.now().date()

    # 六合彩每周二、四、六开奖
    for i in range(200):
        d = today - timedelta(days=i)
        if d.weekday() not in (1, 3, 5):  # 周二、四、六
            continue

        date_str = d.strftime("%Y-%m-%d")
        exists = conn.execute("SELECT id FROM draws WHERE draw_date=?", (date_str,)).fetchone()
        if exists:
            continue

        # 生成随机开奖号码
        nums = random.sample(range(1, 50), 7)
        main = sorted(nums[:6])
        extra = nums[6]

        try:
            conn.execute("""
                INSERT OR IGNORE INTO draws (draw_date, draw_no, n1, n2, n3, n4, n5, n6, extra)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date_str, "", main[0], main[1], main[2], main[3], main[4], main[5], extra))
            conn.commit()
            count += 1
        except:
            pass

    conn.close()
    return count


def fetch_all(limit=200):
    """批量采集"""
    init_db()
    conn = get_db()
    count = 0
    today = datetime.now().date()

    # 先尝试用Playwright实时抓取
    print("  📡 尝试实时抓取...")
    for i in range(min(limit, 60)):
        d = today - timedelta(days=i)
        if d.weekday() not in (1, 3, 5):  # 只查开奖日
            continue

        date_str = d.strftime("%Y-%m-%d")
        exists = conn.execute("SELECT id FROM draws WHERE draw_date=?", (date_str,)).fetchone()
        if exists:
            continue

        result = fetch_marksix_results(d)
        if result:
            conn.execute("""
                INSERT OR IGNORE INTO draws (draw_date, draw_no, n1, n2, n3, n4, n5, n6, extra)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (result["draw_date"], result["draw_no"],
                  result["n1"], result["n2"], result["n3"],
                  result["n4"], result["n5"], result["n6"],
                  result["extra"]))
            conn.commit()
            count += 1
            print(f"  ✅ {result['draw_date']}: {result['n1']},{result['n2']},{result['n3']},{result['n4']},{result['n5']},{result['n6']}+{result['extra']}")

    conn.close()
    print(f"\n✅ 实时采集: {count} 期")

    # 如果实时数据不够，补充模拟数据
    if count < 50:
        print("  📦 补充模拟数据...")
        sample = generate_sample_data()
        print(f"  ✅ 模拟数据: {sample} 期")

    return count


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        limit = 200
        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit") + 1
            if idx < len(sys.argv):
                limit = int(sys.argv[idx])
        fetch_all(limit)
    else:
        print("用法: python3 -m core.fetcher --fetch [--limit N]")
