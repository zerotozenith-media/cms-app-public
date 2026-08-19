from rest_framework import serializers

from .models import Location


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "name", "note", "is_core"]
        read_only_fields = ["is_core"]
        # is_core is set once at seed time (Bahrain), never via the API ,
        # an Admin shouldn't be able to accidentally strip or grant
        # protected status through a plain edit.
