#!/usr/bin/env python3
"""
六合彩推送调度器 — 开奖日自动生成推荐+推送

流程：
  1. 每天运行一次（cron）
  2. 检查当天是否开奖日（从HKJC官网爬）
  3. 如果是 → 跑推荐 → 推送早报集成
  4. 如果不是 → 安静退出
"""
import os, sys, json, re
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent  # 彩灵·智策根目录
sys.path.insert(0, str(BASE))


def is_draw_day(target_date=None):
    """
    检查指定日期是否六合彩开奖日
    先从HKJC官网查，查不到回退到历史数据判断
    """
    if target_date is None:
        target_date = datetime.now()
    date_str = target_date.strftime("%Y-%m-%d")
    
    # 方法1: 从HKJC官网爬
    try:
        import requests
        from bs4 import BeautifulSoup
        # 六合彩首頁有下期开奖日期
        url = "https://bet.hkjc.com/marksix/index.aspx?lang=ch"
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        })
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 找"下一期"或"Next Draw"相关信息
            page_text = soup.get_text()
            # 匹配 YYYY-MM-DD 或 DD/MM/YYYY 格式的日期
            dates = re.findall(r'(\d{4}-\d{2}-\d{2})', page_text)
            for d in dates:
                if d == date_str:
                    return True
            # 也试 DD/MM/YYYY
            dates_dmy = re.findall(r'(\d{2}/\d{2}/\d{4})', page_text)
            target_dmy = target_date.strftime("%d/%m/%Y")
            if target_dmy in dates_dmy:
                return True
    except:
        pass
    
    # 方法2: 从数据库历史数据推断（周二四六）
    # 95%以上开奖日在周二/四/六
    weekday = target_date.weekday()
    if weekday in [1, 3, 5]:  # 周二=1, 周四=3, 周六=5
        return True
    
    return False


def run_daily():
    """六合彩每日调度"""
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    weekday = today.weekday()
    weekdays = ["一","二","三","四","五","六","日"]
    
    print(f"📅 六合彩调度: {date_str} 周{weekdays[weekday]}")
    
    # 检查是否开奖日
    if not is_draw_day(today):
        print(f"  📭 今日不开奖，跳过")
        return {"status": "skipped", "reason": "not_draw_day"}
    
    print(f"  🎯 今日开奖日！")
    
    # 跑推荐
    try:
        from core.recommender import get_recommendation
        rec = get_recommendation()
        print(f"  ✅ 推荐已生成: {rec.get('numbers')}")
        
        # 保存到数据库
        from core.history import save_recommendation
        save_recommendation(rec)
        print(f"  ✅ 推荐已保存")
        
        # 推送（通过主项目的notifier）
        try:
            notifier_path = Path.home() / "Desktop" / "彩灵交易系统"
            if str(notifier_path) not in sys.path:
                sys.path.insert(0, str(notifier_path))
            from notifier import push
            
            nums_a = ", ".join(str(n) for n in rec.get("numbers", []))
            plan_c = rec.get("plan_c", {})
            nums_c = ", ".join(str(n) for n in plan_c.get("numbers", []))
            
            body = (
                f"🎯 六合彩 · {date_str} 开奖日\n\n"
                f"方案A（6正选·$10）\n"
                f"推荐号码: {nums_a}\n"
                f"信心: {rec.get('confidence', '')}\n\n"
                f"方案C（九码复式·$840）\n"
                f"推荐号码: {nums_c}\n"
                f"共84注 C(9,6)\n\n"
            )
            push("六合彩", "今日推荐", body=body, level="important")
            print(f"  ✅ 已推送")
        except Exception as e:
            print(f"  ⚠️ 推送失败: {e}")
        
        return {"status": "ok", "numbers": rec.get("numbers")}
    
    except Exception as e:
        print(f"  ❌ 推荐失败: {e}")
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    result = run_daily()
    print(f"结果: {result}")
