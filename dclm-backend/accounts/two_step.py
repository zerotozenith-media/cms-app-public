"""
Two-step sign-in with an authenticator app (approved 10 November 2026, the
same design as DCLM Canada).

- Each role is Required, Person chooses or Off (Admin, Settings).
- A person sets it up once by scanning a QR code into any standard
  authenticator app (Microsoft Authenticator, Google Authenticator and the
  like), which then shows a new 6-digit number every 30 seconds. The app and
  this code agree on the number from a shared secret and the time, with no
  outside service (RFC 6238).
- Ten one-time backup codes cover a lost phone. Another Administrator can
  reset a person who has lost both.
- A browser can be remembered for the days in Settings (30 at first).
- Wrong numbers count with wrong passwords, so the same sign-in lock applies.

The secret is kept encrypted with the app's secret key, backup codes hashed
like passwords, and each number is accepted once (two_step_last_step).
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.db import transaction
from django.utils import timezone

DIGITS = 6
STEP = 30
DRIFT = 1                       # one step either side, for a phone clock a little off
BACKUP_CODES = 10
ISSUER = "DCLM Bahrain"
TICKET_MINUTES = 10


# ------------------------------------------------------------------ the secret

def _fernet():
    from cryptography.fernet import Fernet
    key = base64.urlsafe_b64encode(hashlib.sha256(("two-step:" + settings.SECRET_KEY).encode()).digest())
    return Fernet(key)


def seal(secret):
    return _fernet().encrypt(secret.encode()).decode()


def unseal(token):
    return _fernet().decrypt(token.encode()).decode()


def new_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def number(secret, counter):
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    h = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return str((struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % (10 ** DIGITS)).zfill(DIGITS)


def matching_step(secret, code, now=None):
    """The time step the 6-digit number belongs to, or None."""
    code = "".join(ch for ch in str(code) if ch.isdigit())
    if len(code) != DIGITS:
        return None
    t = int((now if now is not None else time.time()) // STEP)
    for step in range(t - DRIFT, t + DRIFT + 1):
        if hmac.compare_digest(number(secret, step), code):
            return step
    return None


def otpauth(user, secret):
    label = quote(f"{ISSUER}:{user.email}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(ISSUER)}&digits={DIGITS}&period={STEP}"


def grouped(secret):
    return " ".join(secret[i:i + 4] for i in range(0, len(secret), 4))


# ------------------------------------------------------------------ who needs it

def mode(user):
    """"required", "choose" or "off" for this person's role."""
    return getattr(user.role, "two_step", "off") if user.role_id else "off"


def is_on(user):
    return bool(user.two_step_secret)


def needed_at_sign_in(user):
    """None, "code" (it is on) or "setup" (the role requires it and it is not set up)."""
    m = mode(user)
    if m == "off":
        return None
    if is_on(user):
        return "code"
    return "setup" if m == "required" else None


# ------------------------------------------------------------------ tickets and devices

def ticket(user, stage, secret=None):
    """A short-lived signed note that the password was right, carried to the
    second step. Holds the new secret, sealed, while setting up."""
    data = {"u": user.id, "v": user.two_step_version, "s": stage}
    if secret:
        data["k"] = seal(secret)
    return signing.dumps(data, salt="two-step-ticket")


def read_ticket(value):
    from .models import User
    try:
        data = signing.loads(value or "", salt="two-step-ticket", max_age=TICKET_MINUTES * 60)
    except signing.BadSignature:
        return None, None, None
    user = User.objects.filter(id=data.get("u"), is_active=True).first()
    if not user or user.two_step_version != data.get("v"):
        return None, None, None
    return user, data.get("s"), unseal(data["k"]) if data.get("k") else None


def device_token(user):
    return signing.dumps({"u": user.id, "v": user.two_step_version}, salt="two-step-device")


def device_ok(user, value):
    from core import settings_store
    days = settings_store.get("two_step_remember_days")
    if not value or not days:
        return False
    try:
        data = signing.loads(value, salt="two-step-device", max_age=days * 86400)
    except signing.BadSignature:
        return False
    return data.get("u") == user.id and data.get("v") == user.two_step_version


# ------------------------------------------------------------------ checking a number

def _norm_backup(code):
    return "".join(ch for ch in str(code).upper() if ch.isalnum())


def new_backup_codes():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    plain = ["".join(secrets.choice(alphabet) for _ in range(8)) for _ in range(BACKUP_CODES)]
    return [f"{p[:4]}-{p[4:]}" for p in plain], [make_password(p) for p in plain]


@transaction.atomic
def check(user, code):
    """Whether a 6-digit number or an unused backup code is right. A number
    is accepted once, and a backup code is used up."""
    from .models import User
    user = User.objects.select_for_update().get(pk=user.pk)
    if not user.two_step_secret:
        return False
    step = matching_step(unseal(user.two_step_secret), code)
    if step is not None and step > user.two_step_last_step:
        user.two_step_last_step = step
        user.save(update_fields=["two_step_last_step"])
        return True
    b = _norm_backup(code)
    if len(b) == 8:
        for i, h in enumerate(user.two_step_backup):
            if check_password(b, h):
                user.two_step_backup = user.two_step_backup[:i] + user.two_step_backup[i + 1:]
                user.save(update_fields=["two_step_backup"])
                return True
    return False


def turn_on(user, secret, code):
    """Saves the secret once the person has typed a right number from the
    app. Returns the backup codes to show once, or None."""
    step = matching_step(secret, code)
    if step is None:
        return None
    plain, hashed = new_backup_codes()
    user.two_step_secret = seal(secret)
    user.two_step_last_step = step
    user.two_step_backup = hashed
    user.two_step_on_since = timezone.now()
    user.save(update_fields=["two_step_secret", "two_step_last_step", "two_step_backup", "two_step_on_since"])
    return plain


def turn_off(user):
    user.two_step_secret = ""
    user.two_step_backup = []
    user.two_step_on_since = None
    user.two_step_last_step = 0
    user.two_step_version += 1
    user.save(update_fields=["two_step_secret", "two_step_backup", "two_step_on_since", "two_step_last_step",
                             "two_step_version"])
