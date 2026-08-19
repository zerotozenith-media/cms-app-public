from django.db import connection
from django.db.models import ProtectedError
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import log_audit
from accounts.permissions import ModulePermission, user_can_view_module
from .models import Location, AppSetting
from .serializers import LocationSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Simple health-check endpoint, deliberately unauthenticated so
    Azure App Service (and anyone deploying this) can verify the app
    is up and the database connection actually works.
    """
    db_ok = True
    db_error = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001 - intentionally broad for a health check
        db_ok = False
        db_error = str(exc)

    return Response({
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "database_error": db_error,
    })


class LocationViewSet(viewsets.ModelViewSet):
    module = "admin"
    permission_classes = [ModulePermission]
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(self.request.user, "Created", "Location", instance.name, instance=instance)

    def destroy(self, request, *args, **kwargs):
        # Location.delete() raises ProtectedError for the core (Bahrain)
        # location , caught here and turned into a clean 400, not left to
        # bubble up as an unhandled 500. Verified this needed explicit
        # handling rather than assumed DRF does it automatically.
        instance = self.get_object()
        try:
            name = instance.name
            instance.delete()
        except ProtectedError as exc:
            return Response({"detail": str(exc.args[0] if exc.args else exc)}, status=400)
        log_audit(request.user, "Deleted", "Location", name)
        return Response(status=204)


class AppSettingsView(APIView):
    """
    Church-wide switches an administrator controls from the UI.

    Exposed as a flat object rather than a list of key/value rows,
    because the frontend wants `settings.auto_assign_newcomers`, not to
    hunt through an array. Reading is open to any authenticated user
    (the assignment screen needs to know the current state to label
    itself correctly), but only the admin module can change anything.
    """
    permission_classes = [IsAuthenticated]

    BOOL_KEYS = {
        "auto_assign_newcomers": True,   # key -> default when unset
    }

    def get(self, request):
        return Response({
            k: AppSetting.get_bool(k, default) for k, default in self.BOOL_KEYS.items()
        })

    def patch(self, request):
        if not user_can_view_module(request.user, "admin"):
            return Response(
                {"detail": "Only administrators can change church settings."}, status=403,
            )

        unknown = set(request.data) - set(self.BOOL_KEYS)
        if unknown:
            return Response(
                {"detail": f"Unknown setting(s): {', '.join(sorted(unknown))}."}, status=400,
            )

        for key in request.data:
            value = request.data[key]
            if not isinstance(value, bool):
                return Response({key: "Must be true or false."}, status=400)
            AppSetting.set_bool(key, value)
            log_audit(
                request.user,
                "Enabled setting" if value else "Disabled setting",
                "Setting", key, "",
            )

        return Response({
            k: AppSetting.get_bool(k, default) for k, default in self.BOOL_KEYS.items()
        })
