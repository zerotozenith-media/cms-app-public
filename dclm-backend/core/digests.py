"""
What the notification emails actually say.

Kept apart from the sending layer and from the commands that trigger
them, so the wording can be reviewed and changed in one place without
touching scheduling or delivery.

Tone follows the rest of the system: plain, specific, and pointing at
the one thing the reader should do next.
"""
from django.conf import settings
from django.utils import timezone


def _app_url(path=""):
    base = getattr(settings, "APP_BASE_URL", "").rstrip("/")
    return f"{base}{path}" if base else ""


def build_shepherd_digest(shepherd_name, tasks, today=None):
    """
    One shepherd's outstanding follow-ups.

    `tasks` is an iterable of MemberFollowUpTask, already filtered to
    that shepherd and to open items. Returns (subject, text, html), or
    None if there is nothing worth sending, since an email saying "you
    have no tasks" trains people to ignore the next one.
    """
    tasks = list(tasks)
    if not tasks:
        return None

    today = today or timezone.localdate()
    overdue = [t for t in tasks if t.due_date < today]
    count = len(tasks)

    if overdue:
        subject = f"{count} follow-up{'s' if count != 1 else ''} waiting, {len(overdue)} overdue"
    else:
        subject = f"{count} follow-up{'s' if count != 1 else ''} waiting"

    lines = [
        f"Hello {shepherd_name},",
        "",
        f"You have {count} follow-up{'s' if count != 1 else ''} to make.",
        "",
    ]
    for t in sorted(tasks, key=lambda x: x.due_date):
        marker = "OVERDUE" if t.due_date < today else f"due {t.due_date}"
        lines.append(f"  {t.member.full_name}, missed {t.missed_meeting_name} on {t.missed_date} ({marker})")

    lines += [
        "",
        "Go in with a goal, share a scripture that fits, find out what is",
        "really keeping them away, and agree a next step before you finish.",
        "",
    ]
    url = _app_url("/members/follow-up")
    if url:
        lines += [f"Open your list: {url}", ""]

    text = "\n".join(lines)

    rows = "".join(
        f"<li><strong>{t.member.full_name}</strong>, missed {t.missed_meeting_name} "
        f"on {t.missed_date} "
        f"({'<span style=\"color:#D6202C\">overdue</span>' if t.due_date < today else f'due {t.due_date}'})</li>"
        for t in sorted(tasks, key=lambda x: x.due_date)
    )
    button = (
        f'<p><a href="{url}" style="background:#0B3C91;color:#fff;padding:10px 16px;'
        f'border-radius:8px;text-decoration:none;display:inline-block">Open your list</a></p>'
        if url else ""
    )
    html = f"""<div style="font-family:system-ui,sans-serif;color:#122;line-height:1.6">
<p>Hello {shepherd_name},</p>
<p>You have <strong>{count}</strong> follow-up{'s' if count != 1 else ''} to make.</p>
<ul>{rows}</ul>
<p style="color:#555">Go in with a goal, share a scripture that fits, find out what is
really keeping them away, and agree a next step before you finish.</p>
{button}
</div>"""

    return subject, text, html


def build_leadership_summary(stats, today=None):
    """
    Church-level weekly picture. Sent even when the numbers are good,
    because "nothing outstanding" is itself worth knowing once a week.
    """
    today = today or timezone.localdate()
    subject = f"Follow-up summary, week of {today}"

    lines = [
        f"Follow-up summary for the week of {today}.",
        "",
        f"  Open follow-ups:  {stats['open']}",
        f"  Overdue:          {stats['overdue']}",
        f"  Unassigned:       {stats['unassigned']}",
        f"  Completed this week: {stats['completed_this_week']}",
        "",
    ]
    if stats["unassigned"]:
        lines += [
            f"{stats['unassigned']} follow-up{'s have' if stats['unassigned'] != 1 else ' has'} nobody assigned.",
            "Those members have no shepherd, so nobody is responsible for them.",
            "",
        ]
    url = _app_url("/members/follow-up")
    if url:
        lines += [f"Open the follow-up list: {url}", ""]

    text = "\n".join(lines)

    warning = (
        f'<p style="color:#D6202C"><strong>{stats["unassigned"]}</strong> follow-up'
        f'{"s have" if stats["unassigned"] != 1 else " has"} nobody assigned. '
        f'Those members have no shepherd, so nobody is responsible for them.</p>'
        if stats["unassigned"] else ""
    )
    button = (
        f'<p><a href="{url}" style="background:#0B3C91;color:#fff;padding:10px 16px;'
        f'border-radius:8px;text-decoration:none;display:inline-block">Open the follow-up list</a></p>'
        if url else ""
    )
    html = f"""<div style="font-family:system-ui,sans-serif;color:#122;line-height:1.6">
<p>Follow-up summary for the week of {today}.</p>
<table cellpadding="6" style="border-collapse:collapse">
<tr><td>Open follow-ups</td><td><strong>{stats['open']}</strong></td></tr>
<tr><td>Overdue</td><td><strong>{stats['overdue']}</strong></td></tr>
<tr><td>Unassigned</td><td><strong>{stats['unassigned']}</strong></td></tr>
<tr><td>Completed this week</td><td><strong>{stats['completed_this_week']}</strong></td></tr>
</table>
{warning}
{button}
</div>"""

    return subject, text, html
