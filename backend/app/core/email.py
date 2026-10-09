import logging
import re
import smtplib
import ssl
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Union

from app.core.config import settings

logger = logging.getLogger("app.email")

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def is_valid_email(email_str: str) -> bool:
    """Validate that the string is a well-formed email address."""
    if not email_str or not isinstance(email_str, str):
        return False
    return bool(EMAIL_REGEX.match(email_str.strip()))


@dataclass
class EmailDeliveryResult:
    """
    Structured outcome of an email transmission attempt.
    Implements __bool__ to maintain backward-compatibility with boolean checks.
    """
    success: bool
    status: str  # 'Sent', 'Simulated', 'Failed'
    error_message: Optional[str] = None
    detail: Optional[str] = None

    def __bool__(self) -> bool:
        return self.success


def send_live_email(
    recipients: Union[str, List[str]],
    subject: str,
    body: str,
    html_body: str = None,
) -> EmailDeliveryResult:
    """
    Sends an email via SMTP (supporting both Port 465 SSL and Port 587 STARTTLS).
    If simulation mode is active or credentials are intentionally unconfigured,
    records the dispatch as 'Simulated'.
    Returns an EmailDeliveryResult instance with delivery status and sanitized errors.
    """
    # 1. Parse and validate recipients
    if isinstance(recipients, str):
        recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]
    elif isinstance(recipients, list):
        recipient_list = [r.strip() for r in recipients if isinstance(r, str) and r.strip()]
    else:
        recipient_list = []

    if not recipient_list:
        return EmailDeliveryResult(
            success=False,
            status="Failed",
            error_message="No recipient email address provided.",
        )

    invalid_recipients = [r for r in recipient_list if not is_valid_email(r)]
    if invalid_recipients:
        return EmailDeliveryResult(
            success=False,
            status="Failed",
            error_message=f"Invalid email recipient format: {', '.join(invalid_recipients)}",
        )

    # 2. Check Simulation mode
    if not getattr(settings, "SMTP_ENABLED", True):
        logger.info(f"[Email Sim] SMTP sending is disabled in settings. Email to {recipient_list} recorded in simulation mode.")
        return EmailDeliveryResult(
            success=True,
            status="Simulated",
            detail="Simulation mode active (SMTP_ENABLED=False).",
        )

    sender_email = getattr(settings, "SMTP_FROM_EMAIL", "tdevendiran123@gmail.com")
    sender_name = getattr(settings, "SMTP_FROM_NAME", "ToolShoppe Industrial Supply")
    smtp_host = getattr(settings, "SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(getattr(settings, "SMTP_PORT", 465))
    smtp_user = getattr(settings, "SMTP_USER", sender_email)
    smtp_pass = getattr(settings, "SMTP_PASSWORD", "")

    # 3. Missing Credentials check
    if not smtp_pass or not smtp_user:
        logger.warning("[Email Sim] SMTP credentials not fully configured. Email logged as simulated.")
        return EmailDeliveryResult(
            success=True,
            status="Simulated",
            error_message="SMTP credentials not configured. Recorded as simulated send.",
            detail="Missing SMTP_PASSWORD or SMTP_USER in environment variables.",
        )

    # 4. Construct message
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = ", ".join(recipient_list)
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        raw_message = msg.as_string()
    except Exception as exc:
        return EmailDeliveryResult(
            success=False,
            status="Failed",
            error_message=f"Failed to compose email message: {str(exc)}",
        )

    # 5. Connect and send via SSL (465) or STARTTLS (587), with auto-fallback
    def _send_ssl():
        ssl_ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, 465, context=ssl_ctx, timeout=6) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, recipient_list, raw_message)

    def _send_starttls():
        with smtplib.SMTP(smtp_host, 587, timeout=4) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, recipient_list, raw_message)

    try:
        if smtp_port == 465:
            _send_ssl()
        elif smtp_port == 587:
            try:
                _send_starttls()
            except Exception as starttls_err:
                logger.info(f"STARTTLS on 587 failed ({starttls_err}), attempting fallback to SSL on 465...")
                _send_ssl()
        else:
            # General port connection
            try:
                _send_ssl()
            except Exception:
                _send_starttls()

        logger.info(f"[Email Success] Dispatched email to {recipient_list}: '{subject}'")
        return EmailDeliveryResult(
            success=True,
            status="Sent",
            detail="Server accepted email for delivery.",
        )
    except Exception as exc:
        # Sanitize exception message to prevent credential leakage
        raw_err = str(exc)
        if smtp_pass:
            raw_err = raw_err.replace(smtp_pass, "******")
        logger.error(f"[Email Error] Failed sending email to {recipient_list}: {raw_err}")
        return EmailDeliveryResult(
            success=False,
            status="Failed",
            error_message=f"SMTP transmission failed: {raw_err}",
        )



def fetch_inbox_messages(limit: int = 15) -> List[dict]:
    """
    Connects to IMAP (Gmail) and retrieves recent incoming emails (e.g. supplier replies).
    """
    import imaplib
    import email
    from email.header import decode_header

    smtp_user = getattr(settings, "SMTP_USER", "tdevendiran123@gmail.com")
    smtp_pass = getattr(settings, "SMTP_PASSWORD", "")
    if not smtp_pass:
        return []

    results = []
    mail = None
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=3)
        mail.login(smtp_user, smtp_pass)
        status, count_data = mail.select("inbox")
        total = int(count_data[0]) if count_data and count_data[0] else 0
        if total == 0:
            return []

        start = max(1, total - limit + 1)
        res, data = mail.fetch(f"{start}:{total}", "(RFC822)")

        for item in reversed(data):
            if isinstance(item, tuple) and len(item) > 1:
                try:
                    msg = email.message_from_bytes(item[1])
                    sub_raw = decode_header(msg.get("Subject", ""))[0]
                    subject = sub_raw[0].decode(sub_raw[1] or "utf-8", errors="ignore") if isinstance(sub_raw[0], bytes) else str(sub_raw[0] or "")
                    
                    sender = msg.get("From", "")
                    date_str = msg.get("Date", "")
                    
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = payload.decode("utf-8", errors="ignore")
                                    break
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="ignore")

                    results.append({
                        "id": str(len(results) + 1),
                        "sender": sender,
                        "subject": subject,
                        "date": date_str,
                        "body": body.strip(),
                        "preview": body.strip()[:180].replace("\n", " "),
                    })
                except Exception as e:
                    logger.debug(f"Error parsing email item: {e}")
                    continue
    except Exception as exc:
        logger.error(f"[IMAP Error] Failed to fetch inbox messages: {exc}")
    finally:
        if mail:
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass

    return results

