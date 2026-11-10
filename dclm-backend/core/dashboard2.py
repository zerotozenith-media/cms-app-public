"""
The dashboard (Dashboard redesign, approved 10 November 2026; layout and
charts as on DCLM Canada).

One request returns everything the page draws for this person: the cards,
the charts, the lists and the summary table. Each part is present only when
the person's role can see the area it comes from. "Needs your attention"
is the bell's list (core/outstanding.py), so the two never disagree.

Kinds of dashboard, from the role:
  leader    Administrator, Location Coordinator and anyone else who can see
            attendance or newcomers and money. Table by location (all
            locations in view) or by meeting (one location).
  accounts  Sees money but not attendance or newcomers (Accounts, Finance
            Approver). Table by month for each location.
  worker    Sees newcomers but not money or Admin (Follow-up). Their own
            follow-ups. No table.

The number of database queries does not grow with the records
(tests_dashboard2.QueryCountTests): every figure is added up by the
database, by month or by location, in one query each.
"""
import datetime
from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import user_can_view_module, user_has
from core import dash_period as dp
from core import settings_store
from core.viewing import scope_location_id

MAIN = "fri-worship"
ZERO = Decimal("0")
PEOPLE = ["men", "women", "youth_boys", "youth_girls", "children_boys", "children_girls",
          "online_men", "online_women", "online_youth_boys", "online_youth_girls",
          "online_children_boys", "online_children_girls"]


def _total_expr():
    from django.db.models import Value
    e = Value(0)
    for f in PEOPLE:
        e = e + F(f)
    return e


def _money(v):
    return str(Decimal(v or 0).quantize(Decimal("0.01")))


def view_kind(user):
    finance = user_can_view_module(user, "finance")
    people = user_can_view_module(user, "attendance") or user_can_view_module(user, "newcomers")
    if finance and not people:
        return "accounts"
    if not finance and not user_has(user, "admin", "can_view"):
        return "worker"
    return "leader"


def _loc_q(loc, field="location_id"):
    return Q(**{field: loc}) if loc else Q()


# ------------------------------------------------------------------ attendance

def attendance_by_date(meeting, start, end, loc=None, by_location=False):
    """{date: total} (or {(location, date): total}) for filled sessions of a
    meeting: every location's session on a date added up, as one service."""
    from attendance.models import AttendanceSession
    keys = ["location_id", "date"] if by_location else ["date"]
    rows = (AttendanceSession.objects.filter(_loc_q(loc), meeting_type_id=meeting, status="filled",
                                             date__gte=start, date__lte=end)
            .values(*keys).annotate(t=Sum(_total_expr())))
    return {(r["location_id"], r["date"]) if by_location else r["date"]: r["t"] or 0 for r in rows}


def average(by_date):
    return round(sum(by_date.values()) / len(by_date)) if by_date else None


def attendance_months(meeting, months, loc, today):
    """[{month, attendance}]: the average per service each month, or None
    when nothing was recorded (drawn as a gap, never as 0)."""
    if not months:
        return []
    by_date = attendance_by_date(meeting, months[0], min(dp.month_end(months[-1]), today), loc)
    sums = defaultdict(list)
    for d, t in by_date.items():
        sums[d.replace(day=1)].append(t)
    return [{"month": m.isoformat()[:7],
             "attendance": round(sum(sums[m]) / len(sums[m])) if sums.get(m) else None}
            for m in months]


# ------------------------------------------------------------------ money

def money_by_month(model, months, loc, field="date", by_location=False):
    """Totals by month, up to today: a month still running is "so far"."""
    if not months:
        return {}
    keys = ["location_id", "m"] if by_location else ["m"]
    end = min(dp.month_end(months[-1]), timezone.localdate())
    rows = (model.objects.filter(_loc_q(loc), **{f"{field}__gte": months[0], f"{field}__lte": end})
            .annotate(m=TruncMonth(field)).values(*keys).annotate(t=Sum("amount")))
    out = {}
    for r in rows:
        m = r["m"].date() if hasattr(r["m"], "date") else r["m"]
        out[(r["location_id"], m) if by_location else m] = r["t"] or ZERO
    return out


def total(model, start, end, loc, by_location=False):
    qs = model.objects.filter(_loc_q(loc), date__gte=start, date__lte=end)
    if by_location:
        return {r["location_id"]: r["t"] or ZERO for r in qs.values("location_id").annotate(t=Sum("amount"))}
    return qs.aggregate(t=Sum("amount"))["t"] or ZERO


def funds(start, end, loc):
    from finance.models import Giving
    rows = [{"fund": r["fund__name"], "amount": float(r["t"])}
            for r in Giving.objects.filter(_loc_q(loc), date__gte=start, date__lte=end)
            .values("fund__name").annotate(t=Sum("amount")).order_by("-t") if r["t"]]
    if len(rows) > 5:
        rest = rows[4:]
        rows = rows[:4] + [{"fund": f"Other, {len(rest)} funds", "amount": sum(r["amount"] for r in rest)}]
    return rows


def expense_categories(start, end, loc):
    from finance.models import Expense
    rows = [{"category": r["category__name"], "amount": float(r["t"])}
            for r in Expense.objects.filter(_loc_q(loc), date__gte=start, date__lte=end)
            .values("category__name").annotate(t=Sum("amount")).order_by("-t") if r["t"]]
    return {"top": rows[:5], "more": max(0, len(rows) - 5)}


def cash_by_month(locations, today):
    """For each location, every month from its balancing start month to this
    month: cash at the start, giving, expenses, remitted, net, cash in hand
    and the month-end status. A closed month's counted cash is the next
    month's start, as on Month-end balance. Fixed number of queries."""
    from finance.models import Expense, Giving
    from finance.monthend_models import MonthEnd, MoneySettings
    from finance.remittance_models import RemittanceLine
    rs = settings_store.records_start()
    sets = {s.location_id: s for s in MoneySettings.objects.filter(location__in=locations)}
    starts = {l.id: max((sets[l.id].start_month.replace(day=1) if l.id in sets else rs), rs) for l in locations}
    if not starts:
        return {}
    first = min(starts.values())
    months = []
    m = first
    while m <= today.replace(day=1):
        months.append(m)
        m = dp.add_months(m, 1)
    ids = [l.id for l in locations]
    giving = money_by_month(Giving, months, None, by_location=True)
    expenses = money_by_month(Expense, months, None, by_location=True)
    rem = defaultdict(lambda: ZERO)
    for r in (RemittanceLine.objects.filter(remittance__location_id__in=ids, remittance__sent_on__gte=first,
                                            remittance__sent_on__lte=today)
              .annotate(m=TruncMonth("remittance__sent_on")).values("remittance__location_id", "m")
              .annotate(t=Sum("amount_sent"))):
        mm = r["m"].date() if hasattr(r["m"], "date") else r["m"]
        rem[(r["remittance__location_id"], mm)] = r["t"] or ZERO
    ends = {(e.location_id, e.month): e for e in MonthEnd.objects.filter(location_id__in=ids, month__gte=first)}
    out = {}
    for l in locations:
        rows, cash = [], None
        for m in months:
            if m < starts[l.id]:
                continue
            if cash is None:
                cash = sets[l.id].opening_balance if l.id in sets else ZERO
            g, x, r = giving.get((l.id, m), ZERO), expenses.get((l.id, m), ZERO), rem[(l.id, m)]
            close = cash + g - x - r
            me = ends.get((l.id, m))
            status = me.status if me else "open"
            if me and me.status == MonthEnd.Status.CLOSED and me.counted_amount is not None:
                close = me.counted_amount
            rows.append({"month": m.isoformat()[:7], "start": _money(cash), "giving": _money(g), "expenses": _money(x),
                         "remitted": _money(r), "net": _money(g - x), "cash": _money(close),
                         "status": status, "status_label": {"open": "Open", "sent": "Waiting for approval",
                                                            "closed": "Closed"}.get(status, "Open"),
                         "so_far": m == today.replace(day=1)})
            cash = close
        out[l.id] = rows
    return out


# ------------------------------------------------------------------ people

def newcomers_by_month(months, loc):
    from newcomers.models import Newcomer
    if not months:
        return []
    rows = (Newcomer.objects.filter(_loc_q(loc), created_at__gte=months[0],
                                    created_at__lte=min(dp.month_end(months[-1]), timezone.localdate()))
            .annotate(m=TruncMonth("created_at")).values("m").annotate(n=Count("id")))
    got = {(r["m"].date() if hasattr(r["m"], "date") else r["m"]): r["n"] for r in rows}
    return [{"month": m.isoformat()[:7], "newcomers": got.get(m, 0)} for m in months]


def pipeline(loc, user=None):
    from newcomers.models import Newcomer
    qs = Newcomer.objects.filter(_loc_q(loc), stage__in=["new", "contacted", "attending"])
    return qs.filter(assigned_to=user) if user else qs


def my_tasks(user, today):
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    out = {"due": 0, "overdue": 0, "today": 0}
    for model in (NewcomerTask, MemberFollowUpTask):
        r = model.objects.filter(assigned_to=user, done=False).aggregate(
            due=Count("id"), overdue=Count("id", filter=Q(due_date__lt=today)), today=Count("id", filter=Q(due_date=today)))
        for k in out:
            out[k] += r[k] or 0
    return out


def fellowships(start, end, loc):
    from attendance.models import AttendanceSession, Fellowship
    from finance.models import Giving
    sessions = AttendanceSession.objects.filter(_loc_q(loc), fellowship__isnull=False, status="filled",
                                                date__gte=start, date__lte=end)
    got = {r["fellowship_id"]: r for r in sessions.values("fellowship_id").annotate(t=Sum(_total_expr()), n=Count("id"))}
    groups = [{"name": f.name, "attendance": (got.get(f.id) or {}).get("t") or 0, "meetings": (got.get(f.id) or {}).get("n") or 0}
              for f in Fellowship.objects.filter(is_active=True).order_by("name")]
    offering = Giving.objects.filter(session__in=sessions).aggregate(t=Sum("amount"))["t"] or ZERO
    return {"groups": groups, "meetings_held": sum(g["meetings"] for g in groups), "offering": _money(offering)}


def new_members(start, end, loc):
    from members.models import Member
    qs = Member.objects.filter(_loc_q(loc), from_newcomer__isnull=False, joined_date__gte=start, joined_date__lte=end)
    return {"count": qs.count(),
            "recent": [{"id": m.id, "name": m.full_name, "joined": m.joined_date.isoformat()}
                       for m in qs.order_by("-joined_date")[:4]]}


def enquiries_waiting(today):
    from enquiries.models import Enquiry
    qs = Enquiry.objects.filter(stage="new").select_related("source").order_by("received_at")
    return {"count": qs.count(),
            "oldest": [{"id": e.id, "name": e.name, "source": e.source.name if e.source_id else "",
                        "days": (today - e.received_at).days} for e in qs[:3]]}


def goals():
    from goals.calculations import compute_goal_value
    from goals.models import Goal
    out = []
    for g in Goal.objects.filter(horizon=Goal.Horizon.SHORT)[:4]:
        current = g.current if g.tracking == "manual" else (compute_goal_value(g) or 0)
        pct = min(100, round(float(current) / float(g.target) * 100)) if g.target else 0
        out.append({"id": g.id, "name": g.name, "current": float(current), "target": float(g.target), "pct": pct,
                    "status": "achieved" if pct >= 100 else "on_track" if pct >= 60 else "not_started" if pct == 0 else "behind"})
    return out


def testimonies():
    from reports.models import Testimony
    t = Testimony.objects.select_related("service").order_by("-date", "-id").first()
    return {"count": Testimony.objects.count(),
            "latest": None if not t else {"text": t.text, "by": "Anonymous" if t.is_anonymous else (t.member_name or ""),
                                          "service": t.service.name if t.service_id else "", "date": t.date.isoformat()}}


# ------------------------------------------------------------------ tables

def change_pct(now, before):
    if now is None or before in (None, 0):
        return None
    return round((float(now) - float(before)) / abs(float(before)) * 100)


def table_by_location(p, cmp, user, today):
    from attendance.models import AttendanceSession  # noqa: F401
    from core.models import Location
    from finance.models import Expense, Giving
    from finance.monthend_models import MonthEnd
    from newcomers.models import Newcomer
    locations = list(Location.objects.order_by("name"))
    att = user_can_view_module(user, "attendance")
    fin = user_can_view_module(user, "finance")
    nc = user_can_view_module(user, "newcomers")
    now = attendance_by_date(MAIN, p["start"], p["end"], by_location=True) if att else {}
    before = attendance_by_date(MAIN, cmp[0], cmp[1], by_location=True) if att and cmp else {}
    newc = {r["location_id"]: r["n"] for r in Newcomer.objects.filter(created_at__gte=p["start"], created_at__lte=p["end"])
            .values("location_id").annotate(n=Count("id"))} if nc else {}
    g = total(Giving, p["start"], p["end"], None, by_location=True) if fin else {}
    x = total(Expense, p["start"], p["end"], None, by_location=True) if fin else {}
    last = dp.add_months(today.replace(day=1), -1)
    ends = {e.location_id: e for e in MonthEnd.objects.filter(month=last)} if fin else {}

    def avg_for(src, loc_id):
        vals = [t for (l, _), t in src.items() if loc_id is None or l == loc_id]
        if loc_id is None:
            by = defaultdict(int)
            for (l, d), t in src.items():
                by[d] += t
            vals = list(by.values())
        return round(sum(vals) / len(vals)) if vals else None
    rows = []
    for l in locations:
        r = {"id": l.id, "name": l.name}
        if att:
            r["attendance"] = avg_for(now, l.id)
            r["attendance_change"] = change_pct(r["attendance"], avg_for(before, l.id)) if cmp else None
        if nc:
            r["newcomers"] = newc.get(l.id, 0)
        if fin:
            gi, ex = g.get(l.id, ZERO), x.get(l.id, ZERO)
            me = ends.get(l.id)
            r.update(giving=_money(gi), expenses=_money(ex), net=_money(gi - ex),
                     month_end={"sent": "Waiting for approval", "closed": "Closed"}.get(me.status, "Open") if me else "Open")
        rows.append(r)
    tot = {"name": "All locations"}
    if att:
        tot["attendance"] = avg_for(now, None)
        tot["attendance_change"] = change_pct(tot["attendance"], avg_for(before, None)) if cmp else None
    if nc:
        tot["newcomers"] = sum(newc.values())
    if fin:
        gi, ex = sum(g.values(), ZERO), sum(x.values(), ZERO)
        tot.update(giving=_money(gi), expenses=_money(ex), net=_money(gi - ex))
    return {"by": "location", "rows": rows, "total": tot, "month_end_month": last.isoformat()[:7],
            "columns": {"attendance": att, "newcomers": nc, "money": fin}}


def table_by_meeting(p, cmp, loc, user):
    from attendance.models import AttendanceSession, MeetingType
    from finance.models import Giving
    fin = user_can_view_module(user, "finance")
    qs = AttendanceSession.objects.filter(location_id=loc, date__gte=p["start"], date__lte=p["end"])
    held = {r["meeting_type_id"]: r for r in qs.values("meeting_type_id").annotate(
        n=Count("id"), pending=Count("id", filter=~Q(status="filled")))}

    def avgs(start, end):
        rows = (AttendanceSession.objects.filter(location_id=loc, status="filled", date__gte=start, date__lte=end)
                .values("meeting_type_id", "date").annotate(t=Sum(_total_expr())))
        by = defaultdict(list)
        for r in rows:
            by[r["meeting_type_id"]].append(r["t"] or 0)
        return {k: round(sum(v) / len(v)) for k, v in by.items()}
    now = avgs(p["start"], p["end"])
    before = avgs(cmp[0], cmp[1]) if cmp else {}
    off = {r["session__meeting_type_id"]: r["t"] for r in Giving.objects.filter(
        session__location_id=loc, session__date__gte=p["start"], session__date__lte=p["end"])
        .values("session__meeting_type_id").annotate(t=Sum("amount"))} if fin else {}
    rows = []
    for mt in MeetingType.objects.order_by("name"):
        h = held.get(mt.id)
        if not h and mt.id not in before:
            continue
        r = {"id": mt.id, "name": mt.name, "held": h["n"] if h else 0, "not_filled": h["pending"] if h else 0,
             "attendance": now.get(mt.id), "attendance_change": change_pct(now.get(mt.id), before.get(mt.id)) if cmp else None}
        if fin:
            r["offering"] = _money(off.get(mt.id)) if mt.collects_offering else None
        rows.append(r)
    return {"by": "meeting", "rows": rows, "columns": {"money": fin}}


# ------------------------------------------------------------------ the view

def build(user, params, today=None):
    from core.models import Location
    from finance.models import Expense, Giving
    today = today or timezone.localdate()
    p = dp.resolve(params, today)
    cmp = dp.comparison(p)
    loc = scope_location_id(user)
    kind = view_kind(user)
    can = {m: user_can_view_module(user, m) for m in ("attendance", "finance", "newcomers", "goals", "reports", "members")}
    months = dp.chart_months(p)
    location = Location.objects.filter(id=loc).first() if loc else None
    d = {
        "kind": kind, "today": today.isoformat(), "name": user.first_name or "",
        "period": {"key": p["key"], "label": p["label"], "span": p["span"], "start": p["start"].isoformat(),
                   "end": p["end"].isoformat()},
        "compare": {"label": cmp[2], "kind": cmp[3]} if cmp else None,
        "records_start": settings_store.records_start().isoformat()[:7],
        "scope": {"id": location.id, "name": location.name} if location else None,
        "access": can, "cards": {}, "charts": {},
        "receipt_flag_over": _money(settings_store.get("receipt_flag_over")),
    }
    c, ch = d["cards"], d["charts"]

    if can["attendance"]:
        now = attendance_by_date(MAIN, p["start"], p["end"], loc)
        before = attendance_by_date(MAIN, cmp[0], cmp[1], loc) if cmp else {}
        latest = max(now) if now else None
        c["attendance"] = {"value": average(now), "before": average(before) if cmp else None,
                           "latest": {"date": latest.isoformat(), "total": now[latest]} if latest else None}
        meeting = params.get("meeting") or MAIN
        from attendance.models import MeetingType
        mts = list(MeetingType.objects.order_by("name").values("id", "name"))
        if meeting not in {m["id"] for m in mts}:
            meeting = MAIN
        ch["attendance_by_month"] = {"meeting": meeting, "meetings": mts,
                                     "months": attendance_months(meeting, months, loc, today)}

    if can["finance"]:
        g, x = total(Giving, p["start"], p["end"], loc), total(Expense, p["start"], p["end"], loc)
        gb = total(Giving, cmp[0], cmp[1], loc) if cmp else None
        xb = total(Expense, cmp[0], cmp[1], loc) if cmp else None
        c["giving"] = {"value": _money(g), "before": _money(gb) if gb is not None else None}
        c["expenses"] = {"value": _money(x), "before": _money(xb) if xb is not None else None}
        c["net"] = {"value": _money(g - x)}
        gm, xm = money_by_month(Giving, months, loc), money_by_month(Expense, months, loc)
        rs = settings_store.records_start()
        ly_months = [dp.add_months(m, -12) for m in months]
        gl = money_by_month(Giving, [m for m in ly_months if m >= rs], loc) if any(m >= rs for m in ly_months) else {}
        ch["money_by_month"] = [{"month": m.isoformat()[:7], "giving": _money(gm.get(m)), "expenses": _money(xm.get(m)),
                                 "giving_last_year": _money(gl.get(dp.add_months(m, -12))) if dp.add_months(m, -12) >= rs else None,
                                 "so_far": m == today.replace(day=1)} for m in months]
        ch["funds"] = funds(p["start"], p["end"], loc)
        if kind == "accounts":
            ch["expense_categories"] = expense_categories(p["start"], p["end"], loc)
            locs = [location] if location else list(Location.objects.order_by("name"))
            cash = cash_by_month(locs, today)
            c["cash"] = {"value": _money(sum((Decimal(rows[-1]["cash"]) for rows in cash.values() if rows), ZERO)),
                         "by_location": [{"name": l.name, "value": rows[-1]["cash"] if (rows := cash.get(l.id)) else None}
                                         for l in locs]}
            waiting = [{"location": l.name, "month": r["month"]} for l in locs for r in cash.get(l.id, []) if r["status"] == "sent"]
            open_past = [{"location": l.name, "month": r["month"]} for l in locs for r in cash.get(l.id, [])
                         if r["status"] == "open" and not r["so_far"]]
            c["month_end"] = {"waiting": waiting, "open": open_past}
            d["table"] = {"by": "month", "locations": [{"id": l.id, "name": l.name, "rows": list(reversed(cash.get(l.id, [])))}
                                                         for l in locs]}

    if can["newcomers"]:
        ch["newcomers_by_month"] = newcomers_by_month(months, loc)
        from newcomers.membership import readiness_counts
        mine = user if kind == "worker" else None
        c["membership"] = readiness_counts(pipeline(loc, mine), today)
        from newcomers.models import NewcomerTask
        tq = NewcomerTask.objects.filter(done=False, newcomer__in=pipeline(loc))
        d["newcomer_stats"] = {"pipeline": pipeline(loc).count(), "follow_ups_due": tq.count()}
        d["new_members"] = new_members(p["start"], p["end"], loc)
        if user_has(user, "newcomers", "can_edit") or kind != "worker":
            d["enquiries"] = enquiries_waiting(today)
        from core.outstanding import follow_up_people
        d["follow_up_people"] = follow_up_people(user)
        if kind == "worker":
            c["my_tasks"] = my_tasks(user, today)
            c["my_newcomers"] = pipeline(loc, user).count()

    if can["goals"] and kind != "worker":
        d["goals"] = goals()
    if can["reports"] and kind != "accounts":
        d["testimonies"] = testimonies()
    if can["attendance"] and kind == "leader":
        d["fellowships"] = fellowships(p["start"], p["end"], loc)

    if kind == "leader":
        d["table"] = table_by_meeting(p, cmp, loc, user) if loc else table_by_location(p, cmp, user, today)
        if loc:
            d["table"]["location"] = location.name

    d["actions"] = [a for a, ok in (
        ("new_session", user_has(user, "attendance", "can_create")),
        ("add_member", user_has(user, "members", "can_create") and kind != "worker"),
        ("add_newcomer", user_has(user, "newcomers", "can_create")),
        ("add_testimony", user_has(user, "reports", "can_create") and kind == "leader"),
        ("record_giving", user_has(user, "finance", "can_create")),
        ("add_expense", user_has(user, "finance", "can_create") and kind == "accounts"),
        ("month_end", user_can_view_module(user, "monthend") and kind == "accounts"),
    ) if ok]
    return d


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build(request.user, request.query_params))


# ------------------------------------------------------------------ export

def _table_rows(d, location_id=None):
    """(title, headers, rows) of the summary table, as shown."""
    t = d.get("table")
    if not t:
        return None
    cmp = d["compare"]["label"] if d["compare"] else None
    chg = f"Change from {cmp} (%)" if cmp else "Change (%)"

    def pct(v):
        return "" if v is None else v
    if t["by"] == "location":
        cols = t["columns"]
        heads = ["Location"]
        if cols["attendance"]:
            heads += ["Average Friday Worship", chg]
        if cols["newcomers"]:
            heads += ["Newcomers"]
        if cols["money"]:
            heads += ["Giving (BHD)", "Expenses (BHD)", "Net (BHD)", f"Month-end, {t['month_end_month']}"]

        def row(r, last=False):
            out = [r["name"]]
            if cols["attendance"]:
                out += [r["attendance"] if r["attendance"] is not None else "Not recorded", pct(r["attendance_change"])]
            if cols["newcomers"]:
                out += [r["newcomers"]]
            if cols["money"]:
                out += [float(r["giving"]), float(r["expenses"]), float(r["net"]), "" if last else r["month_end"]]
            return out
        return "By location", heads, [row(r) for r in t["rows"]] + [row(t["total"], True)]
    if t["by"] == "meeting":
        heads = ["Meeting", "Held", "Not filled in", "Average attendance", chg]
        if t["columns"]["money"]:
            heads.append("Offering (BHD)")
        rows = []
        for r in t["rows"]:
            out = [r["name"], r["held"], r["not_filled"], r["attendance"] if r["attendance"] is not None else "Not recorded",
                   pct(r["attendance_change"])]
            if t["columns"]["money"]:
                out.append(float(r["offering"]) if r["offering"] is not None else "Not collected")
            rows.append(out)
        return f"By meeting, {t.get('location', '')}", heads, rows
    loc = next((l for l in t["locations"] if l["id"] == location_id), t["locations"][0] if t["locations"] else None)
    if not loc:
        return "By month", ["Month"], []
    heads = ["Month", "Cash at start (BHD)", "Giving (BHD)", "Expenses (BHD)", "Remitted (BHD)", "Net (BHD)",
             "Cash in hand (BHD)", "Month-end"]
    rows = [[r["month"] + (" (so far)" if r["so_far"] else ""), float(r["start"]), float(r["giving"]), float(r["expenses"]),
             float(r["remitted"]), float(r["net"]), float(r["cash"]), r["status_label"]] for r in loc["rows"]]
    return f"By month, {loc['name']}", heads, rows


class DashboardExportView(APIView):
    """The summary table as Excel or PDF, exactly as the dashboard shows it."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import io
        from django.http import HttpResponse
        output = request.query_params.get("output")
        if output not in ("excel", "pdf"):
            return Response({"detail": "Choose excel or pdf."}, status=400)
        d = build(request.user, request.query_params)
        got = _table_rows(d, request.query_params.get("location"))
        if not got:
            return Response({"detail": "This dashboard has no table to export.",
                             "why": "A Follow-up dashboard shows your own follow-ups and has no summary table."}, status=400)
        title, heads, rows = got
        when = d["period"]["span"]
        name = f"DCLM-dashboard-{title.replace(', ', '-').replace(' ', '-')}-{d['period']['start']}"
        if output == "excel":
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill
            wb = Workbook()
            ws = wb.active
            ws.title = "Dashboard"
            ws.append([f"DCLM Bahrain, {title}"])
            ws.append([when + (f". Change compared with {d['compare']['label']}." if d["compare"] else "")])
            ws.append([])
            ws.append(heads)
            for cell in ws[4]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F4E79")
                cell.alignment = Alignment(wrap_text=True, vertical="center")
            for i, r in enumerate(rows):
                ws.append(r)
                if i % 2:
                    for cell in ws[ws.max_row]:
                        cell.fill = PatternFill("solid", fgColor="E8EFF7")
            for row in ws.iter_rows(min_row=5):
                for cell in row:
                    if isinstance(cell.value, float):
                        cell.number_format = "#,##0.00"
            ws["A1"].font = Font(bold=True, size=13)
            for i, _ in enumerate(heads):
                ws.column_dimensions[chr(65 + i)].width = 22 if i else 34
            buf = io.BytesIO()
            wb.save(buf)
            resp = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            resp["Content-Disposition"] = f'attachment; filename="{name}.xlsx"'
            return resp
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36,
                                    title=f"DCLM Bahrain, {title}")
            ss = getSampleStyleSheet()
            ss["Title"].fontName = ss["Normal"].fontName = "Helvetica"
            cell = ss["Normal"].clone("cell", fontSize=8.5, leading=10.5)
            headst = cell.clone("head", textColor=colors.white, fontName="Helvetica-Bold")

            def fmt(v):
                return f"{v:,.2f}" if isinstance(v, float) else str(v)
            data = [[Paragraph(h, headst) for h in heads]] + [[Paragraph(fmt(v), cell) for v in r] for r in rows]
            tbl = Table(data, repeatRows=1)
            style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                     ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D3E0")),
                     ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
            for i in range(1, len(data)):
                if i % 2 == 0:
                    style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#E8EFF7")))
            tbl.setStyle(TableStyle(style))
            sub = when + (f". Change compared with {d['compare']['label']}." if d["compare"] else "")
            doc.build([Paragraph(f"DCLM Bahrain, {title}", ss["Title"]), Paragraph(sub, ss["Normal"]), Spacer(1, 10), tbl])
        except Exception:
            return Response({"detail": "The PDF could not be made.",
                             "why": "Something went wrong while drawing it. Nothing was changed.",
                             "fix": "Try again, or choose Excel instead and tell an administrator."}, status=500)
        resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{name}.pdf"'
        return resp
