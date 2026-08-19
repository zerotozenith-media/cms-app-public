from rest_framework import serializers

from .models import Fund, PaymentMethod, ExpenseCategory, Project, Giving, Expense


class FundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fund
        fields = ["id", "name"]


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "name"]


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name"]


class ProjectSerializer(serializers.ModelSerializer):
    amount_raised = serializers.ReadOnlyField()
    amount_spent = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "name", "description", "location", "target_amount",
            "target_date", "status", "amount_raised", "amount_spent",
        ]

    def get_amount_spent(self, obj):
        # Batch 0.4, Flag 3 fix , a project now tracks spending too, not
        # just income. Live aggregate, same pattern as amount_raised,
        # never a stored running total.
        from django.db.models import Sum
        return obj.expenses.aggregate(total=Sum("amount"))["total"] or 0


class GivingSerializer(serializers.ModelSerializer):
    fund_name = serializers.CharField(source="fund.name", read_only=True)
    method_name = serializers.CharField(source="method.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    member_name = serializers.CharField(source="member.full_name", read_only=True, default=None)

    class Meta:
        model = Giving
        fields = [
            "id", "date", "fund", "fund_name", "method", "method_name", "amount",
            "location", "project", "project_name", "member", "member_name",
        ]


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)

    class Meta:
        model = Expense
        fields = [
            "id", "date", "category", "category_name", "amount", "location",
            "description", "receipt_file", "project", "project_name",
        ]
        # receipt_file is a real Django FileField (Batch 2.8) , the
        # ViewSet accepts multipart/form-data so an actual file can be
        # uploaded, not just a URL string referencing one that doesn't exist.
