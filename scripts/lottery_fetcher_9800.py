#!/usr/bin/env python3
"""
乐透堂六合彩数据爬虫 — 备选数据源

当HKJC官网抓取失败时，从乐透堂补爬。
乐透堂不需要Playwright，直接curl即可。
"""
import sys, os, csv
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "core"))
from database import get_db


def fetch_lottery_data(start_period=26001, end_period=26080):
    """从乐透堂爬取六合彩数据"""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("❌ 需要 requests 和 bs4")
        return []

    url = "http://www.9800.com.tw/lotto6/drop.html"
    data = {"drop_nums": f"{start_period}-{end_period}"}

    try:
        resp = requests.post(url, data=data, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find_all('table')[1]
        rows = table.find_all('tr')[1:]

        results = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 5:
                period = cells[0].get_text(strip=True)
                date_str = cells[1].get_text(strip=True)
                sorted_nums = cells[4].get_text(strip=True)
                nums = sorted_nums.replace('+', ' ').split()
                results.append({
                    "draw_no": period,
                    "draw_date": date_str,
                    "nums": [int(x) for x in nums],
                })
        return results
    except Exception as e:
        print(f"❌ 乐透堂抓取失败: {e}")
        return []


def sync_to_db(results, source="scraped"):
    """将乐透堂数据写入数据库（不覆盖已有但n1>0的记录）"""
    conn = get_db()
    count = 0
    for r in results:
        existing = conn.execute(
            "SELECT n1 FROM draws WHERE draw_no=?", (r["draw_no"],)
        ).fetchone()
        if existing and existing[0] > 0 and existing[0] < 50:
            continue  # 已有真实数据，跳过
        n = r["nums"]
        conn.execute("""
            INSERT OR REPLACE INTO draws
            (draw_date, draw_no, n1,n2,n3,n4,n5,n6,extra, data_source, scraped_at)
            VALUES (?,?,?,?,?,?,?,?,?,?, datetime('now'))
        """, (r["draw_date"], r["draw_no"],
              n[0], n[1], n[2], n[3], n[4], n[5], n[6],
              source))
        count += 1
    conn.commit()
    conn.close()
    return count


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="乐透堂六合彩爬虫")
    parser.add_argument("--start", type=int, default=26001, help="起始期号")
    parser.add_argument("--end", type=int, default=26080, help="结束期号")
    parser.add_argument("--sync", action="store_true", help="同步到数据库")
    args = parser.parse_args()

    print(f"📡 爬取乐透堂 {args.start}-{args.end}...")
    data = fetch_lottery_data(args.start, args.end)
    print(f"✅ 获取 {len(data)} 期")

    if args.sync and data:
        count = sync_to_db(data)
        print(f"✅ 同步 {count} 期到数据库")
    elif data:
        for d in data:
            print(f"  {d['draw_no']} {d['draw_date']}: {d['nums'][:7]}")
