"""
Journeys start and hand over by themselves (F20), from things the app
already records, so nobody has to remember:

  a new enquiry                   starts Online contacts
  an enquiry becoming a newcomer  moves them to Newcomers, history kept
  a new newcomer who ticked "Keep in touch" starts Newcomers
  the Salvation milestone         moves them to New converts
  becoming a member               ends Newcomers (New converts carries on)
  Not Interested or Not pursuing  ends their journey
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from enquiries.models import Enquiry
from newcomers.models import Newcomer, NewcomerMilestone

from . import engine
from .models import Enrolment


@receiver(pre_save, sender=Newcomer)
def _remember_stage(sender, instance, **kwargs):
    instance._old_stage = sender.objects.filter(pk=instance.pk).values_list("stage", flat=True).first() if instance.pk else None


@receiver(post_save, sender=Newcomer)
def _newcomer_saved(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    if created:
        if instance.keep_in_touch and instance.stage not in ("member", "not-interested"):
            engine.start("newcomers", newcomer=instance)
        return
    old = getattr(instance, "_old_stage", None)
    if old == instance.stage:
        return
    active = Enrolment.objects.filter(newcomer=instance, status=Enrolment.Status.ACTIVE)
    if instance.stage == "member":
        for e in active.filter(journey="newcomers"):
            engine.end(e, "Became a member")
    elif instance.stage == "not-interested":
        for e in active:
            engine.end(e, "Marked Not Interested")


@receiver(pre_save, sender=Enquiry)
def _remember_enquiry(sender, instance, **kwargs):
    row = sender.objects.filter(pk=instance.pk).values("stage", "converted_newcomer_id").first() if instance.pk else None
    instance._old = row or {}


@receiver(post_save, sender=Enquiry)
def _enquiry_saved(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    if created:
        if not instance.converted_newcomer_id and instance.stage != "not-pursuing":
            engine.start("online", enquiry=instance)
        return
    old = getattr(instance, "_old", {})
    if instance.converted_newcomer_id and not old.get("converted_newcomer_id"):
        for e in Enrolment.objects.filter(enquiry=instance, status=Enrolment.Status.ACTIVE):
            engine.end(e, "Attended, and moved to Newcomers", moved=True)
        nc = instance.converted_newcomer
        if nc.keep_in_touch and not Enrolment.objects.filter(newcomer=nc, status=Enrolment.Status.ACTIVE).exists():
            engine.start("newcomers", newcomer=nc)
    elif instance.stage == "not-pursuing" and old.get("stage") != "not-pursuing":
        for e in Enrolment.objects.filter(enquiry=instance, status=Enrolment.Status.ACTIVE):
            engine.end(e, "Marked Not pursuing")


@receiver(post_save, sender=NewcomerMilestone)
def _milestone_saved(sender, instance, **kwargs):
    if kwargs.get("raw") or not instance.achieved_date:
        return
    if instance.milestone_type.name.strip().lower() == "salvation":
        nc = instance.newcomer
        member = getattr(nc, "became_member", None)
        if member is not None:
            engine.start("converts", member=member, note="Decision for Christ recorded")
        else:
            engine.start("converts", newcomer=nc, note="Decision for Christ recorded")
