"""
Reusable helper for writing AuditLog entries. Explicit calls (e.g.
"Marked Not Interested", login/logout) take priority over the automatic
signal-based logging in core/signals.py , calling this with a real model
instance marks it as "already specifically logged" for this request, so
the generic automatic entry is skipped for that same save.
"""
from .models import AuditLog
from .names import display_name


def log_audit(user, action, entity_type, entity_name="", details="", instance=None):
    entry = AuditLog.objects.create(
        user=user,
        user_name_snapshot=display_name(user) if user else "System",
        action=action,
        entity_type=entity_type,
        entity_name=entity_name,
        details=details,
    )
    if instance is not None:
        from core.audit_context import mark_explicitly_logged, pop_auto_entry
        model_label = f"{instance._meta.app_label}.{instance._meta.model_name}"
        mark_explicitly_logged(model_label, instance.pk)

        # A creation fires post_save before the view can mark it, so a
        # generic entry already exists by now. Remove it, or the log shows
        # the same action twice and credits one of them to "System".
        auto_id = pop_auto_entry(model_label, instance.pk)
        if auto_id is not None and auto_id != entry.pk:
            AuditLog.objects.filter(pk=auto_id).delete()

    return entry
