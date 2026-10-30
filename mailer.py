"""Email notifications for new bookings. Configured entirely through environment variables."""

import os
import smtplib
import sys
import threading
from datetime import date
from email.message import EmailMessage

SSL_PORT = 465


def format_slot(slot):
    """'2026-11-02T10' -> 'Monday, 2 Nov 2026, 10 AM – 11 AM'."""
    day, hour = slot.split("T")
    start = int(hour)
    label = lambda h: f"{h % 12 or 12} {'AM' if h % 24 < 12 else 'PM'}"
    when = date.fromisoformat(day)
    return f"{when.strftime('%A')}, {when.day} {when.strftime('%b %Y')}, {label(start)} – {label((start + 1) % 24)}"


def booking_message(name, slot, kind, note):
    """Return (subject, body). Only the fixed visitor name goes into the subject."""
    lines = [
        f"{name} just booked time with you.",
        "",
        f"When:   {format_slot(slot)}",
        f"Reason: {kind}",
    ]
    if note:
        lines.append(f"Note:   {note}")
    lines += ["", "Don't hope for more than 15 minutes. 😉"]
    return f"📅 {name} booked time with you", "\n".join(lines)


class Mailer:
    def __init__(self, host, port, username, password, sender, recipient, smtp_class=None, timeout=10):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender
        self._recipient = recipient
        self._smtp_class = smtp_class
        self._timeout = timeout

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        host = env.get("SMTP_HOST", "").strip()
        recipient = env.get("NOTIFY_EMAIL", "").strip()
        if not host or not recipient:
            return cls("", 0, "", "", "", "")
        username = env.get("SMTP_USER", "").strip()
        return cls(
            host,
            int(env.get("SMTP_PORT") or 587),
            username,
            env.get("SMTP_PASSWORD", ""),
            env.get("MAIL_FROM", "").strip() or username,
            recipient,
        )

    @property
    def enabled(self):
        return bool(self._host and self._recipient and self._sender)

    def send(self, subject, body):
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._sender
        message["To"] = self._recipient
        message.set_content(body)
        smtp_class = self._smtp_class or (smtplib.SMTP_SSL if self._port == SSL_PORT else smtplib.SMTP)
        with smtp_class(self._host, self._port, timeout=self._timeout) as smtp:
            if self._port != SSL_PORT:
                smtp.starttls()
            if self._username:
                smtp.login(self._username, self._password)
            smtp.send_message(message)

    def send_async(self, subject, body):
        """Fire and forget: a mail failure is logged and never affects the booking."""
        if not self.enabled:
            return None

        def work():
            try:
                self.send(subject, body)
            except Exception as error:
                print(f"Email notification failed: {error}", file=sys.stderr)

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        return thread
