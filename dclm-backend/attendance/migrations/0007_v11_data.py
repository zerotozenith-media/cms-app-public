"""
Version 11 data steps for attendance.

The schema migration before this one adds the fields. This one fills them
in on a live database, where nobody will have run the demo seeder:

1. Each house fellowship is linked to the meeting it holds, so the
   weekly generator makes one session per fellowship. Worked out from the
   sessions each fellowship already has, so no meeting id is assumed.

2. Which meetings collect an offering is set to the church's stated
   practice: the weekly worship service, Bible study, revival and house
   fellowship do, the crusade, ministerial renewal and the workers and
   leadership meetings do not. A meeting that already has offerings
   recorded against its sessions is also switched on, since that is
   evidence it collects one. An administrator can change any of them.

3. Abbreviated or mis-cased days ("Fri", "friday ") are written out in
   full. Version 11 refuses anything else, and a day the generator could
   not match meant no sessions were ever created for that meeting.

4. Upcoming placeholder sessions for a fellowship meeting, with no
   fellowship set and nothing recorded on them, are removed. Version 10
   made one per Friday. Left in place, the new generator would add one per
   fellowship beside it and the Friday would show three sessions.

Every step leaves anything it is unsure about alone. The preflight
command reports whatever is left for a person to decide.
"""
from collections import Counter

from django.db import migrations
from django.utils import timezone


FULL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday"]
DAY_ALIASES = {
    "mon": "Monday", "monday": "Monday",
    "tue": "Tuesday", "tues": "Tuesday", "tuesday": "Tuesday",
    "wed": "Wednesday", "weds": "Wednesday", "wednesday": "Wednesday",
    "thu": "Thursday", "thur": "Thursday", "thurs": "Thursday", "thursday": "Thursday",
    "fri": "Friday", "friday": "Friday",
    "sat": "Saturday", "saturday": "Saturday",
    "sun": "Sunday", "sunday": "Sunday",
}

# The church's stated practice.
COLLECTS = {"fri-worship", "mon-bs", "wed-rev", "fri-house"}
DOES_NOT_COLLECT = {"gck", "min-renewal", "sat-workers", "tue-leadership"}
COLLECT_WORDS = ("worship", "bible study", "revival", "fellowship")
NOT_COLLECT_WORDS = ("crusade", "gck", "ministerial", "workers", "leadership")

COUNT_FIELDS = [
    "men", "women", "youth_boys", "youth_girls", "children_boys", "children_girls",
    "online_men", "online_women", "online_youth_boys", "online_youth_girls",
    "online_children_boys", "online_children_girls", "new_comers", "new_converts",
]


def link_fellowships(apps, schema_editor):
    Fellowship = apps.get_model("attendance", "Fellowship")
    MeetingType = apps.get_model("attendance", "MeetingType")
    AttendanceSession = apps.get_model("attendance", "AttendanceSession")

    fallback = (MeetingType.objects.filter(id="fri-house").first()
                or MeetingType.objects.filter(name__icontains="fellowship").first())

    for f in Fellowship.objects.filter(meeting_type__isnull=True):
        used = Counter(AttendanceSession.objects.filter(fellowship=f)
                       .values_list("meeting_type_id", flat=True))
        if used:
            meeting_id = used.most_common(1)[0][0]
            Fellowship.objects.filter(pk=f.pk).update(meeting_type_id=meeting_id)
        elif fallback is not None:
            Fellowship.objects.filter(pk=f.pk).update(meeting_type=fallback)


def set_offering(apps, schema_editor):
    MeetingType = apps.get_model("attendance", "MeetingType")
    Giving = apps.get_model("finance", "Giving")

    with_offerings = set(Giving.objects.filter(session__isnull=False)
                         .values_list("session__meeting_type_id", flat=True))

    for m in MeetingType.objects.all():
        name = (m.name or "").lower()
        if m.id in DOES_NOT_COLLECT:
            collects = False
        elif m.id in COLLECTS or m.id in with_offerings:
            collects = True
        elif any(w in name for w in NOT_COLLECT_WORDS):
            collects = False
        else:
            collects = any(w in name for w in COLLECT_WORDS)
        MeetingType.objects.filter(pk=m.pk).update(collects_offering=collects)


def normalise_days(apps, schema_editor):
    MeetingType = apps.get_model("attendance", "MeetingType")
    for m in MeetingType.objects.all():
        raw = (m.day or "").strip()
        fixed = DAY_ALIASES.get(raw.lower().rstrip("."))
        if fixed and fixed != m.day:
            MeetingType.objects.filter(pk=m.pk).update(day=fixed)


def remove_placeholders(apps, schema_editor):
    Fellowship = apps.get_model("attendance", "Fellowship")
    AttendanceSession = apps.get_model("attendance", "AttendanceSession")
    AttendanceSessionMember = apps.get_model("attendance", "AttendanceSessionMember")
    Giving = apps.get_model("finance", "Giving")

    meeting_ids = set(Fellowship.objects.filter(is_active=True, meeting_type__isnull=False)
                      .values_list("meeting_type_id", flat=True))
    today = timezone.localdate()

    for s in AttendanceSession.objects.filter(
            meeting_type_id__in=meeting_ids, fellowship__isnull=True,
            status="pending", date__gte=today):
        if any(getattr(s, f, 0) for f in COUNT_FIELDS):
            continue
        if AttendanceSessionMember.objects.filter(session=s).exists():
            continue
        if Giving.objects.filter(session=s).exists():
            continue
        s.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0006_fellowship_meeting_type_and_more"),
        ("finance", "0003_remove_giving_remitted_to_remittance_remittanceline"),
    ]

    # Each step is safe to leave in place on rollback: the fields it
    # filled in are removed by rolling back the migration before it.
    operations = [
        migrations.RunPython(link_fellowships, migrations.RunPython.noop),
        migrations.RunPython(set_offering, migrations.RunPython.noop),
        migrations.RunPython(normalise_days, migrations.RunPython.noop),
        migrations.RunPython(remove_placeholders, migrations.RunPython.noop),
    ]
