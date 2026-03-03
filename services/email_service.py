"""SMTP email sender — supports both STARTTLS (587) and SSL (465)."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
TARGET_EMAIL = os.getenv("TARGET_EMAIL", "")


def send_excerpt_email(
    book_name: str,
    start: int,
    end: int,
    status_url: str,
    file_url: str,
) -> None:
    """Send an email with progress and download links for the requested excerpt."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📚 Excerpt ready: {book_name} (pages {start}–{end})"
    msg["From"] = SMTP_USER
    msg["To"] = TARGET_EMAIL

    html = f"""\
<html>
<body style="font-family:sans-serif;line-height:1.6;color:#222;max-width:520px;margin:auto">
  <h2 style="margin-bottom:4px">📖 Book Excerpt Ready</h2>
  <p style="color:#555;margin-top:0">{book_name} &mdash; pages {start}–{end}</p>

  <p>Your excerpt is being generated in the background.</p>

  <p>🔄 <a href="{status_url}" style="color:#555">Check progress</a></p>

  <div style="margin:28px 0">
    <a href="{file_url}"
       style="display:inline-block;padding:14px 32px;background:#1a73e8;color:#fff;
              font-size:18px;font-weight:700;text-decoration:none;border-radius:8px;
              letter-spacing:0.3px">
      ⬇&nbsp; Download PDF Excerpt
    </a>
  </div>

  <p style="font-size:0.9em;color:#444">
    💡 <strong>Open with Kami:</strong> after downloading, open the file in your browser
    and click <em>"Open with Kami"</em> from the Kami Chrome extension, or drag the PDF
    into <a href="https://www.kamiapp.com" style="color:#1a73e8">kamiapp.com</a>.
  </p>

  <p style="color:#aaa;font-size:0.8em">Sent automatically by Book Gateway API.</p>
</body>
</html>"""

    plain = (
        f"Book excerpt requested: {book_name} (pages {start}–{end})\n\n"
        f"Progress: {status_url}\n"
        f"Download PDF: {file_url}\n"
    )

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    # Port 465 → implicit SSL; anything else → STARTTLS
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, TARGET_EMAIL, msg.as_string())
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, TARGET_EMAIL, msg.as_string())
