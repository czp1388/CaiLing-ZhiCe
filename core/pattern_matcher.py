#!/usr/bin/env python3
"""历史相似pattern匹配：找出和当前遗漏走势最像的历史时期"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.kline import build_kline_data
from core.database import get_db

def find_similar_patterns(window=50, top=3):
    """找和当前最近window期遗漏走势最相似的top个历史区间"""
    conn = get_db()
    all_dates = [r["draw_date"] for r in conn.execute("SELECT draw_date FROM draws ORDER BY draw_date").fetchall()]
    conn.close()
    if len(all_dates) < window * 3:
        return {"error": "数据不足"}
    # 当前走势向量（用热号28代表）
    ref = build_kline_data(28, window)
    if "error" in ref:
        return {"error": "参考数据不足"}
    ref_omit = [s["omission"] for s in ref["kline"]]
    # 滑动窗口找相似
    from core.kline import get_omission_series
    scores = []
    for start in range(0, len(all_dates) - window * 2, 5):
        dates_window = all_dates[start:start + window]
        comp = get_omission_series(28, window)
        if not comp:
            continue
        comp_omit = [s["omission"] for s in comp]
        # 均方误差
        mse = sum((a - b) ** 2 for a, b in zip(ref_omit, comp_omit)) / window
        scores.append({"period": f"{dates_window[0]}~{dates_window[-1]}", "similarity": round(1 / (1 + mse), 3)})
    scores.sort(key=lambda x: -x["similarity"])
    return {"current_period": f"{all_dates[-window]}~{all_dates[-1]}", "matches": scores[:top]}

if __name__ == "__main__":
    print(json.dumps(find_similar_patterns(), ensure_ascii=False, indent=2))
