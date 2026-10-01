"""
Server addresses for follow-up journeys (F19, F20).

Who can do what:
  - Anyone who can view newcomers can use follow-up.
  - A person following someone up acts on their own people. Those who
    oversee (administrators and coordinators) act on everyone at their
    location.
  - Only administrators covering every location change the message bank,
    as with other church-wide settings.
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.names import display_name
from accounts.permissions import user_has
from core.outstanding import oversees
from core.viewing import scope_location_id

from . import engine
from .models import DISCIPLER_STEPS, BANK_GROUPS, Enrolment, MessageLog, MessageTemplate, PlanStep, SavedMessage, StepDone


def can_follow_up(user):
    return user_has(user, "newcomers", "can_view")


def in_scope(user, enrolment):
    loc = scope_location_id(user)
    pl = engine.location_id(enrolment)
    return not loc or not pl or pl == loc


def can_act(user, enrolment):
    return engine.owner(enrolment) == user or (oversees(user) and in_scope(user, enrolment))


def bank_editor(user):
    return user_has(user, "admin", "can_edit") and not user.location_id


def refuse(msg="You can't do that.", code=status.HTTP_403_FORBIDDEN):
    return Response({"detail": msg}, status=code)


def due_today(user):
    """Everyone due a message today that this user follows up, not yet done."""
    from django.db.models import Q
    # Include plans that ended today with today's message, such as the final
    # gentle message, so the card stays as Sent instead of vanishing.
    qs = Enrolment.objects.filter(Q(status=Enrolment.Status.ACTIVE) | Q(ended_on=timezone.localdate(), log__on_date=timezone.localdate())
                                  ).distinct().select_related("newcomer", "member", "enquiry")
    mine_all = oversees(user)
    rows = []
    for e in qs:
        if not (can_act(user, e) if mine_all else engine.owner(e) == user):
            continue
        entry = engine.todays_entry(e)
        if entry:
            rows.append((e, entry))
    return rows


class TodayView(APIView):
    """Today's messages: every person due something today, for this user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not can_follow_up(request.user):
            return refuse()
        rows = []
        for e, entry in due_today(request.user):
            who = engine.owner(e)
            entry["follower"] = display_name(who) if who else ""
            rows.append(entry)
        order = {"converts": 0, "newcomers": 1, "online": 2}
        rows.sort(key=lambda r: (r["done"] is not None, order[r["journey"]], r["person"]["name"]))
        return Response({"date": timezone.localdate().isoformat(), "results": rows})


class RecordView(APIView):
    """What the sender did today: sent, replied personally, own message, or skipped."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        e = get_object_or_404(Enrolment, pk=pk, status=Enrolment.Status.ACTIVE)
        if not can_act(request.user, e):
            return refuse()
        kind = request.data.get("kind")
        if kind not in MessageLog.Kind.values:
            return refuse("Choose sent, reply, own or skipped.", status.HTTP_400_BAD_REQUEST)
        if e.log.filter(on_date=timezone.localdate()).exists():
            return refuse("Today's message for this person is already recorded.", status.HTTP_400_BAD_REQUEST)
        text = (request.data.get("text") or "").strip()[:4000]
        if kind != MessageLog.Kind.SKIPPED and not text:
            return refuse("The message is empty.", status.HTTP_400_BAD_REQUEST)
        tpl = None
        if request.data.get("template"):
            tpl = MessageTemplate.objects.filter(pk=request.data["template"], active=True).first()
        log = engine.record(e, kind, request.user, text=text, template=tpl)
        return Response({"id": log.id, "day": log.day, "kind": log.kind, "status": Enrolment.objects.get(pk=e.pk).status})


class EnrolmentActionView(APIView):
    """Change the plan, stop or restart messages, or tick a discipler's step."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, action):
        e = get_object_or_404(Enrolment, pk=pk)
        if not can_act(request.user, e):
            return refuse()
        if action == "plan":
            if request.data.get("plan") not in Enrolment.Plan.values:
                return refuse("Choose Standard or Daily.", status.HTTP_400_BAD_REQUEST)
            e.plan = request.data["plan"]; e.save(update_fields=["plan"])
        elif action == "stop":
            if e.status != Enrolment.Status.ACTIVE:
                return refuse("Messages are not running for this person.", status.HTTP_400_BAD_REQUEST)
            e.status, e.ended_on = Enrolment.Status.STOPPED, timezone.localdate()
            e.ended_reason = "Stopped by " + display_name(request.user)
            e.save(update_fields=["status", "ended_on", "ended_reason"])
        elif action == "restart":
            if e.status != Enrolment.Status.STOPPED:
                return refuse("Only stopped messages can be restarted.", status.HTTP_400_BAD_REQUEST)
            e.status, e.ended_on, e.ended_reason = Enrolment.Status.ACTIVE, None, ""
            e.save(update_fields=["status", "ended_on", "ended_reason"])
        elif action == "steps":
            step = int(request.data.get("step", -1))
            if e.journey != "converts" or not 0 <= step < len(DISCIPLER_STEPS):
                return refuse("That step does not exist.", status.HTTP_400_BAD_REQUEST)
            if request.data.get("done"):
                StepDone.objects.get_or_create(enrolment=e, step=step, defaults={"done_on": timezone.localdate(), "by": request.user})
            else:
                StepDone.objects.filter(enrolment=e, step=step).delete()
        else:
            return refuse("Unknown action.", status.HTTP_404_NOT_FOUND)
        return Response(person_payload(e.person, request.user, e))


def person_payload(person, user, focus=None):
    """A person's journeys for the Messages tab: plan strip, log, visits, steps."""
    from members.models import Member
    from newcomers.models import Newcomer
    q = Enrolment.objects.none()
    if isinstance(person, Member):
        q = Enrolment.objects.filter(member=person)
        if person.from_newcomer_id:
            q = q | Enrolment.objects.filter(newcomer_id=person.from_newcomer_id)
    elif isinstance(person, Newcomer):
        q = Enrolment.objects.filter(newcomer=person)
        q = q | Enrolment.objects.filter(enquiry__converted_newcomer=person)
    else:
        q = Enrolment.objects.filter(enquiry=person)
    out = []
    today = timezone.localdate()
    for e in q.order_by("-started", "-id"):
        day = engine.plan_day(e, today)
        if e.plan == Enrolment.Plan.DAILY:
            days = list(range(max(1, day - 3), max(1, day - 3) + 7))
        else:
            steps = list(PlanStep.objects.filter(journey=e.journey).values_list("day", flat=True))
            past = [d for d in steps if d < day][-3:]
            days = (past + [d for d in steps if d >= day])[:7]
        logs = {l.day: l.kind for l in e.log.all()}
        out.append({
            "id": e.id, "journey": e.journey, "journey_label": e.get_journey_display(), "status": e.status,
            "started": e.started.isoformat(), "plan": e.plan, "day": day, "ended_reason": e.ended_reason,
            "ended_on": e.ended_on.isoformat() if e.ended_on else None,
            "belonging": bool(engine.in_belonging(e)),
            "visits": engine.visits(e.newcomer) if e.newcomer_id else None,
            "strip": [{"day": d, "state": logs.get(d) or ("today" if d == day and e.status == "active" else "")} for d in days],
            "log": [{"day": l.day, "kind": l.kind, "theme": l.theme, "text": l.text, "on_date": l.on_date.isoformat(),
                     "by": display_name(l.sent_by) if l.sent_by else ""} for l in e.log.select_related("sent_by")[:30]],
            "steps": ([{"when": w, "what": s, "done": e.steps_done.filter(step=i).exists()} for i, (w, s) in enumerate(DISCIPLER_STEPS)]
                      if e.journey == "converts" else []),
            "can_act": can_act(user, e),
        })
    return {"enrolments": out}


class PersonView(APIView):
    """A person's follow-up journeys, for the Messages tab on their profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not can_follow_up(request.user):
            return refuse()
        person = _lookup(request.query_params, request.user)
        if person is None:
            return refuse("Not found.", status.HTTP_404_NOT_FOUND)
        return Response(person_payload(person, request.user))


def _lookup(params, user):
    """The person asked for, within the user's location."""
    from enquiries.models import Enquiry
    from members.models import Member
    from newcomers.models import Newcomer
    loc = scope_location_id(user)
    for key, model in (("newcomer", Newcomer), ("member", Member), ("enquiry", Enquiry)):
        if params.get(key):
            obj = model.objects.filter(pk=params[key]).first()
            if obj is None:
                return None
            pl = getattr(obj, "location_id", None)
            if loc and pl and pl != loc:
                return None
            return obj
    return None


class StartView(APIView):
    """Start messages for someone, or record a decision for Christ."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        journey = request.data.get("journey")
        if journey not in dict(Enrolment._meta.get_field("journey").choices):
            return refuse("Choose a journey.", status.HTTP_400_BAD_REQUEST)
        if not user_has(request.user, "newcomers", "can_edit"):
            return refuse()
        person = _lookup(request.data, request.user)
        if person is None:
            return refuse("Not found.", status.HTTP_404_NOT_FOUND)
        kind = person._meta.model_name
        kw = {"newcomer": person} if kind == "newcomer" else {"member": person} if kind == "member" else {"enquiry": person}
        note = "Decision for Christ recorded" if journey == "converts" else "Started by " + display_name(request.user)
        if journey == "converts" and kind == "newcomer":
            from newcomers.models import MilestoneType, NewcomerMilestone
            mt = MilestoneType.objects.filter(name__iexact="Salvation").first()
            if mt and not NewcomerMilestone.objects.filter(newcomer=person, milestone_type=mt, achieved_date__isnull=False).exists():
                m, _ = NewcomerMilestone.objects.get_or_create(newcomer=person, milestone_type=mt)
                m.achieved_date = timezone.localdate(); m.save()   # the signal moves them to New converts
        engine.start(journey, note=note, **kw)
        return Response(person_payload(person, request.user), status=status.HTTP_201_CREATED)


class BankView(APIView):
    """The shared message bank. Everyone following up reads it, and only
    administrators covering every location change it."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not can_follow_up(request.user):
            return refuse()
        plan_days = {}
        for s in PlanStep.objects.all():
            plan_days.setdefault(s.template_id, []).append({"journey": s.journey, "day": s.day})
        rows = [{"id": t.id, "journey": t.journey, "theme": t.theme, "number": t.number, "verse": t.verse, "reference": t.reference,
                 "body": t.body, "active": t.active, "plan_days": plan_days.get(t.id, [])}
                for t in MessageTemplate.objects.order_by("id")]   # the order leadership wrote them, Welcome first
        return Response({"groups": [{"key": k, "label": v} for k, v in BANK_GROUPS], "results": rows, "can_edit": bank_editor(request.user)})

    def post(self, request):
        if not bank_editor(request.user):
            return refuse()
        journey, theme, body = request.data.get("journey"), (request.data.get("theme") or "").strip(), (request.data.get("body") or "").strip()
        if journey not in dict(BANK_GROUPS) or not theme or not body:
            return refuse("Choose the journey and theme, and write the message.", status.HTTP_400_BAD_REQUEST)
        n = (MessageTemplate.objects.filter(journey=journey, theme=theme).order_by("-number").values_list("number", flat=True).first() or 0) + 1
        t = MessageTemplate.objects.create(journey=journey, theme=theme[:60], number=n, body=body[:2000],
                                           verse=(request.data.get("verse") or "").strip()[:1000], reference=(request.data.get("reference") or "").strip()[:60])
        return Response({"id": t.id, "number": t.number}, status=status.HTTP_201_CREATED)


class BankItemView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not bank_editor(request.user):
            return refuse()
        t = get_object_or_404(MessageTemplate, pk=pk)
        for f, cap in (("verse", 1000), ("reference", 60), ("body", 2000)):
            if f in request.data:
                setattr(t, f, (request.data.get(f) or "").strip()[:cap])
        if "active" in request.data:
            if not request.data["active"] and t.plan_steps.exists():
                return refuse("This message is used by a plan, so it can't be switched off. Edit its wording instead.", status.HTTP_400_BAD_REQUEST)
            t.active = bool(request.data["active"])
        if not t.body:
            return refuse("The message is empty.", status.HTTP_400_BAD_REQUEST)
        t.save()
        return Response({"id": t.id})


def clean_html(html):
    """Keeps only paragraphs, line breaks, bold and italics, with no attributes."""
    from html.parser import HTMLParser
    from html import escape
    allowed = {"p", "br", "b", "strong", "i", "em"}
    out = []

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag in allowed:
                out.append(f"<{tag}>")
        def handle_endtag(self, tag):
            if tag in allowed and tag != "br":
                out.append(f"</{tag}>")
        def handle_data(self, data):
            out.append(escape(data))
    P(convert_charrefs=True).feed(html)
    return "".join(out)


class SavedView(APIView):
    """My saved messages, visible only to their owner."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"results": [{"id": s.id, "html": s.html} for s in request.user.saved_messages.all()[:50]]})

    def post(self, request):
        html = (request.data.get("html") or "").strip()
        if not html:
            return refuse("The message is empty.", status.HTTP_400_BAD_REQUEST)
        s = SavedMessage.objects.create(user=request.user, html=clean_html(html)[:6000])
        return Response({"id": s.id}, status=status.HTTP_201_CREATED)

    def delete(self, request, pk=None):
        SavedMessage.objects.filter(pk=pk, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
