#!/usr/bin/env python3
"""
彩灵·智策 — Plotly图表渲染

生成K线图、技术指标、分布图等交互式HTML图表
嵌入PyQt5的QWebEngineView中显示
"""
import json, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from core.kline import build_kline_data, analyze_number_distribution


def render_kline_html(number, window=200, indicators=None):
    """生成号码遗漏值K线图HTML（含技术指标）

    indicators: 要显示的指标列表，如 ["ma5","ma10","boll","kdj","macd","rsi","adx"]
    """
    data = build_kline_data(number, window)
    if "error" in data:
        return f"<h3>❌ {data['error']}</h3>"

    if indicators is None:
        indicators = ["ma5", "ma10", "boll"]

    dates = [s["date"] for s in data["kline"]]
    omit = [s["omission"] for s in data["kline"]]
    hits = [s["hit"] for s in data["kline"]]
    ind = data["indicators"]
    stats = data["stats"]

    # 构建Plotly traces
    traces = []

    # 主K线（用柱状图表示遗漏值，红色=开出，蓝色=未开出）
    colors = ["#ef5350" if h else "#42a5f5" for h in hits]
    traces.append({
        "type": "bar",
        "x": dates, "y": omit,
        "marker": {"color": colors},
        "name": f"号码{number}遗漏值",
        "hovertemplate": "%{x}<br>遗漏: %{y}期<extra></extra>",
    })

    # 均线
    indicator_configs = {
        "ma5": {"data": ind["ma5"], "name": "MA5", "color": "#ff9800"},
        "ma10": {"data": ind["ma10"], "name": "MA10", "color": "#4caf50"},
        "ma20": {"data": ind["ma20"], "name": "MA20", "color": "#f44336"},
        "ema5": {"data": ind["ema5"], "name": "EMA5", "color": "#ff5722", "dash": "dot"},
        "ema10": {"data": ind["ema10"], "name": "EMA10", "color": "#795548", "dash": "dot"},
    }

    for key in indicators:
        if key in indicator_configs:
            cfg = indicator_configs[key]
            trace = {
                "type": "scatter", "mode": "lines",
                "x": dates, "y": cfg["data"],
                "name": cfg["name"],
                "line": {"color": cfg["color"], "width": 1.5},
                "hovertemplate": f"{cfg['name']}: %{{y}}<extra></extra>",
            }
            if "dash" in cfg:
                trace["line"]["dash"] = cfg["dash"]
            traces.append(trace)

    # 布林带
    if "boll" in indicators:
        upper, mid, lower = ind["boll"]
        traces.append({
            "type": "scatter", "mode": "lines",
            "x": dates, "y": upper,
            "name": "BOLL上", "line": {"color": "rgba(156,39,176,0.5)", "width": 1},
            "hovertemplate": "上轨: %{y}<extra></extra>",
        })
        traces.append({
            "type": "scatter", "mode": "lines",
            "x": dates, "y": lower,
            "name": "BOLL下", "line": {"color": "rgba(156,39,176,0.5)", "width": 1},
            "fill": "tonexty", "fillcolor": "rgba(156,39,176,0.1)",
            "hovertemplate": "下轨: %{y}<extra></extra>",
        })

    # 技术指标副图
    subplot_traces = []
    if "kdj" in indicators:
        k, d, j = ind["kdj"]
        subplot_traces.extend([
            {"type": "scatter", "mode": "lines", "x": dates, "y": k, "name": "K", "line": {"color": "#ff7043"}, "yaxis": "y2", "hovertemplate": "K: %{y}<extra></extra>"},
            {"type": "scatter", "mode": "lines", "x": dates, "y": d, "name": "D", "line": {"color": "#42a5f5"}, "yaxis": "y2", "hovertemplate": "D: %{y}<extra></extra>"},
            {"type": "scatter", "mode": "lines", "x": dates, "y": j, "name": "J", "line": {"color": "#66bb6a"}, "yaxis": "y2", "hovertemplate": "J: %{y}<extra></extra>"},
        ])
    if "macd" in indicators:
        dif, dea, macd_hist = ind["macd"]
        colors_macd = ["#ef5350" if v and v >= 0 else "#42a5f5" for v in macd_hist]
        subplot_traces.extend([
            {"type": "bar", "x": dates, "y": macd_hist, "name": "MACD", "marker": {"color": colors_macd}, "yaxis": "y3", "hovertemplate": "MACD: %{y}<extra></extra>"},
            {"type": "scatter", "mode": "lines", "x": dates, "y": dif, "name": "DIF", "line": {"color": "#1565c0", "width": 1}, "yaxis": "y3", "hovertemplate": "DIF: %{y}<extra></extra>"},
            {"type": "scatter", "mode": "lines", "x": dates, "y": dea, "name": "DEA", "line": {"color": "#e65100", "width": 1}, "yaxis": "y3", "hovertemplate": "DEA: %{y}<extra></extra>"},
        ])
    if "rsi" in indicators:
        rsi = ind["rsi"]
        subplot_traces.append({
            "type": "scatter", "mode": "lines", "x": dates, "y": rsi,
            "name": "RSI", "line": {"color": "#e91e63", "width": 1.5},
            "yaxis": "y4",
            "hovertemplate": "RSI: %{y}<extra></extra>",
        })
    if "adx" in indicators:
        adx = ind["adx"]
        subplot_traces.append({
            "type": "scatter", "mode": "lines", "x": dates, "y": adx,
            "name": "ADX", "line": {"color": "#9c27b0", "width": 1.5, "dash": "dot"},
            "yaxis": "y4",
            "hovertemplate": "ADX: %{y}<extra></extra>",
        })

    all_traces = traces + subplot_traces

    # 构建布局
    subplot_count = 0
    if "kdj" in indicators: subplot_count += 1
    if "macd" in indicators: subplot_count += 1
    if "rsi" in indicators or "adx" in indicators: subplot_count += 1

    grid_rows = 1 + subplot_count
    heights = [60] + [20] * subplot_count if subplot_count > 0 else [100]

    layout = {
        "title": {
            "text": f"号码{number} 遗漏值K线图 | 当前遗漏{stats['current_omission']}期 | 最大遗漏{stats['max_omission']}期 | 开出率{stats['hit_rate']}",
            "font": {"size": 14},
        },
        "xaxis": {
            "rangeslider": {"visible": True},
            "showspikes": True,
            "spikemode": "across",
        },
        "yaxis": {"title": "遗漏值", "domain": [0, 0.6]},
        "barmode": "overlay",
        "hovermode": "x unified",
        "height": 800,
        "template": "plotly_white",
        "showlegend": True,
        "legend": {"orientation": "h", "y": -0.2},
    }

    # 副图Y轴
    y_axis_count = 1
    if "kdj" in indicators:
        y_axis_count += 1
        layout[f"yaxis{y_axis_count}"] = {"title": "KDJ", "domain": [0.6, 0.75], "overlaying": "y", "side": "right"}
    if "macd" in indicators:
        y_axis_count += 1
        layout[f"yaxis{y_axis_count}"] = {"title": "MACD", "domain": [0.35, 0.5], "overlaying": "y", "side": "right"}
    if "rsi" in indicators or "adx" in indicators:
        y_axis_count += 1
        layout[f"yaxis{y_axis_count}"] = {"title": "RSI/ADX", "domain": [0.15, 0.3], "overlaying": "y", "side": "right"}

    figure = {"data": all_traces, "layout": layout}
    plotly_json = json.dumps(figure, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>*{{margin:0;padding:0}} body{{background:#fff}}</style>
</head><body>
<div id="chart"></div>
<script>
var data = {plotly_json};
Plotly.newPlot('chart', data.data, data.layout, {{
    responsive: true,
    scrollZoom: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
}});
</script></body></html>"""
    return html


def render_distribution_html():
    """号码分布分析HTML（区间/奇偶/大小/和值）"""
    dist = analyze_number_distribution()
    if not dist:
        return "<h3>❌ 无数据</h3>"

    # 提取最近50期
    recent = dist[-50:]

    traces = [
        {
            "type": "scatter", "mode": "lines+markers",
            "x": [r["date"] for r in recent],
            "y": [r["sum"] for r in recent],
            "name": "和值",
            "line": {"color": "#ff7043"},
            "hovertemplate": "%{x}<br>和值: %{y}<extra></extra>",
        },
        {
            "type": "bar",
            "x": [r["date"] for r in recent],
            "y": [int(r["odd_even"].split(":")[0]) for r in recent],
            "name": "奇数个数",
            "marker": {"color": "#42a5f5"},
        },
    ]

    figure = {
        "data": traces,
        "layout": {
            "title": "号码分布走势",
            "xaxis": {"rangeslider": {"visible": True}},
            "hovermode": "x unified",
            "height": 500,
            "template": "plotly_white",
        }
    }

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
</head><body>
<div id="chart"></div>
<script>
var data = {json.dumps(figure, ensure_ascii=False)};
Plotly.newPlot('chart', data.data, data.layout, {{responsive: true}});
</script></body></html>"""
    return html




def render_omission_chart(number, window=100):
    """生成单号码遗漏值走势折线图HTML"""
    from core.kline import build_kline_data
    data = build_kline_data(number, window)
    if "error" in data: return f"<h3>❌ {data['error']}</h3>"
    dates = [s["date"] for s in data["kline"]]
    omit = [s["omission"] for s in data["kline"]]
    import json
    fig = {"data": [{"type": "scatter", "mode": "lines+markers", "x": dates, "y": omit,
                     "name": f"号码{number}遗漏值", "line": {"color": "#ffd700", "width": 2},
                     "marker": {"color": "#ef5350", "size": 3},
                     "hovertemplate": "%{x}<br>遗漏: %{y}期<extra></extra>"}],
           "layout": {"title": f"号码{number} 遗漏值走势", "xaxis": {"rangeslider": {"visible": True}},
                      "yaxis": {"title": "遗漏值"}, "height": 400, "template": "plotly_dark",
                      "hovermode": "x unified"}}
    html = f'<!DOCTYPE html><html><head><meta charset="utf-8"><script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script></head><body><div id="c"></div><script>var d={json.dumps(fig)};Plotly.newPlot("c",d.data,d.layout,{{responsive:true}})</script></body></html>'
    return html


def render_zone_heatmap(window=50):
    """生成区间热度图HTML"""
    from core.predictor import predict_hot_zones
    from core.database import get_db
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
    labels, values = list(zones.keys()), list(zones.values())
    import json
    fig = {"data": [{"type": "bar", "x": labels, "y": values, "marker": {"color": ["#ffd700","#ef5350","#4caf50","#42a5f5"]},
                     "hovertemplate": "%{x}: %{y}次<extra></extra>"}],
           "layout": {"title": f"号码区间热度 (最近{window}期)", "yaxis": {"title": "出现次数"}, "height": 350,
                      "template": "plotly_dark", "hovermode": "x"}}
    html = f'<!DOCTYPE html><html><head><meta charset="utf-8"><script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script></head><body><div id="c"></div><script>var d={json.dumps(fig)};Plotly.newPlot("c",d.data,d.layout,{{responsive:true}})</script></body></html>'
    return html

def save_kline_chart(number, window=200, indicators=None, output_dir=None):
    """保存K线图到HTML文件"""
    if output_dir is None:
        output_dir = os.path.join(BASE, "output")
    os.makedirs(output_dir, exist_ok=True)

    html = render_kline_html(number, window, indicators)
    path = os.path.join(output_dir, f"kline_{number}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ K线图已保存: {path}")
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="图表生成")
    parser.add_argument("--number", type=int, default=28, help="号码")
    parser.add_argument("--window", type=int, default=200)
    parser.add_argument("--indicators", nargs="+",
                       default=["ma5", "ma10", "boll", "kdj", "macd", "rsi", "adx"],
                       help="技术指标")
    parser.add_argument("--output", help="输出目录")
    args = parser.parse_args()

    path = save_kline_chart(args.number, args.window, args.indicators, args.output)
    print(f"打开: {path}")
