"""
Request-scoped context shared between CurrentUserMiddleware and the audit
signal handlers. Uses contextvars (not threading.local) so this works
correctly under async views too, not just classic sync Django.
"""
import contextvars

current_user_var = contextvars.ContextVar("current_user", default=None)

# Tracks (app_label.model_name, pk) pairs already given a specific,
# hand-written audit entry during this request , e.g. log_audit() called
# explicitly for "Marked Not Interested". The automatic signal handler
# checks this before writing a generic fallback entry, so a single
# meaningful action never shows up twice in the log.
explicitly_logged_var = contextvars.ContextVar("explicitly_logged", default=None)


def get_current_user():
    return current_user_var.get()


def mark_explicitly_logged(model_label, pk):
    logged = explicitly_logged_var.get()
    if logged is None:
        logged = set()
        explicitly_logged_var.set(logged)
    logged.add((model_label, pk))


def was_explicitly_logged(model_label, pk):
    logged = explicitly_logged_var.get()
    return logged is not None and (model_label, pk) in logged
