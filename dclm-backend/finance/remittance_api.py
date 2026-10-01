"""
The remittance endpoint.

Reads what a month collected and spent, proposes what should be sent,
and records what actually was. The proposal is never binding: a member
sometimes covers the expenses and more goes than the arithmetic says.
"""
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.audit import log_audit
from accounts.permissions import ModulePermission
from finance.models import Expense, Fund, Giving, Remittance, RemittanceLine
from core.viewing import scope_location_id


class RemittanceLineSerializer(serializers.ModelSerializer):
    fund_name = serializers.CharField(source="fund.name", read_only=True)
    difference = serializers.ReadOnlyField()

    class Meta:
        model = RemittanceLine
        fields = ["id", "fund", "fund_name", "amount_due", "amount_sent",
                  "destination", "difference"]


class RemittanceSerializer(serializers.ModelSerializer):
    lines = RemittanceLineSerializer(many=True)
    total_due = serializers.ReadOnlyField()
    total_sent = serializers.ReadOnlyField()
    difference = serializers.ReadOnlyField()
    recorded_by_name = serializers.CharField(
        source="recorded_by.full_name", read_only=True, default="")
    location_name = serializers.CharField(source="location.name", read_only=True, default="")

    class Meta:
        model = Remittance
        fields = ["id", "month", "location", "location_name", "sent_on", "reference", "note",
                  "lines", "total_due", "total_sent", "difference",
                  "recorded_by_name", "recorded_at"]
        read_only_fields = ["location"]

    def validate(self, attrs):
        """
        A figure that differs from the one worked out needs a reason.

        Without this the difference is silent, and six months later
        nobody can say why one month sent 300 more than it collected.
        """
        lines = attrs.get("lines") or []
        diff = sum((Decimal(str(l["amount_sent"])) - Decimal(str(l["amount_due"]))
                    for l in lines), Decimal("0"))
        note = (attrs.get("note") or "").strip()
        if diff and not note:
            raise ValidationError({
                "note": "The amount sent differs from the amount due. "
                        "Say why before recording it."
            })
        return attrs

    def create(self, validated):
        lines = validated.pop("lines")
        remittance = Remittance.objects.create(**validated)
        for line in lines:
            RemittanceLine.objects.create(remittance=remittance, **line)
        return remittance

    def update(self, instance, validated):
        """
        Editable after recording, because a reference gets mistyped. The
        original stays in the audit log, since silently altering a money
        record is not acceptable.
        """
        lines = validated.pop("lines", None)
        for field, value in validated.items():
            setattr(instance, field, value)
        instance.save()
        if lines is not None:
            instance.lines.all().delete()
            for line in lines:
                RemittanceLine.objects.create(remittance=instance, **line)
        return instance


def remittance_location(request):
    """
    Whose money a remittance is about. Somebody limited to one location
    always gets their own. Anybody else chooses with ?location= or in the
    body, and gets the main location when they do not say.
    """
    from core.models import Location
    user = request.user
    if not user.is_superuser and user.location_id:
        return user.location
    wanted = request.query_params.get("location") or (
        request.data.get("location") if hasattr(request.data, "get") else None) or scope_location_id(user)
    if wanted:
        loc = Location.objects.filter(id=wanted).first()
        if loc:
            return loc
    return Location.objects.filter(is_core=True).first()


class RemittanceViewSet(viewsets.ModelViewSet):
    module = "finance"
    permission_classes = [ModulePermission]
    queryset = Remittance.objects.prefetch_related("lines__fund")
    serializer_class = RemittanceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser and user.location_id:
            return qs.filter(location_id=user.location_id)
        wanted = self.request.query_params.get("location") or scope_location_id(user)
        return qs.filter(location_id=wanted) if wanted else qs

    def perform_create(self, serializer):
        location = remittance_location(self.request)
        month = serializer.validated_data["month"]
        if Remittance.objects.filter(month__year=month.year, month__month=month.month,
                                     location=location).exists():
            raise ValidationError({"month": f"{month:%B %Y} is already recorded for "
                                            f"{location.name}. Open it with Edit to change it."})
        obj = serializer.save(recorded_by=self.request.user, location=location)
        log_audit(self.request.user, "Recorded", "Remittance",
                  f"{obj.month:%B %Y}",
                  f"{obj.total_sent} sent"
                  + (f", ref {obj.reference}" if obj.reference else ""), instance=obj)

    def perform_update(self, serializer):
        before = serializer.instance.total_sent
        obj = serializer.save()
        log_audit(self.request.user, "Updated", "Remittance",
                  f"{obj.month:%B %Y}",
                  f"Was {before}, now {obj.total_sent}", instance=obj)

    @action(detail=False, methods=["get"])
    def proposed(self, request):
        """
        What a month should send, worked out from its records.

        Expenses come out before anything is remitted, so the figure is
        what is actually left rather than what came in. Each fund carries
        its share of the expenses, in proportion to what it raised.
        """
        month = request.query_params.get("month")   # YYYY-MM
        if not month or len(month) != 7:
            raise ValidationError({"month": "Give a month as YYYY-MM."})
        year, mon = int(month[:4]), int(month[5:])

        location = remittance_location(request)
        giving = Giving.objects.filter(date__year=year, date__month=mon, location=location)
        expenses = Expense.objects.filter(date__year=year, date__month=mon, location=location) \
            .aggregate(t=Sum("amount"))["t"] or Decimal("0")
        collected = giving.aggregate(t=Sum("amount"))["t"] or Decimal("0")

        by_fund = (giving.values("fund", "fund__name")
                   .annotate(raised=Sum("amount")).order_by("fund__name"))
        total_raised = sum((row["raised"] for row in by_fund), Decimal("0")) or Decimal("1")

        lines = []
        for row in by_fund:
            share = expenses * (row["raised"] / total_raised)
            due = max(Decimal("0"), (row["raised"] - share).quantize(Decimal("0.001")))
            lines.append({
                "fund": row["fund"],
                "fund_name": row["fund__name"],
                "amount_due": due,
                "amount_sent": due,
                "destination": ("lagos" if row["fund__name"] == "Building" else "dubai"),
            })

        # Rounding each fund to the fils can leave the lines a fils away
        # from the total, so the form showed 2,249.856 sent against
        # 2,249.855 due. The remainder goes on the largest line, so the
        # lines always add up to exactly what is due.
        target = max(Decimal("0"), (collected - expenses).quantize(Decimal("0.001")))
        residue = target - sum((l["amount_due"] for l in lines), Decimal("0"))
        if lines and residue:
            biggest = max(lines, key=lambda l: l["amount_due"])
            biggest["amount_due"] += residue
            biggest["amount_sent"] = biggest["amount_due"]

        existing = Remittance.objects.filter(
            month__year=year, month__month=mon, location=location).first()

        return Response({
            "month": f"{month}-01",
            "location": location.id if location else None,
            "location_name": location.name if location else "",
            "collected": collected,
            "expenses": expenses,
            "due": target,
            "lines": lines,
            "already_recorded": existing.id if existing else None,
        })
