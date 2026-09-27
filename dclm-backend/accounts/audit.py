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
    from core.audit_context import claim_automatic, register_explicit
    fields = dict(
        user=user,
        user_name_snapshot=display_name(user) if user else "System",
        action=action,
        entity_type=entity_type,
        entity_name=entity_name,
        details=details,
    )
    # If the save being described already produced an automatic entry in
    # this request, upgrade that one instead of writing a second.
    model_label = (f"{instance._meta.app_label}.{instance._meta.model_name}"
                   if instance is not None else None)
    existing = claim_automatic(action, entity_type, model_label,
                               instance.pk if instance is not None else None)
    if existing and AuditLog.objects.filter(pk=existing).update(**fields):
        entry = AuditLog.objects.get(pk=existing)
    else:
        entry = AuditLog.objects.create(**fields)
        # Written before the save or delete it describes, so the automatic
        # entry that follows should be skipped.
        register_explicit(action, entity_type, model_label,
                          instance.pk if instance is not None else None)
    if instance is not None:
        from core.audit_context import mark_explicitly_logged
        model_label = f"{instance._meta.app_label}.{instance._meta.model_name}"
        mark_explicitly_logged(model_label, instance.pk)
    return entry


def log_automatic(user, action, entity_type, entity_name, model_label, pk):
    """The generic entry the signal handlers write for any save or delete."""
    from core.audit_context import claim_explicit, register_automatic
    if claim_explicit(action, entity_type, model_label, pk):
        return None       # the view already described this, more fully
    entry = AuditLog.objects.create(
        user=user,
        user_name_snapshot=display_name(user) if user else "System",
        action=action, entity_type=entity_type, entity_name=entity_name,
    )
    register_automatic(model_label, pk, action, entity_type, entry.pk)
    return entry
