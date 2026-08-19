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
    queryset = Member.objects.select_related("location", "household", "assigned_to").prefetch_related("category_history")
    serializer_class = MemberSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["surname", "first_name", "other_names", "email", "phone"]
    ordering_fields = ["surname", "first_name", "joined_date", "category"]

    def get_queryset(self):
        from decimal import Decimal
        from django.db.models import Sum, DecimalField
        from django.db.models.functions import Coalesce

        qs = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        household = self.request.query_params.get("household")
        if household:
            qs = qs.filter(household_id=household)
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
        base = LocationScopedQuerySetMixin.get_queryset(self)
        return Response({
            "total": base.count(),
            "workers": base.filter(category="Worker").count(),
            "workers_in_training": base.filter(category="Worker in Training").count(),
            "general_members": base.filter(category="General Member").count(),
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


class MemberCategoryHistoryViewSet(viewsets.ModelViewSet):
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
        instance = serializer.save()
        log_audit(
            self.request.user, "Corrected", "Member category history",
            str(instance.member), instance=instance,
        )


class MemberFollowUpTaskViewSet(viewsets.ModelViewSet):
    """
    Real member-absence follow-up (confirmed design, built after the
    Newcomers follow-up pattern already proven in this app). Governed by
    the 'members' module permission , following up with a member is part
    of managing that member, same reasoning as MemberCategoryHistory.
    """
    module = "members"
    permission_classes = [ModulePermission]
    queryset = MemberFollowUpTask.objects.select_related("member", "assigned_to")
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
        instance = serializer.save()
        log_audit(
            self.request.user, "Created follow-up task", "Member", instance.member.full_name,
            f"Missed {instance.missed_meeting_name} on {instance.missed_date}", instance=instance,
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """The only correct way to mark a follow-up done , requires the
        real visitation outcome, mirroring NewcomerTaskViewSet.complete()."""
        task = self.get_object()
        serializer = CompleteMemberFollowUpTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        task.done = True
        task.contact_date = data.get("contact_date") or timezone.localdate()
        task.contact_method = data["contact_method"]
        task.contact_goal = data["contact_goal"]
        task.contact_scripture = data["contact_scripture"]
        task.contact_root_cause = data["contact_root_cause"]
        task.contact_next_step = data["contact_next_step"]
        task.save()
        log_audit(
            request.user, "Recorded follow-up outcome", "Member", task.member.full_name,
            f"{task.contact_method}: {task.contact_goal[:60]}", instance=task,
        )
        return Response(MemberFollowUpTaskSerializer(task).data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Same reasoning as every other stats endpoint in this app ,
        follow-up tasks accumulate over years, so a real aggregate query
        is correct regardless of how much history exists."""
        base = self.get_queryset().filter(done=False)
        today = timezone.localdate()
        return Response({
            "open_followups": base.count(),
            "overdue": base.filter(due_date__lt=today).count(),
            "unassigned": base.filter(assigned_to__isnull=True).count(),
        })


class AssignmentPreviewSerializer(serializers.Serializer):
    reassign_everyone = serializers.BooleanField(required=False, default=False)


class BulkAssignSerializer(serializers.Serializer):
    member_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    shepherd_id = serializers.IntegerField()


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

        location = None if request.user.is_superuser or not request.user.location_id else request.user.location
        changes, error = build_assignment_preview(location=location, reassign_everyone=reassign)
        if error:
            return Response({"detail": error}, status=400)
        return Response({
            "reassign_everyone": reassign,
            "count": len(changes),
            "changes": changes,
        })

    def post(self, request):
        """Recompute and commit. Deliberately recomputes rather than
        trusting a client-supplied list, so a stale preview left open in
        a browser tab cannot write assignments based on data that has
        since changed."""
        reassign = bool(request.data.get("reassign_everyone", False))
        location = None if request.user.is_superuser or not request.user.location_id else request.user.location
        changes, error = build_assignment_preview(location=location, reassign_everyone=reassign)
        if error:
            return Response({"detail": error}, status=400)
        if not changes:
            return Response({"detail": "Nothing to assign. Everyone in scope already has a shepherd.",
                             "applied_members": 0, "applied_newcomers": 0})

        applied_members, applied_newcomers = apply_assignment_changes(changes)
        log_audit(
            request.user, "Auto-assigned shepherds", "Member",
            f"{applied_members + applied_newcomers} record(s)",
            "Reassigned everyone" if reassign else "Filled unassigned only",
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
        if not shepherd.member_id or shepherd.member.category != Member.Category.WORKER:
            return Response(
                {"shepherd_id": "Only users linked to a member in the Worker category can be shepherds."},
                status=400,
            )

        qs = Member.objects.filter(id__in=data["member_ids"])
        if not request.user.is_superuser and request.user.location_id:
            qs = qs.filter(location_id=request.user.location_id)

        updated = qs.update(assigned_to=shepherd)
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
        location = None
        if not request.user.is_superuser and request.user.location_id:
            location = request.user.location_id
        shepherds = eligible_shepherds(location)
        return Response([
            {"id": s.id, "name": display_name(s)} for s in shepherds
        ])
