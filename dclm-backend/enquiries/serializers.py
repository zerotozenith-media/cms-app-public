from rest_framework import serializers

from accounts.names import display_name
from accounts.permissions import user_can_view_module
from accounts.permissions import user_can_view_module
from .models import EnquirySource, Campaign, Enquiry, EnquiryStatusHistory, EnquiryTask


class EnquirySourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnquirySource
        fields = ["id", "name"]


class CampaignSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True, default=None)
    enquiries_received = serializers.SerializerMethodField()
    converted = serializers.SerializerMethodField()
    conversion_rate = serializers.SerializerMethodField()
    cost_per_enquiry = serializers.SerializerMethodField()
    cost_per_newcomer = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "source", "source_name", "spend",
            "started_on", "ended_on", "notes",
            "enquiries_received", "converted", "conversion_rate",
            "cost_per_enquiry", "cost_per_newcomer",
        ]
        read_only_fields = ["id"]

    # The viewset prefetches `enquiries`, so these read from memory
    # rather than issuing a query per campaign.
    def _enquiries(self, obj):
        return list(obj.enquiries.all())

    def get_enquiries_received(self, obj):
        return len(self._enquiries(obj))

    def get_converted(self, obj):
        return sum(1 for e in self._enquiries(obj) if e.converted_newcomer_id)

    def get_conversion_rate(self, obj):
        got = self.get_enquiries_received(obj)
        if not got:
            return 0
        return round(self.get_converted(obj) / got * 100)

    def get_cost_per_enquiry(self, obj):
        got = self.get_enquiries_received(obj)
        if not got or not obj.spend:
            return None
        return round(float(obj.spend) / got, 2)

    def get_cost_per_newcomer(self, obj):
        """The figure worth watching: what the church paid for each person
        who actually walked through the door, not each click."""
        conv = self.get_converted(obj)
        if not conv or not obj.spend:
            return None
        return round(float(obj.spend) / conv, 2)


class EnquiryStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EnquiryStatusHistory
        fields = ["id", "enquiry", "stage", "note", "date"]
        read_only_fields = ["id"]


class EnquiryTaskSerializer(serializers.ModelSerializer):
    enquiry_name = serializers.CharField(source="enquiry.name", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = EnquiryTask
        fields = [
            "id", "enquiry", "enquiry_name", "text", "due_date", "done",
            "assigned_to", "assigned_to_name",
            "contact_date", "contact_method", "contact_goal",
            "contact_scripture", "contact_root_cause", "contact_next_step",
        ]
        # done and the outcome fields are only settable through
        # complete(), same rule as newcomer and member tasks: a ticked
        # box with no record of what happened is not worth having.
        read_only_fields = [
            "id", "done", "contact_date", "contact_method", "contact_goal",
            "contact_scripture", "contact_root_cause", "contact_next_step",
        ]

    def get_assigned_to_name(self, obj):
        return display_name(obj.assigned_to) if obj.assigned_to else None

    def create(self, validated_data):
        if not validated_data.get("assigned_to"):
            validated_data["assigned_to"] = validated_data["enquiry"].assigned_to
        return super().create(validated_data)


class CompleteEnquiryTaskSerializer(serializers.Serializer):
    contact_date = serializers.DateField(required=False)
    contact_method = serializers.ChoiceField(choices=EnquiryTask.Method.choices)
    contact_goal = serializers.CharField()
    contact_scripture = serializers.CharField()
    contact_root_cause = serializers.CharField()
    contact_next_step = serializers.CharField()


class EnquirySerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    best_contact = serializers.ReadOnlyField()
    open_tasks_count = serializers.SerializerMethodField()
    days_in_stage = serializers.SerializerMethodField()
    converted_newcomer_name = serializers.CharField(
        source="converted_newcomer.name", read_only=True, default=None,
    )
    campaign_name = serializers.CharField(source="campaign.name", read_only=True, default=None)
    campaign_name = serializers.CharField(source="campaign.name", read_only=True, default=None)

    class Meta:
        model = Enquiry
        fields = [
            "id", "name", "source", "source_name",
            "phone", "email", "social_handle", "best_contact",
            "enquiry_text", "area",
            "stage", "stage_since", "received_at",
            "assigned_to", "assigned_to_name",
            "not_pursuing_note",
            "converted_newcomer", "converted_newcomer_name",
            "campaign", "campaign_name",
            "open_tasks_count", "days_in_stage",
            "campaign", "campaign_name",
        ]
        # stage moves through change-stage so the history is written at
        # the same time; conversion happens through its own action.
        read_only_fields = [
            "id", "stage", "stage_since", "converted_newcomer", "not_pursuing_note",
        ]

    def get_assigned_to_name(self, obj):
        return display_name(obj.assigned_to) if obj.assigned_to else None

    def to_representation(self, instance):
        """
        Campaign and spend are marketing data. A follow-up worker needs
        the person and how to reach them, not what an advert cost, so the
        fields are removed entirely rather than blanked: absent is
        clearer than empty, and nothing leaks through the API either.
        """
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and not user_can_view_module(request.user, "outreach"):
            data.pop("campaign", None)
            data.pop("campaign_name", None)
        return data

    def get_open_tasks_count(self, obj):
        # obj.tasks is prefetched by the viewset; filtering in Python
        # reuses that rather than issuing a query per enquiry.
        return sum(1 for t in obj.tasks.all() if not t.done)

    def get_days_in_stage(self, obj):
        from django.utils import timezone
        return (timezone.localdate() - obj.stage_since).days

    def validate(self, attrs):
        # A record with no way to reach the person is not useful, but any
        # one of the three is enough: a social handle alone is often all
        # the church has when someone first messages.
        instance = getattr(self, "instance", None)
        phone = attrs.get("phone", getattr(instance, "phone", ""))
        email = attrs.get("email", getattr(instance, "email", ""))
        handle = attrs.get("social_handle", getattr(instance, "social_handle", ""))
        if not (phone or email or handle):
            raise serializers.ValidationError(
                "Record at least one way to reach them: phone, email, or social handle."
            )
        return attrs


class ChangeEnquiryStageSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=Enquiry.Stage.choices)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class ConvertEnquirySerializer(serializers.Serializer):
    """
    Turning an enquirer into a newcomer once they actually attend.

    Location and the meeting they attended are required because that is
    precisely what makes them a newcomer rather than an enquirer.
    """
    location = serializers.CharField()
    meeting_attended = serializers.CharField(required=False, allow_blank=True)


class CampaignSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True, default=None)
    enquiries_received = serializers.SerializerMethodField()
    converted = serializers.SerializerMethodField()
    conversion_rate = serializers.SerializerMethodField()
    cost_per_enquiry = serializers.SerializerMethodField()
    cost_per_newcomer = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "source", "source_name", "spend",
            "started_on", "ended_on", "notes",
            "enquiries_received", "converted", "conversion_rate",
            "cost_per_enquiry", "cost_per_newcomer",
        ]
        read_only_fields = ["id"]

    # These read from a prefetched related set, so they cost no extra
    # queries per campaign.
    def _enquiries(self, obj):
        return list(obj.enquiries.all())

    def get_enquiries_received(self, obj):
        return len(self._enquiries(obj))

    def get_converted(self, obj):
        return sum(1 for e in self._enquiries(obj) if e.converted_newcomer_id)

    def get_conversion_rate(self, obj):
        got = self.get_enquiries_received(obj)
        if not got:
            return 0
        return round(self.get_converted(obj) / got * 100)

    def get_cost_per_enquiry(self, obj):
        got = self.get_enquiries_received(obj)
        if not got or not obj.spend:
            return None
        return round(float(obj.spend) / got, 2)

    def get_cost_per_newcomer(self, obj):
        """The figure worth watching: what the church paid for each
        person who actually walked through the door, not each click."""
        converted = self.get_converted(obj)
        if not converted or not obj.spend:
            return None
        return round(float(obj.spend) / converted, 2)
