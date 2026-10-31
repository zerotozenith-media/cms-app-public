"""
Month-end balance API (Kay, 30 October 2026).

  GET  /api/month-end/?location=&month=YYYY-MM   the month, its figures and every month's status
  POST /api/month-end/send/        Accounts: counted amount, two counters, note, photo
  POST /api/month-end/approve/     Approve month-end: a different person closes it
  POST /api/month-end/send-back/   Approve month-end: back to the Accounts person with a note
  POST /api/month-end/reopen/      Administrator: reopen the latest closed month, with a reason
  GET/PUT /api/money-settings/?location=   Administrator: cash or bank, start month, opening balance
"""
import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import log_audit
from accounts.names import display_name
from accounts.permissions import user_has

from . import monthend as M
from .monthend_models import MoneySettings, MonthEnd
from .remittance_api import remittance_location


def _month(request):
    raw = request.query_params.get("month") or (request.data.get("month") if hasattr(request.data, "get") else None)
    if not raw:
        return M.first(timezone.localdate())
    try:
        return datetime.date(int(str(raw)[:4]), int(str(raw)[5:7]), 1)
    except (ValueError, TypeError):
        raise ValidationError({"month": "Give the month as YYYY-MM, for example 2026-10."})


def _money(v):
    return None if v is None else str(Decimal(v).quantize(Decimal("0.001")))


def _who(u):
    return display_name(u) if u else ""


def _can(user):
    return {
        "prepare": user_has(user, "finance", "can_edit"),
        "approve": user_has(user, "monthend", "can_edit"),
        "reopen": user_has(user, "admin", "can_edit"),
        "settings": user_has(user, "admin", "can_edit"),
    }


def _approvers(location, exclude=None):
    from accounts.models import User
    out = []
    for u in User.objects.filter(is_active=True):
        if exclude and u.pk == exclude:
            continue
        if u.location_id and u.location_id != location.pk:
            continue
        if user_has(u, "monthend", "can_edit"):
            out.append(u.pk)
    return out


def _payload(location, month, user):
    s = M.settings_for(location)
    rec = M.record(location, month)
    figs = M.figures(location, month)
    shown = figs
    if rec and rec.status in (MonthEnd.Status.SENT, MonthEnd.Status.CLOSED) and rec.expected is not None:
        # What was balanced, exactly as it was sent.
        shown = dict(figs, opening=rec.opening, giving=rec.giving, expenses=rec.expenses,
                     remittance=rec.remittance, expected=rec.expected)
    hist = {r.month: r for r in MonthEnd.objects.filter(location=location)}
    months = []
    for m in M.months(location):
        r = hist.get(m)
        months.append({
            "month": m.strftime("%Y-%m"), "label": M.label(m),
            "status": r.status if r else "open",
            "status_label": r.get_status_display() if r else "Open",
            "closing": _money(r.counted_amount) if r and r.status == MonthEnd.Status.CLOSED else None,
            "difference": _money(r.difference) if r and r.status == MonthEnd.Status.CLOSED else None,
            "approved_by": _who(r.approved_by) if r and r.status == MonthEnd.Status.CLOSED else "",
            "approved_at": r.approved_at.isoformat() if r and r.approved_at else None,
        })
    latest_closed = MonthEnd.objects.filter(location=location, status=MonthEnd.Status.CLOSED).order_by("-month").first()
    return {
        "location": {"id": location.pk, "name": location.name},
        "settings": {"kept_as": s.kept_as, "kept_as_label": s.get_kept_as_display(),
                     "start_month": s.start_month.strftime("%Y-%m"), "start_label": M.label(s.start_month),
                     "opening_balance": _money(s.opening_balance)},
        "month": month.strftime("%Y-%m"), "label": M.label(month),
        "ended": timezone.localdate() >= M.last_day(month),
        "last_day": M.last_day(month).isoformat(),
        "before_start": month < M.first(s.start_month),
        "figures": {k: (_money(v) if isinstance(v, Decimal) else v) for k, v in shown.items()},
        "record": None if not rec else {
            "status": rec.status, "status_label": rec.get_status_display(),
            "counted_amount": _money(rec.counted_amount),
            "counted_by_1": rec.counted_by_1, "counted_by_2": rec.counted_by_2,
            "difference": _money(rec.difference), "difference_note": rec.difference_note,
            "attachment": rec.attachment.url if rec.attachment else None,
            "prepared_by": _who(rec.prepared_by), "prepared_by_id": rec.prepared_by_id,
            "sent_at": rec.sent_at.isoformat() if rec.sent_at else None,
            "approved_by": _who(rec.approved_by), "approved_at": rec.approved_at.isoformat() if rec.approved_at else None,
            "sent_back_note": rec.sent_back_note, "sent_back_by": _who(rec.sent_back_by),
            "sent_back_at": rec.sent_back_at.isoformat() if rec.sent_back_at else None,
            "reopen_reason": rec.reopen_reason, "reopened_by": _who(rec.reopened_by),
            "reopened_at": rec.reopened_at.isoformat() if rec.reopened_at else None,
        },
        "months": months,
        "latest_closed": latest_closed.month.strftime("%Y-%m") if latest_closed else None,
        "can": _can(user),
        "is_preparer": bool(rec and rec.prepared_by_id == user.pk),
    }


class _Base(APIView):
    permission_classes = [IsAuthenticated]

    def setup_(self, request):
        if not user_has(request.user, "finance", "can_view"):
            raise PermissionDenied("Your role does not allow this.")
        return remittance_location(request), _month(request)


class MonthEndView(_Base):
    def get(self, request):
        location, month = self.setup_(request)
        return Response(_payload(location, month, request.user))


class MonthEndSendView(_Base):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        location, month = self.setup_(request)
        user = request.user
        if not user_has(user, "finance", "can_edit"):
            raise PermissionDenied("Only someone whose role can change Giving & Finance balances a month.")
        M.check_can_send(location, month, user)
        rec = M.record(location, month)
        if rec and rec.status != MonthEnd.Status.OPEN:
            raise ValidationError({"detail": f"{M.label(month)} is {rec.get_status_display().lower()}, so it "
                                             f"cannot be sent again."})
        s = M.settings_for(location)
        noun = "Cash counted" if s.kept_as == MoneySettings.KeptAs.CASH else "The bank statement balance"
        errors = {}
        try:
            counted = Decimal(str(request.data.get("counted_amount", "")).replace(",", "").strip())
            if counted < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            counted = None
            errors["counted_amount"] = f"{noun} is needed, in BHD, for example 665.250."
        c1 = (request.data.get("counted_by_1") or "").strip()
        c2 = (request.data.get("counted_by_2") or "").strip()
        if s.kept_as == MoneySettings.KeptAs.CASH:
            if not c1 or not c2:
                errors["counted_by_2"] = "Give the names of the two people who counted the cash together."
            elif c1.lower() == c2.lower():
                errors["counted_by_2"] = "The cash is counted by two different people, so the two names must differ."
        figs = M.figures(location, month)
        note = (request.data.get("difference_note") or "").strip()
        if counted is not None and figs["expected"] is not None and counted != figs["expected"] and not note:
            diff = counted - figs["expected"]
            errors["difference_note"] = (f"There is a difference of BHD {abs(diff):.3f} "
                                         f"({'more' if diff > 0 else 'less'} than expected). Find it, or explain it.")
        if errors:
            raise ValidationError(errors)
        with transaction.atomic():
            rec = rec or MonthEnd(location=location, month=month)
            rec.counted_amount, rec.counted_by_1, rec.counted_by_2 = counted, c1, c2
            rec.difference_note = note
            if request.FILES.get("attachment"):
                rec.attachment = request.FILES["attachment"]
            rec.opening, rec.giving, rec.expenses = figs["opening"], figs["giving"], figs["expenses"]
            rec.remittance, rec.expected = figs["remittance"], figs["expected"]
            rec.status, rec.prepared_by, rec.sent_at = MonthEnd.Status.SENT, user, timezone.now()
            rec.save()
            log_audit(user, "Sent for approval", "Month-end balance", f"{location.name} {M.label(month)}",
                      f"Expected {rec.expected:.3f}, counted {counted:.3f}", instance=rec)
        from alerts.events import notify
        notify(_approvers(location, exclude=user.pk), f"{M.label(month)} is ready to approve",
               f"{display_name(user)} balanced {location.name} for {M.label(month)}. Expected BHD {rec.expected:.3f}, "
               f"counted BHD {counted:.3f}.", "/finance?tab=monthend&month=" + month.strftime("%Y-%m"),
               tag=f"monthend-{location.pk}-{month:%Y%m}", kind="assigned")
        return Response(_payload(location, month, user))


class MonthEndApproveView(_Base):
    def post(self, request):
        location, month = self.setup_(request)
        user = request.user
        if not user_has(user, "monthend", "can_edit"):
            raise PermissionDenied("Only someone whose role includes Approve month-end can approve a month. "
                                   "An administrator gives it in Admin, Roles & Permissions.")
        rec = M.record(location, month)
        if not rec or rec.status != MonthEnd.Status.SENT:
            raise ValidationError({"detail": f"{M.label(month)} has not been sent for approval."})
        if rec.prepared_by_id == user.pk:
            raise ValidationError({"detail": f"You prepared {M.label(month)}, so a different person approves it. "
                                             f"That way every month is checked by two people."})
        figs = M.figures(location, month)
        if figs["expected"] != rec.expected:
            raise ValidationError({"detail": f"The records for {M.label(month)} changed after it was sent, so the "
                                             f"figures no longer match. Send it back so it is balanced again."})
        rec.status, rec.approved_by, rec.approved_at = MonthEnd.Status.CLOSED, user, timezone.now()
        rec.save()
        log_audit(user, "Approved and closed", "Month-end balance", f"{location.name} {M.label(month)}",
                  f"Closing balance {rec.counted_amount:.3f}", instance=rec)
        from alerts.events import notify
        if rec.prepared_by_id:
            notify(rec.prepared_by_id, f"{M.label(month)} is closed",
                   f"{display_name(user)} approved {location.name} for {M.label(month)}. Closing balance "
                   f"BHD {rec.counted_amount:.3f}.", "/finance?tab=monthend&month=" + month.strftime("%Y-%m"),
                   tag=f"monthend-{location.pk}-{month:%Y%m}", kind="assigned")
        return Response(_payload(location, month, user))


class MonthEndSendBackView(_Base):
    def post(self, request):
        location, month = self.setup_(request)
        user = request.user
        if not user_has(user, "monthend", "can_edit"):
            raise PermissionDenied("Only someone whose role includes Approve month-end can send a month back.")
        rec = M.record(location, month)
        if not rec or rec.status != MonthEnd.Status.SENT:
            raise ValidationError({"detail": f"{M.label(month)} has not been sent for approval."})
        note = (request.data.get("note") or "").strip()
        if not note:
            raise ValidationError({"note": "Say what needs correcting, for example \"The 12 October expense has no "
                                           "receipt\"."})
        rec.status, rec.sent_back_note, rec.sent_back_by, rec.sent_back_at = MonthEnd.Status.OPEN, note, user, timezone.now()
        rec.save()
        log_audit(user, "Sent back", "Month-end balance", f"{location.name} {M.label(month)}", note, instance=rec)
        from alerts.events import notify
        if rec.prepared_by_id:
            notify(rec.prepared_by_id, f"{M.label(month)} was sent back",
                   f"{display_name(user)}: {note}", "/finance?tab=monthend&month=" + month.strftime("%Y-%m"),
                   tag=f"monthend-{location.pk}-{month:%Y%m}", kind="assigned")
        return Response(_payload(location, month, user))


class MonthEndReopenView(_Base):
    def post(self, request):
        location, month = self.setup_(request)
        user = request.user
        if not user_has(user, "admin", "can_edit"):
            raise PermissionDenied("Only an administrator can reopen a closed month.")
        rec = M.record(location, month)
        if not rec or rec.status != MonthEnd.Status.CLOSED:
            raise ValidationError({"detail": f"{M.label(month)} is not closed."})
        later = MonthEnd.objects.filter(location=location, month__gt=month,
                                        status__in=[MonthEnd.Status.SENT, MonthEnd.Status.CLOSED]).order_by("month").first()
        if later:
            raise ValidationError({"detail": f"{M.label(later.month)} is {later.get_status_display().lower()} too, "
                                             f"and its opening balance comes from {M.label(month)}. Reopen "
                                             f"{M.label(later.month)} first."})
        reason = (request.data.get("reason") or "").strip()
        if not reason:
            raise ValidationError({"reason": "Say why it is reopened, for example \"Receipt for the 28 October fuel "
                                             "expense handed in late\"."})
        rec.status = MonthEnd.Status.OPEN
        rec.reopen_reason, rec.reopened_by, rec.reopened_at = reason, user, timezone.now()
        rec.approved_by, rec.approved_at = None, None
        rec.save()
        log_audit(user, "Reopened", "Month-end balance", f"{location.name} {M.label(month)}", reason, instance=rec)
        return Response(_payload(location, month, user))


class MoneySettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not user_has(request.user, "finance", "can_view") and not user_has(request.user, "admin", "can_view"):
            raise PermissionDenied("Your role does not allow this.")
        location = remittance_location(request)
        s = M.settings_for(location)
        first_closed = MonthEnd.objects.filter(location=location, status=MonthEnd.Status.CLOSED).order_by("month").first()
        return Response({"location": {"id": location.pk, "name": location.name}, "kept_as": s.kept_as,
                         "start_month": s.start_month.strftime("%Y-%m"),
                         "opening_balance": _money(s.opening_balance),
                         "locked": bool(first_closed or MonthEnd.objects.filter(
                             location=location, month=s.start_month, status=MonthEnd.Status.SENT).exists()),
                         "updated_by": _who(s.updated_by), "updated_at": s.updated_at.isoformat() if s.updated_at else None})

    def put(self, request):
        user = request.user
        if not user_has(user, "admin", "can_edit"):
            raise PermissionDenied("Only an administrator can change how money is kept.")
        location = remittance_location(request)
        s = M.settings_for(location)
        kept = request.data.get("kept_as", s.kept_as)
        if kept not in MoneySettings.KeptAs.values:
            raise ValidationError({"kept_as": "Choose Cash or Bank account."})
        start, opening = s.start_month, s.opening_balance
        if "start_month" in request.data or "opening_balance" in request.data:
            begun = MonthEnd.objects.filter(location=location,
                                            status__in=[MonthEnd.Status.SENT, MonthEnd.Status.CLOSED]).order_by("month").first()
            if begun:
                raise ValidationError({"detail": f"{M.label(begun.month)} is already "
                                                 f"{begun.get_status_display().lower()}, so the start month and "
                                                 f"opening balance can no longer change. Reopen {M.label(begun.month)} "
                                                 f"and every month after it first."})
            try:
                raw = request.data.get("start_month", s.start_month.strftime("%Y-%m"))
                start = datetime.date(int(raw[:4]), int(raw[5:7]), 1)
            except (ValueError, TypeError):
                raise ValidationError({"start_month": "Give the start month as YYYY-MM, for example 2026-07."})
            if start > M.first(timezone.localdate()):
                raise ValidationError({"start_month": "The start month cannot be in the future."})
            try:
                opening = Decimal(str(request.data.get("opening_balance", s.opening_balance)).replace(",", ""))
            except InvalidOperation:
                raise ValidationError({"opening_balance": "Give the opening balance in BHD, for example 0.00."})
            if opening < 0:
                raise ValidationError({"opening_balance": "The opening balance cannot be below zero."})
        before = f"{s.get_kept_as_display()}, from {M.label(s.start_month)}, opening {s.opening_balance:.3f}"
        s.kept_as, s.start_month, s.opening_balance, s.updated_by = kept, start, opening, user
        s.save()
        log_audit(user, "Changed", "Money settings", location.name,
                  f"Was {before}. Now {s.get_kept_as_display()}, from {M.label(s.start_month)}, "
                  f"opening {s.opening_balance:.3f}")
        return self.get(request)
