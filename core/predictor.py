"""走势预测：冷号反弹预警 + 简单时间序列预测"""
import json, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.kline import build_kline_data
from core.database import get_db
from core.analyzer import missing_stats

def get_cold_alerts(threshold=20):
    """遗漏超过threshold期的冷号，标注反弹预警"""
    miss = missing_stats(200)
    alerts = [(num, days) for num, days in miss if days >= threshold]
    return alerts[:10]

def predict_next_range():
    """基于最近60期走势，预测下一期的和值区间"""
    conn = get_db()
    rows = conn.execute("SELECT n1,n2,n3,n4,n5,n6 FROM draws ORDER BY draw_date DESC LIMIT 60").fetchall()
    conn.close()
    sums = [sum(r[c] for c in ["n1","n2","n3","n4","n5","n6"]) for r in rows]
    avg_s = sum(sums) / len(sums)
    std_s = (sum((s - avg_s)**2 for s in sums) / len(sums)) ** 0.5
    return {"predicted_range": [round(avg_s - std_s), round(avg_s + std_s)], "avg": round(avg_s), "std": round(std_s)}

def predict_hot_zones(window=30):
    """预测热号区间分布"""
    conn = get_db()
    rows = conn.execute("SELECT n1,n2,n3,n4,n5,n6,extra FROM draws ORDER BY draw_date DESC LIMIT ?", (window,)).fetchall()
    conn.close()
    zones = {"1-12": 0, "13-24": 0, "25-36": 0, "37-49": 0}
    for r in rows:
        for n in [r[c] for c in ["n1","n2","n3","n4","n5","n6","extra"]]:
            if n <= 12: zones["1-12"] += 1
            elif n <= 24: zones["13-24"] += 1
            elif n <= 36: zones["25-36"] += 1
            else: zones["37-49"] += 1
    total = sum(zones.values())
    for k in zones:
        zones[k] = round(zones[k] / total * 100, 1)
    return {"zones": zones, "most_active": max(zones, key=zones.get)}

if __name__ == "__main__":
    result = {"cold_alerts": get_cold_alerts(), "next_sum": predict_next_range(), "hot_zones": predict_hot_zones()}
    print(json.dumps(result, ensure_ascii=False, indent=2))
