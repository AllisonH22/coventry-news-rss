from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from email.utils import format_datetime
from datetime import datetime, timezone
import re
import xml.etree.ElementTree as ET
import time

NEWS_URL = "https://www.coventrypublicschools.org/news"
BASE_URL = "https://www.coventrypublicschools.org"

print("Opening Coventry Public Schools news page...")

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True
    )

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

    print("Page loaded.")

    # Give Apptegy's JavaScript time to render the news.
    page.wait_for_timeout(8000)

    # Scroll down so lazy-loaded news items have a chance to appear.
    for _ in range(5):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(1500)

    # Capture the fully rendered HTML.
    html = page.content()

    browser.close()


print(f"Rendered page size: {len(html)} characters")

soup = BeautifulSoup(html, "html.parser")

articles = []


# Find article links in the rendered page.
for link in soup.find_all("a", href=True):

    href = link.get("href", "")

    match = re.search(
        r"/article/(\d+)",
        href
    )

    if not match:
        continue

    article_id = match.group(1)

    title = link.get_text(
        " ",
        strip=True
    )

    if not title:
        continue

    article_url = urljoin(
        BASE_URL,
        f"/article/{article_id}"
    )

    # Avoid duplicates.
    if any(
        article["url"] == article_url
        for article in articles
    ):
        continue

    # Try to find a publication date near the article.
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

    # Parse date if possible.
    try:

        published = datetime.strptime(
            date_text,
            "%B %d, %Y"
        ).replace(
            tzinfo=timezone.utc
        )

    except ValueError:

        published = datetime.now(
            timezone.utc
        )

    articles.append({
        "title": title,
        "url": article_url,
        "published": published
    })


# Remove duplicates.
unique_articles = {}

for article in articles:
    unique_articles[
        article["url"]
    ] = article

articles = list(
    unique_articles.values()
)


# Newest first.
articles.sort(
    key=lambda article: article["published"],
    reverse=True
)


# Keep the 50 newest.
articles = articles[:50]


print(
    f"Found {len(articles)} Coventry news articles."
)


# If nothing was found, fail the workflow instead of
# replacing a working feed with an empty feed.
if not articles:

    print("")
    print("ERROR: No Coventry articles were found.")
    print("The rendered page did not contain /article/######## links.")
    print("The existing feed.xml will NOT be replaced.")

    raise SystemExit(1)


# Create RSS document.
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


# Add articles.
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


# Write feed.xml.
tree = ET.ElementTree(rss)

tree.write(
    "feed.xml",
    encoding="utf-8",
    xml_declaration=True
)

print(
    "Successfully generated feed.xml."
)
