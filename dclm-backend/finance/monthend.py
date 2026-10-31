"""
Month-end balance rules (Kay, 30 October 2026). See monthend_models.py.

Every refusal says why and what to do, in words a church treasurer uses.
"""
import calendar
import datetime
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

ZERO = Decimal("0")


def first(d):
    return d.replace(day=1)


def last_day(m):
    return m.replace(day=calendar.monthrange(m.year, m.month)[1])


def prev_month(m):
    return first(m - datetime.timedelta(days=1))


def next_month(m):
    return last_day(m) + datetime.timedelta(days=1)


def label(m):
    return f"{m:%B %Y}"


def settings_for(location):
    from .monthend_models import MoneySettings
    s, _ = MoneySettings.objects.get_or_create(location=location)
    return s


def record(location, month):
    from .monthend_models import MonthEnd
    return MonthEnd.objects.filter(location=location, month=first(month)).first()


def is_locked(location, d):
    """Closed, or sent and waiting for approval."""
    from .monthend_models import MonthEnd
    if not location or not d:
        return None
    return MonthEnd.objects.filter(location=location, month=first(d),
                                   status__in=[MonthEnd.Status.SENT, MonthEnd.Status.CLOSED]).first()


def refuse_if_locked(location, d, what="this"):
    """Refuses a change to giving, an expense, a remittance or an offering
    dated in a month that is closed, or sent and waiting for approval."""
    me = is_locked(location, d)
    if not me:
        return
    from .monthend_models import MonthEnd
    m = label(me.month)
    if me.status == MonthEnd.Status.CLOSED:
        raise ValidationError({"detail": f"{m} is closed for {location.name}, so {what} dated in {me.month:%B} "
                                         f"cannot be added, changed or deleted. Use a date in a month still open, "
                                         f"or ask an administrator to reopen {me.month:%B} in Giving & Finance, "
                                         f"Month-end balance."})
    raise ValidationError({"detail": f"{m} has been sent for approval for {location.name}, so {what} dated in "
                                     f"{me.month:%B} cannot be added, changed or deleted. The approver can send "
                                     f"it back if something needs correcting."})


def figures(location, month):
    """The month's figures from the records, as they stand now."""
    from .models import Expense, Giving
    from .remittance_models import Remittance
    from .monthend_models import MonthEnd
    month = first(month)
    s = settings_for(location)
    end = last_day(month)
    giving = Giving.objects.filter(location=location, date__gte=month, date__lte=end) \
        .aggregate(t=Sum("amount"))["t"] or ZERO
    giving_n = Giving.objects.filter(location=location, date__gte=month, date__lte=end).count()
    expenses = Expense.objects.filter(location=location, date__gte=month, date__lte=end) \
        .aggregate(t=Sum("amount"))["t"] or ZERO
    expenses_n = Expense.objects.filter(location=location, date__gte=month, date__lte=end).count()
    # Money leaves when it is sent, so a remittance counts in the month of
    # its sent date, whichever month's money it was.
    rems = list(Remittance.objects.filter(location=location, sent_on__gte=month, sent_on__lte=end)
                .prefetch_related("lines"))
    remittance = sum((r.total_sent for r in rems), ZERO)
    if month == first(s.start_month):
        opening, opening_from = s.opening_balance, "start"
    else:
        prev = MonthEnd.objects.filter(location=location, month=prev_month(month),
                                       status=MonthEnd.Status.CLOSED).first()
        opening = prev.counted_amount if prev else None
        opening_from = "previous" if prev else "missing"
    q = Decimal("0.001")
    giving, expenses, remittance = Decimal(giving).quantize(q), Decimal(expenses).quantize(q), Decimal(remittance).quantize(q)
    expected = None if opening is None else (opening + giving - expenses - remittance).quantize(q)
    return {
        "opening": opening, "opening_from": opening_from,
        "giving": giving, "giving_count": giving_n,
        "expenses": expenses, "expenses_count": expenses_n,
        "remittance": remittance,
        "remittances": [{"month": label(r.month), "sent_on": r.sent_on.isoformat(), "amount": r.total_sent}
                        for r in rems],
        "expected": expected,
    }


def months(location):
    """Every month from the start month to the current month, newest first."""
    s = settings_for(location)
    m, today = first(s.start_month), timezone.localdate()
    out = []
    while m <= first(today):
        out.append(m)
        m = next_month(m)
    return list(reversed(out))


def check_can_send(location, month, user):
    s = settings_for(location)
    month = first(month)
    if month < first(s.start_month):
        raise ValidationError({"detail": f"Balancing starts in {label(s.start_month)} for {location.name}, so "
                                         f"{label(month)} is not balanced. An administrator sets the start month "
                                         f"in Admin, Config Lists, Money."})
    if timezone.localdate() < last_day(month):
        raise ValidationError({"detail": f"{label(month)} has not ended yet. It can be balanced from "
                                         f"{last_day(month):%-d %B}, its last day."})
    if month != first(s.start_month):
        from .monthend_models import MonthEnd
        prev = MonthEnd.objects.filter(location=location, month=prev_month(month)).first()
        if not prev or prev.status != MonthEnd.Status.CLOSED:
            raise ValidationError({"detail": f"{label(prev_month(month))} is not closed yet, and its closing "
                                             f"balance is {label(month)}'s opening balance. Close "
                                             f"{label(prev_month(month))} first."})
