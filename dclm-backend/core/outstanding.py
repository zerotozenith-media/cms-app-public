# The bell and the "Needs your attention" card (F4, F5, F6). Kept apart from
# core/notifications.py, which sends email and was overwritten by mistake.
"""
What needs someone's attention (F4): the bell on every page, and in batch 4
the dashboard's "Needs your attention" card, from this one list so the two
never disagree.

Each item is counted only for people whose role can open that list, and
limited to the location they are viewing. Overdue items are red, items that
are only waiting are amber.
"""
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import user_has
from core.viewing import scope_location_id


def _plural(n, one, many):
    return one if n == 1 else many


def oversees(user):
    """Administrators and coordinators see everyone's follow-ups at their
    location. Everyone else, such as the Follow-up role, sees their own
    (F6): a worker with nothing overdue was told "12 follow-ups are overdue"
    about other people's."""
    return user_has(user, "admin", "can_view")


def outstanding(user):
    from attendance.models import AttendanceSession
    from enquiries.models import Enquiry
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask

    today = timezone.localdate()
    loc = scope_location_id(user)
    mine_all = oversees(user)
    items = []

    if user_has(user, "newcomers", "can_view"):
        qs = NewcomerTask.objects.filter(done=False, due_date__lt=today)
        if loc:
            qs = qs.filter(newcomer__location_id=loc)
        if not mine_all:
            qs = qs.filter(assigned_to=user)
        n = qs.count()
        if n:
            whose = "" if mine_all else "of your "
            items.append({"key": "newcomer-follow-ups", "count": n, "level": "overdue",
                          "label": f"{n} {whose}newcomer {_plural(n, 'follow-up', 'follow-ups')} overdue",
                          "link": "/newcomers/follow-up"})
    if user_has(user, "members", "can_view"):
        qs = MemberFollowUpTask.objects.filter(done=False, due_date__lt=today)
        if loc:
            qs = qs.filter(member__location_id=loc)
        if not mine_all:
            qs = qs.filter(assigned_to=user)
        n = qs.count()
        if n:
            whose = "" if mine_all else "of your "
            items.append({"key": "member-follow-ups", "count": n, "level": "overdue",
                          "label": f"{n} {whose}member {_plural(n, 'follow-up', 'follow-ups')} overdue",
                          "link": "/members?tab=follow-up"})
    if user_has(user, "newcomers", "can_edit"):
        # Enquiries belong to no location until the person attends.
        n = Enquiry.objects.filter(stage="new").count()
        if n:
            items.append({"key": "enquiries", "count": n, "level": "waiting",
                          "label": f"{n} {_plural(n, 'enquiry', 'enquiries')} waiting for a reply",
                          "link": "/enquiries"})
    # Only for people who can fill sessions in. Telling someone who can only
    # view attendance about sessions left them with a job they could not do.
    if user_has(user, "attendance", "can_edit"):
        qs = AttendanceSession.objects.filter(status="pending", date__lte=today)
        if loc:
            qs = qs.filter(location_id=loc)
        n = qs.count()
        if n:
            items.append({"key": "sessions", "count": n, "level": "waiting",
                          "label": f"{n} {_plural(n, 'session', 'sessions')} not filled in",
                          "link": "/attendance?status=pending"})
    # F19: follow-up messages still to send today.
    if user_has(user, "newcomers", "can_view"):
        from followup.views import due_today
        n = sum(1 for _, entry in due_today(user) if not entry["done"])
        if n:
            items.append({"key": "followup-messages", "count": n, "level": "waiting",
                          "label": f"{n} follow-up {_plural(n, 'message', 'messages')} to send today",
                          "link": "/newcomers/messages"})
    return items


class NotificationSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = outstanding(request.user)
        level = ("overdue" if any(i["level"] == "overdue" for i in items)
                 else "waiting" if items else None)
        return Response({"items": items, "total": sum(i["count"] for i in items), "level": level})



def follow_up_people(user, limit=6):
    """The people behind the follow-ups, most overdue first, members and
    newcomers together (F14): the dashboard showed only counts, three times
    over. Their own for people who do not oversee (F6)."""
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    today = timezone.localdate()
    loc = scope_location_id(user)
    mine_all = oversees(user)
    rows = []
    if user_has(user, "newcomers", "can_view"):
        qs = NewcomerTask.objects.filter(done=False).select_related("newcomer")
        if loc:
            qs = qs.filter(newcomer__location_id=loc)
        if not mine_all:
            qs = qs.filter(assigned_to=user)
        rows += [{"name": t.newcomer.name, "task": t.text, "due_date": t.due_date,
                  "link": f"/newcomers/{t.newcomer_id}"} for t in qs.order_by("due_date")[:limit]]
    if user_has(user, "members", "can_view"):
        qs = MemberFollowUpTask.objects.filter(done=False).select_related("member")
        if loc:
            qs = qs.filter(member__location_id=loc)
        if not mine_all:
            qs = qs.filter(assigned_to=user)
        rows += [{"name": t.member.full_name, "task": t.text, "due_date": t.due_date,
                  "link": f"/members/{t.member_id}"} for t in qs.order_by("due_date")[:limit]]
    rows.sort(key=lambda r: r["due_date"])
    for r in rows[:limit]:
        r["days_overdue"] = max(0, (today - r["due_date"]).days)
        r["due_date"] = r["due_date"].isoformat()
    return rows[:limit]
