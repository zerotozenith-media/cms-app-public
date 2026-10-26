"""
Help & Guide files (Kay, 26 October 2026): the user manual and Help
pictures, for signed-in people only, because the pictures show church
names. Also who to ask when Help does not answer it.
"""
import os
import re

from django.http import FileResponse, Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

HERE = os.path.join(os.path.dirname(__file__), "help_files")


def _send(path, kind):
    if not os.path.isfile(path):
        raise Http404("That help file is not on this server.")
    r = FileResponse(open(path, "rb"), content_type=kind)
    r["Cache-Control"] = "private, max-age=86400"
    return r


class ManualView(APIView):
    """The user manual as a PDF."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        r = _send(os.path.join(HERE, "manual.pdf"), "application/pdf")
        r["Content-Disposition"] = 'inline; filename="DCLM-user-manual.pdf"'
        return r


class HelpImageView(APIView):
    """A Help picture, by name, such as reasons."""
    permission_classes = [IsAuthenticated]

    def get(self, request, name):
        if not re.fullmatch(r"[a-z0-9-]{1,40}", name):
            raise Http404("That picture is not in Help.")
        return _send(os.path.join(HERE, "img", f"{name}.jpg"), "image/jpeg")


class HelpContactsView(APIView):
    """Who to ask: the Follow-up Coordinator for this person's location and
    the administrators who cover it."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from accounts.models import User
        from accounts.names import display_name
        from accounts.permissions import user_has
        from .followup_access import coordinators_for
        u = request.user
        admins = []
        for a in User.objects.filter(is_active=True).select_related("location").order_by("first_name", "last_name"):
            if a.pk == u.pk or not (a.is_superuser or user_has(a, "admin", "can_edit")):
                continue
            if a.location_id and u.location_id and a.location_id != u.location_id:
                continue
            admins.append({"name": display_name(a), "email": a.email,
                           "covers": a.location.name if a.location_id else "All locations"})
        coords = [c for c in coordinators_for(u.location_id) if c.is_followup_coordinator and c.pk != u.pk]
        return Response({
            "administrators": admins[:6],
            "coordinators": [{"name": display_name(c), "email": c.email,
                              "covers": c.coordinates_location.name if c.coordinates_location_id else "All locations"}
                             for c in coords],
        })
