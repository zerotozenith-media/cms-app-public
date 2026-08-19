"""
Stashes the requesting user into request-scoped context so the audit
signal handlers (core/signals.py) know who made a change, even though
signals themselves have no access to the HTTP request. Cleared after
every response so nothing leaks between requests.
"""
from .audit_context import current_user_var, explicitly_logged_var


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        user_token = current_user_var.set(user if user and user.is_authenticated else None)
        logged_token = explicitly_logged_var.set(set())
        try:
            response = self.get_response(request)
        finally:
            current_user_var.reset(user_token)
            explicitly_logged_var.reset(logged_token)
        return response
