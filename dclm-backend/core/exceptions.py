"""
Turn a model's refusal into a message rather than a server error.

A model that refuses a save raises Django's ValidationError, which the
API does not translate on its own, so the person saw a server error with
nothing to act on. This passes it back as an ordinary 400 with the
model's own words.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    # Removing something still in use, such as a fund with giving recorded
    # against it, is refused by the database. Without this the person saw
    # a server error rather than the reason.
    if isinstance(exc, (ProtectedError, RestrictedError)):
        n = len(exc.protected_objects if isinstance(exc, ProtectedError) else exc.restricted_objects)
        return Response(
            {"detail": f"This is still used by {n} record{'s' if n != 1 else ''}, so it cannot "
                       f"be removed."},
            status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "error_dict") else {"detail": exc.messages}
        return Response(detail, status=status.HTTP_400_BAD_REQUEST)
    return exception_handler(exc, context)
