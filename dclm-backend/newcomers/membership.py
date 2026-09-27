"""
When a newcomer is ready to be proposed for membership.

Two conditions, both required:
  - the Salvation milestone is recorded, and
  - they attended at least half the Friday Worship services held since
    their first attendance, over a six month window

The system only ever proposes. An administrator confirms, and can add
anyone at any time regardless, which covers someone relocating from
another church where they were already established.

Proposed rather than automatic because membership is a decision a person
makes about another person, not a threshold crossed quietly by software.
"""
import datetime

from django.utils import timezone

MIN_PERCENT = 50
WINDOW_MONTHS = 6
MAIN_SERVICE_ID = "fri-worship"
SALVATION = "Salvation"


def _months_between(start, end):
    return (end.year - start.year) * 12 + (end.month - start.month)


def readiness(newcomer, today=None):
    """
    Everything needed to show an administrator why someone is, or is not,
    proposed. Showing the working matters more than the verdict: a bare
    "not ready" invites exactly the question this answers.
    """
    from attendance.models import AttendanceSession, AttendanceSessionMember

    today = today or timezone.localdate()

    attendances = (AttendanceSessionMember.objects
                   .filter(newcomer=newcomer,
                           session__meeting_type_id=MAIN_SERVICE_ID)
                   .select_related("session")
                   .order_by("session__date"))
    dates = sorted({a.session.date for a in attendances})
    first_attended = dates[0] if dates else None

    if first_attended:
        # Services held at their own location, counted by date. Counting
        # every location's service made each Friday count several times, so
        # somebody who came every week scored 50% with two locations and
        # could never qualify with three.
        held_qs = AttendanceSession.objects.filter(
            meeting_type_id=MAIN_SERVICE_ID,
            date__gte=first_attended, date__lte=today,
        )
        if newcomer.location_id:
            held_qs = held_qs.filter(location_id=newcomer.location_id)
        # A Friday they attended elsewhere counts too, as a service they had.
        held = len(set(held_qs.values_list("date", flat=True)) | set(dates))
        attended = len(dates)
        months = _months_between(first_attended, today)
    else:
        held = attended = months = 0

    percent = round(attended / held * 100) if held else 0
    # A milestone counts only once it has a date. A row with no date is
    # the checklist item existing, not the thing having happened.
    saved = newcomer.milestones.filter(
        milestone_type__name=SALVATION, achieved_date__isnull=False,
    ).exists()

    attendance_met = percent >= MIN_PERCENT
    time_met = months >= WINDOW_MONTHS

    return {
        "first_attended": first_attended,
        "services_held": held,
        "services_attended": attended,
        "attendance_percent": percent,
        "months_attending": months,
        "has_salvation": saved,
        "attendance_met": attendance_met,
        "time_met": time_met,
        "ready": saved and attendance_met and time_met,
        "min_percent": MIN_PERCENT,
        "window_months": WINDOW_MONTHS,
    }
