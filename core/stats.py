"""推荐准确率统计看板"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.history import get_history
from core.database import get_db

def accuracy_report():
    history = get_history(100)
    conn = get_db()
    total_recs = len(history)
    total_matches = 0
    per_draw = []
    for h in history:
        nums = json.loads(h["numbers"]) if isinstance(h["numbers"], str) else h["numbers"]
        date_str = h["created_at"][:10]
        # 模拟实际开奖匹配（用最近一期）
        actual = conn.execute("SELECT n1,n2,n3,n4,n5,n6,extra FROM draws ORDER BY draw_date DESC LIMIT 1").fetchone()
        if actual:
            an = {actual[c] for c in ["n1","n2","n3","n4","n5","n6","extra"]}
            match = len(set(nums) & an)
            if match >= 1:
                total_matches += 1
            per_draw.append({"date": date_str, "numbers": nums, "match": match, "confidence": h.get("confidence","")})
    conn.close()
    return {
        "total_recommendations": total_recs,
        "draws_with_hits": total_matches,
        "hit_rate": f"{total_matches/max(total_recs,1)*100:.1f}%",
        "random_baseline": "14.3% (7/49)",
        "per_draw": per_draw[-10:]
    }

if __name__ == "__main__":
    print(json.dumps(accuracy_report(), ensure_ascii=False, indent=2))
