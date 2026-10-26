from accounts.permissions import require
from core.scoping import LocationScopedMixin
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import log_audit
from accounts.permissions import ModulePermission, LocationScopedQuerySetMixin
from .assignment import build_assignment_preview, apply_assignment_changes, eligible_shepherds
from .models import Household, Member, MemberCategoryHistory, MemberFollowUpTask
from accounts.names import display_name
from core.viewing import scope_location_id
from .serializers import (
    HouseholdSerializer, MemberSerializer,
    MemberCategoryHistorySerializer, MoveCategorySerializer,
    MemberFollowUpTaskSerializer, CompleteMemberFollowUpTaskSerializer,
)


class HouseholdViewSet(viewsets.ModelViewSet):
    """
    Deliberately NOT location-scoped , Household has no location field of
    its own in the approved schema (see Batch 2.1 delivery note). Flagged
    for review; every member of a household could in principle span
    different locations.
    """
    module = "members"
    permission_classes = [ModulePermission]
    queryset = Household.objects.all()
    serializer_class = HouseholdSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "address", "phone"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(self.request.user, "Created", "Household", instance.name, instance=instance)

    def perform_destroy(self, instance):
        name = instance.name
        log_audit(self.request.user, "Deleted", "Household", name)
        instance.delete()


class MemberViewSet(LocationScopedQuerySetMixin, viewsets.ModelViewSet):
    module = "members"
    permission_classes = [ModulePermission]
    queryset = Member.objects.select_related("location", "household", "assigned_to", "assigned_to__member").prefetch_related("category_history")
    serializer_class = MemberSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["surname", "first_name", "other_names", "email", "phone"]
    ordering_fields = ["surname", "first_name", "joined_date", "category"]

    @action(detail=True, methods=["get"])
    def person(self, request, pk=None):
        """The one-profile summary (F16), including the newcomer history."""
        from members.person import build_person
        return Response(build_person(member=self.get_object()))

    def get_queryset(self):
        from decimal import Decimal
        from django.db.models import Sum, DecimalField
        from django.db.models.functions import Coalesce

        qs = super().get_queryset()
        # Review item P4: people who moved away or left keep their history
        # but leave the list, unless asked for.
        status = self.request.query_params.get("status")
        if status in ("moved-away", "left", "active"):
            qs = qs.filter(status=status)
        elif status == "inactive":
            qs = qs.exclude(status="active")
        elif status != "all" and getattr(self, "action", None) in ("list", "stats"):
            qs = qs.filter(status="active")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        household = self.request.query_params.get("household")
        if household == "none":
            qs = qs.filter(household__isnull=True)
        elif household:
            qs = qs.filter(household_id=household)

        # "No shepherd" is the one that matters: the stat card shows that
        # count, but there was no way to get from the number to the people.
        shepherd = self.request.query_params.get("shepherd")
        if shepherd == "none":
            qs = qs.filter(assigned_to__isnull=True)
        elif shepherd:
            qs = qs.filter(assigned_to_id=shepherd)

        if self.request.query_params.get("is_leader") == "true":
            qs = qs.filter(is_leader=True)

        # Behind the "earlier members" link on the newcomer board. Without
        # it the link opened every member, which is not what it said.
        if self.request.query_params.get("from_pipeline") == "true":
            qs = qs.filter(from_newcomer__isnull=False)
        # Phase 4.1 fix: total_given was a per-object live .aggregate()
        # call in the serializer , correct, but O(n) queries for a list
        # of n members. Measured against the real ~42-member seed data:
        # 47 queries, ~37ms for a full member fetch, worse than every
        # comparable list endpoint. Annotating the sum at the queryset
        # level turns that into one query with a GROUP BY, the same
        # data, computed once. Coalesce keeps members with zero giving
        # at 0 rather than the LEFT JOIN's NULL , output_field must
        # match Giving.amount's exact type (DecimalField, 12/3) or
        # Coalesce can't resolve mixing it with a bare 0 literal; the
        # test suite caught this immediately on the first real run.
        # Confirmed by inspecting the generated SQL directly: adding an
        # aggregate .annotate() silently drops Member's Meta.ordering ,
        # Django clears default ordering once a GROUP BY is involved,
        # rather than risk an ambiguous ordering column. Without this
        # explicit re-application, DRF's LIMIT/OFFSET pagination has no
        # guaranteed stable order, which risks duplicate or skipped rows
        # across pages , a real correctness bug this performance fix
        # would otherwise have introduced, caught before it shipped.
        qs = qs.annotate(total_given_annotated=Coalesce(
            Sum("giving_entries__amount"), Decimal("0"),
            output_field=DecimalField(max_digits=12, decimal_places=3),
        )).order_by("surname", "first_name")
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(self.request.user, "Created", "Member", instance.full_name, instance=instance)
        if instance.assigned_to_id:
            from alerts.events import given
            given([("member", instance.pk, instance.full_name, instance.assigned_to_id)], by=self.request.user)

    @action(detail=True, methods=["get"], url_path="delete-preview")
    def delete_preview(self, request, pk=None):
        """P4 (review, 25 October 2026): what deleting this member would
        remove for good, so the person can set a status instead."""
        m = self.get_object()
        n = {
            "check_ins": m.attendance_records.count(),
            "follow_ups": m.followup_tasks.count(),
            "message_plans": m.enrolments.count(),
            "category_changes": m.category_history.count(),
            "giving_kept": m.giving_entries.count(),
        }
        return Response(n)

    @action(detail=True, methods=["post", "delete"])
    def away(self, request, pk=None):
        """Mark the member away for a known absence, or clear it."""
        return away_action(self, request, self.get_object(), "members")

    def get_permissions(self):
        if getattr(self, "action", None) == "away":
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_update(self, serializer):
        before = serializer.instance.assigned_to_id
        before_status = serializer.instance.status
        instance = serializer.save()
        if instance.assigned_to_id != before:
            # Their open tasks move with them (Kay, 26 October 2026).
            from core.task_actions import move_open_tasks
            move_open_tasks(instance, instance.assigned_to_id)
        if instance.status != before_status:
            log_audit(self.request.user, "Changed status", "Member", instance.full_name,
                      f"{before_status} to {instance.status}" + (f". {instance.status_note}" if instance.status_note else ""),
                      instance=instance)
            if instance.status != "active":
                # No more follow-up for someone who has left.
                from core.accountable import TaskResult
                from core.task_actions import close_open_for
                close_open_for(instance, self.request.user, TaskResult.MOVED_AWAY,
                               instance.get_status_display() + (f". {instance.status_note}" if instance.status_note else ""))
        if instance.assigned_to_id and instance.assigned_to_id != before:
            from alerts.events import given
            given([("member", instance.pk, instance.full_name, instance.assigned_to_id)], by=self.request.user)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Batch 3.4: the list view's stat-row needs unfiltered counts by
        category. Fetching a large page and counting client-side would
        have silently given wrong numbers past max_page_size (100) ,
        caught this before it shipped. A dedicated aggregate query is
        correct regardless of how many members actually exist.
        """
        qs = self.filter_queryset(self.get_queryset())
        # get_queryset() already applies location scoping (and any
        # ?category= filter) via LocationScopedQuerySetMixin , but this
        # endpoint's whole purpose is UNFILTERED-by-category counts, so
        # re-derive the location-scoped-only base rather than reuse a
        # possibly category-filtered queryset.
        everyone = LocationScopedQuerySetMixin.get_queryset(self)
        base = everyone.filter(status="active")
        return Response({
            "inactive": everyone.exclude(status="active").count(),
            "total": base.count(),
            "workers": base.filter(category="Worker").count(),
            "workers_in_training": base.filter(category="Worker in Training").count(),
            "general_members": base.filter(category="General Member").count(),
        })

    @action(detail=False, methods=["get"], url_path="shepherd-problems")
    def shepherd_problems(self, request):
        """
        Members whose shepherd breaks a rule: a man shepherding a woman, a
        woman shepherding a man, or someone shepherding themselves. Across
        every page of the list, for the box at the top of Members.
        """
        from .shepherd_rules import rule_breaks
        base = LocationScopedQuerySetMixin.get_queryset(self)
        found = rule_breaks(base.filter(status="active").order_by("surname", "first_name"))
        return Response({
            "count": len(found),
            "people": [{"id": m.id, "name": m.full_name, "tag": tag} for m, _, tag in found],
        })

    def perform_destroy(self, instance):
        name = instance.full_name
        log_audit(self.request.user, "Deleted", "Member", name)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="move-category")
    def move_category(self, request, pk=None):
        """
        The only correct way to change a Member's category , bundles the
        field update with a MemberCategoryHistory entry, atomically, so
        the two can never drift out of sync (Batch 0.1 approved behavior).
        """
        require(request.user, ("members", "can_edit"))
        member = self.get_object()
        serializer = MoveCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_category = serializer.validated_data["to_category"]
        from_category = member.category

        if to_category == from_category:
            return Response(
                {"detail": f"Member is already {to_category}."}, status=400
            )

        with transaction.atomic():
            MemberCategoryHistory.objects.create(
                member=member, from_category=from_category,
                to_category=to_category, changed_date=timezone.localdate(),
            )
            # Mark as explicitly logged BEFORE save() , the dedup check in
            # core/signals.py runs inside member.save()'s post_save signal,
            # so this must happen first or the automatic "Updated Member"
            # entry fires before this call gets a chance to suppress it.
            log_audit(
                request.user, "Moved", "Member", member.full_name,
                f"{from_category} -> {to_category}", instance=member,
            )
            member.category = to_category
            member.save(update_fields=["category"])

        # Re-fetch fresh rather than reusing `member` , its .category_history
        # relation was already cached by prefetch_related at get_object()
        # time, so the response would otherwise show the history list from
        # *before* this update, missing the entry just created above.
        # (Found this bug retroactively in Batch 2.3 while fixing the
        # identical pattern in Newcomer.set_milestone , same root cause,
        # same fix, applied back here.)
        fresh = self.get_queryset().get(pk=member.pk)
        return Response(MemberSerializer(fresh).data)


class MemberCategoryHistoryViewSet(LocationScopedMixin, viewsets.ModelViewSet):
    location_lookup = "member__location_id"
    """
    Corrections allowed directly (Batch 0.1, Finding 4) , not append-only.
    Governed by the same 'members' module permission as Member itself,
    since correcting a member's history is part of managing that member.
    """
    module = "members"
    permission_classes = [ModulePermission]
    queryset = MemberCategoryHistory.objects.select_related("member")
    serializer_class = MemberCategoryHistorySerializer

    def perform_update(self, serializer):
        instance = self._save_within_reach(serializer)
        log_audit(
            self.request.user, "Corrected", "Member category history",
            str(instance.member), instance=instance,
        )


from core.task_views import TaskActionsMixin, away_action


class MemberFollowUpTaskViewSet(TaskActionsMixin, LocationScopedMixin, viewsets.ModelViewSet):
    location_lookup = "member__location_id"
    """
    Real member-absence follow-up (confirmed design, built after the
    Newcomers follow-up pattern already proven in this app). Governed by
    the 'members' module permission , following up with a member is part
    of managing that member, same reasoning as MemberCategoryHistory.
    """
    module = "members"
    permission_classes = [ModulePermission]
    queryset = MemberFollowUpTask.objects.select_related("member", "assigned_to").prefetch_related(
        "attempts", "attempts__by", "reviews")
    serializer_class = MemberFollowUpTaskSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["due_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        member = self.request.query_params.get("member")
        if member:
            qs = qs.filter(member_id=member)
        assigned_to = self.request.query_params.get("assigned_to")
        if assigned_to:
            qs = qs.filter(assigned_to_id=assigned_to)
        done = self.request.query_params.get("done")
        if done is not None:
            qs = qs.filter(done=done.lower() == "true")
        return qs

    def perform_create(self, serializer):
        instance = self._save_within_reach(serializer)
        # A task added by hand on the profile has no missed service.
        detail = (f"Missed {instance.missed_meeting_name} on {instance.missed_date}" if instance.missed_meeting_name
                  else instance.text)
        log_audit(
            self.request.user, "Created follow-up task", "Member", instance.member.full_name,
            detail, instance=instance,
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Record that the member was reached. The four outcome boxes are
        required; the visit closes every open absence task for the member
        (Kay, 26 October 2026). The same as record-result with Reached."""
        from core import task_actions as acts
        from core.task_views import block_until_reasons
        task = self.get_object()
        self._may_record(request, task)
        block_until_reasons(request.user, task)
        serializer = CompleteMemberFollowUpTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        extra = acts.reached(task, request.user, serializer.validated_data)
        task.refresh_from_db()
        data = dict(MemberFollowUpTaskSerializer(task).data)
        data.update(extra)
        return Response(data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Same reasoning as every other stats endpoint in this app ,
        follow-up tasks accumulate over years, so a real aggregate query
        is correct regardless of how much history exists."""
        from django.db.models import Q
        base = self.get_queryset().filter(done=False)
        today = timezone.localdate()
        late = Q(due_at__lt=timezone.now()) | Q(due_at__isnull=True, due_date__lt=today)
        return Response({
            "open_followups": base.count(),
            "overdue": base.filter(late).count(),
            "unassigned": base.filter(assigned_to__isnull=True).count(),
        })


class AssignmentPreviewSerializer(serializers.Serializer):
    reassign_everyone = serializers.BooleanField(required=False, default=False)


class BulkAssignSerializer(serializers.Serializer):
    member_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    shepherd_id = serializers.IntegerField()


def _viewed_location(user):
    """Auto-assign works on the location being viewed, or every location."""
    from core.models import Location
    loc = scope_location_id(user)
    return Location.objects.filter(id=loc).first() if loc else None


class ShepherdAssignmentView(APIView):
    """
    Preview and apply shepherd assignments. Preview never writes, so an
    administrator always sees exactly what will change before committing.
    Governed by the members module permission, since assigning a shepherd
    is part of managing members.
    """
    module = "members"
    permission_classes = [ModulePermission]

    def get(self, request):
        """Propose changes without saving anything."""
        serializer = AssignmentPreviewSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        reassign = serializer.validated_data["reassign_everyone"]

        location = _viewed_location(request.user)
        changes, error = build_assignment_preview(location=location, reassign_everyone=reassign)
        if error:
            return Response({"detail": error}, status=400)
        from accounts.gender import skipped_notice
        return Response({
            "reassign_everyone": reassign,
            "count": len(changes),
            "changes": changes,
            "load": _load_summary(location, changes),
            "notice": skipped_notice(eligible_shepherds(location=location)),
        })

    def post(self, request):
        """Recompute and commit. Deliberately recomputes rather than
        trusting a client-supplied list, so a stale preview left open in
        a browser tab cannot write assignments based on data that has
        since changed."""
        require(request.user, ("members", "can_edit"))
        reassign = bool(request.data.get("reassign_everyone", False))
        location = _viewed_location(request.user)
        changes, error = build_assignment_preview(location=location, reassign_everyone=reassign)
        if error:
            return Response({"detail": error}, status=400)
        if not changes:
            return Response({"detail": "Nothing to assign. Everyone in scope already has a shepherd.",
                             "applied_members": 0, "applied_newcomers": 0})

        # Apply what the reviewer chose, on top of a fresh recomputation.
        #
        # The recomputation stays: it is what stops a preview left open in
        # a browser tab from writing assignments against data that has
        # since changed. But without honouring the reviewer's edits, a
        # shepherd chosen by hand would be silently replaced by the
        # system's original pick when Apply was pressed.
        changes, hand_picked, skipped = _apply_reviewer_edits(
            changes, request.data, location)
        if not changes:
            return Response({"detail": "Every change was skipped, so nothing was assigned.",
                             "applied_members": 0, "applied_newcomers": 0})

        applied_members, applied_newcomers = apply_assignment_changes(changes, by=request.user)
        detail = "Reassigned everyone" if reassign else "Filled unassigned only"
        if hand_picked:
            detail += f", {hand_picked} chosen by hand"
        if skipped:
            detail += f", {skipped} skipped"
        log_audit(
            request.user, "Auto-assigned shepherds", "Member",
            f"{applied_members + applied_newcomers} record(s)", detail,
        )
        return Response({
            "applied_members": applied_members,
            "applied_newcomers": applied_newcomers,
            "changes": changes,
        })


class BulkAssignShepherdView(APIView):
    """Assign one shepherd to several members at once."""
    module = "members"
    permission_classes = [ModulePermission]

    def post(self, request):
        require(request.user, ("members", "can_edit"))
        serializer = BulkAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # A shepherd is a User account (that is who logs in and receives
        # the task), and "Worker only" is checked through the member
        # record that account is linked to.
        from accounts.models import User
        shepherd = User.objects.filter(id=data["shepherd_id"], is_active=True).select_related("member").first()
        if not shepherd:
            return Response({"shepherd_id": "No active user with that id."}, status=400)
        if not shepherd.can_shepherd:
            return Response(
                {"shepherd_id": "That person is not set up to shepherd others. An administrator can "
                                "tick Can shepherd others on their account."},
                status=400,
            )

        qs = Member.objects.filter(id__in=data["member_ids"])
        if not request.user.is_superuser and request.user.location_id:
            qs = qs.filter(location_id=request.user.location_id)
        from .shepherd_rules import is_self
        himself = [m for m in qs if is_self(shepherd, m)]
        if himself:
            return Response({"detail": f"Nobody can shepherd themselves. Not saved, because {himself[0].full_name} "
                                       "is ticked. Untick them or choose someone else."}, status=400)
        from accounts.gender import can_pair, WORD
        clash = [m for m in qs if not can_pair(m.gender, shepherd)]
        if clash:
            names = ", ".join(f"{m.full_name} ({WORD[m.gender]})" for m in clash[:5]) + (" and more" if len(clash) > 5 else "")
            return Response({"detail": f"Men follow up men and women follow up women. Not saved, because of {names}. "
                                       "Untick them or choose someone of the same gender."}, status=400)

        from alerts.events import given
        newly = [("member", m.id, m.full_name, shepherd.id) for m in qs if m.assigned_to_id != shepherd.id]
        moving = list(qs)
        updated = qs.update(assigned_to=shepherd)
        from core.task_actions import move_open_tasks
        for m in moving:
            move_open_tasks(m, shepherd.id)
        given(newly, by=request.user)
        log_audit(
            request.user, "Bulk assigned shepherd", "Member",
            f"{updated} member(s)", f"Assigned to {display_name(shepherd)}",
        )
        return Response({"updated": updated, "shepherd": display_name(shepherd)})


class EligibleShepherdsView(APIView):
    """
    Who can be picked as a shepherd, for the bulk-assign dropdown.

    Needed as its own endpoint because a shepherd is a User account, not
    a Member, so the members list cannot supply it: bulk assign takes a
    user id. Returns the same set the auto-assign engine uses, so the
    dropdown can never offer someone the engine would reject.
    """
    module = "members"
    permission_classes = [ModulePermission]

    def get(self, request):
        # A location-limited person always gets their own location's
        # shepherds. Anyone else may ask for one location, so a member's
        # profile only offers shepherds who can actually be assigned there.
        location = request.query_params.get("location") or scope_location_id(request.user)
        if not request.user.is_superuser and request.user.location_id:
            location = request.user.location_id
        shepherds = eligible_shepherds(location)
        # On a member's profile, never offer that member themselves.
        member = Member.objects.filter(id=request.query_params.get("member") or 0).first() \
            if str(request.query_params.get("member") or "").isdigit() else None
        if member:
            from .shepherd_rules import is_self
            shepherds = [s for s in shepherds if not is_self(s, member)]
        from accounts.gender import shepherd_gender
        return Response([
            {"id": s.id, "name": display_name(s), "gender": shepherd_gender(s)} for s in shepherds
        ])

def _apply_reviewer_edits(changes, data, location):
    """
    Lay the reviewer's choices over a freshly computed set of changes.

    Only people still in the fresh set are touched. If somebody was
    assigned in another tab while this one sat open, their override is
    ignored rather than overwriting the newer decision.

    An override may only name an eligible shepherd for that location. The
    list comes from the browser, so it is checked rather than trusted: a
    crafted request must not be able to make anybody a shepherd.
    """
    eligible = {u.id: u for u in eligible_shepherds(location=location)}
    overrides = {}
    for o in (data.get("overrides") or []):
        try:
            key = (o["kind"], int(o["id"]))
            to_id = int(o["to_id"])
        except (KeyError, TypeError, ValueError):
            continue
        if to_id in eligible:
            overrides[key] = to_id
    from accounts.gender import can_pair
    from .shepherd_rules import is_self
    skips = set()
    for s in (data.get("skips") or []):
        try:
            skips.add((s["kind"], int(s["id"])))
        except (KeyError, TypeError, ValueError):
            continue

    kept, hand_picked, skipped = [], 0, 0
    for ch in changes:
        key = (ch["kind"], ch["id"])
        if key in skips:
            skipped += 1
            continue
        if key in overrides and overrides[key] != ch["to_id"]:
            # Men follow up men, women follow up women (Kay), and nobody
            # shepherds themselves. A hand pick that breaks either is
            # ignored, like any other bad override.
            pick = eligible[overrides[key]]
            selfpick = ch["kind"] == "member" and any(
                is_self(pick, m) for m in Member.objects.filter(id=ch["id"]))
            if can_pair(ch.get("gender", ""), pick) and not selfpick:
                ch = dict(ch, to_id=overrides[key], reason="Chosen by hand")
                hand_picked += 1
        if not ch.get("to_id"):
            continue
        kept.append(ch)
    return kept, hand_picked, skipped


def _load_summary(location, changes):
    """
    Each shepherd's load now and after these changes.

    Without it, a batch that sends everyone to one worker reads as a
    fault, when that worker was simply carrying far fewer than the rest.
    """
    from collections import Counter
    from .assignment import _shepherd_name, current_load
    shepherds = eligible_shepherds(location=location)
    now = current_load(shepherds)
    from accounts.gender import shepherd_gender
    gained = Counter(ch["to_id"] for ch in changes if ch.get("to_id"))
    # Someone moving to a new shepherd leaves their old one.
    lost = Counter(ch.get("from_id") for ch in changes if ch.get("to_id") and ch.get("from_id"))
    return sorted(({
        "id": s.id, "name": _shepherd_name(s), "gender": shepherd_gender(s),
        "now": now.get(s.id, 0),
        "after": now.get(s.id, 0) + gained.get(s.id, 0) - lost.get(s.id, 0),
    } for s in shepherds), key=lambda x: x["name"])

