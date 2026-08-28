"""
notify_email.py
Sends the top-3 digest via email using Gmail SMTP (works with any SMTP provider
if you change the host/port).

Required environment variables:
  EMAIL_SENDER        - the Gmail address sending the email
  EMAIL_APP_PASSWORD  - a 16-char Gmail "App Password" (NOT your normal password)
  EMAIL_RECIPIENT      - where to send the digest (can be same as sender)
"""

import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _format_html(top3, date_str):
    items_html = "".join(
        f"""
        <div style="margin-bottom:20px;">
          <h3 style="margin:0 0 4px 0;">{i+1}. {item['title']}</h3>
          <p style="margin:0 0 4px 0;">{item['blurb']}</p>
          <a href="{item['link']}">{item['link']}</a>
        </div>
        """
        for i, item in enumerate(top3)
    )
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; max-width:600px;">
        <h2>🤖 Today's Top 3 AI News — {date_str}</h2>
        {items_html}
        <p style="color:#888; font-size:12px;">Sent automatically by your AI News Assistant</p>
      </body>
    </html>
    """


def send_email(top3):
    sender = os.environ["EMAIL_SENDER"]
    app_password = os.environ["EMAIL_APP_PASSWORD"]
    recipient = os.environ["EMAIL_RECIPIENT"]

    date_str = datetime.now().strftime("%B %d, %Y")  # e.g. "August 28, 2026"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🤖 Your Top 3 AI News — {date_str}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(_format_html(top3, date_str), "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, app_password)
        server.sendmail(sender, recipient, msg.as_string())

    print(f"[info] Email sent to {recipient}")


if __name__ == "__main__":
    sample = [{"title": "Test", "link": "https://example.com", "blurb": "This is a test."}]
    send_email(sample)