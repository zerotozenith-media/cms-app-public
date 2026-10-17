"""
When a newcomer is ready to be proposed for membership.

Three conditions, all required:
  - the Salvation milestone is recorded,
  - they attended at least half the Friday Worship services held since
    their first check-in, and
  - they first came at least six months ago (Kay, 16 Oct 2026: counted
    from the First came date, not the first check-in, since Fridays were
    only recorded by name from then)

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
    """Whole months: 1 July to 1 January is six, 31 July to 1 January five."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    return months - 1 if end.day < start.day else months


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
    else:
        held = attended = 0

    # First came: registration or the first check-in, whichever is
    # earlier, the same date the profile shows.
    first_came = newcomer.created_at
    if first_attended and (first_came is None or first_attended < first_came):
        first_came = first_attended
    months = _months_between(first_came, today) if first_came else 0

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
        "first_came": first_came,
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
