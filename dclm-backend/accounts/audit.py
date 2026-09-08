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
    AuditLog.objects.create(
        user=user,
        user_name_snapshot=display_name(user) if user else "System",
        action=action,
        entity_type=entity_type,
        entity_name=entity_name,
        details=details,
    )
    if instance is not None:
        from core.audit_context import mark_explicitly_logged
        model_label = f"{instance._meta.app_label}.{instance._meta.model_name}"
        mark_explicitly_logged(model_label, instance.pk)
