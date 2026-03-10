import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional


SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER or "")


def send_email(to: str, subject: str, html_body: str) -> bool:
  """
  Send a single HTML email via SMTP.
  Returns True if successful, False if failed.
  """
  if not (SMTP_HOST and SMTP_USER and SMTP_PASS and EMAIL_FROM):
      # Misconfigured SMTP; log for debugging
      print("SMTP not configured; skipping email to", to)
      print("Required env vars: SMTP_HOST, SMTP_USER, SMTP_PASS, EMAIL_FROM")
      return False

  msg = EmailMessage()
  msg["From"] = EMAIL_FROM
  msg["To"] = to
  msg["Subject"] = subject
  msg.set_content("This email requires an HTML-capable client.")
  msg.add_alternative(html_body, subtype="html")

  context = ssl.create_default_context()

  try:
      with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
          # Most providers use STARTTLS on 587
          server.starttls(context=context)
          server.login(SMTP_USER, SMTP_PASS)
          server.send_message(msg)
      print(f"[EMAIL SUCCESS] Email sent to {to}")
      return True
  except Exception as e:
      # Do not crash the API if email fails
      print(f"[EMAIL ERROR] Failed to send email to {to}: {e}")
      return False

