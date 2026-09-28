import os
import smtplib
import xml.etree.ElementTree as ET

from email.message import EmailMessage


FEED_FILE = "feed.xml"


# ---------------------------------------------------------
# Read credentials from GitHub Actions secrets
# ---------------------------------------------------------

SMTP_USERNAME = os.environ["SMTP_USERNAME"]
SMTP_P = os.environ["SMTP_P"]
TEST_RECIPIENT = os.environ["TEST_RECIPIENT"]


# ---------------------------------------------------------
# Gmail SMTP settings
# ---------------------------------------------------------

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
    raise RuntimeError("RSS feed does not contain a channel.")


# ---------------------------------------------------------
# Get newest article
# ---------------------------------------------------------

item = channel.find("item")

if item is None:
    raise RuntimeError("RSS feed does not contain any articles.")


title = item.findtext("title", "").strip()
link = item.findtext("link", "").strip()
pub_date = item.findtext("pubDate", "").strip()


if not title or not link:
    raise RuntimeError(
        "Newest RSS item is missing a title or link."
    )


print(f"Newest article: {title}")
print(f"Article URL: {link}")


# ---------------------------------------------------------
# Build email
# ---------------------------------------------------------

subject = f"New Coventry Public Schools News: {title}"


text_body = f"""New Coventry Public Schools News

{title}

Read the full article:
{link}

Published:
{pub_date}

This is a test notification from the Coventry Public Schools RSS project.
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
This is a test notification from the Coventry Public Schools RSS project.
</p>

</body>
</html>
"""


message = EmailMessage()

message["From"] = SMTP_USERNAME
message["To"] = TEST_RECIPIENT
message["Subject"] = subject

message.set_content(text_body)
message.add_alternative(
    html_body,
    subtype="html"
)


# ---------------------------------------------------------
# Send email
# ---------------------------------------------------------

print("Connecting to Gmail SMTP...")

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

    smtp.send_message(message)


print(
    f"Test email successfully sent to {TEST_RECIPIENT}"
)
