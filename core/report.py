#!/usr/bin/env python3
"""生成分析报告HTML（走势图+推荐+理由+历史对比）"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.chart import render_kline_html
from core.recommender import get_recommendation
from core.cooccurrence import analyze_cooccurrence

def generate_html():
    rec = get_recommendation()
    # 为每个推荐号码生成K线图
    charts = ""
    for num in rec["numbers"][:3]:
        charts += render_kline_html(num, 150, ["ma5", "boll", "rsi"])
    # 共现数据
    co_all = analyze_cooccurrence()
    co_table = ""
    for a, b, c in co_all.get("top_pairs", [])[:10]:
        co_table += f"<tr><td>{a}</td><td>{b}</td><td>{c}次</td></tr>"
    nums_html = " ".join(f'<span style="display:inline-block;width:36px;height:36px;line-height:36px;border-radius:50%;background:#ffd700;color:#1a1a2e;text-align:center;font-weight:bold;margin:2px">{n}</span>' for n in rec["numbers"])
    nd_html = ""
    for nd in rec["number_details"]:
        nd_html += f"<tr><td>{nd['number']}</td><td>{nd['hit_rate']}</td><td>{nd['deviation']}</td><td>{nd['omission']}</td></tr>"
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>彩灵·智策 分析报告</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}} body{{font-family:-apple-system,'Segoe UI',sans-serif;background:#0f0f1a;color:#e0e0e0;padding:20px}}
.header{{text-align:center;padding:30px;background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:12px;margin-bottom:20px}}
.header h1{{color:#ffd700;font-size:24px}} .header p{{color:#888;margin-top:8px}}
.numbers{{text-align:center;padding:20px;background:#1a1a2e;border-radius:12px;margin-bottom:20px}}
.numbers h2{{color:#ffd700;font-size:18px;margin-bottom:10px}}
.strategy{{color:#888;margin-top:8px;font-size:14px}}
.confidence{{display:inline-block;padding:2px 10px;border-radius:4px;font-size:12px;font-weight:bold}}
.high{{background:#4caf50;color:#fff}} .medium{{background:#ff9800;color:#fff}} .low{{background:#f44336;color:#fff}}
.section{{background:#1a1a2e;border-radius:12px;padding:20px;margin-bottom:20px}}
.section h2{{color:#ffd700;font-size:16px;margin-bottom:10px;border-bottom:1px solid #333;padding-bottom:8px}}
table{{width:100%;border-collapse:collapse}} td,th{{padding:8px;text-align:center;border-bottom:1px solid #333;font-size:13px}}
th{{color:#ffd700}} td{{color:#ccc}}
.charts{{display:flex;flex-wrap:wrap;gap:10px}} .charts iframe{{flex:1;min-width:300px;height:400px;border:none;border-radius:8px}}
</style></head><body>
<div class="header"><h1>🎯 彩灵·智策 分析报告</h1><p>生成时间: {__import__('time').strftime('%Y-%m-%d %H:%M')}</p></div>
<div class="numbers"><h2>🎯 AI推荐号码</h2><div style="font-size:28px;margin:10px 0">{nums_html}</div>
<p class="strategy">{rec['strategy']} | 平均开出率 {rec['avg_hit_rate']} | 信心 <span class="confidence {rec['confidence'].lower()}">{rec['confidence']}</span></p></div>
<div class="section"><h2>📊 号码详情</h2><table><tr><th>号码</th><th>开出率</th><th>偏差</th><th>遗漏</th></tr>{nd_html}</table></div>
<div class="section"><h2>🤝 号码共现 Top 10</h2><table><tr><th>号码A</th><th>号码B</th><th>共现次数</th></tr>{co_table}</table></div>
<div class="section"><h2>📈 走势图</h2><div class="charts">{charts}</div></div>
</body></html>"""
    return html

def save_report(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "report.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    html = generate_html()
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path

if __name__ == "__main__":
    p = save_report()
    print(json.dumps({"status": "ok", "file": p}, ensure_ascii=False, indent=2))
