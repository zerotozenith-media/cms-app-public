"""
Real server-side permission enforcement (Batch 0.6 hard requirement,
Batch 1.4 scope). These are reusable building blocks , Phase 2's actual
module endpoints (members, attendance, finance, etc.) attach these,
each declaring which `module` name it represents and relying on
LocationScopedQuerySetMixin to filter data automatically.

Nothing here is UI-cosmetic. A disabled dropdown in the frontend is a
convenience for honest users; this is the actual boundary.
"""
from rest_framework.permissions import BasePermission


ACTION_TO_PERMISSION_FIELD = {
    "GET": "can_view",
    "HEAD": "can_view",
    "OPTIONS": "can_view",
    "POST": "can_create",
    "PUT": "can_edit",
    "PATCH": "can_edit",
    "DELETE": "can_delete",
}


def user_can_view_module(user, module):
    """
    Same rule ModulePermission enforces for GET requests (can_view), but
    usable outside a ViewSet's permission_classes , for views like the
    Dashboard that are open to any authenticated user overall, but need
    to gate individual *sections* of their response by the viewer's real
    per-module permission, not the endpoint as a whole.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.role_id:
        return False
    perm = user.role.permissions.filter(module=module).first()
    return bool(perm and perm.can_view)


class ModulePermission(BasePermission):
    """
    Checks the requesting user's Role against RolePermission for the
    view's declared `module`, using the correct action for the HTTP
    method actually being used , not just "can this role see this page."

    A view using this must declare: module = "attendance"  (etc.)
    """

    def has_permission(self, request, view):
        module = getattr(view, "module", None)
        if not module:
            # A view that forgets to declare its module fails closed,
            # not open , better an accidental 403 than an accidental leak.
            return False

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if not user.role_id:
            return False

        field = ACTION_TO_PERMISSION_FIELD.get(request.method)
        if field is None:
            return False

        perm = user.role.permissions.filter(module=module).first()
        if not perm:
            return False

        return getattr(perm, field, False)


class LocationScopedQuerySetMixin:
    """
    Mix into any ViewSet whose model has a `location` field. Automatically
    restricts the queryset to the requesting user's location, unless their
    location is blank (Administrator / all-location access) , matching the
    approved rule that a null location means access to everything.

    This is deliberately a queryset-level filter, not just a permission
    check, so a Location Coordinator physically cannot retrieve another
    location's rows even by guessing an ID.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or not user.location_id:
            return qs
        return qs.filter(location_id=user.location_id)
