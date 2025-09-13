# scraper.py
import datetime as dt
import json
import re
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse

import feedparser
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from dateutil import parser as dateparser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------- CONFIG ----------
DAYS_BACK = 2 
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
    # "http://www.espn.com/espn/rss/soccer/news",  # optional
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

# ---------- SESSION WITH RETRY ----------
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


# ---------- HELPERS ----------
def _now():
    return dt.datetime.now()


def _cutoff():
    return _now() - dt.timedelta(days=DAYS_BACK)


def normalize_url(url: str) -> str:
    """Lowercase, strip trailing slashes, remove utm params."""
    if not url:
        return url
    parsed = urlparse(url)
    clean = parsed._replace(query="", fragment="")
    norm = urlunparse(clean)
    return norm.rstrip("/")


def clean_title(title: str) -> str:
    if not title:
        return title or ""
    t = title.strip()
    # remove weird appended relative time like "17h 56m Ago" or "2h ago"
    t = re.sub(r'\s*\d+\s*h(?:ours?|h)?\s*\d*\s*m(?:in(?:utes?)?)?\s*(ago)?$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*\d+\s*(h|m|min|seconds?|minutes?)\s*ago$', '', t, flags=re.IGNORECASE)
    # remove site suffixes
    t = re.sub(r'(-|\u2014|\|)\s*(BBC Sport|Goal\.com|ESPN|Arab News|OneFootball).*$', '', t, flags=re.IGNORECASE)
    # other cleanup
    t = re.sub(r'([a-z])([A-Z])', r'\1 \2', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def parse_date_safe(s: Optional[str]) -> Optional[dt.datetime]:
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


def fmt(dt_obj: Optional[dt.datetime]) -> str:
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


def safe_get(url: str, timeout: int = TIMEOUT) -> Optional[requests.Response]:
    try:
        r = _session.get(url, timeout=timeout, headers=HEADERS)
        if r.status_code != 200:
            return None
        if looks_like_block_page(r.text):
            return None
        return r
    except Exception:
        return None


def extract_meta_image_from_html(html_text: str, base_url: str = "") -> Optional[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    meta_candidates = [
        ("meta", {"property": "og:image"}),
        ("meta", {"name": "twitter:image"}),
        ("meta", {"name": "twitter:image:src"}),
        ("meta", {"name": "image"}),
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


def _try_resolve_twitter_image(url: str, timeout: int = 4) -> Optional[str]:
    """
    Attempt to follow redirects and find an image URL (pbs.twimg.com). This helps convert pic.twitter.com -> pbs.twimg.com images.
    If resolving fails, return None.
    """
    try:
        # HEAD first to avoid downloading the image
        r = _session.head(url, allow_redirects=True, timeout=timeout, headers=HEADERS)
        final = r.url if r is not None else url
        if "pbs.twimg.com" in final or re.search(r'\.(jpg|jpeg|png|gif)(?:\?|$)', final, flags=re.IGNORECASE):
            return final
        # sometimes the HEAD doesn't return content-type, try GET but stream
        r2 = _session.get(url, allow_redirects=True, timeout=timeout, stream=True, headers=HEADERS)
        final2 = r2.url
        if "pbs.twimg.com" in final2 or re.search(r'\.(jpg|jpeg|png|gif)(?:\?|$)', final2, flags=re.IGNORECASE):
            return final2
    except Exception:
        return None
    return None


# ---------- CONTENT CLEANING ----------
def clean_article_content(html_text: str, base_url: str = "") -> str:
    """
    Clean article HTML:
    - Remove scripts/styles
    - Remove related/recommendation blocks
    - Convert twitter pic links to inline <img> when resolvable, otherwise insert twitter blockquote
    - Convert twitter/t.co links to blockquote
    - Remove empty tags
    Return HTML string.
    """
    soup = BeautifulSoup(html_text or "", "html.parser")

    # remove scripts/styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # remove likely related/recommendations by class or role
    related_selectors = [
        "aside", ".related", ".related-articles", ".more-like-this",
        ".recommended", ".o-media-pod__summary", ".widget-related",
        ".related-content", ".related-posts", ".sp-related", ".more-on",
        ".promo", ".inline-promo"
    ]
    for sel in related_selectors:
        for node in soup.select(sel):
            node.decompose()

    # remove empty header/footer
    for node in soup.select("header, footer, nav"):
        # if they are long / not content-like, remove them
        if not node.get_text(strip=True) or len(node.get_text(strip=True)) < 60:
            node.decompose()

    # process all anchor tags
    for a in list(soup.find_all("a", href=True)):
        href_raw = a["href"].strip()
        href = urljoin(base_url, href_raw) if base_url else href_raw

        # handle pic.twitter.com -> try to resolve to image and embed
        if "pic.twitter.com" in href or re.search(r'pic\.twitter\.com/\w+', href):
            img_url = _try_resolve_twitter_image(href)
            if img_url:
                img_tag = soup.new_tag("img", src=img_url)
                a.replace_with(img_tag)
            else:
                blockquote = soup.new_tag("blockquote", **{"class": "twitter-tweet"})
                link_tag = soup.new_tag("a", href=href)
                link_tag.string = href
                blockquote.append(link_tag)
                a.replace_with(blockquote)
            continue

        # twitter/t.co links -> embed as blockquote (tweet)
        if "twitter.com" in href or "t.co/" in href:
            blockquote = soup.new_tag("blockquote", **{"class": "twitter-tweet"})
            link_tag = soup.new_tag("a", href=href)
            link_tag.string = href
            blockquote.append(link_tag)
            a.replace_with(blockquote)
            continue

        # otherwise normalize anchor
        a["href"] = href
        a["target"] = "_blank"
        a["rel"] = "noopener noreferrer nofollow"

    # catch plain text occurrences like "pic.twitter.com/..." or "https://t.co/..."
    text_url_re = re.compile(r'(https?://\S*pic\.twitter\.com/\S+|https?://\S*t\.co/\S+|pic\.twitter\.com/\S+|t\.co/\S+)', flags=re.IGNORECASE)
    for string_node in list(soup.find_all(string=text_url_re)):
        parent: Tag = string_node.parent if isinstance(string_node.parent, Tag) else None
        if not parent:
            continue
        text = str(string_node)
        parts = text_url_re.split(text)
        new_children = []
        for part in parts:
            if not part:
                continue
            m = text_url_re.match(part)
            if m:
                url_candidate = part
                if not url_candidate.startswith("http"):
                    url_candidate = "https://" + url_candidate
                if "pic.twitter.com" in url_candidate:
                    img_url = _try_resolve_twitter_image(url_candidate)
                    if img_url:
                        new_children.append(soup.new_tag("img", src=img_url))
                    else:
                        bq = soup.new_tag("blockquote", **{"class": "twitter-tweet"})
                        a_tag = soup.new_tag("a", href=url_candidate)
                        a_tag.string = url_candidate
                        bq.append(a_tag)
                        new_children.append(bq)
                else:
                    bq = soup.new_tag("blockquote", **{"class": "twitter-tweet"})
                    a_tag = soup.new_tag("a", href=url_candidate)
                    a_tag.string = url_candidate
                    bq.append(a_tag)
                    new_children.append(bq)
            else:
                new_children.append(NavigableString(part))
        # replace the string_node with new elements
        for new_el in reversed(new_children):
            parent.insert_after(new_el)
        string_node.extract()

    # remove nodes that are now empty
    for tag in list(soup.find_all()):
        # keep images if present in tag
        if tag.name in ("img", "iframe", "video"):
            continue
        # remove tags with no text and no media
        if not tag.get_text(strip=True) and not tag.find("img") and not tag.find("iframe"):
            try:
                tag.decompose()
            except Exception:
                pass

    # final HTML
    cleaned = str(soup).strip()
    # small normalization: remove duplicate whitespace
    cleaned = re.sub(r'\n\s*\n+', '\n\n', cleaned)
    return cleaned or ""


# ---------- CATEGORY EXTRACTION ----------
def _extract_category_from_jsonld(soup: BeautifulSoup) -> Optional[str]:
    # find application/ld+json and parse for articleSection / keywords
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            text = script.string
            if not text:
                continue
            data = json.loads(text)
            # data may be list or dict
            candidates = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        candidates.append(item)
            elif isinstance(data, dict):
                candidates.append(data)
            for item in candidates:
                # check for articleSection
                if "articleSection" in item and item["articleSection"]:
                    if isinstance(item["articleSection"], list):
                        return str(item["articleSection"][0]).strip()
                    return str(item["articleSection"]).strip()
                # check for keywords
                if "keywords" in item and item["keywords"]:
                    if isinstance(item["keywords"], list):
                        return str(item["keywords"][0]).strip()
                    return str(item["keywords"]).split(",")[0].strip()
        except Exception:
            continue
    return None


def detect_category(title: str = "", content: str = "", entry=None, article_soup: Optional[BeautifulSoup] = None) -> str:
    """
    Robust category detection:
    1) RSS tags
    2) JSON-LD articleSection / keywords
    3) common meta tags (article:section, news_keywords, keywords)
    4) common CSS selectors (.category, .post-category, .tags, .kicker, .tag)
    5) heuristics/keyword mapping
    6) fallback "General"
    """
    title = (title or "").strip()
    content = (content or "").strip()
    text = (title + " " + BeautifulSoup(content, "html.parser").get_text(" ", strip=True)).lower()

    # 1) feedparser tags/categories
    if entry:
        try:
            # feedparser entry.tags -> list of dicts with 'term'
            tags = getattr(entry, "tags", None)
            if tags and isinstance(tags, (list, tuple)) and len(tags) > 0:
                term = getattr(tags[0], "term", None) or (tags[0].get("term") if isinstance(tags[0], dict) else None)
                if term:
                    return str(term).strip().title()
            # entry.get('category') if present
            cat = getattr(entry, "category", None) or entry.get("category") if isinstance(entry, dict) else None
            if cat:
                return str(cat).strip().title()
        except Exception:
            pass

    # 2) article_soup -> JSON-LD
    if article_soup:
        try:
            jld = _extract_category_from_jsonld(article_soup)
            if jld:
                return jld.title() if isinstance(jld, str) else str(jld)
        except Exception:
            pass

        # 3) meta tags
        meta_keys = [
            ("meta", {"property": "article:section"}),
            ("meta", {"name": "article:section"}),
            ("meta", {"name": "news_keywords"}),
            ("meta", {"name": "keywords"}),
            ("meta", {"property": "og:section"}),
        ]
        for tag_name, attrs in meta_keys:
            tag = article_soup.find(tag_name, attrs=attrs)
            if tag:
                val = tag.get("content") or tag.get("value") or tag.get_text()
                if val:
                    return str(val).strip().title()

        # 4) try CSS selectors
        css_selectors = [
            ".category", ".categories", ".post-category", ".entry-category", ".article-category",
            ".tag", ".tags", ".kicker", ".breadcrumb li a", ".breadcrumb a", ".post_meta .cat",
            ".article-meta .cat", ".meta .category"
        ]
        for sel in css_selectors:
            el = article_soup.select_one(sel)
            if el:
                txt = el.get_text(" ", strip=True)
                if txt:
                    return txt.strip().title()

    # 5) heuristics / keyword mapping
    heuristics = [
        (["transfer", "signing", "loan", "deal", "contract"], "Transfer News"),
        (["injury", "fitness", "medical"], "Injury Update"),
        (["match report", "full-time", "kick-off", "lineup", "report"], "Match Report"),
        (["opinion", "column", "analysis"], "Opinion"),
        (["interview"], "Interview"),
        (["preview", "round-up", "round up"], "Preview"),
    ]
    for terms, label in heuristics:
        if any(t in text for t in terms):
            return label

    # 6) fallback
    return "General"


# ---------- FETCHERS ----------
def fetch_rss_articles() -> list:
    out = []
    cutoff = _cutoff()
    seen = set()

    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"❌ Failed to parse {feed_url}: {e}")
            continue

        for entry in getattr(feed, "entries", []):
            title_raw = getattr(entry, "title", "") or ""
            # prefer 'content' field if present
            desc = ""
            if getattr(entry, "content", None):
                try:
                    # entry.content is often a list of dicts
                    content_list = entry.content
                    if isinstance(content_list, (list, tuple)) and len(content_list) > 0:
                        desc = content_list[0].value or content_list[0].get("value", "") or ""
                except Exception:
                    desc = ""
            if not desc:
                desc = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""

            link = (getattr(entry, "link", "") or getattr(entry, "guid", "") or "").replace("&amp;", "&")
            if not link or not title_raw:
                continue

            if not is_relevant(title_raw + " " + desc):
                continue

            published_raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
            d = parse_date_safe(published_raw) or _now()
            if d < cutoff:
                continue

            image_url = None
            for field in ("media_content", "media_thumbnail", "enclosures"):
                val = getattr(entry, field, None)
                if val and isinstance(val, (list, tuple)) and len(val) > 0:
                    d0 = val[0]
                    if isinstance(d0, dict) and d0.get("url"):
                        image_url = d0["url"]
                        break

            key = normalize_url(link)
            if key in seen:
                continue
            seen.add(key)

            raw_html = f"<div>{desc}</div>"
            content = clean_article_content(raw_html, base_url=link)

            category = detect_category(title_raw, content, entry=entry)

            out.append({
                "title": clean_title(title_raw),
                "link": normalize_url(link),
                "published_at": fmt(d),
                "content": content,
                "image": image_url,
                "category": category or "General",
            })

    print(f"📰 RSS: {len(out)} items (last {DAYS_BACK} days)")
    return out


def scrape_spl_official(max_articles: int = 50) -> list:
    base = "https://www.spl.com.sa"
    index_url = f"{base}/en/news"
    out = []
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

        # try several ways to find publish date
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

        # attempt to identify main article container heuristically
        container_selectors = [
            "article", ".article-details", ".newsDetails", ".content", ".article-body", ".post-content",
            ".story-body", ".article__body", ".entry-content", "#article"
        ]
        main_container = None
        for sel in container_selectors:
            main_container = s.select_one(sel)
            if main_container and main_container.get_text(strip=True):
                break
        if not main_container:
            # fallback: use body paragraphs but exclude known non-content
            paras = s.select("p")
        else:
            paras = main_container.select("p")

        # filter out related/advert paragraphs by class or short length or repeated patterns
        excluded_class_patterns = re.compile(r'(related|promo|more-like-this|o-media-pod__summary|cta|subscribe|read more)', flags=re.I)
        filtered_paras = []
        for p in paras:
            text = p.get_text(" ", strip=True)
            if not text:
                continue
            # skip summaries or widgets commonly appended
            cls = " ".join(p.get("class") or [])
            if excluded_class_patterns.search(cls) or excluded_class_patterns.search(text):
                continue
            # skip "Read more" or tiny fragments that look like extra nav
            if len(text) < 20 and not p.find("img"):
                continue
            filtered_paras.append(str(p))

        raw_html = "\n".join(filtered_paras)
        content = clean_article_content(raw_html, base_url=href) or ""

        image_url = extract_meta_image_from_html(rr.text, base_url=href)
        if not image_url:
            img = s.find("img")
            if img and img.get("src"):
                image_url = urljoin(href, img["src"])

        title = clean_title(title_raw or (s.title.get_text(strip=True) if s.title else ""))

        if not title or looks_like_block_page(content or ""):
            continue

        category = detect_category(title, content, article_soup=s)

        out.append({
            "title": title,
            "link": normalize_url(href),
            "published_at": fmt(pub_dt),
            "content": content or "<p>No article content available.</p>",
            "image": image_url,
            "category": category or "General",
        })

    print(f"🏟️ SPL: {len(out)} items (last {DAYS_BACK} days)")
    return out


def get_all_articles() -> list:
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
