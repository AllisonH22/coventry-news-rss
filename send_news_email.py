import json
import os
import smtplib
import xml.etree.ElementTree as ET

from email.message import EmailMessage


FEED_FILE = "feed.xml"
LAST_SENT_FILE = "last_sent.txt"

# File downloaded from the private subscriber repository
SUBSCRIBER_FILE = os.environ["SUBSCRIBER_FILE"]


# ---------------------------------------------------------
# Email configuration
# ---------------------------------------------------------

SMTP_USERNAME = os.environ["SMTP_USERNAME"]
SMTP_P = os.environ["SMTP_P"]

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


# ---------------------------------------------------------
# Read RSS feed
# ---------------------------------------------------------

print("Reading feed.xml...")

tree = ET.parse(FEED_FILE)
root = tree.getroot()

channel = root.find("channel")

if channel is None:
    raise RuntimeError(
        "RSS feed does not contain a channel."
    )


item = channel.find("item")

if item is None:
    raise RuntimeError(
        "RSS feed does not contain any articles."
    )


title = item.findtext(
    "title",
    ""
).strip()

link = item.findtext(
    "link",
    ""
).strip()

pub_date = item.findtext(
    "pubDate",
    ""
).strip()


if not title or not link:
    raise RuntimeError(
        "Newest RSS item is missing a title or link."
    )


print(f"Newest article: {title}")
print(f"Article URL: {link}")


# ---------------------------------------------------------
# Read last-sent article
# ---------------------------------------------------------

last_sent = ""

if os.path.exists(LAST_SENT_FILE):

    with open(
        LAST_SENT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        last_sent = file.read().strip()


# ---------------------------------------------------------
# Check whether this article was already sent
# ---------------------------------------------------------

if last_sent == link:

    print(
        "Newest article has already been emailed."
    )

    print(
        "No email will be sent."
    )

    raise SystemExit(0)


# ---------------------------------------------------------
# First-run handling
# ---------------------------------------------------------

if not last_sent:

    print(
        "No previous article found."
    )

    print(
        "This appears to be the first run."
    )

    print(
        "The current article will be recorded "
        "without sending an email."
    )

    with open(
        LAST_SENT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(link)

    raise SystemExit(0)


# ---------------------------------------------------------
# A new article has been detected
# ---------------------------------------------------------

print(
    "NEW ARTICLE DETECTED!"
)

print(
    "Preparing email..."
)


# ---------------------------------------------------------
# Read private subscriber list
# ---------------------------------------------------------

print(
    f"Reading subscriber list from {SUBSCRIBER_FILE}..."
)

with open(
    SUBSCRIBER_FILE,
    "r",
    encoding="utf-8"
) as file:

    subscriber_data = json.load(file)


subscribers = subscriber_data.get(
    "subscribers",
    []
)


# ---------------------------------------------------------
# Find active subscribers
# ---------------------------------------------------------

active_subscribers = []

for subscriber in subscribers:

    email = subscriber.get(
        "email",
        ""
    ).strip()

    active = subscriber.get(
        "active",
        False
    )

    if email and active is True:

        active_subscribers.append(
            email
        )


if not active_subscribers:

    print(
        "No active subscribers found."
    )

    # We do NOT update last_sent.txt here.
    # This means the article can be sent later
    # after a subscriber is added.

    raise SystemExit(0)


print(
    f"Found {len(active_subscribers)} "
    "active subscriber(s)."
)


# ---------------------------------------------------------
# Build email
# ---------------------------------------------------------

subject = (
    "New Coventry Public Schools News: "
    + title
)


text_body = f"""New Coventry Public Schools News

{title}

Read the full article:
{link}

Published:
{pub_date}

You are receiving this notification because you subscribed
to Coventry Public Schools News.
"""


html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.5;">

<h2>New Coventry Public Schools News</h2>

<h3>{title}</h3>

<p>
<a href="{link}"
   style="
   display:inline-block;
   background:#1f4e79;
   color:white;
   padding:10px 18px;
   text-decoration:none;
   border-radius:4px;">
Read the full article
</a>
</p>

<p>
<strong>Published:</strong> {pub_date}
</p>

<hr>

<p style="color:#666; font-size:12px;">
You are receiving this notification because you subscribed
to Coventry Public Schools News.
</p>

</body>
</html>
"""


# ---------------------------------------------------------
# Connect to SMTP
# ---------------------------------------------------------

print(
    "Connecting to Gmail SMTP..."
)


with smtplib.SMTP(
    SMTP_SERVER,
    SMTP_PORT
) as smtp:

    smtp.ehlo()

    smtp.starttls()

    smtp.ehlo()

    smtp.login(
        SMTP_USERNAME,
        SMTP_P
    )


    # -----------------------------------------------------
    # Send email to every active subscriber
    # -----------------------------------------------------

    for recipient in active_subscribers:

        print(
            f"Sending email to {recipient}"
        )

        message = EmailMessage()

        message["From"] = SMTP_USERNAME
        message["To"] = recipient
        message["Subject"] = subject

        message.set_content(
            text_body
        )

        message.add_alternative(
            html_body,
            subtype="html"
        )

        smtp.send_message(
            message
        )

        print(
            f"Successfully sent to {recipient}"
        )


# ---------------------------------------------------------
# Remember this article
# ---------------------------------------------------------

with open(
    LAST_SENT_FILE,
    "w",
    encoding="utf-8"
) as file:

    file.write(link)


print(
    "Updated last_sent.txt"
)

print(
    "Email notification process complete."
)
