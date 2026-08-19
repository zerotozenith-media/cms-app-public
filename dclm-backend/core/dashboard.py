"""
Dashboard summary endpoint , Batch 3.3. A dedicated aggregation endpoint,
not the frontend making 5+ separate paginated requests and summing
client-side. Genuinely necessary: GivingViewSet paginates at 25 records,
so a client-side "sum everything" would mean walking every page of every
Giving record on every dashboard load, which is both wasteful and fragile.

Location scoping matches LocationScopedQuerySetMixin's rule (a null
location means all-location access) , applied manually here since this
isn't a ModelViewSet. Goals are deliberately NOT location-filtered: per
the approved schema, a Goal has no location field, it represents
church-wide progress regardless of who's viewing.

Phase 4.3 security review: every section below is now gated by the
viewer's real per-module view permission, confirmed as the intended
design , a Members-only user should not see real Giving totals just
because the Dashboard itself is open to any authenticated user. Each
section is entirely omitted (not computed, not just hidden) when the
viewer lacks permission for it, and carries an explicit "_access": false
marker so the frontend can render a real restricted state rather than
an empty one that looks like "nothing to show yet."
"""
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import user_can_view_module
from attendance.models import AttendanceSession
from finance.models import Giving, Expense
from goals.calculations import compute_goal_value
from goals.models import Goal
from newcomers.models import Newcomer, NewcomerTask


def _location_filter(queryset, user, field="location_id"):
    if user.is_superuser or not user.location_id:
        return queryset
    return queryset.filter(**{field: user.location_id})


class DashboardSummaryView(APIView):
    # Deliberately not module-gated as a whole , Dashboard isn't one of
    # the seven real modules, it's the shared home page every
    # authenticated user lands on. What's gated is each section within it.
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {}

        if user_can_view_module(user, "attendance"):
            data.update(self._attendance_section(user))
        else:
            data["attendance_access"] = False

        if user_can_view_module(user, "finance"):
            data.update(self._finance_section(user))
        else:
            data["finance_access"] = False

        if user_can_view_module(user, "newcomers"):
            data.update(self._newcomers_section(user))
        else:
            data["newcomers_access"] = False

        if user_can_view_module(user, "goals"):
            data.update(self._goals_section())
        else:
            data["goals_access"] = False

        return Response(data)

    def _attendance_section(self, user):
        fw_sessions = _location_filter(
            AttendanceSession.objects.filter(meeting_type_id="fri-worship", status="filled"), user
        )
        fw_dates = sorted(fw_sessions.values_list("date", flat=True).distinct())
        fw_total = 0
        fw_trend = []
        if fw_dates:
            for d in fw_dates[-5:]:
                day_total = sum(s.total for s in fw_sessions.filter(date=d))
                fw_trend.append({"date": d.isoformat(), "total": day_total})
            fw_total = fw_trend[-1]["total"]
        fw_goal = Goal.objects.filter(calculation_type="latest_session_total", calculation_meeting_type_id="fri-worship").first()
        fw_target = fw_goal.target if fw_goal else None
        return {
            "attendance_access": True,
            "friday_worship": {"total": fw_total, "target": fw_target, "trend": fw_trend},
        }

    def _finance_section(self, user):
        giving_qs = _location_filter(Giving.objects.all(), user)
        expense_qs = _location_filter(Expense.objects.all(), user)
        giving_total = giving_qs.aggregate(t=Sum("amount"))["t"] or 0
        expense_total = expense_qs.aggregate(t=Sum("amount"))["t"] or 0
        by_fund = [
            {"fund": row["fund__name"], "value": float(row["total"])}
            for row in giving_qs.values("fund__name").annotate(total=Sum("amount")).order_by("-total")
            if row["total"]
        ]
        return {
            "finance_access": True,
            "giving_total": float(giving_total),
            "expense_total": float(expense_total),
            "net_total": float(giving_total) - float(expense_total),
            "giving_by_fund": by_fund,
            "fund_count": len(by_fund),
        }

    def _newcomers_section(self, user):
        newcomers_qs = _location_filter(Newcomer.objects.exclude(stage="not-interested"), user)
        newcomers_in_pipeline = newcomers_qs.count()
        open_tasks = NewcomerTask.objects.filter(
            newcomer__in=newcomers_qs, done=False
        ).select_related("newcomer").order_by("due_date")[:10]
        follow_ups_due = [
            {
                "newcomer_id": t.newcomer_id,
                "newcomer_name": t.newcomer.name,
                "due_date": t.due_date.isoformat(),
                "text": t.text,
            }
            for t in open_tasks
        ]
        pending_followups_count = NewcomerTask.objects.filter(newcomer__in=newcomers_qs, done=False).count()
        return {
            "newcomers_access": True,
            "newcomers_in_pipeline": newcomers_in_pipeline,
            "pending_followups_count": pending_followups_count,
            "follow_ups_due": follow_ups_due,
        }

    def _goals_section(self):
        short_term_goals = []
        for g in Goal.objects.filter(horizon=Goal.Horizon.SHORT)[:4]:
            current = g.current if g.tracking == "manual" else (compute_goal_value(g) or 0)
            pct = min(100, round(float(current) / float(g.target) * 100)) if g.target else 0
            short_term_goals.append({
                "id": g.id, "name": g.name, "current": float(current), "target": float(g.target),
                "unit": g.unit, "pct": pct, "link_route": g.link_route, "link_tab": g.link_tab,
            })
        return {"goals_access": True, "short_term_goals": short_term_goals}
