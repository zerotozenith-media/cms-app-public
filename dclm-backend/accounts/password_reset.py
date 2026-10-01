"""
Self-service password reset.

Somebody who has forgotten their password asks for a link by email and
chooses a new one, instead of waiting for an administrator. Only people
with no account need an administrator.

- The request always gets the same answer, so it never reveals whether
  an email address has an account.
- The link works once and for one hour. Django's token is tied to the
  current password, so it stops working the moment the password changes.
- Requests are limited per email address, so the form cannot be used to
  flood somebody's inbox.
- The new password must pass the same rules as everywhere else.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import log_audit
from accounts.models import AuditLog, User
from accounts.names import display_name
import logging

from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

REQUESTS_PER_HOUR = 3
SENT_ANSWER = {"detail": "If an account exists for that email, a link to reset the password is on its way."}
BAD_LINK = {"detail": "This link has expired or has already been used. Ask for a new one."}


def _reset_link(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    base = (getattr(settings, "APP_BASE_URL", "") or "").rstrip("/")
    return f"{base}/reset-password?uid={uid}&token={token}"


def _send(user):
    link = _reset_link(user)
    name = (user.first_name or display_name(user)).strip()
    text = (
        f"Hello {name},\n\n"
        "We received a request to reset the password for your DCLM Bahrain account. "
        "Open the link below to choose a new one.\n\n"
        f"{link}\n\n"
        "The link works once and expires in one hour. If you didn't ask for this, "
        "you can ignore this email. Your password won't change.\n"
    )
    html = (
        "<div style=\"font-family:Arial,sans-serif;max-width:560px;margin:0 auto;border:1px solid #E3E8F1;"
        "border-radius:14px;overflow:hidden\"><div style=\"background:#0B1F44;color:#fff;text-align:center;"
        "padding:20px;font-weight:700;letter-spacing:1px;font-size:14px\">DEEPER CHRISTIAN LIFE MINISTRY BAHRAIN"
        "<div style=\"height:2px;background:#E01E28;width:60px;margin:10px auto 0\"></div></div>"
        "<div style=\"padding:26px;color:#0F1B2E\"><div style=\"font-size:20px;font-weight:700\">Reset your password</div>"
        f"<p style=\"color:#33415C;line-height:1.6\">Hello {name},</p>"
        "<p style=\"color:#33415C;line-height:1.6\">We received a request to reset the password for your DCLM "
        "Bahrain account. Press the button below to choose a new one.</p>"
        f"<p><a href=\"{link}\" style=\"display:inline-block;background:#1C4E9E;color:#fff;border-radius:999px;"
        "padding:12px 22px;font-weight:700;text-decoration:none\">Choose a new password</a></p>"
        "<p style=\"color:#5A667C;font-size:13px;line-height:1.6\">This link works once and expires in one hour. "
        "If you didn't ask for this, you can ignore this email. Your password won't change.</p></div></div>"
    )
    # Sent directly, not through the digest notifications switch: the person
    # has just asked for it, and a reset that silently never arrives would
    # leave them locked out.
    try:
        message = EmailMultiAlternatives(subject="Reset your DCLM Bahrain password", body=text,
                                         from_email=settings.DEFAULT_FROM_EMAIL, to=[user.email])
        message.attach_alternative(html, "text/html")
        message.send()
    except Exception:
        logger.exception("Password reset email could not be sent to %s", user.email)


def _user_from(uid):
    try:
        return User.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None


class PasswordResetRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response({"email": ["Enter the email you sign in with."]}, status=400)
        recent = AuditLog.objects.filter(
            action="Password reset requested", entity_name=email,
            timestamp__gte=timezone.now() - timedelta(hours=1),
        ).count()
        log_audit(None, "Password reset requested", "User", email, "")
        if recent < REQUESTS_PER_HOUR:
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user:
                _send(user)
        return Response(SENT_ANSWER)


class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        user = _user_from(request.data.get("uid") or "")
        token = request.data.get("token") or ""
        if user is None or not default_token_generator.check_token(user, token):
            return Response(BAD_LINK, status=400)
        if request.data.get("check_only"):
            return Response({"email": user.email})
        password = request.data.get("password") or ""
        if password != (request.data.get("password_again") or ""):
            return Response({"password_again": ["The two passwords don't match."]}, status=400)
        try:
            password_validation.validate_password(password, user)
        except ValidationError as err:
            return Response({"password": list(err.messages)}, status=400)
        user.set_password(password)
        user.save(update_fields=["password"])
        log_audit(user, "Reset password", "User", display_name(user), "by email link", instance=user)
        from accounts.views import signed_in_payload
        return Response(signed_in_payload(user))
