#!/usr/bin/env python3
"""号码共现网络分析：哪些号码经常一起出现"""
import json, sys, os
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_db

def analyze_cooccurrence(target=None, top=5):
    """分析号码共现关系。target=None则全局分析"""
    conn = get_db()
    rows = conn.execute("SELECT n1,n2,n3,n4,n5,n6,extra FROM draws").fetchall()
    conn.close()
    pairs = defaultdict(int)
    for r in rows:
        nums = [r["n1"],r["n2"],r["n3"],r["n4"],r["n5"],r["n6"],r["extra"]]
        for i in range(len(nums)):
            for j in range(i+1, len(nums)):
                a, b = sorted([nums[i], nums[j]])
                pairs[(a, b)] += 1
    if target:
        related = []
        for (a, b), cnt in pairs.items():
            if a == target:
                related.append((b, cnt))
            elif b == target:
                related.append((a, cnt))
        related.sort(key=lambda x: -x[1])
        return {"number": target, "top_partners": related[:top]}
    top_pairs = sorted(pairs.items(), key=lambda x: -x[1])[:20]
    return {"top_pairs": [(a, b, c) for (a, b), c in top_pairs]}

if __name__ == "__main__":
    t = int(sys.argv[1]) if len(sys.argv) > 1 else None
    print(json.dumps(analyze_cooccurrence(t), ensure_ascii=False, indent=2))
