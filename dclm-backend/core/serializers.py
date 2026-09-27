from rest_framework import serializers

from .models import Location


class LocationSerializer(serializers.ModelSerializer):
    def validate_name(self, value):
        """A location is renamed freely, for example to HQ or Bahrain HQ,
        but two locations may not share a name, or every list and report
        would show them identically."""
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("A location needs a name.")
        clash = Location.objects.filter(name__iexact=value)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(f"Another location is already called {value}.")
        return value

    def validate_id(self, value):
        # The short code is what every member, session and gift points to,
        # so it is fixed once created. Only the name and note change.
        if self.instance is not None and value != self.instance.pk:
            raise serializers.ValidationError("A location's short code cannot be changed. Rename it instead.")
        return value

    class Meta:
        model = Location
        fields = ["id", "name", "note", "is_core"]
        read_only_fields = ["is_core"]
        # is_core is set once at seed time (Bahrain), never via the API ,
        # an Admin shouldn't be able to accidentally strip or grant
        # protected status through a plain edit.
