"""
Automatic audit logging (Batch 1.5) , connects to every model's
post_save/post_delete signals, not the demo's manually-scattered
logAudit() calls at every individual action.

Known, deliberate limitation: Django signals do not fire for bulk
operations (queryset.update(), bulk_create(), bulk_update(), queryset
.delete()) by design. Anything Phase 2 does in bulk needs an explicit
log_audit() call , this is a genuine gap worth remembering, not
something quietly worked around.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .audit_context import get_current_user, was_explicitly_logged

TRACKED_APP_LABELS = {
    "core", "accounts", "members", "attendance",
    "newcomers", "finance", "goals", "reports",
}

# Excluded even though they're in a tracked app: AuditLog would log itself
# into infinite recursion, and LoginAttempt is already its own dedicated
# security log (Batch 1.4), with login/logout already explicitly audited.
EXCLUDED_MODELS = {"accounts.auditlog", "accounts.loginattempt"}


def _should_track(sender):
    label = f"{sender._meta.app_label}.{sender._meta.model_name}"
    return sender._meta.app_label in TRACKED_APP_LABELS and label not in EXCLUDED_MODELS


@receiver(post_save)
def audit_on_save(sender, instance, created, **kwargs):
    if not _should_track(sender):
        return
    model_label = f"{sender._meta.app_label}.{sender._meta.model_name}"
    if was_explicitly_logged(model_label, instance.pk):
        return  # a specific, hand-written entry already covered this exact save

    from accounts.audit import log_audit
    log_audit(
        user=get_current_user(),
        action="Created" if created else "Updated",
        entity_type=sender._meta.verbose_name.title(),
        entity_name=str(instance),
    )


@receiver(post_delete)
def audit_on_delete(sender, instance, **kwargs):
    if not _should_track(sender):
        return
    from accounts.audit import log_audit
    log_audit(
        user=get_current_user(),
        action="Deleted",
        entity_type=sender._meta.verbose_name.title(),
        entity_name=str(instance),
    )
