"""
My profile: each person manages their own account.

Before this nobody could change their own details or password, and there
was no picture anywhere. Role and location stay with administrators.
"""
import io

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import log_audit
from accounts.models import User
from accounts.names import display_name

PHOTO_SIZE = 400                 # pixels, square
PHOTO_MAX_UPLOAD = 8 * 1024 * 1024


def photo_url(user, request=None):
    if not user.photo:
        return None
    url = user.photo.url
    return request.build_absolute_uri(url) if request is not None else url


def profile_payload(user, request=None):
    return {
        "id": user.id,
        "email": user.email,
        # One name per person: a linked member record's name is the one the
        # whole app shows, so that is the one shown and edited here.
        "first_name": user.member.first_name if getattr(user, "member", None) else user.first_name,
        "last_name": user.member.surname if getattr(user, "member", None) else user.last_name,
        "name": display_name(user),
        "phone": user.phone,
        "photo": photo_url(user, request),
        "role": user.role.name if user.role_id else None,
        "location": user.location_id,
        "location_name": user.location.name if user.location_id else None,
    }


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(profile_payload(request.user, request))

    def patch(self, request):
        user = request.user
        errors = {}
        linked = getattr(user, "member", None)
        first = request.data.get("first_name", linked.first_name if linked else user.first_name)
        last = request.data.get("last_name", linked.surname if linked else user.last_name)
        if not (first or "").strip():
            errors["first_name"] = ["Enter your first name."]
        email = (request.data.get("email", user.email) or "").strip().lower()
        if not email:
            errors["email"] = ["Enter your email."]
        elif User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            errors["email"] = ["Another account already uses this email."]
        if errors:
            return Response(errors, status=400)
        user.first_name = first.strip()
        user.last_name = (last or "").strip()
        user.phone = (request.data.get("phone", user.phone) or "").strip()
        changed_email = email != user.email
        user.email = email
        user.save(update_fields=["first_name", "last_name", "phone", "email"])
        member = getattr(user, "member", None)
        if member is not None:
            # Keep the linked member record's name the same, since it is the
            # name the rest of the app shows. Editing only the account used to
            # leave the top bar showing the old name.
            member.first_name, member.surname = user.first_name, user.last_name or member.surname
            member.save(update_fields=["first_name", "surname"])
        log_audit(user, "Updated own profile", "User", display_name(user),
                  "email changed" if changed_email else "", instance=user)
        return Response(profile_payload(user, request))


class MyPhotoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        upload = request.FILES.get("photo")
        if upload is None:
            return Response({"photo": ["Choose a picture."]}, status=400)
        if upload.size > PHOTO_MAX_UPLOAD:
            return Response({"photo": ["That picture is too large. Choose one under 8 MB."]}, status=400)
        try:
            image = ImageOps.exif_transpose(Image.open(upload)).convert("RGB")
        except (UnidentifiedImageError, OSError):
            return Response({"photo": ["That file isn't a picture we can read. Use a JPG or PNG."]}, status=400)
        # A centred square, small enough to load instantly everywhere.
        image = ImageOps.fit(image, (PHOTO_SIZE, PHOTO_SIZE), Image.LANCZOS)
        out = io.BytesIO()
        image.save(out, "JPEG", quality=85, optimize=True)
        user = request.user
        if user.photo:
            user.photo.delete(save=False)
        user.photo.save(f"user-{user.pk}.jpg", ContentFile(out.getvalue()), save=True)
        log_audit(user, "Changed own photo", "User", display_name(user), "", instance=user)
        return Response(profile_payload(user, request))

    def delete(self, request):
        user = request.user
        if user.photo:
            user.photo.delete(save=True)
            log_audit(user, "Removed own photo", "User", display_name(user), "", instance=user)
        return Response(profile_payload(user, request))


class MyPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.check_password(request.data.get("current_password") or ""):
            return Response({"current_password": ["That isn't your current password."]}, status=400)
        new = request.data.get("new_password") or ""
        if new != (request.data.get("new_password_again") or ""):
            return Response({"new_password_again": ["The two passwords don't match."]}, status=400)
        try:
            password_validation.validate_password(new, user)
        except ValidationError as err:
            return Response({"new_password": list(err.messages)}, status=400)
        user.set_password(new)
        user.save(update_fields=["password"])
        log_audit(user, "Changed own password", "User", display_name(user), "", instance=user)
        return Response({"detail": "Password changed."})
