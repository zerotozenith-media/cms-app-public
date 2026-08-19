"""
Wraps SimpleJWT's authentication to also populate the audit context.

Why this exists: classic Django middleware runs *before* DRF resolves
the JWT-authenticated user (that happens later, inside the view's own
authentication step) , empirically confirmed while building Batch 1.5,
where a diagnostic endpoint showed the middleware layer seeing an
anonymous user even for a correctly JWT-authenticated request.

Wiring this in centrally via DEFAULT_AUTHENTICATION_CLASSES means every
future DRF view gets correct audit attribution automatically , nobody
building Phase 2 endpoints needs to remember to do anything extra.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication

from .audit_context import current_user_var


class AuditAwareJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            user, _token = result
            current_user_var.set(user)
        return result
