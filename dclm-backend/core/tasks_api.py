"""
An endpoint a scheduler can call to run a scheduled command.

This exists because Azure App Service has no cron. A timer elsewhere
calls this, and the work happens here where the code and the database
settings already are, rather than in a second copy that would drift.

Locked down deliberately, because an endpoint that runs management
commands is worth attacking:

  - only the four scheduled commands can be named, from a fixed list.
    Anything else is refused, so this can never become a way to run
    arbitrary commands
  - a shared secret is required, compared in constant time
  - the secret must be set; if it is missing the endpoint refuses
    everything rather than defaulting to open
  - every call is written to the audit log, successful or not
"""
import hmac
import io
import logging

from django.conf import settings
from django.core.management import call_command
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)

# The only commands this endpoint will ever run. A fixed list rather than
# anything the caller names: the difference between a scheduler and a
# remote shell is exactly this line.
ALLOWED = {
    "check_absences",
    "generate_recurring_sessions",
    "send_followup_digests",
    "send_leadership_summary",
}


@api_view(["POST"])
@permission_classes([AllowAny])
def run_scheduled_task(request):
    secret = getattr(settings, "TASK_SECRET", "") or ""
    if not secret:
        # Refuse rather than default to open. A deployment that forgot to
        # set this should fail loudly, not quietly accept anyone.
        logger.warning("Scheduled task endpoint called but TASK_SECRET is not set.")
        return Response({"detail": "Scheduled tasks are not configured."}, status=503)

    provided = request.headers.get("X-Task-Secret", "")
    if not hmac.compare_digest(provided, secret):
        logger.warning("Scheduled task called with a bad secret.")
        return Response({"detail": "Not authorised."}, status=403)

    command = request.data.get("command", "")
    if command not in ALLOWED:
        return Response(
            {"detail": f"Not a scheduled command. Allowed: {', '.join(sorted(ALLOWED))}."},
            status=400,
        )

    out = io.StringIO()
    try:
        call_command(command, stdout=out)
    except Exception as exc:
        logger.exception("Scheduled command %s failed", command)
        _audit(command, f"Failed: {exc}")
        # 500 so the scheduler records a failed run rather than a green tick.
        return Response({"detail": str(exc)}, status=500)

    output = out.getvalue().strip()
    _audit(command, output[:400] or "Completed")
    return Response({"command": command, "output": output})


def _audit(command, detail):
    """Written to the audit log so scheduled runs are visible in the app,
    not only in a cloud console somebody has to remember to open."""
    try:
        from accounts.audit import log_audit
        log_audit(None, "Scheduled task", "System", command, detail)
    except Exception:
        logger.exception("Could not write the audit entry for %s", command)
