import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from email.utils import format_datetime
from datetime import datetime, timezone
import html
import re
import xml.etree.ElementTree as ET

NEWS_URL = "https://www.coventrypublicschools.org/news"
BASE_URL = "https://www.coventrypublicschools.org"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CoventryPublicSchoolsRSS/1.0)"
}

response = requests.get(NEWS_URL, headers=HEADERS, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

articles = []

# Find every link pointing to an Apptegy article.
for link in soup.find_all("a", href=True):
    href = link["href"]

    if not re.search(r"^/article/\d+", href):
        continue

    title = link.get_text(" ", strip=True)

    if not title:
        continue

    article_url = urljoin(BASE_URL, href)

    # Avoid duplicates.
    if any(a["url"] == article_url for a in articles):
        continue

    # Try to find a nearby date.
    container = link
    for _ in range(5):
        if container.parent:
            container = container.parent

        text = container.get_text(" ", strip=True)

        date_match = re.search(
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"[a-z]*\s+\d{1,2},\s+\d{4}\b",
            text,
            re.IGNORECASE
        )

        if date_match:
            date_text = date_match.group(0)
            break
    else:
        date_text = ""

    # Try to parse the date.
    try:
        published = datetime.strptime(
            date_text, "%b %d, %Y"
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        published = datetime.now(timezone.utc)

    articles.append({
        "title": title,
        "url": article_url,
        "published": published
    })

# Remove duplicate titles/URLs and sort newest first.
unique = {}
for article in articles:
    unique[article["url"]] = article

articles = list(unique.values())
articles.sort(key=lambda x: x["published"], reverse=True)

# Limit feed to the most recent 50 articles.
articles = articles[:50]

# Build RSS XML.
rss = ET.Element("rss", {
    "version": "2.0"
})

channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = "Coventry Public Schools News"
ET.SubElement(channel, "link").text = NEWS_URL
ET.SubElement(channel, "description").text = (
    "Latest news from Coventry Public Schools"
)
ET.SubElement(channel, "language").text = "en-us"

for article in articles:
    item = ET.SubElement(channel, "item")

    ET.SubElement(item, "title").text = article["title"]
    ET.SubElement(item, "link").text = article["url"]
    ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = article["url"]

    ET.SubElement(item, "pubDate").text = format_datetime(
        article["published"]
    )

    ET.SubElement(item, "description").text = (
        "Coventry Public Schools news: " + article["title"]
    )

# Write RSS file.
tree = ET.ElementTree(rss)

tree.write(
    "feed.xml",
    encoding="utf-8",
    xml_declaration=True
)

print(f"Created RSS feed with {len(articles)} articles.")
