"""
Dashboard summary.

One aggregation endpoint rather than the frontend walking several
paginated lists and summing client-side.

Every section is gated by the viewer's own permission for that module
and carries an explicit "_access": false marker when it is withheld, so
the page can show a restricted state rather than an empty one that
reads as "nothing to show yet". A finance officer sees outstanding
expenses; a follow-up worker does not see giving totals.

One period applies to every section at once, so the cards can never
disagree with each other about which month they describe.
"""
import datetime
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import user_can_view_module
from attendance.models import AttendanceSession, MeetingType
from finance.models import Expense, Giving
from goals.calculations import compute_goal_value
from goals.models import Goal
from newcomers.models import Newcomer, NewcomerTask
from core.viewing import scope_location_id


PERIODS = {"this-month", "last-month", "this-year", "last-year"}


def _location_filter(queryset, user, field="location_id"):
    loc = scope_location_id(user)
    return queryset.filter(**{field: loc}) if loc else queryset


def resolve_period(key, today=None):
    """
    The first day, last day and a readable label for a period.

    Also accepts a bare year such as "2025", so a past year can be
    looked at without a separate control.
    """
    today = today or timezone.localdate()
    first_this = today.replace(day=1)

    if key and key.isdigit() and len(key) == 4:
        y = int(key)
        return datetime.date(y, 1, 1), datetime.date(y, 12, 31), str(y)
    if key == "last-month":
        end = first_this - datetime.timedelta(days=1)
        return end.replace(day=1), end, end.strftime("%B %Y")
    if key == "this-year":
        return (datetime.date(today.year, 1, 1), today, f"{today.year} so far")
    if key == "last-year":
        y = today.year - 1
        return datetime.date(y, 1, 1), datetime.date(y, 12, 31), str(y)
    # This month is the default.
    nxt = (first_this + datetime.timedelta(days=32)).replace(day=1)
    return first_this, nxt - datetime.timedelta(days=1), today.strftime("%B %Y")


def previous_period(start, end):
    """The same length of time immediately before, for a comparison."""
    if start.month == 1 and start.day == 1 and end.month == 12 and end.day == 31:
        return (start.replace(year=start.year - 1), end.replace(year=end.year - 1))
    if start.year == end.year and start.month == 1 and start.day == 1:
        # A year so far compares against the same stretch of last year.
        return (start.replace(year=start.year - 1), end.replace(year=end.year - 1))
    prev_end = start - datetime.timedelta(days=1)
    return prev_end.replace(day=1), prev_end


def _session_groups(session):
    """A session's attendance split the way the chart shows it."""
    online = session.online_total
    return {
        "adults": session.men + session.women,
        "youth": session.youth_boys + session.youth_girls,
        "children": session.children_boys + session.children_girls,
        "online": online,
    }


class DashboardSummaryView(APIView):
    # Not gated as a whole: every signed-in user lands here. What is gated
    # is each section within it.
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        start, end, label = resolve_period(request.query_params.get("period"))
        data = {
            "period": {"start": start.isoformat(), "end": end.isoformat(), "label": label},
        }

        if user_can_view_module(user, "attendance"):
            # The chart has its own period, the year by default (F8): a month
            # holds only four or five services, too few to see a trend.
            c_key = request.query_params.get("chart_period") or "this-year"
            c_start, c_end, c_label = resolve_period(c_key)
            data.update(self._attendance_section(
                user, c_start, c_end, request.query_params.get("meeting") or "fri-worship"))
            data["attendance"]["period"] = {"key": c_key, "label": c_label}
        else:
            data["attendance_access"] = False

        if user_can_view_module(user, "finance"):
            data.update(self._finance_section(user, start, end))
        else:
            data["finance_access"] = False

        if user_can_view_module(user, "newcomers"):
            data.update(self._newcomers_section(user, start, end))
        else:
            data["newcomers_access"] = False

        if user_can_view_module(user, "goals"):
            data.update(self._goals_section())
        else:
            data["goals_access"] = False

        if user_can_view_module(user, "reports"):
            data.update(self._testimonies_section(user))
        else:
            data["testimonies_access"] = False

        # Issue 3: with every location in view, each location's share.
        if not scope_location_id(user):
            data["by_location"] = self._by_location(user, start, end, data)

        data["banner"] = self._banner(user, data)
        from core.outstanding import follow_up_people
        data["follow_up_people"] = follow_up_people(user)
        return Response(data)

    # ---------------------------------------------------------- by location
    def _by_location(self, user, start, end, data):
        """Each location's giving, expenses, newcomers and latest Friday Worship,
        for the dashboard's By location card when every location is in view."""
        from core.models import Location
        latest = {r["location"]: r for r in (data.get("attendance") or {}).get("latest_by_location", [])}
        rows = []
        for loc in Location.objects.order_by("name"):
            row = {"location": loc.name}
            if user_can_view_module(user, "finance"):
                row["giving"] = float(Giving.objects.filter(location=loc, date__gte=start, date__lte=end).aggregate(t=Sum("amount"))["t"] or 0)
                row["expenses"] = float(Expense.objects.filter(location=loc, date__gte=start, date__lte=end).aggregate(t=Sum("amount"))["t"] or 0)
            if user_can_view_module(user, "newcomers"):
                row["newcomers"] = Newcomer.objects.filter(location=loc, created_at__gte=start, created_at__lte=end).count()
            if user_can_view_module(user, "attendance"):
                row["worship_latest"] = latest.get(loc.name, {}).get("total", 0)
                row["worship_date"] = latest.get(loc.name, {}).get("date")
            rows.append(row)
        return rows

    # ---------------------------------------------------------- attendance
    def _attendance_section(self, user, start, end, meeting_id):
        """
        Any meeting, not only Friday Worship: the church runs eight.

        One entry per date, because two locations meeting the same day are
        one service as far as the chart is concerned.
        """
        mt = MeetingType.objects.filter(id=meeting_id).first() \
            or MeetingType.objects.filter(id="fri-worship").first()
        sessions = _location_filter(
            AttendanceSession.objects.filter(
                meeting_type=mt, status="filled", date__gte=start, date__lte=end),
            user) if mt else AttendanceSession.objects.none()

        by_date = {}
        for s in sessions.order_by("date"):
            row = by_date.setdefault(
                s.date.isoformat(), {"adults": 0, "youth": 0, "children": 0, "online": 0})
            for k, v in _session_groups(s).items():
                row[k] += v
        trend = [{"date": d, **g, "total": sum(g.values())} for d, g in by_date.items()]
        totals = [t["total"] for t in trend]

        # Over more than two months, one group per month, each the average per
        # service that month (F8). Drawing every service squeezed 38 Fridays
        # into the card, with the dates on top of each other.
        grouping = "service"
        if (end - start).days > 62 and trend:
            grouping = "month"
            months = {}
            for t in trend:
                months.setdefault(t["date"][:7], []).append(t)
            trend = []
            for ym, rows in months.items():
                avg = {k: round(sum(r[k] for r in rows) / len(rows)) for k in ("adults", "youth", "children", "online")}
                trend.append({"date": f"{ym}-01", "month": ym, "services": len(rows), **avg,
                              "total": sum(avg.values())})

        # The latest service is every location's session on the most recent
        # date, summed. Taking the single newest session would count only
        # one location and understate the service for anyone who can see
        # more than one.
        scoped = _location_filter(
            AttendanceSession.objects.filter(meeting_type=mt, status="filled",
                                             date__lte=timezone.localdate()), user
        ) if mt else AttendanceSession.objects.none()
        # Issue 3: each location's latest service, added up. Summing only the
        # most recent date counted just the location that filled in last, so
        # All locations showed Qatar's 63 instead of the church's 126.
        latest_by_location = []
        for loc_id in scoped.order_by().values_list("location_id", flat=True).distinct():
            s = scoped.filter(location_id=loc_id).order_by("-date", "-id").first()
            same_day = scoped.filter(location_id=loc_id, date=s.date)
            latest_by_location.append({"location": s.location.name, "total": sum(x.total for x in same_day), "date": s.date.isoformat()})
        latest_by_location.sort(key=lambda r: r["location"])
        latest_total = sum(r["total"] for r in latest_by_location)


        return {
            "attendance_access": True,
            "attendance": {
                "meeting_id": mt.id if mt else None,
                "meeting_name": mt.name if mt else "",
                "trend": trend,
                "grouping": grouping,
                "average": round(sum(totals) / len(totals)) if totals else 0,
                "latest": latest_total,
                "latest_by_location": latest_by_location,
                "target": mt.effective_target if mt else None,
            },
            "meetings": [{"id": m.id, "name": m.name}
                         for m in MeetingType.objects.all().order_by("name")],
            "pending_sessions": _location_filter(
                AttendanceSession.objects.filter(status="pending",
                                                 date__lte=timezone.localdate()), user
            ).count(),
            "fellowships": self._fellowship_section(user, start, end),
        }

    def _fellowship_section(self, user, start, end):
        """House fellowships for the period, with the offering collected."""
        from attendance.models import Fellowship
        sessions = _location_filter(
            AttendanceSession.objects.filter(
                fellowship__isnull=False, status="filled",
                date__gte=start, date__lte=end), user)
        groups = []
        for f in Fellowship.objects.filter(is_active=True).order_by("name"):
            mine = sessions.filter(fellowship=f)
            groups.append({"name": f.name, "attendance": sum(s.total for s in mine),
                           "meetings": mine.count()})
        offering = Giving.objects.filter(session__in=sessions) \
            .aggregate(t=Sum("amount"))["t"] or 0
        return {"groups": groups, "meetings_held": sessions.count(),
                "offering": float(offering)}

    # ---------------------------------------------------------- finance
    def _finance_section(self, user, start, end):
        giving = _location_filter(
            Giving.objects.filter(date__gte=start, date__lte=end), user)
        expenses = _location_filter(
            Expense.objects.filter(date__gte=start, date__lte=end), user)
        giving_total = giving.aggregate(t=Sum("amount"))["t"] or Decimal("0")
        expense_total = expenses.aggregate(t=Sum("amount"))["t"] or Decimal("0")

        p_start, p_end = previous_period(start, end)
        prev_total = _location_filter(
            Giving.objects.filter(date__gte=p_start, date__lte=p_end), user
        ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
        # No comparison when either side is empty. A period with nothing in
        # it is not a hundred percent fall.
        change = (round(float((giving_total - prev_total) / prev_total * 100))
                  if prev_total and giving_total else None)

        rows = [{"fund": r["fund__name"], "value": float(r["total"])}
                for r in giving.values("fund__name").annotate(total=Sum("amount"))
                .order_by("-total") if r["total"]]
        # Slices too thin to read are grouped, with the count said.
        if len(rows) > 4:
            rest = rows[3:]
            rows = rows[:3] + [{
                "fund": f"Other, {len(rest)} fund{'s' if len(rest) != 1 else ''}",
                "value": sum(r["value"] for r in rest)}]

        return {
            "finance_access": True,
            "giving_total": float(giving_total),
            "expense_total": float(expense_total),
            "net_total": float(giving_total - expense_total),
            "giving_previous": float(prev_total),
            "giving_change_pct": change,
            "giving_by_fund": rows,
        }

    # ---------------------------------------------------------- newcomers
    def _newcomers_section(self, user, start, end):
        today = timezone.localdate()
        week = today + datetime.timedelta(days=7)
        pipeline = _location_filter(
            Newcomer.objects.exclude(stage__in=["not-interested", "member"]), user)
        open_tasks = NewcomerTask.objects.filter(
            newcomer__in=_location_filter(Newcomer.objects.all(), user), done=False
        ).select_related("newcomer")

        overdue = open_tasks.filter(due_date__lt=today)
        this_week = open_tasks.filter(due_date__gte=today, due_date__lte=week)
        later = open_tasks.filter(due_date__gt=week)

        # The three most urgent, rather than nine near-identical rows.
        urgent = [{
            "newcomer_id": t.newcomer_id,
            "newcomer_name": t.newcomer.name,
            "text": t.text,
            "due_date": t.due_date.isoformat(),
            "days": (today - t.due_date).days,
        } for t in open_tasks.order_by("due_date")[:3]]

        from members.models import Member
        joined = _location_filter(
            Member.objects.filter(from_newcomer__isnull=False,
                                  joined_date__gte=start, joined_date__lte=end), user
        ).select_related("from_newcomer__source").order_by("-joined_date")

        new_members = [{
            "id": m.id, "name": m.full_name,
            "how": (m.from_newcomer.source.name
                    if m.from_newcomer and m.from_newcomer.source else ""),
        } for m in joined[:3]]

        section = {
            "newcomers_access": True,
            "newcomers_in_pipeline": pipeline.count(),
            "newcomers_registered": _location_filter(
                Newcomer.objects.filter(created_at__gte=start, created_at__lte=end), user
            ).count(),
            "unassigned_newcomers": pipeline.filter(assigned_to__isnull=True).count(),
            "follow_ups": {
                "overdue": overdue.count(),
                "this_week": this_week.count(),
                "later": later.count(),
                "urgent": urgent,
            },
            "new_members": {"count": joined.count(), "recent": new_members},
        }
        section.update(self._enquiries_section(user))
        return section

    def _enquiries_section(self, user):
        """
        People who messaged and have not been answered. The enquiries
        board had no presence on the dashboard at all, so somebody could
        wait three days without anyone noticing.
        """
        from enquiries.models import Enquiry
        today = timezone.localdate()
        waiting = Enquiry.objects.filter(stage="new").order_by("received_at")
        return {"enquiries_waiting": {
            "count": waiting.count(),
            "oldest": [{
                "id": e.id, "name": e.name,
                "source": e.source.name if e.source_id else "",
                "days": (today - e.received_at).days,
            } for e in waiting[:2]],
        }}

    # ---------------------------------------------------------- goals
    def _goals_section(self):
        goals = []
        for g in Goal.objects.filter(horizon=Goal.Horizon.SHORT)[:4]:
            current = g.current if g.tracking == "manual" else (compute_goal_value(g) or 0)
            pct = min(100, round(float(current) / float(g.target) * 100)) if g.target else 0
            goals.append({
                "id": g.id, "name": g.name, "current": float(current),
                "target": float(g.target), "unit": g.unit, "pct": pct,
                # Stated rather than implied by colour alone.
                "status": ("on-track" if pct >= 80 else
                           "behind" if pct >= 40 else "attention"),
                "not_started": pct == 0,
                "link_route": g.link_route, "link_tab": g.link_tab,
            })
        return {"goals_access": True, "short_term_goals": goals}

    # ---------------------------------------------------------- testimonies
    def _testimonies_section(self, user):
        from reports.models import Testimony
        # The ten most recent for the slider (F15). Two was too few.
        recent = Testimony.objects.select_related("service").order_by("-date", "-id")[:10]
        return {"testimonies_access": True, "testimonies": {
            "count": Testimony.objects.count(),
            "recent": [{
                "text": t.text,
                "by": "Anonymous" if t.is_anonymous else (t.member_name or ""),
                "service": t.service.name if t.service_id else "",
                "date": t.date.isoformat(),
            } for t in recent],
        }}

    # ---------------------------------------------------------- banner
    def _banner(self, user, data):
        """
        What needs doing, for this person. Only names things they can act
        on: a finance officer is not told about follow-ups.

        When nothing is outstanding it says so, rather than inventing an
        alert to fill the space.
        """
        things = []
        # Named only when this person can act on it. A view-only role was
        # told sessions needed filling in that it could not open to fill.
        def can(module, field):
            if user.is_superuser:
                return True
            p = user.role.permissions.filter(module=module).first() if user.role_id else None
            return bool(p and getattr(p, field))
        if data.get("newcomers_access") and can("newcomers", "can_edit"):
            overdue = data["follow_ups"]["overdue"]
            if overdue:
                things.append(f"{overdue} follow-up{'s are' if overdue != 1 else ' is'} overdue")
            waiting = data.get("enquiries_waiting", {}).get("count", 0)
            if waiting:
                things.append(f"{waiting} enquir{'ies are' if waiting != 1 else 'y is'} waiting for a reply")
        if data.get("attendance_access") and can("attendance", "can_edit"):
            pending = data.get("pending_sessions", 0)
            if pending:
                things.append(f"{pending} session{'s have' if pending != 1 else ' has'} not been filled in")

        if things:
            message = (things[0] if len(things) == 1
                       else ", ".join(things[:-1]) + " and " + things[-1]) + "."
        else:
            message = "Nothing needs your attention."

        return {"message": message, "has_outstanding": bool(things)}
