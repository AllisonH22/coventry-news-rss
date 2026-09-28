import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from email.utils import format_datetime
from datetime import datetime, timezone
import re
import xml.etree.ElementTree as ET

NEWS_URL = "https://www.coventrypublicschools.org/news"
BASE_URL = "https://www.coventrypublicschools.org"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(
    NEWS_URL,
    headers=headers,
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

articles = []

# Find every link whose URL contains /article/
for link in soup.find_all("a", href=True):

    href = link.get("href", "")

    match = re.search(r"/article/(\d+)", href)

    if not match:
        continue

    article_id = match.group(1)

    title = link.get_text(" ", strip=True)

    if not title:
        continue

    article_url = urljoin(BASE_URL, f"/article/{article_id}")

    # Don't add the same article twice
    if any(a["url"] == article_url for a in articles):
        continue

    # Look around the link for a date
    parent = link

    date_text = ""

    for _ in range(8):

        parent = parent.parent

        if not parent:
            break

        text = parent.get_text(" ", strip=True)

        date_match = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)"
            r"\s+\d{1,2},\s+\d{4}",
            text,
            re.IGNORECASE
        )

        if date_match:
            date_text = date_match.group(0)
            break

    # Convert date
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


# Remove duplicates
unique_articles = {}

for article in articles:
    unique_articles[article["url"]] = article

articles = list(unique_articles.values())

# Newest first
articles.sort(
    key=lambda x: x["published"],
    reverse=True
)

# Keep latest 50
articles = articles[:50]


# Create RSS
rss = ET.Element(
    "rss",
    {"version": "2.0"}
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
).text = "Latest news from Coventry Public Schools"

ET.SubElement(
    channel,
    "language"
).text = "en-us"


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
        {"isPermaLink": "true"}
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

print(
    f"Found {len(articles)} Coventry news articles."
)
