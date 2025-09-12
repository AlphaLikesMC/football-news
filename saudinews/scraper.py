# scraper.py
import datetime as dt
import re
from urllib.parse import urljoin, urlparse, urlunparse

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def normalize_url(url: str) -> str:
    """Lowercase, strip trailing slashes, remove utm params."""
    if not url:
        return url
    parsed = urlparse(url)
    clean = parsed._replace(query="", fragment="")
    norm = urlunparse(clean)
    return norm.rstrip("/").lower()


DAYS_BACK = 60   # last 2 months
TIMEOUT = 8
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/116 Safari/537.36"
    )
}

FEEDS = [
    "https://www.goal.com/en/feeds/news?fmt=rss",
    "http://feeds.bbci.co.uk/sport/football/rss.xml",
    "http://www.espn.com/espn/rss/soccer/news",
    "https://www.arabnews.com/rss.xml",
    "https://onefootball.com/en/rss",
]

KEYWORDS = [
    "Saudi Pro League", "Roshn Saudi League", "SPL",
    "Al Hilal", "Al-Hilal", "Al Nassr", "Al-Nassr",
    "Al Ittihad", "Al-Ittihad", "Al Ahli", "Al-Ahli",
    "Cristiano Ronaldo", "Neymar", "Benzema",
    "Mahrez", "Mané", "Mitrovic", "Kanté", "Fabinho", "Talisca"
]

# ---------- requests session with retry ----------
_session = requests.Session()
_retries = Retry(
    total=2,
    backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD"],
    respect_retry_after_header=True,
)
_adapter = HTTPAdapter(max_retries=_retries, pool_connections=50, pool_maxsize=50)
_session.mount("http://", _adapter)
_session.mount("https://", _adapter)


def _now():
    return dt.datetime.now()


def _cutoff():
    return _now() - dt.timedelta(days=DAYS_BACK)


def clean_title(title: str) -> str:
    if not title:
        return title
    title = re.sub(r'([a-z])([A-Z])', r'\1 \2', title)
    title = re.sub(r'([?!.])([A-Z])', r'\1 \2', title)
    title = re.sub(r'(Feature|News)\s*\d{1,2}\s+\w+\s+\d{4}', '', title, flags=re.IGNORECASE)
    title = re.sub(r'(BBC Sport|Goal\.com|ESPN|Arab News).*$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\b\d{1,2}\s+\w+\s+\d{4}$', '', title)
    return re.sub(r'\s+', ' ', title).strip()


def parse_date_safe(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        d = dateparser.parse(s)
        if not d:
            return None
        if d.tzinfo is not None:
            d = d.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return d
    except Exception:
        return None


def fmt(dt_obj: dt.datetime | None) -> str:
    if not dt_obj:
        return _now().strftime("%Y-%m-%d %H:%M:%S")
    return dt_obj.strftime("%Y-%m-%d %H:%M:%S")


def is_relevant(text: str) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in KEYWORDS)


def looks_like_block_page(html: str) -> bool:
    if not html:
        return False
    h = html.lower()
    suspicious = [
        "429 too many requests", "access denied", "request blocked",
        "bot detection", "verify you are human", "captcha", "cloudflare",
    ]
    return any(s in h for s in suspicious)


def safe_get(url: str, timeout: int = TIMEOUT) -> requests.Response | None:
    try:
        r = _session.get(url, timeout=timeout, headers=HEADERS)
        if r.status_code != 200:
            return None
        if looks_like_block_page(r.text):
            return None
        return r
    except Exception:
        return None


def extract_meta_image_from_html(html_text: str, base_url: str = "") -> str | None:
    soup = BeautifulSoup(html_text, "html.parser")
    meta_candidates = [
        ("meta", {"property": "og:image"}),
        ("meta", {"name": "twitter:image"}),
        ("meta", {"name": "twitter:image:src"}),
    ]
    for tag_name, attrs in meta_candidates:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get("content"):
            return urljoin(base_url, tag["content"])
    fig_img = soup.select_one("figure img")
    if fig_img and fig_img.get("src"):
        return urljoin(base_url, fig_img["src"])
    first_img = soup.find("img")
    if first_img and first_img.get("src"):
        return urljoin(base_url, first_img["src"])
    return None


# ---------- CATEGORY DETECTION ----------
def detect_category(title: str, content: str, entry=None, article_soup=None) -> str:
    text = (title or "") + " " + (content or "")
    text = text.lower()

    if entry and hasattr(entry, "tags"):
        tags = [t.get("term", "").lower() for t in entry.tags if t]
        if tags:
            return tags[0].title()

    if article_soup:
        cat_tag = article_soup.select_one(".category, .breadcrumb a, .tags a")
        if cat_tag:
            return cat_tag.get_text(strip=True)

    if any(w in text for w in ["transfer", "signing", "loan", "deal", "contract"]):
        return "Transfer News"
    if any(w in text for w in ["injury", "fitness", "medical"]):
        return "Injury Update"
    if any(w in text for w in ["match report", "full-time", "kick-off", "lineup"]):
        return "Match Report"

    return "General"  # ✅ always return a non-null category


# ---------- FETCHERS ----------
def fetch_rss_articles() -> list[dict]:
    out: list[dict] = []
    cutoff = _cutoff()
    seen = set()

    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"❌ Failed to parse {feed_url}: {e}")
            continue

        for entry in getattr(feed, "entries", []):
            title = getattr(entry, "title", "") or ""
            desc = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
            link = (getattr(entry, "link", "") or getattr(entry, "guid", "") or "").replace("&amp;", "&")
            if not link or not title:
                continue
            if not is_relevant(title + " " + desc):
                continue

            published_raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
            d = parse_date_safe(published_raw) or _now()
            if d < cutoff:
                continue

            image_url = None
            for field in ("media_content", "media_thumbnail", "enclosures"):
                val = getattr(entry, field, None)
                if val and isinstance(val, (list, tuple)):
                    d0 = val[0]
                    if isinstance(d0, dict) and d0.get("url"):
                        image_url = d0["url"]
                        break

            key = link.strip()
            if key in seen:
                continue
            seen.add(key)

            out.append({
                "title": clean_title(title),
                "link": normalize_url(link),
                "published_at": fmt(d),
                "content": BeautifulSoup(desc, "html.parser").get_text(" ", strip=True) or None,
                "image": image_url,
                "category": detect_category(title, desc, entry=entry),
            })

    print(f"📰 RSS: {len(out)} items (last {DAYS_BACK} days)")
    return out


def scrape_spl_official(max_articles: int = 50) -> list[dict]:
    base = "https://www.spl.com.sa"
    index_url = f"{base}/en/news"
    out: list[dict] = []
    cutoff = _cutoff()

    r = safe_get(index_url)
    if not r:
        print("⚠️ SPL index failed or blocked.")
        return out

    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    for a in soup.select('a[href*="/en/news/"]'):
        href = a.get("href") or ""
        href = urljoin(base, href)
        if "/en/news/" in href and href != index_url:
            links.append((a.get_text(strip=True), href))

    seen = set()
    unique_links = []
    for title, href in links:
        if href in seen:
            continue
        seen.add(href)
        unique_links.append((title, href))
        if len(unique_links) >= max_articles:
            break

    for title_raw, href in unique_links:
        rr = safe_get(href)
        if not rr:
            print(f"⚠️ SPL article blocked/failed: {href}")
            continue

        s = BeautifulSoup(rr.text, "html.parser")

        date_text = None
        mt = s.find("meta", {"property": "article:published_time"})
        if mt and mt.get("content"):
            date_text = mt["content"]
        if not date_text:
            t_tag = s.find("time")
            if t_tag:
                date_text = t_tag.get("datetime") or t_tag.get_text(strip=True)
        if not date_text:
            cand = s.select_one(".date, .post-date, .published, .article-date")
            if cand:
                date_text = cand.get_text(strip=True)

        pub_dt = parse_date_safe(date_text) or _now()
        if pub_dt < cutoff:
            continue

        paras = s.select("div.article-details p, div.newsDetails p, article p, .content p, .news-details p")
        content = "\n".join(p.get_text(strip=True) for p in paras if p.get_text(strip=True)) or None

        image_url = extract_meta_image_from_html(rr.text, base_url=href)
        if not image_url:
            img = s.find("img")
            if img and img.get("src"):
                image_url = urljoin(href, img["src"])

        title = clean_title(title_raw or (s.title.get_text(strip=True) if s.title else ""))

        if not title or looks_like_block_page(content or ""):
            continue

        out.append({
            "title": title,
            "link": normalize_url(href),
            "published_at": fmt(pub_dt),
            "content": content or "No article content available.",
            "image": image_url,
            "category": detect_category(title, content, article_soup=s),
        })

    print(f"🏟️ SPL: {len(out)} items (last {DAYS_BACK} days)")
    return out


def get_all_articles() -> list[dict]:
    items = []
    try:
        items.extend(scrape_spl_official(max_articles=120))
    except Exception as e:
        print("⚠️ SPL scrape error:", e)

    try:
        items.extend(fetch_rss_articles())
    except Exception as e:
        print("⚠️ RSS scrape error:", e)

    cutoff = _cutoff()
    filtered = []
    seen = set()
    for a in items:
        try:
            d = dt.datetime.strptime(a["published_at"], "%Y-%m-%d %H:%M:%S")
            if d >= cutoff:
                if a["link"] not in seen:
                    seen.add(a["link"])
                    filtered.append(a)
        except Exception:
            continue

    filtered.sort(key=lambda x: x["published_at"], reverse=True)
    print(f"✅ Final: {len(filtered)} items (merged, deduped, sorted)")
    return filtered
