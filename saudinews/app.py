#app.py

from flask import Flask, jsonify
from scraper import get_all_articles
import time

app = Flask(__name__)

# Cache storage
cached_articles = []
last_fetch = 0
CACHE_TTL = 3600  # refresh every 1 hour

@app.route("/saudi-news", methods=["GET"])
def saudi_news():
    global cached_articles, last_fetch
    now = time.time()

    # Refresh cache if older than CACHE_TTL
    if not cached_articles or (now - last_fetch > CACHE_TTL):
        print("🔄 Fetching fresh Saudi Pro League news...")
        try:
            cached_articles = get_all_articles()
            last_fetch = now
            print(f"✅ Cached {len(cached_articles)} articles.")
        except Exception as e:
            print("❌ Error fetching articles:", e)

    return jsonify(cached_articles)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
