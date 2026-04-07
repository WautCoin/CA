"""
Email service with CC (Carbon Copy) support.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Union


def send_email(
    smtp_host: str,
    smtp_port: int,
    sender: str,
    recipients: Union[str, List[str]],
    subject: str,
    body: str,
    cc: Optional[Union[str, List[str]]] = None,
    bcc: Optional[Union[str, List[str]]] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_tls: bool = True,
) -> None:
    """
    Send an email with optional CC and BCC recipients.

    Args:
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port.
        sender: The sender's email address.
        recipients: Primary recipient(s) (To).
        subject: Email subject.
        body: Email body text.
        cc: Carbon Copy recipient(s).
        bcc: Blind Carbon Copy recipient(s).
        username: SMTP authentication username.
        password: SMTP authentication password.
        use_tls: Whether to use TLS (default True).
    """
    to_list = _normalize_addresses(recipients)
    cc_list = _normalize_addresses(cc)
    bcc_list = _normalize_addresses(bcc)

    msg = build_message(sender, to_list, subject, body, cc_list)

    # Deduplicate while preserving order (To > CC > BCC precedence).
    seen: set = set()
    all_recipients: List[str] = []
    for addr in to_list + cc_list + bcc_list:
        if addr not in seen:
            seen.add(addr)
            all_recipients.append(addr)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.sendmail(sender, all_recipients, msg.as_string())
    except smtplib.SMTPException as exc:
        raise RuntimeError(f"Failed to send email: {exc}") from exc


def build_message(
    sender: str,
    to_list: List[str],
    subject: str,
    body: str,
    cc_list: Optional[List[str]] = None,
) -> MIMEMultipart:
    """
    Build a MIME email message with optional CC header.

    Args:
        sender: The sender's email address.
        to_list: List of primary recipients.
        subject: Email subject.
        body: Email body text.
        cc_list: List of CC recipients.

    Returns:
        A MIMEMultipart message object.
    """
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(to_list)
    msg["Subject"] = subject

    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    msg.attach(MIMEText(body, "plain"))
    return msg


def _normalize_addresses(
    addresses: Optional[Union[str, List[str]]],
) -> List[str]:
    """
    Normalize an address or list of addresses to a flat list of strings.

    Args:
        addresses: A single address string, a list of address strings, or None.

    Returns:
        A list of address strings (empty list if input is None).
    """
    if addresses is None:
        return []
    if isinstance(addresses, str):
        return [addresses]
    return list(addresses)
