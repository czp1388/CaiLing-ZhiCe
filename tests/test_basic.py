#!/usr/bin/env python3
"""彩灵·智策 基础测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def t(name, fn):
    try:
        fn()
        print(f"  ✅ {name}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")

def test_imports():
    from core.database import get_db
    from core.analyzer import hot_cold_numbers, missing_stats
    from core.kline import build_kline_data
    from core.ev import calculate_ev

def test_hot_cold():
    from core.analyzer import hot_cold_numbers
    hc = hot_cold_numbers(50, 5)
    assert len(hc["hot"]) == 5
    for n, c in hc["hot"]:
        assert 1 <= n <= 49

def test_missing():
    from core.analyzer import missing_stats
    m = missing_stats(50)
    assert len(m) == 49
    assert m[0][1] >= 0

def test_ev():
    from core.ev import calculate_ev
    r = calculate_ev([1,2,3,4,5,6])
    assert r["ev_total"] > 0

def test_kline():
    from core.kline import build_kline_data
    k = build_kline_data(28, 50)
    assert k["stats"]["total_draws"] > 0

def test_recommend():
    from core.recommender import get_recommendation
    r = get_recommendation()
    assert len(r["numbers"]) == 6

if __name__ == "__main__":
    print("🧪 彩灵·智策 单元测试")
    for fn in [test_imports, test_hot_cold, test_missing, test_ev, test_kline, test_recommend]:
        t(fn.__name__, fn)
    print("\n✅ 全部通过")
