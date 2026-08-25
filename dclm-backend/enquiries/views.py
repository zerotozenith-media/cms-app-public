from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.audit import log_audit
from accounts.permissions import ModulePermission
from core.models import Location
from newcomers.models import Newcomer, NewcomerSource
from .models import EnquirySource, Campaign, Enquiry, EnquiryStatusHistory, EnquiryTask
from .serializers import (
    EnquirySourceSerializer, CampaignSerializer, EnquirySerializer, EnquiryStatusHistorySerializer,
    EnquiryTaskSerializer, CompleteEnquiryTaskSerializer,
    ChangeEnquiryStageSerializer, ConvertEnquirySerializer,
)


class EnquirySourceViewSet(viewsets.ModelViewSet):
    # Enquiries sit under the newcomers module rather than getting their
    # own permission: anyone who follows up newcomers is the same person
    # who follows up online enquiries, and a separate module would mean
    # every church had to configure one more thing for no benefit.
    module = "newcomers"
    permission_classes = [ModulePermission]
    queryset = EnquirySource.objects.all()
    serializer_class = EnquirySourceSerializer
    pagination_class = None


class EnquiryViewSet(viewsets.ModelViewSet):
    module = "newcomers"
    permission_classes = [ModulePermission]
    queryset = Enquiry.objects.select_related(
        "source", "assigned_to", "assigned_to__member", "converted_newcomer",
    ).prefetch_related("tasks")
    serializer_class = EnquirySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "social_handle", "phone", "email"]
    ordering_fields = ["received_at", "stage_since", "name"]

    # No location scoping: an enquirer may be anywhere, including outside
    # Bahrain, so there is often no location to scope by.

    def get_queryset(self):
        qs = super().get_queryset()
        stage = self.request.query_params.get("stage")
        if stage:
            qs = qs.filter(stage=stage)
        source = self.request.query_params.get("source")
        if source:
            qs = qs.filter(source_id=source)
        assigned_to = self.request.query_params.get("assigned_to")
        if assigned_to:
            qs = qs.filter(assigned_to_id=assigned_to)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        EnquiryStatusHistory.objects.create(
            enquiry=instance, stage=instance.stage, note="Enquiry received",
        )
        log_audit(
            self.request.user, "Created", "Enquiry", instance.name,
            f"via {instance.source.name}", instance=instance,
        )

    @action(detail=True, methods=["post"], url_path="change-stage")
    def change_stage(self, request, pk=None):
        enquiry = self.get_object()
        serializer = ChangeEnquiryStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_stage = serializer.validated_data["stage"]
        note = serializer.validated_data.get("note", "")

        if new_stage == Enquiry.Stage.NOT_PURSUING and not note:
            return Response(
                {"note": "Say briefly why, so the record makes sense later."},
                status=400,
            )

        previous = enquiry.get_stage_display()
        enquiry.stage = new_stage
        enquiry.stage_since = timezone.localdate()
        if new_stage == Enquiry.Stage.NOT_PURSUING:
            enquiry.not_pursuing_note = note
        enquiry.save()

        EnquiryStatusHistory.objects.create(enquiry=enquiry, stage=new_stage, note=note)
        log_audit(
            request.user, "Stage changed", "Enquiry", enquiry.name,
            f"{previous} to {enquiry.get_stage_display()}", instance=enquiry,
        )
        return Response(EnquirySerializer(enquiry).data)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """
        They attended. Create the matching Newcomer and link the two.

        The enquiry is kept rather than deleted: the link is what makes
        "how many online enquiries became people in the room" answerable.
        """
        enquiry = self.get_object()

        if enquiry.converted_newcomer_id:
            return Response(
                {"detail": f"Already converted to newcomer '{enquiry.converted_newcomer.name}'."},
                status=400,
            )

        serializer = ConvertEnquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location_id = serializer.validated_data["location"]

        location = Location.objects.filter(id=location_id).first()
        if not location:
            return Response({"location": "No location with that id."}, status=400)

        with transaction.atomic():
            # Record the original platform on the newcomer too, so the
            # source is visible without following the link back.
            source_name = f"{enquiry.source.name} (online enquiry)"
            newcomer_source, _ = NewcomerSource.objects.get_or_create(name=source_name)

            newcomer = Newcomer.objects.create(
                name=enquiry.name,
                source=newcomer_source,
                location=location,
                stage="new",
                created_at=timezone.localdate(),
                stage_since=timezone.localdate(),
                assigned_to=enquiry.assigned_to,
                phone=enquiry.phone,
                email=enquiry.email,
                address=enquiry.area,
                prayer_request=enquiry.enquiry_text,
            )

            enquiry.converted_newcomer = newcomer
            enquiry.stage = Enquiry.Stage.ATTENDED
            enquiry.stage_since = timezone.localdate()
            enquiry.save()

            EnquiryStatusHistory.objects.create(
                enquiry=enquiry, stage=Enquiry.Stage.ATTENDED,
                note=f"Attended and added as a newcomer",
            )

        log_audit(
            request.user, "Converted to newcomer", "Enquiry", enquiry.name,
            f"from {enquiry.source.name}", instance=enquiry,
        )
        return Response(EnquirySerializer(enquiry).data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        today = timezone.localdate()
        active = Enquiry.objects.exclude(stage__in=[
            Enquiry.Stage.ATTENDED, Enquiry.Stage.NOT_PURSUING,
        ])
        open_tasks = EnquiryTask.objects.filter(done=False)
        return Response({
            "active": active.count(),
            "awaiting_first_contact": active.filter(stage=Enquiry.Stage.NEW).count(),
            "unassigned": active.filter(assigned_to__isnull=True).count(),
            "overdue_tasks": open_tasks.filter(due_date__lt=today).count(),
            "converted": Enquiry.objects.filter(converted_newcomer__isnull=False).count(),
        })


class EnquiryTaskViewSet(viewsets.ModelViewSet):
    module = "newcomers"
    permission_classes = [ModulePermission]
    queryset = EnquiryTask.objects.select_related(
        "enquiry", "assigned_to", "assigned_to__member",
    )
    serializer_class = EnquiryTaskSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["due_date"]
    ordering = ["due_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        enquiry = self.request.query_params.get("enquiry")
        if enquiry:
            qs = qs.filter(enquiry_id=enquiry)
        done = self.request.query_params.get("done")
        if done is not None:
            qs = qs.filter(done=done.lower() == "true")
        return qs

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        serializer = CompleteEnquiryTaskSerializer(data=request.data)
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
            request.user, "Recorded follow-up outcome", "Enquiry", task.enquiry.name,
            f"{task.contact_method}: {task.contact_goal[:50]}", instance=task,
        )
        return Response(EnquiryTaskSerializer(task).data)


class EnquiryStatusHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    module = "newcomers"
    permission_classes = [ModulePermission]
    queryset = EnquiryStatusHistory.objects.select_related("enquiry")
    serializer_class = EnquiryStatusHistorySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        enquiry = self.request.query_params.get("enquiry")
        if enquiry:
            qs = qs.filter(enquiry_id=enquiry)
        return qs


class CampaignViewSet(viewsets.ModelViewSet):
    """
    Campaigns and their performance.

    Behind its own `outreach` module rather than `admin`: whoever runs
    the church's adverts is not necessarily an administrator, and should
    be able to see what a campaign cost per person reached without also
    being able to create user accounts and change church settings.
    """
    module = "outreach"
    permission_classes = [ModulePermission]
    queryset = Campaign.objects.select_related("source").prefetch_related("enquiries")
    serializer_class = CampaignSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["name", "started_on", "spend"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            self.request.user, "Created", "Campaign", instance.name,
            f"spend BHD {instance.spend}", instance=instance,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Totals across every campaign, for the top of the outreach screen."""
        campaigns = self.get_queryset()
        total_spend = sum(float(c.spend) for c in campaigns)
        enquiries = Enquiry.objects.all()
        total_enquiries = enquiries.count()
        total_converted = enquiries.filter(converted_newcomer__isnull=False).count()
        return Response({
            "total_spend": round(total_spend, 2),
            "total_enquiries": total_enquiries,
            "total_converted": total_converted,
            "cost_per_newcomer": round(total_spend / total_converted, 2) if total_converted and total_spend else None,
            "campaigns": campaigns.count(),
        })
