"""
Sending alerts. Every call is safe: a phone that has gone away, a push
service that is down, or a missing library never stops the action that
caused the alert. Failures are logged, and a device the push service says
no longer exists is forgotten.
"""
import base64
import json
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

TTL = 24 * 60 * 60          # a phone switched off for a day still gets it


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def keys():
    """(public, private) as the browser and pywebpush expect them. Taken from
    VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY when set on the server, otherwise
    made once and kept in the database."""
    pub = getattr(settings, "VAPID_PUBLIC_KEY", "") or ""
    priv = getattr(settings, "VAPID_PRIVATE_KEY", "") or ""
    if pub and priv:
        return pub, priv
    from .models import PushKeys
    row = PushKeys.objects.first()
    if row:
        return row.public_key, row.private_key
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    key = ec.generate_private_key(ec.SECP256R1())
    private = _b64(key.private_numbers().private_value.to_bytes(32, "big"))
    public = _b64(key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
    from django.db import IntegrityError
    try:
        with transaction.atomic():
            row = PushKeys.objects.create(public_key=public, private_key=private)
    except IntegrityError:
        row = PushKeys.objects.get()          # another server made it first
    return row.public_key, row.private_key


def _subject():
    s = getattr(settings, "VAPID_SUBJECT", "") or ""
    if s:
        return s
    base = getattr(settings, "APP_BASE_URL", "") or ""
    return base if base.startswith("https://") else "mailto:noreply@dclm-bh.org"


def _deliver(sub, payload):
    """Send to one device. True when the push service accepted it."""
    from pywebpush import WebPushException, webpush
    _, private = keys()
    try:
        webpush(subscription_info=sub.info(), data=json.dumps(payload), vapid_private_key=private,
                vapid_claims={"sub": _subject()}, ttl=TTL, timeout=10)
    except WebPushException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (404, 410):
            sub.delete()                      # the device turned alerts off or no longer exists
        else:
            logger.warning("Alert to device %s refused: %s", sub.pk, exc)
        return False
    except Exception:
        logger.exception("Alert to device %s could not be sent", sub.pk)
        return False
    sub.last_sent_at = timezone.now()
    sub.save(update_fields=["last_sent_at"])
    return True


def send(user, kind, title, body, url="/", tag=None):
    """Send one alert to every device of one person, if they want this kind.
    Returns how many devices accepted it."""
    from .models import AlertSettings
    if not user or not user.is_active:
        return 0
    subs = list(user.push_subscriptions.all())
    if not subs or not AlertSettings.for_user(user).wants(kind):
        return 0
    payload = {"title": title[:80], "body": body[:300], "url": url or "/", "tag": tag or kind}
    return sum(1 for s in subs if _deliver(s, payload))


def in_background(fn):
    """Run fn after the current change is saved, away from the request, so
    nobody waits on phones. Tests switch the background off."""
    def safe():
        try:
            fn()
        except Exception:
            logger.exception("Alerts could not be sent")
        finally:
            if getattr(settings, "ALERTS_IN_BACKGROUND", True):
                from django.db import connection
                connection.close()
    def start():
        if getattr(settings, "ALERTS_IN_BACKGROUND", True):
            import threading
            threading.Thread(target=safe, daemon=True).start()
        else:
            safe()
    transaction.on_commit(start)


def send_later(user_ids, kind, title, body, url="/", tag=None):
    """Send to these people once the change that caused it is saved, so an
    alert never describes something that was rolled back."""
    ids = [i for i in ({user_ids} if isinstance(user_ids, int) else set(user_ids)) if i]
    if not ids:
        return
    def go():
        from accounts.models import User
        for u in User.objects.filter(pk__in=ids, is_active=True):
            send(u, kind, title, body, url, tag)
    in_background(go)
