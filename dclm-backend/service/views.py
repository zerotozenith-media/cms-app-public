"""
Server addresses for the service ladder (F21).

Everyone signed in sees the team at their location, with levels and
points, as Kay chose. Only people who follow others up have a standing.
"""
import datetime

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.names import display_name
from core.viewing import scope_location_id

from . import engine
from .models import ServiceStanding

NOTE_DAYS = 7  # a "moved up" note shows for a week, unless dismissed


def initials(name):
    parts = [p for p in name.split() if p]
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper() if parts else "?"


def describe(user, today=None):
    today = today or timezone.localdate()
    s, total, got = engine.refresh(user, today)
    name, ref, _ = engine.LEVELS[s.level]
    # Below their level, during the notice: the steps that keep it. Otherwise
    # the steps to the next level.
    keeping = engine.level_for(total) < s.level
    need, steps = engine.next_steps(total, s.level - 1 if keeping else s.level)
    note = None
    if s.grace_until and s.grace_until > today:
        days = (s.grace_until - today).days
        note = {"kind": "notice", "text": f"You have {days} days to keep {name}. "
                + (" and ".join(f"{n} {t}" for n, t in steps) + " will hold your place." if steps else "")}
    elif s.moved_up_on and (today - s.moved_up_on).days < NOTE_DAYS:
        note = {"kind": "moved_up", "text": f"You have moved up to {name}. Keep going steadily."}
    if note and s.note_dismissed_on and s.note_dismissed_on >= (s.moved_up_on if note["kind"] == "moved_up" else s.grace_until - datetime.timedelta(days=engine.GRACE_DAYS)):
        note = None
    nxt = engine.LEVELS[s.level + 1][0] if s.level + 1 < len(engine.LEVELS) else None
    return {
        "eligible": True, "level": s.level, "level_name": name, "scripture": ref, "points": total,
        "next_level_name": nxt, "keeping": keeping, "points_needed": need,
        "steps": [{"count": n, "text": t} for n, t in steps], "breakdown": got,
        "grace_until": s.grace_until.isoformat() if s.grace_until else None, "note": note,
        "levels": [{"name": n, "scripture": r, "from": low} for n, r, low in engine.LEVELS],
    }


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user not in engine.eligible_users():
            return Response({"eligible": False})
        return Response(describe(request.user))


class DismissNoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ServiceStanding.objects.filter(user=request.user).update(note_dismissed_on=timezone.localdate())
        return Response({"ok": True})


class TeamView(APIView):
    """Everyone who follows people up at the viewer's location, by level then by name."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        loc = scope_location_id(request.user)
        rows = []
        for u in engine.eligible_users(loc):
            s, total, _ = engine.refresh(u)
            name = display_name(u)
            rows.append({"id": u.id, "name": name, "initials": initials(name), "level": s.level,
                         "level_name": engine.LEVELS[s.level][0], "points": total, "is_me": u.id == request.user.id})
        rows.sort(key=lambda r: (-r["level"], r["name"].lower()))
        return Response({"location": loc, "results": rows})
