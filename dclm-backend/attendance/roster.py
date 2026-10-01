"""
Names for taking attendance.

Named check-in, the name search on a session and the Led by list all need
member names. They read them from the Members section, which an usher
cannot open, so an usher could not tick anybody off by name. Giving ushers
the Members permission would also show them phone numbers and emails.

This list is governed by the Attendance permission and returns only what
taking attendance needs: a name and a category. It is limited to the
person's own location, as the member list is.
"""
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import ModulePermission
from members.models import Member
from core.viewing import scope_location_id


class AttendanceRosterView(APIView):
    module = "attendance"
    permission_classes = [ModulePermission]

    def get(self, request):
        qs = Member.objects.all().order_by("surname", "first_name")
        user = request.user
        if scope_location_id(user):
            qs = qs.filter(location_id=scope_location_id(user))
        location = request.query_params.get("location")
        if location:
            qs = qs.filter(location_id=location)
        category = request.query_params.get("category")
        if category:
            qs = qs.filter(category__iexact=category)
        search = (request.query_params.get("search") or "").strip()
        for word in search.split():
            qs = qs.filter(Q(first_name__icontains=word) | Q(surname__icontains=word)
                           | Q(other_names__icontains=word))
        try:
            limit = max(1, min(int(request.query_params.get("page_size", 500)), 1000))
        except ValueError:
            limit = 500
        rows = [{"id": m.id, "first_name": m.first_name, "surname": m.surname,
                 "full_name": m.full_name, "category": m.category, "location": m.location_id}
                for m in qs[:limit]]
        return Response({"count": qs.count(), "results": rows})


class FinanceRosterView(AttendanceRosterView):
    """The same names-only list for recording who gave. A finance officer
    could not open the member list, so giving could not be linked to the
    person who gave it."""
    module = "finance"
