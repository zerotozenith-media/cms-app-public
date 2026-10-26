"""
The morning and weekly alerts. Run from the hourly scheduled job that is
already in place, so no new schedule is needed. Each goes once a day or once
a week per person, however often the job runs, and only after its time.
"""
import datetime

from django.utils import timezone

from accounts.names import display_name

MORNING = datetime.time(7, 0)      # Bahrain time
WEEKLY = datetime.time(7, 30)      # Mondays


def _first_name(user):
    return (user.first_name or display_name(user).split(" ")[0] or "").strip()


def morning(now=None):
    """What is waiting for each person today, the same list as their bell.
    Sent only when something is waiting."""
    from accounts.models import User
    from core.outstanding import outstanding
    from .models import AlertSettings
    from .push import send
    now = timezone.localtime(now or timezone.now())
    from core.followup_rules import rules
    if now.time() < rules().morning_alert_time:
        return 0
    today = now.date()
    sent = 0
    for u in User.objects.filter(is_active=True, push_subscriptions__isnull=False).distinct().select_related("role"):
        st = AlertSettings.for_user(u)
        if st.last_morning == today:
            continue
        st.last_morning = today
        st.save(update_fields=["last_morning"])
        if not st.morning:
            continue
        items = outstanding(u)
        if not items:
            continue
        labels = [i["label"] for i in items]
        body = (", ".join(labels[:-1]) + " and " + labels[-1]) if len(labels) > 1 else labels[0]
        body = body[0].upper() + body[1:] + ". Tap to open."
        name = _first_name(u)
        link = items[0]["link"] if len(items) == 1 else "/"
        if send(u, "morning", f"Good morning{', ' + name if name else ''}", body, link, tag="morning"):
            sent += 1
    return sent


def weekly(now=None):
    """Monday morning, how follow-up went last week, for leaders (Admin
    access). The same figures as the weekly leadership email."""
    from accounts.models import User
    from accounts.permissions import user_can_view_module
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    from .models import AlertSettings
    from .push import send
    now = timezone.localtime(now or timezone.now())
    if now.weekday() != 0 or now.time() < WEEKLY:
        return 0
    today = now.date()
    week_ago = today - datetime.timedelta(days=7)
    done = (MemberFollowUpTask.objects.filter(done=True, contact_date__gte=week_ago).count()
            + NewcomerTask.objects.filter(done=True, contact_date__gte=week_ago).count())
    open_m = MemberFollowUpTask.objects.filter(done=False)
    open_n = NewcomerTask.objects.filter(done=False)
    from core.followup_rules import late_q
    overdue = open_m.filter(late_q()).count() + open_n.filter(late_q()).count()
    nobody = open_m.filter(assigned_to__isnull=True).count() + open_n.filter(assigned_to__isnull=True, newcomer__assigned_to__isnull=True).count()
    body = (f"{done} follow-up{'' if done == 1 else 's'} done last week. "
            f"{overdue} overdue, {nobody} with nobody. Tap for the dashboard.")
    sent = 0
    for u in User.objects.filter(is_active=True, push_subscriptions__isnull=False).distinct().select_related("role"):
        if not user_can_view_module(u, "admin"):
            continue
        st = AlertSettings.for_user(u)
        if st.last_weekly == today:
            continue
        st.last_weekly = today
        st.save(update_fields=["last_weekly"])
        if st.weekly and send(u, "weekly", "Your week in follow-up", body, "/", tag="weekly"):
            sent += 1
    return sent


def run(now=None):
    """Both, safely. Returns a line for the scheduled job's output."""
    import logging
    try:
        m, w = morning(now), weekly(now)
    except Exception:
        logging.getLogger(__name__).exception("Morning or weekly alerts failed")
        return "Alerts: could not be sent, see the log."
    return f"Alerts: {m} morning, {w} weekly."
