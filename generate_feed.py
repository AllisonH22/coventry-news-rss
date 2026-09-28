from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from email.utils import format_datetime
from datetime import datetime, timezone
import re
import xml.etree.ElementTree as ET


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

NEWS_URL = "https://www.coventrypublicschools.org/news"
BASE_URL = "https://www.coventrypublicschools.org"
FEED_URL = "https://allisonh22.github.io/coventry-news-rss/feed.xml"

MAX_ARTICLES = 50

ATOM_NS = "http://www.w3.org/2005/Atom"


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def parse_date(text):
    """
    Look for a date such as:
    January 15, 2026
    """
    if not text:
        return None

    match = re.search(
        r"\b("
        r"January|February|March|April|May|June|July|August|"
        r"September|October|November|December"
        r")\s+\d{1,2},\s+\d{4}\b",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    date_text = match.group(0)

    try:
        return datetime.strptime(
            date_text,
            "%B %d, %Y"
        ).replace(tzinfo=timezone.utc)

    except ValueError:
        return None


def clean_text(text):
    """
    Normalize whitespace.
    """
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------
# Scrape Coventry Public Schools
# ---------------------------------------------------------

print("Opening Coventry Public Schools news page...")

with sync_playwright() as p:

    browser = p.chromium.launch(headless=True)

    page = browser.new_page(
        viewport={
            "width": 1440,
            "height": 1200
        }
    )

    page.goto(
        NEWS_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    # Allow JavaScript content to finish rendering.
    page.wait_for_timeout(8000)

    # Scroll to encourage lazy-loaded articles to appear.
    for _ in range(5):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(1500)

    html = page.content()

    browser.close()


print(f"Rendered page size: {len(html)} characters")

if len(html) < 1000:
    print("ERROR: Rendered page is unexpectedly small.")
    raise SystemExit(1)


# ---------------------------------------------------------
# Parse HTML
# ---------------------------------------------------------

soup = BeautifulSoup(
    html,
    "html.parser"
)

articles = []
seen_urls = set()


# ---------------------------------------------------------
# Find article links
# ---------------------------------------------------------

for link in soup.find_all("a", href=True):

    href = link.get("href", "")

    # Coventry article URLs look like:
    # /article/123456
    match = re.search(
        r"/article/(\d+)",
        href
    )

    if not match:
        continue

    article_id = match.group(1)

    title = clean_text(
        link.get_text(" ", strip=True)
    )

    if not title:
        continue

    article_url = urljoin(
        BASE_URL,
        f"/article/{article_id}"
    )

    if article_url in seen_urls:
        continue

    seen_urls.add(article_url)

    # -----------------------------------------------------
    # Look for the publication date near the article link.
    # -----------------------------------------------------

    date_text = ""
    published = None

    parent = link

    for _ in range(10):

        parent = parent.parent

        if not parent:
            break

        surrounding_text = clean_text(
            parent.get_text(
                " ",
                strip=True
            )
        )

        parsed_date = parse_date(
            surrounding_text
        )

        if parsed_date:

            published = parsed_date
            date_text = parsed_date.strftime(
                "%B %d, %Y"
            )

            break

    # -----------------------------------------------------
    # If no date was found, skip the article rather than
    # pretending that it was published today.
    # -----------------------------------------------------

    if published is None:

        print(
            f"WARNING: No publication date found for: "
            f"{title}"
        )

        continue

    articles.append(
        {
            "title": title,
            "url": article_url,
            "published": published
        }
    )


# ---------------------------------------------------------
# Sort newest first
# ---------------------------------------------------------

articles.sort(
    key=lambda article: article["published"],
    reverse=True
)

articles = articles[:MAX_ARTICLES]


print(
    f"Found {len(articles)} dated Coventry news articles."
)


# ---------------------------------------------------------
# Safety check
# ---------------------------------------------------------

if not articles:

    print(
        "ERROR: No dated articles were found."
    )

    raise SystemExit(1)


# ---------------------------------------------------------
# Build RSS 2.0 feed
# ---------------------------------------------------------

ET.register_namespace(
    "atom",
    ATOM_NS
)

rss = ET.Element(
    "rss",
    {
        "version": "2.0"
    }
)

channel = ET.SubElement(
    rss,
    "channel"
)


# ---------------------------------------------------------
# Channel information
# ---------------------------------------------------------

ET.SubElement(
    channel,
    "title"
).text = "Coventry Public Schools News"


ET.SubElement(
    channel,
    "link"
).text = NEWS_URL


ET.SubElement(
    channel,
    "description"
).text = (
    "Latest news from Coventry Public Schools"
)


ET.SubElement(
    channel,
    "language"
).text = "en-us"


ET.SubElement(
    channel,
    "copyright"
).text = "Coventry Public Schools"


ET.SubElement(
    channel,
    "ttl"
).text = "15"


# ---------------------------------------------------------
# Feed self-reference
# ---------------------------------------------------------

ET.SubElement(
    channel,
    f"{{{ATOM_NS}}}link",
    {
        "href": FEED_URL,
        "rel": "self",
        "type": "application/rss+xml"
    }
)


# ---------------------------------------------------------
# Last build date
# ---------------------------------------------------------

ET.SubElement(
    channel,
    "lastBuildDate"
).text = format_datetime(
    datetime.now(timezone.utc)
)


# ---------------------------------------------------------
# Add articles
# ---------------------------------------------------------

for article in articles:

    item = ET.SubElement(
        channel,
        "item"
    )

    ET.SubElement(
        item,
        "title"
    ).text = article["title"]

    ET.SubElement(
        item,
        "link"
    ).text = article["url"]

    ET.SubElement(
        item,
        "guid",
        {
            "isPermaLink": "true"
        }
    ).text = article["url"]

    ET.SubElement(
        item,
        "pubDate"
    ).text = format_datetime(
        article["published"]
    )

    ET.SubElement(
        item,
        "description"
    ).text = (
        "Coventry Public Schools: "
        + article["title"]
    )


# ---------------------------------------------------------
# Write feed.xml
# ---------------------------------------------------------

tree = ET.ElementTree(rss)

ET.indent(
    tree,
    space="  "
)

tree.write(
    "feed.xml",
    encoding="utf-8",
    xml_declaration=True
)


print(
    f"Successfully generated feed.xml "
    f"with {len(articles)} articles."
)
