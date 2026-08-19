from rest_framework import serializers

from .models import Household, Member, MemberCategoryHistory, MemberFollowUpTask
from accounts.names import display_name


class MemberCategoryHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberCategoryHistory
        fields = ["id", "member", "from_category", "to_category", "changed_date"]
        read_only_fields = ["id"]


class MemberSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    household_name = serializers.CharField(source="household.name", read_only=True, default=None)
    category_history = MemberCategoryHistorySerializer(many=True, read_only=True)
    total_given = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            "id", "surname", "first_name", "other_names", "full_name",
            "gender", "date_of_birth", "phone", "email",
            "category",  # read-only below , see note
            "location", "joined_date", "household", "household_name",
            "category_history", "total_given", "assigned_to", "assigned_to_name",
        ]
        read_only_fields = ["id", "category"]
        # `category` is deliberately read-only here: changing it directly via
        # PATCH would bypass MemberCategoryHistory logging entirely. The only
        # correct way to change it is MemberViewSet.move_category(), which
        # creates the history entry and updates the field together, atomically.

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to_id:
            return None
        return display_name(obj.assigned_to)

    def get_total_given(self, obj):
        # Phase 4.1 fix: MemberViewSet.get_queryset() now annotates this
        # as a single GROUP BY query instead of N per-object queries ,
        # use that when it's there. The live .aggregate() fallback stays
        # for safety, in case this serializer is ever used against a
        # queryset that didn't come through the viewset (e.g. a shell
        # or a future internal use), so it degrades correctly rather
        # than raising if the annotation is missing.
        annotated = getattr(obj, "total_given_annotated", None)
        if annotated is not None:
            return annotated
        from django.db.models import Sum
        return obj.giving_entries.aggregate(t=Sum("amount"))["t"] or 0


class HouseholdSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Household
        fields = ["id", "name", "address", "phone", "member_count"]
        read_only_fields = ["id"]

    def get_member_count(self, obj):
        return obj.members.count()


class MoveCategorySerializer(serializers.Serializer):
    to_category = serializers.ChoiceField(choices=Member.Category.choices)


class MemberFollowUpTaskSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source="member.full_name", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = MemberFollowUpTask
        fields = [
            "id", "member", "member_name", "text", "due_date", "done", "assigned_to", "assigned_to_name",
            "missed_session", "missed_meeting_name", "missed_date",
            "contact_date", "contact_method", "contact_notes",
            "contact_goal", "contact_scripture", "contact_root_cause", "contact_next_step",
        ]
        read_only_fields = [
            "id", "done", "contact_date", "contact_method", "contact_notes",
            "contact_goal", "contact_scripture", "contact_root_cause", "contact_next_step",
        ]
        # Same principle as NewcomerTask: done (and the log fields) are
        # only settable through complete(), never plain PATCH , a checked
        # box with no record of what was discussed isn't useful later.
        # missed_meeting_name/missed_date/missed_session stay writable ,
        # the automatic absence-check command is the typical way these
        # get created, but staff can also manually log one (e.g.
        # backfilling an absence the automatic check didn't catch),
        # mirroring how NewcomerTask supports manual creation too.

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to_id:
            return None
        return display_name(obj.assigned_to)


class CompleteMemberFollowUpTaskSerializer(serializers.Serializer):
    """All four outcome fields are required. A tick with no record of what
    happened is not useful to whoever reads it months later. Scripture
    accepts "None this time" as a real answer rather than forcing someone
    to invent one, which would just teach people to fake entries."""
    contact_date = serializers.DateField(required=False)
    contact_method = serializers.ChoiceField(choices=MemberFollowUpTask.Method.choices)
    contact_goal = serializers.CharField(allow_blank=False, trim_whitespace=True)
    contact_scripture = serializers.CharField(allow_blank=False, trim_whitespace=True, max_length=300)
    contact_root_cause = serializers.CharField(allow_blank=False, trim_whitespace=True)
    contact_next_step = serializers.CharField(allow_blank=False, trim_whitespace=True)
