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


# Automatic entries written during this request, so an explicit entry
# written after the save can upgrade the automatic one rather than add a
# second line for the same action. Before this the automatic entry fired
# during the save and the view's fuller entry came after, so creates and
# deletes were logged twice.
automatic_entries_var = contextvars.ContextVar("automatic_entries", default=None)


def register_automatic(model_label, pk, action, entity_type, entry_id):
    entries = automatic_entries_var.get()
    if entries is None:
        return            # outside a request: nothing to merge with
    entries.append({"model": model_label, "pk": pk, "action": action,
                    "type": (entity_type or "").lower(), "id": entry_id})


def claim_automatic(action, entity_type, model_label=None, pk=None):
    """The most recent automatic entry this explicit one describes, if any."""
    entries = automatic_entries_var.get()
    if not entries:
        return None
    for i in range(len(entries) - 1, -1, -1):
        e = entries[i]
        if model_label is not None and pk is not None:
            match = e["model"] == model_label and e["pk"] == pk
        else:
            match = e["action"] == action and e["type"] == (entity_type or "").lower()
        if match:
            entries.pop(i)
            return e["id"]
    return None


# Explicit entries written during this request that did not replace an
# automatic one, because the view wrote its entry before the save or
# delete. The automatic entry that follows is then skipped.
explicit_entries_var = contextvars.ContextVar("explicit_entries", default=None)


def register_explicit(action, entity_type, model_label=None, pk=None):
    entries = explicit_entries_var.get()
    if entries is None:
        return
    entries.append({"model": model_label, "pk": pk, "action": action,
                    "type": (entity_type or "").lower()})


def claim_explicit(action, entity_type, model_label, pk):
    entries = explicit_entries_var.get()
    if not entries:
        return False
    for i in range(len(entries) - 1, -1, -1):
        e = entries[i]
        if e["model"] is not None:
            match = e["model"] == model_label and e["pk"] == pk
        else:
            match = e["action"] == action and e["type"] == (entity_type or "").lower()
        if match:
            entries.pop(i)
            return True
    return False
