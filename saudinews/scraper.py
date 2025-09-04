import datetime
import re
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup
from newspaper import Article
from dateutil import parser as dateparser


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                  " AppleWebKit/537.36 (KHTML, like Gecko)"
                  " Chrome/116.0 Safari/537.36"
}

KEYWORDS = [
    "Saudi Pro League", "Roshn Saudi League", "SPL",
    "Al Hilal", "Al-Hilal",
    "Al Nassr", "Al-Nassr",
    "Al Ittihad", "Al-Ittihad",
    "Al Ahli", "Al-Ahli",
    "Cristiano Ronaldo", "Neymar", "Benzema",
    "Mahrez", "Mané", "Mitrovic", "Kanté", "Fabinho", "Talisca"
]

FEEDS = [
    "https://www.goal.com/en/feeds/news?fmt=rss",
    "http://feeds.bbci.co.uk/sport/football/rss.xml",
    "http://www.espn.com/espn/rss/soccer/news",
    "https://www.arabnews.com/rss.xml",
    "https://onefootball.com/en/rss",
]


def clean_title(title: str) -> str:
    if not title:
        return title
    title = re.sub(r'([a-z])([A-Z])', r'\1 \2', title)
    title = re.sub(r'([?!.])([A-Z])', r'\1 \2', title)
    title = re.sub(r'(Feature|News)\s*\d{1,2}\s+\w+\s+\d{4}', '', title, flags=re.IGNORECASE)
    title = re.sub(r'(BBC Sport|Goal\.com|ESPN|Arab News).*$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\b\d{1,2}\s+\w+\s+\d{4}$', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def normalize_date(date_str):
    try:
        if not date_str:
            raise ValueError("empty date")
        dt = dateparser.parse(date_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_relevant(text: str) -> bool:
    return any(k.lower() in (text or "").lower() for k in KEYWORDS)


def extract_meta_image_from_html(html_text: str, base_url: str = "") -> str | None:
    soup = BeautifulSoup(html_text, "html.parser")

    # og:image
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return urljoin(base_url, og["content"])

    # twitter:image
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return urljoin(base_url, tw["content"])

    tw2 = soup.find("meta", attrs={"name": "twitter:image:src"})
    if tw2 and tw2.get("content"):
        return urljoin(base_url, tw2["content"])

    # figure img
    fig_img = soup.select_one("figure img")
    if fig_img and fig_img.get("src"):
        return urljoin(base_url, fig_img["src"])

    # first img
    first_img = soup.find("img")
    if first_img and first_img.get("src"):
        return urljoin(base_url, first_img["src"])

    return None


def extract_image_from_entry(entry, link: str) -> tuple[str | None, str]:
    """
    Try multiple strategies for image extraction.
    Returns (image_url, source_label)
    """
    # 1) Try newspaper3k
    try:
        art = Article(link)
        art.download()
        art.parse()
        if art.top_image:
            return art.top_image, "newspaper3k"
    except Exception:
        pass

    # 2) Try fetching the page directly
    try:
        r = requests.get(link, timeout=12, headers=HEADERS)
        if r.status_code == 200:
            meta_img = extract_meta_image_from_html(r.text, base_url=link)
            if meta_img:
                return meta_img, "meta"
            # fallback: first img
            soup = BeautifulSoup(r.text, "html.parser")
            first_img = soup.find("img")
            if first_img and first_img.get("src"):
                return urljoin(link, first_img["src"]), "html-img"
    except Exception:
        pass

    # 3) Try RSS media:content / media_thumbnail / enclosures
    for field in ["media_content", "media_thumbnail", "enclosures"]:
        if hasattr(entry, field):
            val = getattr(entry, field)
            if val and isinstance(val, (list, tuple)):
                d = val[0]
                if isinstance(d, dict) and d.get("url"):
                    return d["url"], field

    return None, "none"


def fetch_rss_articles():
    articles = []
    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"❌ Failed to parse {feed_url}: {e}")
            continue

        for entry in feed.entries:
            try:
                raw_title = getattr(entry, "title", "") or ""
                description = getattr(entry, "description", "") or ""
                link = getattr(entry, "link", "") or getattr(entry, "guid", "")
                link = (link or "").replace("&amp;", "&")

                published_raw = getattr(entry, "published", None) or getattr(entry, "updated", None)

                if not is_relevant(raw_title + " " + description):
                    continue

                # Content fallback
                content = None
                try:
                    art = Article(link)
                    art.download()
                    art.parse()
                    content = art.text.strip() if getattr(art, "text", None) else None
                except Exception:
                    pass
                if not content:
                    content = BeautifulSoup(description, "html.parser").get_text(" ", strip=True) or "No article content available."

                # Image extraction
                image_url, src = extract_image_from_entry(entry, link)
                print(f"[IMG:{src}] {raw_title[:50]} -> {image_url}")

                articles.append({
                    "title": clean_title(raw_title),
                    "link": link,
                    "published_at": normalize_date(published_raw),
                    "content": content,
                    "image": image_url
                })
            except Exception as e:
                print(f"⚠️ Skipped entry: {e}")
                continue
    return articles


def scrape_spl_official():
    url = "https://www.spl.com.sa/en/news"
    articles = []
    try:
        res = requests.get(url, timeout=20, headers=HEADERS)
        soup = BeautifulSoup(res.text, "html.parser")

        for a in soup.select('a[href*="/en/news/"]'):
            try:
                title = a.get_text(strip=True)
                href = urljoin("https://www.spl.com.sa", a.get("href", ""))

                article_res = requests.get(href, timeout=20, headers=HEADERS)
                article_soup = BeautifulSoup(article_res.text, "html.parser")

                paragraphs = article_soup.select("div.article-details p, div.newsDetails p, article p, .content p")
                content = "\n".join(
                    p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)
                ) or "No article content available."

                image_url = extract_meta_image_from_html(article_res.text, base_url=href)
                if not image_url:
                    img_tag = article_soup.find("img")
                    if img_tag and img_tag.get("src"):
                        image_url = urljoin(href, img_tag["src"])

                print(f"[SPL] {title[:50]} -> {image_url}")

                articles.append({
                    "title": clean_title(title),
                    "link": href,
                    "published_at": normalize_date(datetime.datetime.now().isoformat()),
                    "content": content,
                    "image": image_url
                })
            except Exception as ee:
                print("⚠️ SPL article error:", ee)
                continue
    except Exception as e:
        print("⚠️ SPL scrape failed:", e)
    return articles


def get_all_articles():
    return fetch_rss_articles() + scrape_spl_official()
