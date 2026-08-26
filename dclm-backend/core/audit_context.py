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


# The generic entry the signal writes, remembered so an explicit entry
# written moments later can replace it.
#
# The ordering is the problem this solves: post_save fires DURING the
# save, but a view calls log_audit() with the instance AFTER it. So at
# the moment the signal checks was_explicitly_logged() the answer is
# always False for a creation, and every create ended up logged twice,
# once attributed to "System" and once to the real person. The System
# row was the misleading one: it reads as though the software acted on
# its own.
auto_entries_var = contextvars.ContextVar("auto_audit_entries", default=None)


def remember_auto_entry(model_label, pk, entry_id):
    entries = auto_entries_var.get()
    if entries is None:
        entries = {}
        auto_entries_var.set(entries)
    entries[(model_label, pk)] = entry_id


def pop_auto_entry(model_label, pk):
    """The id of the generic entry for this instance, if one was written
    during this request, so the caller can remove it."""
    entries = auto_entries_var.get()
    if not entries:
        return None
    return entries.pop((model_label, pk), None)
