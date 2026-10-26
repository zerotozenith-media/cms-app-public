from rest_framework import viewsets, filters

from accounts.audit import log_audit
from accounts.permissions import ModulePermission
from .models import Goal
from .serializers import GoalSerializer


class GoalViewSet(viewsets.ModelViewSet):
    module = "goals"
    permission_classes = [ModulePermission]
    queryset = Goal.objects.select_related("calculation_meeting_type", "calculation_milestone_type", "calculation_location", "calculation_fund")
    serializer_class = GoalSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "source"]
    # No LocationScopedQuerySetMixin , goals are church-wide, not
    # per-location, matching the approved schema (no location field on Goal).

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(self.request.user, "Created", "Goal", instance.name, instance=instance)

    def perform_destroy(self, instance):
        name = instance.name
        log_audit(self.request.user, "Deleted", "Goal", name)
        instance.delete()

    def perform_update(self, serializer):
        instance = serializer.save()
        details = {"name", "horizon", "target", "unit", "target_date", "measured_by"} & set(self.request.data.keys())
        if details:
            log_audit(self.request.user, "Edited", "Goal", instance.name,
                      ", ".join(sorted(details)), instance=instance)
        if "current" in self.request.data and instance.tracking == Goal.Tracking.MANUAL:
            log_audit(
                self.request.user, "Updated progress", "Goal",
                instance.name, f"current = {instance.current}", instance=instance,
            )
