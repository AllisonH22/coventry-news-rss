from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from email.utils import format_datetime
from datetime import datetime, timezone
import re
import xml.etree.ElementTree as ET

NEWS_URL = "https://www.coventrypublicschools.org/news"
BASE_URL = "https://www.coventrypublicschools.org"
FEED_URL = "https://allisonh22.github.io/coventry-news-rss/feed.xml"

print("Opening Coventry Public Schools news page...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    page = browser.new_page(
        viewport={"width": 1440, "height": 1200}
    )

    page.goto(
        NEWS_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(8000)

    for _ in range(5):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(1500)

    html = page.content()

    browser.close()

print(f"Rendered page size: {len(html)} characters")

soup = BeautifulSoup(html, "html.parser")

articles = []

for link in soup.find_all("a", href=True):

    href = link.get("href", "")

    match = re.search(r"/article/(\d+)", href)

    if not match:
        continue

    article_id = match.group(1)

    title = link.get_text(" ", strip=True)

    if not title:
        continue

    article_url = urljoin(
        BASE_URL,
        f"/article/{article_id}"
    )

    if any(a["url"] == article_url for a in articles):
        continue

    parent = link
    date_text = ""

    for _ in range(8):

        parent = parent.parent

        if not parent:
            break

        surrounding_text = parent.get_text(
            " ",
            strip=True
        )

        date_match = re.search(
            r"(January|February|March|April|May|June|July|August|"
            r"September|October|November|December)"
            r"\s+\d{1,2},\s+\d{4}",
            surrounding_text,
            re.IGNORECASE
        )

        if date_match:
            date_text = date_match.group(0)
            break

    try:
        published = datetime.strptime(
            date_text,
            "%B %d, %Y"
        ).replace(tzinfo=timezone.utc)

    except ValueError:
        published = datetime.now(timezone.utc)

    articles.append({
        "title": title,
        "url": article_url,
        "published": published
    })

unique_articles = {
    article["url"]: article
    for article in articles
}

articles = list(unique_articles.values())

articles.sort(
    key=lambda article: article["published"],
    reverse=True
)

articles = articles[:50]

print(f"Found {len(articles)} Coventry news articles.")

if not articles:
    print("ERROR: No articles found.")
    raise SystemExit(1)


# ---------------------------------------------------------
# Build RSS 2.0 feed
# ---------------------------------------------------------

ET.register_namespace(
    "atom",
    "http://www.w3.org/2005/Atom"
)

rss = ET.Element(
    "rss",
    {
        "version": "2.0",
        "xmlns:atom": "http://www.w3.org/2005/Atom"
    }
)

channel = ET.SubElement(rss, "channel")

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
).text = "Latest news from Coventry Public Schools"

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

# RSS self-reference
ET.SubElement(
    channel,
    "{http://www.w3.org/2005/Atom}link",
    {
        "href": FEED_URL,
        "rel": "self",
        "type": "application/rss+xml"
    }
)

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


tree = ET.ElementTree(rss)

tree.write(
    "feed.xml",
    encoding="utf-8",
    xml_declaration=True
)

print("Successfully generated feed.xml.")
