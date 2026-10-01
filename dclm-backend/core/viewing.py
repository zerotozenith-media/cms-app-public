"""
Which location a person is looking at (F2).

Someone limited to one location always sees that location. Someone who
covers every location sees everything, or the one location they have picked
in the top bar, which the app sends with every request as the
X-Viewing-Location header.

This only ever narrows what is shown. Permission checks, such as which
location a record may be saved to, keep using the account's real location.
"""
import contextvars

_viewing = contextvars.ContextVar("viewing_location", default=None)


class ViewingLocationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _viewing.set((request.headers.get("X-Viewing-Location") or "").strip() or None)
        try:
            return self.get_response(request)
        finally:
            _viewing.reset(token)


def scope_location_id(user):
    """The location to show this person, or None for every location."""
    if not user.is_superuser and user.location_id:
        return user.location_id
    code = _viewing.get()
    if not code:
        return None
    from core.models import Location
    return code if Location.objects.filter(id=code).exists() else None
