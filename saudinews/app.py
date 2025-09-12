# app.py
from flask import Flask, jsonify, request
from scraper import get_all_articles
import threading
import time
import datetime as dt

app = Flask(__name__)

CACHE_TTL = 1800  # 30 minutes
_cached = []
_last_fetch = 0
_lock = threading.Lock()


def refresh_cache():
    global _cached, _last_fetch
    try:
        data = get_all_articles()
        with _lock:
            _cached = data
            _last_fetch = time.time()
        print(f"🧠 Cache refreshed: {_last_fetch}, items={len(data)}")
        return True, len(data)
    except Exception as e:
        print("❌ refresh_cache error:", e)
        return False, 0


def get_cache():
    with _lock:
        return list(_cached), _last_fetch


@app.route("/saudi-news", methods=["GET"])
def saudi_news():
    # Optional: ?since=YYYY-MM-DD or full datetime
    since_q = request.args.get("since")

    cached, last = get_cache()
    now = time.time()
    if not cached or (now - last) > CACHE_TTL:
        print("🔄 Cache stale -> refreshing…")
        refresh_cache()
        cached, _ = get_cache()

    if since_q:
        try:
            sd = dt.datetime.fromisoformat(since_q.strip())
        except Exception:
            try:
                sd = dt.datetime.strptime(since_q.strip(), "%Y-%m-%d")
            except Exception:
                sd = None
        if sd:
            cutoff_str = sd.strftime("%Y-%m-%d %H:%M:%S")
            cached = [a for a in cached if a.get("published_at", "") > cutoff_str]

    return jsonify(cached)


@app.route("/refresh", methods=["POST", "GET"])
def manual_refresh():
    ok, n = refresh_cache()
    return jsonify({"ok": ok, "items": n})


if __name__ == "__main__":
    # First warm-up
    refresh_cache()
    app.run(host="0.0.0.0", port=5000)
