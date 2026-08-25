from django.db import models
from django.utils import timezone


class EnquirySource(models.Model):
    """
    Where an online enquiry came from: Instagram, WhatsApp, Facebook,
    the website contact form, and so on.

    Editable rather than a fixed list, for the same reason newcomer
    sources are: which platforms matter changes over time, and the
    church should not need a developer to add one.
    """
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Campaign(models.Model):
    """
    An advert or outreach push, with what it cost.

    Separate from EnquirySource on purpose: the source is the platform
    ("Facebook"), the campaign is the specific push ("Christmas Service
    2026"). Knowing the platform tells the church where people come
    from; knowing the campaign tells them which advert actually worked
    and what it cost to reach one person.

    Campaign and spend are marketing data, gated behind the `outreach`
    permission. A follow-up worker calling someone should see the person
    and how to reach them, not what the church paid to find them.
    """
    name = models.CharField(max_length=150, unique=True)
    source = models.ForeignKey(
        "enquiries.EnquirySource", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="campaigns",
        help_text="The platform this ran on, where it was a single platform.",
    )
    spend = models.DecimalField(
        max_digits=10, decimal_places=3, default=0,
        help_text="What was spent, in BHD. Zero for organic, unpaid pushes.",
    )
    started_on = models.DateField(null=True, blank=True)
    ended_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_on", "name"]

    def __str__(self):
        return self.name


class Enquiry(models.Model):
    """
    Someone who contacted the church online and left a way to reach
    them, but has not attended a service.

    Deliberately separate from Newcomer. A newcomer is someone who came
    to a meeting: they have a location, a meeting they attended, and a
    pipeline ending in Integrated. An enquirer may live anywhere, may
    never have set foot in the building, and the immediate goal is
    different: make contact, then invite them. Folding them into the
    newcomer pipeline would quietly inflate newcomer figures with people
    who were never visitors.

    When an enquirer does attend, the convert action moves them across
    and records where they originally came from, so the church can see
    how many online enquiries turn into people in the room.
    """

    class Stage(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        INVITED = "invited", "Invited"
        ATTENDED = "attended", "Attended"
        NOT_PURSUING = "not-pursuing", "Not pursuing"

    name = models.CharField(max_length=150)
    source = models.ForeignKey(
        "enquiries.EnquirySource", on_delete=models.PROTECT, related_name="enquiries",
    )
    # At least one contact field is required, enforced at the API layer
    # rather than in the database: a social handle alone is often all the
    # church has at first, and refusing to record that would lose people.
    phone = models.CharField(max_length=40, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    social_handle = models.CharField(
        max_length=150, blank=True, default="",
        help_text="Their username on the platform they contacted us through.",
    )

    enquiry_text = models.TextField(
        blank=True, default="",
        help_text="What they asked about, in their words where possible.",
    )
    # Free text, not a Location foreign key: an enquirer may be anywhere,
    # including outside Bahrain, and forcing them into one of the
    # church's locations would be a lie.
    area = models.CharField(
        max_length=150, blank=True, default="",
        help_text="Where they are, if they said. May be outside Bahrain.",
    )

    # Optional and separately permissioned: most enquiries are organic,
    # and only roles with outreach access ever see this.
    campaign = models.ForeignKey(
        "enquiries.Campaign", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="enquiries",
    )

    # Marketing attribution. Only ever exposed to roles with the
    # `outreach` permission, so a follow-up worker never sees it.
    campaign = models.ForeignKey(
        "enquiries.Campaign", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="enquiries",
    )

    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.NEW)
    stage_since = models.DateField(default=timezone.localdate)
    received_at = models.DateField(default=timezone.localdate)

    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="enquiries_assigned",
    )
    not_pursuing_note = models.TextField(blank=True, default="")

    # Set when they attend and are converted. Keeping the enquiry rather
    # than deleting it is what makes "how many enquiries became members"
    # answerable at all.
    converted_newcomer = models.OneToOneField(
        "newcomers.Newcomer", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="from_enquiry",
    )

    class Meta:
        ordering = ["-received_at", "name"]
        verbose_name_plural = "Enquiries"

    def __str__(self):
        return f"{self.name} ({self.source})"

    @property
    def best_contact(self):
        """Whatever we actually have, in order of how directly it reaches
        a person."""
        return self.phone or self.email or self.social_handle or ""


class EnquiryStatusHistory(models.Model):
    """Every stage change, so a leader can see how an enquiry progressed
    rather than only where it ended up."""
    enquiry = models.ForeignKey(
        "enquiries.Enquiry", on_delete=models.CASCADE, related_name="status_history",
    )
    stage = models.CharField(max_length=20, choices=Enquiry.Stage.choices)
    note = models.TextField(blank=True, default="")
    date = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name_plural = "Enquiry status history"

    def __str__(self):
        return f"{self.enquiry}: {self.stage}"


class EnquiryTask(models.Model):
    """
    Follow-up for an enquiry.

    Same shape as NewcomerTask and MemberFollowUpTask, including the four
    required outcome fields, so a worker learns one pattern rather than
    three. The contact methods differ, since these people are reached
    online rather than visited at home.
    """

    class Method(models.TextChoices):
        PHONE_CALL = "Phone call", "Phone call"
        WHATSAPP = "WhatsApp", "WhatsApp"
        SOCIAL_MESSAGE = "Social media message", "Social media message"
        EMAIL = "Email", "Email"
        HOME_VISIT = "Home visit", "Home visit"
        OTHER = "Other", "Other"

    enquiry = models.ForeignKey(
        "enquiries.Enquiry", on_delete=models.CASCADE, related_name="tasks",
    )
    text = models.CharField(max_length=300)
    due_date = models.DateField()
    done = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="enquiry_tasks_assigned",
    )

    contact_date = models.DateField(null=True, blank=True)
    contact_method = models.CharField(max_length=30, choices=Method.choices, blank=True, default="")
    contact_goal = models.TextField(blank=True, default="")
    contact_scripture = models.TextField(blank=True, default="")
    contact_root_cause = models.TextField(blank=True, default="")
    contact_next_step = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["due_date"]

    def __str__(self):
        return f"{self.enquiry}: {self.text}"
