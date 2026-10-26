"""
The follow-up screens' data (Kay, 26 October 2026):

  GET  followup/my/                    a shepherd's one list, members and
                                       newcomers together, late first
  GET  followup/review/                the Follow-up Coordinator's Review list
  POST followup/review/decide/         Accept, Hand to another shepherd,
                                       Take it myself, or Ask the shepherd
  GET  followup/review/overview/       measures and the shepherd table
  GET  followup/review/shepherd/<id>/  one shepherd's people
  GET  followup/review/eligible/       who a task can be handed to
"""
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import followup_overview as ov
from . import followup_review as rev
from .followup_access import can_review, coordinates, coverage, is_administrator


def _task(kind, pk):
    from members.models import MemberFollowUpTask
    from newcomers.models import NewcomerTask
    model = {"member": MemberFollowUpTask, "newcomer": NewcomerTask}.get(kind)
    if model is None:
        raise ValidationError({"type": "Say whether it is a member or a newcomer task."})
    t = model.objects.filter(pk=pk).first()
    if t is None:
        raise ValidationError({"detail": "That task was not found."})
    return t


def _reviewer(user, location_id=None):
    if not can_review(user, location_id):
        raise PermissionDenied("The Review list is for Follow-up Coordinators and administrators.")


def _location(request):
    """The location asked for, kept within what the person covers."""
    asked = request.query_params.get("location") or None
    mine = coverage(request.user)
    if mine and asked and asked != mine:
        raise PermissionDenied("You coordinate follow-up for one location only.")
    return asked or mine


class AccessView(APIView):
    """What follow-up screens this person sees: My follow-up for anyone who
    shepherds or holds tasks, Follow-up Review for coordinators and
    administrators. Read fresh, so a tick changed in Admin shows at once."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from accounts.permissions import user_has
        u = request.user
        loc = coverage(u)
        from core.models import Location
        return Response({
            "can_shepherd": bool(u.can_shepherd),
            "has_tasks": rev.my_followup(u)["open"] > 0 if not u.can_shepherd else True,
            "can_review": can_review(u, None),
            "is_coordinator": bool(u.is_followup_coordinator),
            "is_administrator": is_administrator(u),
            "coverage": loc,
            "coverage_name": (Location.objects.filter(pk=loc).values_list("name", flat=True).first() if loc
                              else "All locations"),
            "can_edit_members": user_has(u, "members", "can_edit"),
            "can_edit_newcomers": user_has(u, "newcomers", "can_edit"),
        })


class MyFollowUpView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shepherd = request.query_params.get("shepherd")
        if shepherd and int(shepherd) != request.user.id:
            _reviewer(request.user)
            return Response(rev.my_followup(request.user, int(shepherd)))
        return Response(rev.my_followup(request.user))


class ReasonsView(APIView):
    """
    POST every late task's reason at once (Kay, 26 October 2026): each task
    still has its own reason and new date, but they are checked together,
    saved together, and the Follow-up Coordinator gets one alert.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.db import transaction
        from django.utils.dateparse import parse_date
        from .followup_events import reasons_given
        items = request.data.get("items") or []
        if not items:
            raise ValidationError({"detail": "There are no reasons to send."})
        errors, done = {}, []
        with transaction.atomic():
            for it in items:
                key = f"{it.get('type')}-{it.get('id')}"
                try:
                    task = _task(it.get("type"), it.get("id"))
                    nd = it.get("new_date")
                    rnd = rev.give_reason(task, request.user, it.get("reason"), it.get("note", ""),
                                          parse_date(nd) if isinstance(nd, str) else None, alert=False)
                    done.append((task, rnd))
                except (ValidationError, PermissionDenied) as e:
                    d = e.detail
                    errors[key] = str(next(iter(d.values()))[0] if isinstance(d, dict) else d)
            if errors:
                transaction.set_rollback(True)
                raise ValidationError({"items": errors, "detail": "Nothing was sent. Correct the reasons shown, then send again."})
        reasons_given(request.user, done)
        return Response({"saved": len(done)})


class ReviewListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        loc = _location(request)
        _reviewer(request.user, loc)
        return Response({"results": rev.review_list(request.user, loc),
                         "can_review": True})


class ReviewDecideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from accounts.models import User
        task = _task(request.data.get("type"), request.data.get("id"))
        to = None
        if request.data.get("handed_to"):
            to = User.objects.filter(pk=request.data["handed_to"], is_active=True).first()
            if to is None:
                raise ValidationError({"handed_to": "That person was not found."})
        rnd = rev.decide(task, request.user, request.data.get("choice"), request.data.get("note", ""), to)
        from django.utils import timezone
        from .followup_rules import rules
        task.refresh_from_db()
        return Response({"choice": rnd.choice, "task": rev.task_row(task, timezone.now(), rules())})


class ReviewOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        loc = _location(request)
        _reviewer(request.user, loc)
        return Response(ov.overview(request.user, loc, request.query_params.get("month")))


class ShepherdPeopleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        loc = _location(request)
        _reviewer(request.user, loc)
        return Response({"results": ov.shepherd_people(int(pk), loc)})


class EligibleView(APIView):
    """Who a task can be handed to: shepherds at the person's location, of
    the same gender, other than the one holding it."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from accounts.gender import can_pair
        from accounts.names import display_name
        from members.assignment import eligible_shepherds
        from . import task_actions as acts
        task = _task(request.query_params.get("type"), request.query_params.get("id"))
        person = acts.person_of(task)
        _reviewer(request.user, person.location_id)
        gender = getattr(person, "gender", "") or ""
        rows = [{"id": u.id, "name": display_name(u)} for u in eligible_shepherds(location=person.location_id)
                if can_pair(gender, u) and u.id != task.assigned_to_id]
        why = (f"Only {'women' if gender == 'Female' else 'men'} at {person.location.name} are offered, because "
               f"{acts.person_name(task)} is a {'woman' if gender == 'Female' else 'man'}." if gender
               else f"Only shepherds at {person.location.name} are offered.")
        return Response({"results": rows, "why": why})
