"""
How the church sends notifications.

Everything goes through `send_notification`, so the rest of the codebase
never touches an email API directly. That is the point: WhatsApp is a
likely second channel later, and adding it should mean writing one more
backend here rather than editing every place that notifies someone.

Sending never raises. A digest that fails to send must not break the
command that generated it, or one bad address stops everyone else's
notifications.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


class NotificationResult:
    def __init__(self, sent=0, failed=0, skipped=0):
        self.sent = sent
        self.failed = failed
        self.skipped = skipped

    def __repr__(self):
        return f"<sent={self.sent} failed={self.failed} skipped={self.skipped}>"


def send_notification(*, to, subject, text_body, html_body=None):
    """
    Send one notification to one person.

    Returns True if it went out, False otherwise. Never raises: the
    caller is usually a scheduled command working through a list of
    people, and one bad address should not stop the rest.
    """
    if not to:
        logger.info("Notification skipped, no address: %s", subject)
        return False

    if not getattr(settings, "NOTIFICATIONS_ENABLED", False):
        # Off by default so a fresh install, or a staging copy of the
        # real database, cannot email the congregation by accident.
        logger.info("Notifications disabled, would have sent to %s: %s", to, subject)
        return False

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to],
        )
        if html_body:
            message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
        return True
    except Exception:
        logger.exception("Failed to send notification to %s", to)
        return False
