"""
The follow-up engine (F19, F20): which message each person is due today,
and the moves between journeys.

Messages are sent by people from their own WhatsApp, so "due" means the
system offers it and records what the sender did: sent, replied
personally, sent their own, or skipped.
"""
from django.db import transaction
from django.utils import timezone

from .models import Enrolment, MessageLog, MessageTemplate, PlanStep

BELONGING_EVERY = 3  # from their third visit, newcomers get a Belonging message every third day


def plan_day(enrolment, today=None):
    today = today or timezone.localdate()
    return max(1, (today - enrolment.started).days + 1 - enrolment.shift)


def visits(newcomer):
    """Services a newcomer has been checked in at."""
    from attendance.models import AttendanceSessionMember
    return AttendanceSessionMember.objects.filter(newcomer=newcomer).values("session").distinct().count()


def in_belonging(enrolment):
    return enrolment.journey == "newcomers" and enrolment.newcomer_id and visits(enrolment.newcomer) >= 3


def _journey_bank(journey):
    return list(MessageTemplate.objects.filter(journey=journey, active=True).order_by("id"))


def due_template(enrolment, day):
    """The planned message for this day, or None when nothing is planned."""
    if in_belonging(enrolment):
        if day % BELONGING_EVERY:
            return None
        pool = list(MessageTemplate.objects.filter(journey="newcomers", theme="Belonging", active=True).order_by("number"))
        return pool[(day // BELONGING_EVERY - 1) % len(pool)] if pool else None
    if enrolment.plan == Enrolment.Plan.DAILY:
        pool = _journey_bank(enrolment.journey)
        return pool[(day - 1) % len(pool)] if pool else None
    step = PlanStep.objects.filter(journey=enrolment.journey, day=day).select_related("template").first()
    return step.template if step and step.template.active else None


def owner(enrolment):
    """Who follows this person up: their shepherd, or whoever has the enquiry."""
    return getattr(enrolment.person, "assigned_to", None)


def location_id(enrolment):
    return getattr(enrolment.person, "location_id", None)


def next_service(location_id_, now=None):
    """The next service at their location, in words, for [Next service].
    A service that has already started today is skipped, and today or
    tomorrow are said as such."""
    import datetime
    from attendance.models import AttendanceSession
    now = now or timezone.localtime()
    today = now.date()
    qs = AttendanceSession.objects.filter(date__gte=today, fellowship__isnull=True).select_related("meeting_type").order_by("date", "id")
    if location_id_:
        qs = qs.filter(location_id=location_id_)
    for s in list(qs.filter(meeting_type__detail_level="detailed")[:10]) or list(qs[:10]):
        t = getattr(s.meeting_type, "start_time", None)
        if s.date == today and (t is None or t <= now.time()):
            continue
        day = "today" if s.date == today else "tomorrow" if s.date == today + datetime.timedelta(days=1) else s.date.strftime("%A %-d %B")
        if t:
            day += " at " + t.strftime("%-I:%M %p").lower().replace(":00", "")
        return day
    return "our next service"


@transaction.atomic
def start(journey, *, newcomer=None, member=None, enquiry=None, today=None, note=""):
    """Start a journey, ending any other active one for the same person, so
    nobody is on two journeys and gets two messages in a day."""
    today = today or timezone.localdate()
    active = Enrolment.objects.filter(status=Enrolment.Status.ACTIVE)
    mine = active.none()
    if newcomer is not None:
        mine = mine | active.filter(newcomer=newcomer)
        conv = getattr(newcomer, "became_member", None)
        if conv is not None:
            mine = mine | active.filter(member=conv)
    if member is not None:
        mine = mine | active.filter(member=member)
        if member.from_newcomer_id:
            mine = mine | active.filter(newcomer_id=member.from_newcomer_id)
    if enquiry is not None:
        mine = mine | active.filter(enquiry=enquiry)
    if mine.filter(journey=journey).exists():
        return mine.filter(journey=journey).first()
    for e in mine:
        end(e, f"Moved to {dict(Enrolment._meta.get_field('journey').choices)[journey]}. {note}".strip(), moved=True, today=today)
    return Enrolment.objects.create(journey=journey, newcomer=newcomer, member=member, enquiry=enquiry, started=today)


def end(enrolment, reason, moved=False, today=None):
    if enrolment.status != Enrolment.Status.ACTIVE:
        return
    enrolment.status = Enrolment.Status.MOVED if moved else Enrolment.Status.ENDED
    enrolment.ended_on = today or timezone.localdate()
    enrolment.ended_reason = reason[:200]
    enrolment.save(update_fields=["status", "ended_on", "ended_reason"])


def record(enrolment, kind, user, text="", template=None, today=None):
    """What the sender did today. A personal reply takes today's place, so
    the planned message moves to tomorrow. The final gentle message ends
    the plan."""
    today = today or timezone.localdate()
    day = plan_day(enrolment, today)
    log = MessageLog.objects.create(
        enrolment=enrolment, day=day, kind=kind, template=template,
        theme=(template.theme if template else ("Personal reply" if kind == MessageLog.Kind.REPLY else "")),
        text=text, sent_by=user, on_date=today)
    if kind == MessageLog.Kind.REPLY:
        enrolment.shift += 1
        enrolment.save(update_fields=["shift"])
    if kind == MessageLog.Kind.PLANNED and template and template.theme == "Final gentle message":
        end(enrolment, "Plan completed with the final gentle message", today=today)
    return log


def todays_entry(enrolment, today=None):
    """What the Today's messages card needs for one person."""
    today = today or timezone.localdate()
    day = plan_day(enrolment, today)
    done = enrolment.log.filter(on_date=today).first()
    if enrolment.status != Enrolment.Status.ACTIVE and not done:
        return None
    tpl = due_template(enrolment, day) if not done or done.template_id is None else done.template
    if not tpl and not done:
        return None
    p = enrolment.person
    name = getattr(p, "full_name", None) or p.name
    return {
        "enrolment": enrolment.id, "journey": enrolment.journey, "journey_label": enrolment.get_journey_display(),
        "day": day, "plan": enrolment.plan, "belonging": bool(in_belonging(enrolment)),
        "person": {"name": name, "first": (getattr(p, "first_name", "") or name.split()[0]), "phone": p.phone or "",
                   "kind": "member" if enrolment.member_id else "newcomer" if enrolment.newcomer_id else "enquiry", "id": p.id},
        "template": None if not tpl else {"id": tpl.id, "theme": tpl.theme, "verse": tpl.verse, "reference": tpl.reference, "body": tpl.body,
                                          "final": tpl.theme == "Final gentle message"},
        "next_service": next_service(location_id(enrolment)),
        "done": None if not done else {"kind": done.kind, "text": done.text},
    }
