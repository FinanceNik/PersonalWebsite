"""Outbound notifications for lead-capture events.

Two delivery paths:

  1. SMTP, if SMTP_HOST / SMTP_USER / SMTP_PASSWORD / NOTIFY_EMAIL are all set
     in the environment. Uses STARTTLS on port 587 by default.
  2. stderr fallback otherwise. The submission is printed in a clearly
     bracketed block so it's visible in `journalctl` / docker logs even when
     SMTP isn't configured yet.

The point of the stderr fallback is that lead capture is never silently broken:
either an email lands in your inbox, or the lead is in your server logs.
"""
import os
import smtplib
import sys
from email.message import EmailMessage


def _smtp_config():
    return {
        'host': os.getenv('SMTP_HOST', '').strip(),
        'port': int(os.getenv('SMTP_PORT', '587') or '587'),
        'user': os.getenv('SMTP_USER', '').strip(),
        'password': os.getenv('SMTP_PASSWORD', ''),
        'recipient': os.getenv('NOTIFY_EMAIL', '').strip(),
        'from_addr': os.getenv('SMTP_FROM', '').strip(),
    }


def _log_to_stderr(subject, body):
    """Fallback when SMTP isn't configured — print to stderr so logs catch it."""
    print(
        f'\n========== LEAD NOTIFICATION (SMTP not configured) ==========\n'
        f'Subject: {subject}\n\n{body}\n'
        f'=============================================================\n',
        file=sys.stderr, flush=True,
    )


def _send_via_smtp(cfg, subject, body, reply_to):
    msg = EmailMessage()
    msg['From'] = cfg['from_addr'] or cfg['user']
    msg['To'] = cfg['recipient']
    msg['Subject'] = subject
    if reply_to:
        msg['Reply-To'] = reply_to
    msg.set_content(body)
    with smtplib.SMTP(cfg['host'], cfg['port'], timeout=10) as server:
        server.starttls()
        server.login(cfg['user'], cfg['password'])
        server.send_message(msg)


def send_contact_notification(firstname, lastname, country, email, message):
    """Notify about a new /contact submission. Never raises."""
    body = (
        f'From:    {firstname} {lastname}\n'
        f'Email:   {email}\n'
        f'Country: {country or "(not provided)"}\n\n'
        f'Message:\n{message}\n'
    )
    subject = f'[Site] New contact: {firstname} {lastname}'
    _deliver(subject, body, reply_to=email)


def send_lead_notification(name, email, source):
    """Notify about a lead-magnet capture (e.g., checklist download)."""
    body = (
        f'Source:  {source}\n'
        f'Name:    {name}\n'
        f'Email:   {email}\n'
    )
    subject = f'[Site] New lead ({source}): {name}'
    _deliver(subject, body, reply_to=email)


def _deliver(subject, body, reply_to=None):
    cfg = _smtp_config()
    smtp_configured = all([cfg['host'], cfg['user'], cfg['password'], cfg['recipient']])
    if not smtp_configured:
        _log_to_stderr(subject, body)
        return
    try:
        _send_via_smtp(cfg, subject, body, reply_to)
    except Exception as e:
        # SMTP failure should not break the form submit; log instead.
        print(
            f'\n!!!!! SMTP DELIVERY FAILED — falling back to log !!!!!\n'
            f'Error: {e}\n',
            file=sys.stderr, flush=True,
        )
        _log_to_stderr(subject, body)
