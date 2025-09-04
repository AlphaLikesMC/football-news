from flask import Flask, request, jsonify
from newspaper import Article

app = Flask(__name__)

@app.route("/extract", methods=["GET"])
def extract():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        article = Article(url)
        article.download()
        article.parse()

        return jsonify({
            "title": article.title,
            "authors": article.authors,
            "published_at": str(article.publish_date) if article.publish_date else None,
            "text": article.text,
            "top_image": article.top_image,
            "url": url
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
