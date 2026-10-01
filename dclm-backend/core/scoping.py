"""
Limit a list to the person's own location.

Each view used to do this itself, and four did not: member and newcomer
follow-up tasks and their histories showed the other location's people
to a location coordinator. This is the one shared way to do it.
"""
from django.db import transaction
from rest_framework.exceptions import PermissionDenied
from core.viewing import scope_location_id


class LocationScopedMixin:
    # How to reach the record's location, for example "member__location_id".
    location_lookup = "location_id"

    def _limit(self):
        user = self.request.user
        return scope_location_id(user)

    def get_queryset(self):
        qs = super().get_queryset()
        loc = self._limit()
        return qs.filter(**{self.location_lookup: loc}) if loc else qs

    def _save_within_reach(self, serializer):
        """Save, then confirm the record belongs to the person's location.
        Undone if it does not, so a task cannot be pinned on somebody at
        another location by sending their id."""
        loc = self._limit()
        with transaction.atomic():
            instance = serializer.save()
            if loc and not type(instance).objects.filter(
                    pk=instance.pk, **{self.location_lookup: loc}).exists():
                raise PermissionDenied("That person belongs to another location.")
        return instance

    def perform_create(self, serializer):
        self._save_within_reach(serializer)

    def perform_update(self, serializer):
        self._save_within_reach(serializer)
