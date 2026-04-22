import json
import os
import datetime

CACHE_FILE = "daily_analysis.json"

def save_analysis(analysis: str):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"date": today, "analysis": analysis}, f, ensure_ascii=False)

def get_cached_analysis() -> str | None:
    if not os.path.exists(CACHE_FILE):
        return None
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return data["analysis"] if data["date"] == today else None