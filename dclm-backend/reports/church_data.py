"""
The figures behind the overseer report and the zonal monthly report, for
any run of whole months, for one location or the whole church.

Everything here is read from what the church has recorded. Nothing is
estimated: a figure the system does not hold is left out, not guessed.
"""
import calendar
import datetime
from collections import OrderedDict, defaultdict
from decimal import Decimal

from django.db.models import Sum

FRIDAY = "fri-worship"
ZERO = Decimal("0")


def whole(x):
    """People are counted in whole numbers, and half rounds up the way
    someone checking by hand expects (Python's round() would give 30 for
    30.5)."""
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def month_list(start, end):
    """[(year, month), ...] from start to end, both (year, month)."""
    out, (y, m) = [], start
    while (y, m) <= end:
        out.append((y, m))
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    return out


def bounds(y, m):
    return datetime.date(y, m, 1), datetime.date(y, m, calendar.monthrange(y, m)[1])


def month_name(y, m):
    return f"{calendar.month_name[m]} {y}"


def period_words(months):
    """Title word, the noun used in sentences, and the period label."""
    n = len(months)
    (y1, m1), (y2, m2) = months[0], months[-1]
    if n == 1:
        label = month_name(y1, m1)
    elif n == 12 and m1 == 1:
        label = str(y1)
    elif y1 == y2:
        label = f"{calendar.month_name[m1]} to {calendar.month_name[m2]} {y2}"
    else:
        label = f"{month_name(y1, m1)} to {month_name(y2, m2)}"
    kind, noun = {1: ("Monthly", "month"), 3: ("Quarterly", "quarter"),
                  6: ("Half-Year", "half-year"), 12: ("Annual", "year")}.get(n, ("", "period"))
    return kind, noun, label


def short_meeting(name):
    """'Global Crusade with Kumuyi (GCK)' -> 'GCK'."""
    if name.endswith(")") and "(" in name:
        return name[name.rindex("(") + 1:-1]
    return name


def day(d):
    return f"{d.day} {d.strftime('%b')}"


def date_range_words(dates):
    a, b = dates[0], dates[-1]
    if a == b:
        return f"{a.day} {calendar.month_name[a.month]}"
    if a.month == b.month:
        return f"{a.day} to {b.day} {calendar.month_name[b.month]}"
    return f"{a.day} {calendar.month_name[a.month]} to {b.day} {calendar.month_name[b.month]}"


def male(s):
    return s.men + s.youth_boys + s.children_boys + s.online_men + s.online_youth_boys + s.online_children_boys


def female(s):
    return s.women + s.youth_girls + s.children_girls + s.online_women + s.online_youth_girls + s.online_children_girls


def groups(s):
    """Headcount by group, in the room and online together."""
    return {
        "men": s.men + s.online_men, "women": s.women + s.online_women,
        "youth_boys": s.youth_boys + s.online_youth_boys, "youth_girls": s.youth_girls + s.online_youth_girls,
        "children_boys": s.children_boys + s.online_children_boys,
        "children_girls": s.children_girls + s.online_children_girls,
    }


class Scope:
    """One location, or the whole church when location is None."""

    def __init__(self, location=None):
        self.location = location

    def __call__(self, qs, field="location"):
        return qs.filter(**{field: self.location}) if self.location else qs

    @property
    def label(self):
        return f"{self.location.name} only" if self.location else "All locations"


def sessions_in(scope, start, end):
    from attendance.models import AttendanceSession
    return list(scope(AttendanceSession.objects.filter(status="filled", date__gte=start, date__lte=end))
                .select_related("meeting_type", "location", "fellowship")
                .prefetch_related("giving__fund").order_by("date", "meeting_type__name", "id"))


def session_name(s):
    return f"{s.meeting_type.name} ({s.fellowship.name})" if s.fellowship_id else s.meeting_type.name


def is_weekly_service(mt):
    return mt.frequency == "weekly" and mt.audience == "everyone"


def is_workers(mt):
    return mt.frequency == "weekly" and mt.audience in ("workers", "leadership")


def is_special(mt):
    return mt.frequency == "occasional"


# --------------------------------------------------------------- months

def month_figures(scope, y, m):
    """One month: services, money, and the rows the zonal report needs."""
    from finance.models import Expense, Giving
    start, end = bounds(y, m)
    sessions = sessions_in(scope, start, end)
    giving = list(scope(Giving.objects.filter(date__gte=start, date__lte=end)).select_related("fund", "session"))
    expenses = scope(Expense.objects.filter(date__gte=start, date__lte=end))
    income = sum((g.amount for g in giving), ZERO)
    spent = expenses.aggregate(t=Sum("amount"))["t"] or ZERO
    by_fund = defaultdict(lambda: ZERO)
    for g in giving:
        by_fund[g.fund.name] += g.amount
    by_category = OrderedDict(
        (r["category__name"], r["t"]) for r in
        expenses.values("category__name").annotate(t=Sum("amount")).order_by("-t", "category__name"))
    fridays = [s for s in sessions if s.meeting_type_id == FRIDAY and not s.fellowship_id]
    return {
        "year": y, "month": m, "name": month_name(y, m), "short": calendar.month_name[m],
        "start": start, "end": end, "sessions": sessions, "giving": giving,
        "income": income, "expenses": spent, "net": income - spent,
        "by_fund": dict(by_fund), "by_category": by_category,
        "fridays": fridays, "friday_total": sum(s.total for s in fridays),
        "newcomer_visits": sum(s.new_comers for s in sessions),
    }


def meeting_averages(months):
    """{meeting name: {(y, m): (average, services)}} for weekly meetings,
    house fellowships counted per fellowship meeting."""
    out = OrderedDict()
    order = []
    for mf in months:
        per = defaultdict(list)
        for s in mf["sessions"]:
            if s.meeting_type.frequency != "weekly":
                continue
            per[s.meeting_type.name].append(s.total)
            if s.meeting_type.name not in order:
                order.append(s.meeting_type.name)
        for name, totals in per.items():
            out.setdefault(name, {})[(mf["year"], mf["month"])] = (whole(sum(totals) / len(totals)), len(totals))
    # Friday Worship first, then the busiest meetings.
    def weight(name):
        vals = out[name].values()
        return (0 if name.startswith("Friday Worship") else 1, -sum(a * n for a, n in vals))
    return OrderedDict((n, out[n]) for n in sorted(out, key=weight))


def special_programmes(sessions):
    """Occasional meetings grouped into programmes: the same meeting and
    edition on dates no more than 2 days apart."""
    runs = []
    for s in sorted((s for s in sessions if is_special(s.meeting_type)), key=lambda s: (s.meeting_type_id, s.edition_name, s.edition_place, s.date)):
        key = (s.meeting_type_id, s.edition_name.strip(), s.edition_place.strip())
        last = runs[-1] if runs else None
        if last and last["key"] == key and (s.date - last["dates"][-1]).days <= 2:
            last["sessions"].append(s)
            if s.date not in last["dates"]:
                last["dates"].append(s.date)
            continue
        runs.append({"key": key, "sessions": [s], "dates": [s.date], "meeting": s.meeting_type.name})
    out = []
    for r in sorted(runs, key=lambda r: (r["meeting"] != "Global Crusade with Kumuyi (GCK)", r["meeting"], r["dates"][0])):
        _, ed, place = r["key"]
        label = short_meeting(r["meeting"])
        if ed:
            label += f', "{ed}"'
        elif place:
            label += f", {place}"
        totals = [s.total for s in r["sessions"]]
        out.append({"label": label, "dates": date_range_words(r["dates"]), "days": len(r["dates"]),
                    "average": whole(sum(totals) / len(totals)), "meeting": r["meeting"]})
    return out


# --------------------------------------------------------------- people

def people_now(scope):
    """Membership as it stands today. These are not kept month by month,
    so the report states the date they were taken."""
    from members.models import Member
    from newcomers.models import Newcomer
    members = scope(Member.objects.all())
    newcomers = scope(Newcomer.objects.filter(stage__in=["new", "contacted", "attending"]))
    out = {
        "members": members.count(),
        "newcomers": newcomers.count(),
        "households": members.exclude(household__isnull=True).values("household").distinct().count(),
        "workers": members.filter(category="Worker").count(),
        "in_training": members.filter(category="Worker in Training").count(),
        "contacts": None,
    }
    out["congregation"] = out["members"] + out["newcomers"]
    if scope.location is None:
        # Online contacts are not tied to a location until they visit.
        from enquiries.followup_people import active_contacts
        out["contacts"] = active_contacts().count()
    return out


def testimonies_in(start, end):
    from reports.models import Testimony
    return [{"date": t.date, "text": t.text.strip()} for t in
            Testimony.objects.filter(date__gte=start, date__lte=end).order_by("date", "id")]


def goals_by_horizon():
    from goals.models import Goal
    out = OrderedDict()
    for h in Goal.Horizon.values:
        rows = [{"name": g.name, "target_date": g.target_date.strip(), "measured_by": g.measured_by.strip()}
                for g in Goal.objects.filter(horizon=h).order_by("id")]
        if rows:
            out[h] = rows
    return out


# --------------------------------------------------------------- whole report

def gather(months, location=None):
    """Everything both reports draw on, for months [(y, m), ...]."""
    scope = Scope(location)
    per_month = [month_figures(scope, y, m) for y, m in months]
    start, end = per_month[0]["start"], per_month[-1]["end"]
    sessions = [s for mf in per_month for s in mf["sessions"]]
    fridays = [s for mf in per_month for s in mf["fridays"]]
    friday_total = sum(s.total for s in fridays)
    income = sum((mf["income"] for mf in per_month), ZERO)
    spent = sum((mf["expenses"] for mf in per_month), ZERO)
    funds = sorted({f for mf in per_month for f in mf["by_fund"]},
                   key=lambda f: -sum((mf["by_fund"].get(f, ZERO) for mf in per_month), ZERO))
    categories = sorted({c for mf in per_month for c in mf["by_category"]},
                        key=lambda c: -sum((mf["by_category"].get(c, ZERO) for mf in per_month), ZERO))
    kind, noun, label = period_words(months)
    return {
        "scope": scope, "months": per_month, "start": start, "end": end,
        "kind_word": kind, "noun": noun, "label": label,
        "sessions": sessions, "fridays": fridays, "friday_total": friday_total,
        "friday_average": whole(friday_total / len(fridays)) if fridays else 0,
        "income": income, "expenses": spent, "net": income - spent,
        "funds": funds, "categories": categories,
        "meetings": meeting_averages(per_month),
        "programmes": special_programmes(sessions),
        "people": people_now(scope),
        "testimonies": testimonies_in(start, end),
        "goals": goals_by_horizon(),
        "newcomer_visits": sum(mf["newcomer_visits"] for mf in per_month),
        "balances": closed_balances(scope, months),
        "taken_on": datetime.date.today(),
    }


def closed_balances(scope, months):
    """Month-end balances approved and closed in these months (Kay, 30
    October 2026), oldest first, so the report shows the money held."""
    from finance.monthend_models import MonthEnd
    firsts = [datetime.date(y, m, 1) for y, m in months]
    qs = scope(MonthEnd.objects.filter(month__in=firsts, status=MonthEnd.Status.CLOSED).select_related("location"))
    return [{"month": me.month, "location": me.location.name, "opening": me.opening, "giving": me.giving,
             "expenses": me.expenses, "remittance": me.remittance, "expected": me.expected,
             "closing": me.counted_amount, "difference": me.difference, "note": me.difference_note}
            for me in qs.order_by("month", "location__name")]
