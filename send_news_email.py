import os
import smtplib
import xml.etree.ElementTree as ET

from email.message import EmailMessage


FEED_FILE = "feed.xml"
LAST_SENT_FILE = "last_sent.txt"


# ---------------------------------------------------------
# Email configuration
# ---------------------------------------------------------

SMTP_USERNAME = os.environ["SMTP_USERNAME"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
TEST_RECIPIENT = os.environ["TEST_RECIPIENT"]

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

You are receiving this notification because you subscribed to Coventry Public Schools News.
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


message = EmailMessage()

message["From"] = SMTP_USERNAME
message["To"] = TEST_RECIPIENT
message["Subject"] = subject

message.set_content(
    text_body
)

message.add_alternative(
    html_body,
    subtype="html"
)


# ---------------------------------------------------------
# Send email
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
        SMTP_PASSWORD
    )

    smtp.send_message(
        message
    )


print(
    f"Email successfully sent to "
    f"{TEST_RECIPIENT}"
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
