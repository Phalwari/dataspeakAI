"""Small provider adapter for transactional email.

Credentials are read only from environment variables. The service never logs
provider credentials or message bodies.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import resend

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, text_body: str, html_body: Optional[str] = None) -> bool:
    """Send email through configured SMTP first, then Resend if available."""
    smtp_user = os.getenv("EMAIL_USER")
    smtp_password = os.getenv("EMAIL_PASS")
    if smtp_user and smtp_password:
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = os.getenv("EMAIL_FROM", smtp_user)
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(text_body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))
            with smtplib.SMTP(os.getenv("EMAIL_HOST", "smtp.gmail.com"), int(os.getenv("EMAIL_PORT", "587"))) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            return True
        except Exception:
            logger.exception("SMTP email delivery failed")

    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key:
        try:
            resend.api_key = resend_key
            resend.Emails.send({
                "from": os.getenv("EMAIL_FROM", "DataSpeakAI <onboarding@resend.dev>"),
                "to": to,
                "subject": subject,
                "text": text_body,
                "html": html_body or f"<p>{text_body}</p>",
            })
            return True
        except Exception:
            logger.exception("Resend email delivery failed")

    logger.warning("No email provider configured; message was not delivered")
    return False
