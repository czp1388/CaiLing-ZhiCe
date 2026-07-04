"""周报生成"""
import json, os, sys
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.history import get_history
from core.recommender import get_recommendation
from core.predictor import get_cold_alerts, predict_next_range, predict_hot_zones

def generate_weekly():
    history = get_history(30)
    total = len(history)
    cold_alerts = get_cold_alerts()
    zones = predict_hot_zones()
    next_sum = predict_next_range()
    rec = get_recommendation()
    return {
        "period": f"{(datetime.now() - timedelta(days=7)).strftime('%m/%d')} - {datetime.now().strftime('%m/%d')}",
        "total_recommendations": total,
        "weekly_pick": rec["numbers"],
        "confidence": rec["confidence"],
        "cold_alerts": cold_alerts[:5],
        "hot_zone": zones["most_active"],
        "next_sum_range": next_sum["predicted_range"],
    }

if __name__ == "__main__":
    print(json.dumps(generate_weekly(), ensure_ascii=False, indent=2))
