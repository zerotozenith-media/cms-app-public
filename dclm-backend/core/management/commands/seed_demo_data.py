"""
Phase 4.2 , realistic, internally-consistent demo/test data for local
development. Confirmed scope: no real church data exists yet, so this
generates synthetic-but-realistic data, not an import/migration script.
Confirmed parameters: ~2.5 years of history, small-church scale
(~40 members).

Idempotency works differently here than the smaller seeders
(seed_default_goals, generate_recurring_sessions): with several hundred
interconnected records across every app, granular per-record dedup
isn't practical. Instead, this checks a single anchor record up front
(the admin user) and refuses to run a second time at all if the data
already exists , safe to re-run, but re-running is a deliberate no-op,
not a reconciliation.

This is synthetic data for local development only. Per the standing
"no mock/fake/synthetic data as fallback" rule: that rule is about
never silently substituting fake data for real data in a live report,
dashboard, or client-facing deliverable. This command is the opposite
case , an explicit, visible, developer-invoked tool whose entire
purpose is generating clearly-synthetic data, run deliberately by a
developer who knows exactly what they're doing. Real reports and
dashboards never call this; they only ever read whatever is actually
in the database.
"""
import datetime
from decimal import Decimal
import random

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Location
from accounts.models import Role, RolePermission, User
from attendance.models import MeetingType, AttendanceSession, AttendanceSessionMember
from members.models import Household, Member, MemberCategoryHistory
from newcomers.models import (
    NewcomerSource, MilestoneType, FollowUpUrgencySetting,
    Newcomer, NewcomerStatusHistory, NewcomerMilestone, NewcomerTask,
)
from newcomers.intake import create_auto_tasks
from finance.models import Fund, PaymentMethod, ExpenseCategory, Project, Giving, Expense
from reports.models import Service, Department, Testimony, WeeklyNote

RNG = random.Random(42)  # fixed seed , a reproducible first run, not a repeat-safety mechanism

TODAY = timezone.localdate()
HISTORY_YEARS = 2.5
START_DATE = TODAY - datetime.timedelta(days=int(365 * HISTORY_YEARS))

FIRST_NAMES_M = [
    "Chinedu", "Emeka", "Ifeanyi", "Obinna", "Chukwuemeka", "Kelechi", "Tobenna",
    "Ahmed", "Yusuf", "Hassan", "David", "Samuel", "Daniel", "Joseph", "Michael",
    "Uchenna", "Kingsley", "Victor", "Chidi", "Ikechukwu",
]
FIRST_NAMES_F = [
    "Ngozi", "Chioma", "Adaeze", "Grace", "Blessing", "Fatima", "Amina", "Sarah",
    "Deborah", "Esther", "Ruth", "Comfort", "Peace", "Faith", "Precious",
    "Chiamaka", "Onyinye", "Adaora", "Ifeoma", "Nkechi",
]
SURNAMES = [
    "Uguru", "Thomas", "Karim", "Osei", "Okafor", "Eze", "Nwosu", "Okonkwo",
    "Adeyemi", "Balogun", "Al-Sayed", "Hassan", "Ibrahim", "Chukwu", "Obi",
    "Nnamdi", "Okoro", "Anyanwu", "Bello", "Musa", "Yusuf", "Dosumu",
]


def rand_date(start, end):
    days = (end - start).days
    if days <= 0:
        return start
    return start + datetime.timedelta(days=RNG.randint(0, days))


def unique_phone(used, prefix="+973 3"):
    while True:
        candidate = f"{prefix}{RNG.randint(100000, 999999)}"
        if candidate not in used:
            used.add(candidate)
            return candidate


class Command(BaseCommand):
    help = "Seeds ~2.5 years of realistic, internally-consistent demo data for local development."

    def handle(self, *args, **options):
        if User.objects.filter(email="chinedu@dclm-bh.org").exists():
            self.stdout.write(self.style.WARNING(
                "Demo data already seeded (chinedu@dclm-bh.org exists) , refusing to run again. "
                "This command doesn't reconcile partial state; wipe the database first if you "
                "genuinely want to regenerate from scratch."
            ))
            return

        # The automatic audit-log signal (core/signals.py) fires on every
        # model save/delete across every tracked app , correct and wanted
        # for real staff actions, but seeding ~1,000+ rows here would
        # flood the Audit Log with synthetic "System created X" noise
        # instead of a real staff history. Confirmed empirically: an
        # unguarded first run of this command produced 1,493 audit
        # entries, nearly all from the bulk history generation below, not
        # from anything a real admin would want to see. Disconnected for
        # the whole seeding pass and guaranteed reconnected via finally ,
        # a freshly-seeded system with an empty audit log is exactly what
        # a real newly-deployed one looks like before staff start using
        # it, which matches this command's own stated scope.
        from django.db.models.signals import post_save, post_delete
        from core.signals import audit_on_save, audit_on_delete
        post_save.disconnect(audit_on_save)
        post_delete.disconnect(audit_on_delete)
        try:
            with transaction.atomic():
                bahrain, others = self._seed_locations()
                admin_role, coord_role = self._seed_roles_and_users(bahrain, others)
                meeting_types = self._seed_meeting_types()
                self._seed_attendance_history(meeting_types, bahrain, others)
                households, members, used_phones = self._seed_members_households(bahrain, others)
                self._seed_newcomers(bahrain, others, members, used_phones)
                funds, methods, categories = self._seed_finance_config()
                self._seed_finance_history(funds, methods, categories, bahrain, others, members)
                services, departments = self._seed_reports_config()
                self._seed_testimonies_and_notes(services, departments, members)
                self._seed_shepherds_and_followup(bahrain, members)
                self._seed_enquiries(members)
        finally:
            post_save.connect(audit_on_save)
            post_delete.connect(audit_on_delete)

        call_command("seed_default_goals")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Seeded ~{HISTORY_YEARS} years of demo data "
            f"({Member.objects.count()} members, {AttendanceSession.objects.count()} sessions, "
            f"{Newcomer.objects.count()} newcomers, {Giving.objects.count()} giving entries, "
            f"{Expense.objects.count()} expenses)."
        ))

    # --- Locations ---

    def _seed_locations(self):
        bahrain, _ = Location.objects.get_or_create(
            id="bahrain", defaults={"name": "Bahrain", "is_core": True},
        )
        others, _ = Location.objects.get_or_create(
            id="others", defaults={"name": "Others", "note": "Qatar , supporting location"},
        )
        self.stdout.write("Seeded locations.")
        return bahrain, others

    # --- Roles and Users ---

    def _seed_roles_and_users(self, bahrain, others):
        admin_role, _ = Role.objects.get_or_create(name="Administrator")
        coord_role, _ = Role.objects.get_or_create(name="Location Coordinator")
        for role, full in [(admin_role, True), (coord_role, False)]:
            # "outreach" governs campaign and spend data. Included here so
            # the demo administrator can actually see the Outreach screen;
            # a real church grants it only to whoever runs the advertising.
            for module in ["members", "attendance", "newcomers", "finance",
                           "goals", "reports", "outreach", "admin"]:
                RolePermission.objects.get_or_create(
                    role=role, module=module,
                    defaults={
                        "can_view": True, "can_create": True,
                        "can_edit": full, "can_delete": full,
                    } if full else {
                        "can_view": True, "can_create": True,
                        "can_edit": module in ("members", "attendance", "newcomers"),
                        "can_delete": False,
                    },
                )

        User.objects.create_user(
            email="chinedu@dclm-bh.org", password="RealPass123!", role=admin_role,
            first_name="Chinedu", last_name="Uguru",
        )
        User.objects.create_user(
            email="grace@dclm-bh.org", password="GracePass123!", role=coord_role, location=bahrain,
            first_name="Grace", last_name="Thomas",
        )
        User.objects.create_user(
            email="ahmed@dclm-bh.org", password="AhmedPass123!", role=coord_role, location=others,
            first_name="Ahmed", last_name="Karim",
        )
        self.stdout.write("Seeded roles and 3 users.")
        return admin_role, coord_role

    # --- Meeting types ---

    def _seed_meeting_types(self):
        specs = [
            # The main service tracks absence, which is what drives
            # follow-up. Without a start time the check has nothing to
            # measure "a few hours after" against, so it is set too.
            dict(id="fri-worship", name="Friday Worship Service", day="Friday",
                 frequency="weekly", detail_level="detailed", monthly_target=45,
                 counts_for_absence=True, start_time=datetime.time(18, 0)),
            dict(id="mon-bs", name="Monday Bible Study", day="Monday",
                 frequency="weekly", detail_level="detailed", monthly_target=25),
            dict(id="sat-workers", name="Saturday Workers Meeting", day="Saturday",
                 frequency="weekly", detail_level="simple", monthly_target=15),
            dict(id="gck", name="General Church Konferencia", day="",
                 frequency="occasional", detail_level="detailed", monthly_target=None),
        ]
        meeting_types = {}
        for spec in specs:
            mt, _ = MeetingType.objects.get_or_create(id=spec["id"], defaults=spec)
            meeting_types[spec["id"]] = mt
        self.stdout.write(f"Seeded {len(meeting_types)} meeting types.")
        return meeting_types

    # --- Attendance history ---

    def _seed_attendance_history(self, meeting_types, bahrain, others):
        weekday_map = {"Friday": 4, "Monday": 0, "Saturday": 5}
        count = 0
        for mt_id, base_total, growth in [
            ("fri-worship", 34, 10), ("mon-bs", 16, 6), ("sat-workers", 9, 3),
        ]:
            mt = meeting_types[mt_id]
            weekday = weekday_map[mt.day]
            d = START_DATE + datetime.timedelta(days=(weekday - START_DATE.weekday()) % 7)
            week = 0
            total_weeks = int((TODAY - START_DATE).days / 7)
            while d <= TODAY:
                # gentle realistic growth over the full span, plus week-to-week noise,
                # plus an occasional dip (holidays / bad weather / etc.)
                progress = week / max(total_weeks, 1)
                trend = base_total + growth * progress
                noise = RNG.gauss(0, trend * 0.12)
                dip = -trend * RNG.uniform(0.25, 0.45) if RNG.random() < 0.06 else 0
                total = max(3, round(trend + noise + dip))

                # the most recent 1-2 occurrences haven't been filled in yet , realistic
                is_recent_unfilled = d > TODAY - datetime.timedelta(days=10)
                location = bahrain if RNG.random() > 0.15 else others

                if is_recent_unfilled:
                    AttendanceSession.objects.create(
                        meeting_type=mt, date=d, location=location, mode="in-person", status="pending",
                    )
                else:
                    if mt.detail_level == "detailed":
                        women = round(total * RNG.uniform(0.5, 0.56))
                        men = total - women
                        youth = round(total * RNG.uniform(0.12, 0.2))
                        youth_boys = youth // 2
                        youth_girls = youth - youth_boys
                        children = round(total * RNG.uniform(0.08, 0.15))
                        children_boys = children // 2
                        children_girls = children - children_boys
                        men = max(0, men - youth - children)
                        women = max(0, women)
                        session = AttendanceSession.objects.create(
                            meeting_type=mt, date=d, location=location, mode="in-person", status="filled",
                            men=men, women=women, youth_boys=youth_boys, youth_girls=youth_girls,
                            children_boys=children_boys, children_girls=children_girls,
                            track_named=False,
                        )
                    else:
                        women = round(total * RNG.uniform(0.4, 0.5))
                        men = total - women
                        session = AttendanceSession.objects.create(
                            meeting_type=mt, date=d, location=location, mode="in-person", status="filled",
                            men=men, women=women,
                        )
                    count += 1
                d += datetime.timedelta(days=7)
                week += 1

        # A handful of occasional GCK-style gatherings, spread realistically
        gck = meeting_types["gck"]
        for _ in range(int(HISTORY_YEARS * 2)):
            d = rand_date(START_DATE, TODAY - datetime.timedelta(days=14))
            AttendanceSession.objects.create(
                meeting_type=gck, date=d, location=bahrain, mode="in-person", status="filled",
                men=RNG.randint(30, 55), women=RNG.randint(35, 60),
                youth_boys=RNG.randint(5, 12), youth_girls=RNG.randint(5, 12),
                children_boys=RNG.randint(4, 10), children_girls=RNG.randint(4, 10),
            )
            count += 1

        self.stdout.write(f"Seeded {count} filled attendance sessions (plus recent pending ones).")

    # --- Members and Households ---

    def _seed_members_households(self, bahrain, others):
        used_phones = set()
        households = []
        for _ in range(18):
            hname = f"{RNG.choice(SURNAMES)} Household"
            households.append(Household.objects.create(
                name=hname,
                address=f"Building {RNG.randint(5, 900)}, Road {RNG.randint(100, 4000)}, Manama",
                phone=unique_phone(used_phones),
            ))

        target_total = 42
        # realistic category distribution for a small church's leadership pyramid
        n_worker = round(target_total * 0.15)
        n_training = round(target_total * 0.25)
        n_general = target_total - n_worker - n_training

        members = []
        plan = (
            [("Worker", ) for _ in range(n_worker)]
            + [("Worker in Training", ) for _ in range(n_training)]
            + [("General Member", ) for _ in range(n_general)]
        )
        RNG.shuffle(plan)

        for i, (final_category,) in enumerate(plan):
            gender = RNG.choice(["Male", "Female"])
            first = RNG.choice(FIRST_NAMES_M if gender == "Male" else FIRST_NAMES_F)
            surname = RNG.choice(SURNAMES)
            joined = rand_date(START_DATE - datetime.timedelta(days=365 * 2), TODAY - datetime.timedelta(days=30))
            location = bahrain if RNG.random() > 0.18 else others
            household = RNG.choice(households) if RNG.random() > 0.35 else None

            member = Member.objects.create(
                surname=surname, first_name=first, gender=gender,
                date_of_birth=rand_date(datetime.date(1955, 1, 1), datetime.date(2008, 1, 1)),
                phone=unique_phone(used_phones),
                email=f"{first.lower()}.{surname.lower()}{i}@example.com" if RNG.random() > 0.3 else "",
                category="General Member",  # starts here; progressed below via real history
                location=location, joined_date=joined, household=household,
            )
            members.append(member)

            # Realistic progression history for anyone who ends up above General Member ,
            # gives the quarter/year "moved to" Goals real signal, not just a static category.
            if final_category in ("Worker in Training", "Worker"):
                training_date = rand_date(joined + datetime.timedelta(days=90), TODAY - datetime.timedelta(days=30))
                MemberCategoryHistory.objects.create(
                    member=member, from_category="General Member", to_category="Worker in Training",
                    changed_date=training_date,
                )
                member.category = "Worker in Training"
                if final_category == "Worker":
                    worker_date = rand_date(
                        training_date + datetime.timedelta(days=120), TODAY - datetime.timedelta(days=1),
                    )
                    MemberCategoryHistory.objects.create(
                        member=member, from_category="Worker in Training", to_category="Worker",
                        changed_date=worker_date,
                    )
                    member.category = "Worker"
                member.save()

        self.stdout.write(f"Seeded {len(households)} households and {len(members)} members.")
        return households, members, used_phones

    # --- Newcomers ---

    def _seed_newcomers(self, bahrain, others, members, used_phones):
        source_names = ["Church website", "Walk-in", "Invited by a member", "Social media",
                         "Church website (QR self-registration)"]
        sources = {n: NewcomerSource.objects.get_or_create(name=n)[0] for n in source_names}
        salvation, _ = MilestoneType.objects.get_or_create(name="Salvation")
        baptism, _ = MilestoneType.objects.get_or_create(name="Water Baptism")
        for stage, amber, red in [("new", 3, 6), ("contacted", 5, 10), ("visiting", 15, 30)]:
            FollowUpUrgencySetting.objects.get_or_create(
                stage=stage, defaults={"amber_days": amber, "red_days": red},
            )

        leaders = list(User.objects.filter(role__name="Location Coordinator"))
        count = 0
        for _ in range(55):
            gender = RNG.choice(["Male", "Female"])
            first = RNG.choice(FIRST_NAMES_M if gender == "Male" else FIRST_NAMES_F)
            surname = RNG.choice(SURNAMES)
            location = bahrain if RNG.random() > 0.2 else others
            created = rand_date(START_DATE, TODAY)
            age_days = (TODAY - created).days

            # Older contacts have realistically resolved; only recent ones are still "active".
            # The chance of staying unresolved in "visiting" must fall sharply with age ,
            # nobody stays in active follow-up limbo for years without resolving one way
            # or the other, so a flat probability regardless of age (the first version of
            # this) produced newcomers "visiting" for 500+ days, which looked like stale
            # data, not a believable pipeline.
            if age_days > 240:
                stage = RNG.choices(["integrated", "not-interested"], weights=[55, 45])[0]
            elif age_days > 60:
                stage = RNG.choices(
                    ["integrated", "not-interested", "visiting"],
                    weights=[40, 30, max(2, 30 - (age_days - 60) // 6)],
                )[0]
            elif age_days > 21:
                stage = RNG.choices(["visiting", "contacted", "integrated"], weights=[40, 35, 25])[0]
            else:
                stage = RNG.choices(["new", "contacted"], weights=[60, 40])[0]

            n = Newcomer.objects.create(
                name=f"{first} {surname}", source=RNG.choice(list(sources.values())),
                location=location, stage="new", created_at=created, stage_since=created,
                assigned_to=RNG.choice(leaders) if leaders and RNG.random() > 0.25 else None,
                gender=gender, phone=unique_phone(used_phones),
                is_first_timer=RNG.random() > 0.3, is_new_resident=RNG.random() > 0.75,
                wants_visit=RNG.random() > 0.6, wants_to_know_more=RNG.random() > 0.5,
                wants_salvation_info=RNG.random() > 0.7,
            )
            create_auto_tasks(n)

            # Walk the newcomer through a realistic stage history to the resolved stage
            stage_path = {
                "new": ["new"], "contacted": ["new", "contacted"],
                "visiting": ["new", "contacted", "visiting"],
                "integrated": ["new", "contacted", "visiting", "integrated"],
                "not-interested": ["new", "contacted", "not-interested"],
            }[stage]
            cursor = created
            for step in stage_path[1:]:
                cursor = rand_date(cursor + datetime.timedelta(days=2), min(cursor + datetime.timedelta(days=40), TODAY))
                NewcomerStatusHistory.objects.create(newcomer=n, stage=step, date=cursor, note="")
            n.stage = stage
            n.stage_since = cursor
            if stage == "not-interested":
                n.not_interested_note = RNG.choice([
                    "Was only visiting family, not relocating.", "Already attends another church.",
                    "Not currently looking for a church home.",
                ])
            n.save()

            if stage == "integrated":
                NewcomerMilestone.objects.create(
                    newcomer=n, milestone_type=salvation,
                    achieved_date=rand_date(created, cursor),
                )
                if RNG.random() > 0.4:
                    NewcomerMilestone.objects.create(
                        newcomer=n, milestone_type=baptism,
                        achieved_date=rand_date(cursor, min(cursor + datetime.timedelta(days=90), TODAY)),
                    )

            # Mark some auto-created tasks done, realistically, for resolved/older newcomers
            if stage in ("integrated", "not-interested", "visiting"):
                for task in n.tasks.all():
                    if RNG.random() > 0.25:
                        task.done = True
                        task.save()
            count += 1

        self.stdout.write(f"Seeded {count} newcomers across the full pipeline.")

    # --- Finance config ---

    def _seed_finance_config(self):
        fund_names = ["Tithe", "Offering", "Missions", "Building"]
        funds = {n: Fund.objects.get_or_create(name=n)[0] for n in fund_names}
        method_names = ["Cash", "Online Transfer"]
        methods = {n: PaymentMethod.objects.get_or_create(name=n)[0] for n in method_names}
        cat_names = ["Rent", "Utilities", "Outreach", "Maintenance", "Administration"]
        categories = {n: ExpenseCategory.objects.get_or_create(name=n)[0] for n in cat_names}
        self.stdout.write("Seeded finance config lists.")
        return funds, methods, categories

    # --- Finance history ---

    def _seed_finance_history(self, funds, methods, categories, bahrain, others, members):
        giving_members = [m for m in members if RNG.random() > 0.4]  # some giving stays anonymous
        d = START_DATE
        giving_count = 0
        while d <= TODAY:
            # weekly giving, loosely correlated with a realistic Friday-Worship-sized crowd
            base = RNG.uniform(420, 640)
            Giving.objects.create(
                date=d, fund=funds["Tithe"], method=RNG.choice(list(methods.values())),
                amount=round(base, 3), location=bahrain,
                member=RNG.choice(giving_members) if RNG.random() > 0.5 else None,
            )
            Giving.objects.create(
                date=d, fund=funds["Offering"], method=RNG.choice(list(methods.values())),
                amount=round(RNG.uniform(140, 280), 3), location=bahrain,
            )
            if RNG.random() > 0.6:
                Giving.objects.create(
                    date=d, fund=RNG.choice([funds["Missions"], funds["Building"]]),
                    method=RNG.choice(list(methods.values())),
                    amount=round(RNG.uniform(50, 300), 3), location=others,
                )
            giving_count += 2
            d += datetime.timedelta(days=7)

        expense_count = 0
        d = START_DATE.replace(day=1)
        while d <= TODAY:
            Expense.objects.create(
                date=d, category=categories["Rent"], amount=round(RNG.uniform(850, 1050), 3),
                location=bahrain, description="Monthly hall rent",
            )
            Expense.objects.create(
                date=d + datetime.timedelta(days=RNG.randint(2, 10)),
                category=categories["Utilities"], amount=round(RNG.uniform(90, 220), 3),
                location=bahrain, description="Electricity and water",
            )
            if RNG.random() > 0.55:
                cat = RNG.choice([categories["Outreach"], categories["Maintenance"], categories["Administration"]])
                Expense.objects.create(
                    date=d + datetime.timedelta(days=RNG.randint(1, 25)),
                    category=cat, amount=round(RNG.uniform(40, 320), 3), location=bahrain,
                    description=f"{cat.name} expense",
                )
            expense_count += 2
            d = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)  # next month

        Project.objects.get_or_create(
            id="qatar-building", defaults=dict(
                name="Qatar Building Project", location=others,
                description="Fund for a dedicated worship space in Qatar.",
                target_amount=20000, status="Active",
            ),
        )
        self.stdout.write(f"Seeded ~{giving_count} giving entries and ~{expense_count} expenses.")

    # --- Reports config, testimonies, weekly notes ---

    def _seed_reports_config(self):
        service_names = ["Friday Worship Service", "Monday Bible Study", "Saturday Workers Meeting"]
        services = {n: Service.objects.get_or_create(name=n)[0] for n in service_names}
        dept_names = ["Follow-up / Care", "Ushering", "Choir", "Media", "Children's Church"]
        departments = {n: Department.objects.get_or_create(name=n)[0] for n in dept_names}
        self.stdout.write("Seeded reports config lists.")
        return services, departments

    def _seed_testimonies_and_notes(self, services, departments, members):
        testimony_texts = [
            "God healed me after we prayed as a church family.",
            "I got a new job after months of prayer and fasting.",
            "My family situation improved after the prayer chain.",
            "I passed my exams after the church prayed for me.",
            "God provided for our rent when we had nothing left.",
            "My relationship was restored after counsel from the pastor.",
        ]
        t_count = 0
        d = START_DATE
        while d <= TODAY:
            if RNG.random() > 0.55:
                member = RNG.choice(members)
                anon = RNG.random() > 0.7
                Testimony.objects.create(
                    member_name="" if anon else member.full_name, is_anonymous=anon,
                    date=d, service=RNG.choice(list(services.values())),
                    text=RNG.choice(testimony_texts),
                )
                t_count += 1
            d += datetime.timedelta(days=7)

        n_count = 0
        d = START_DATE
        while d <= TODAY:
            for dept in departments.values():
                if RNG.random() > 0.5:
                    WeeklyNote.objects.create(
                        department=dept, week_label=f"{d.strftime('%d %b')}–{(d + datetime.timedelta(days=6)).strftime('%d %b %Y')}",
                        week_start=d,
                        highlights=f"Good turnout for {dept.name.lower()} this week.",
                        challenges="Could use more volunteers." if RNG.random() > 0.5 else "",
                        prayer_points="Continued strength for the team." if RNG.random() > 0.6 else "",
                    )
                    n_count += 1
            d += datetime.timedelta(days=28)  # roughly monthly per department, not every week

        self.stdout.write(f"Seeded {t_count} testimonies and {n_count} weekly notes.")

    # --- Shepherds, check-in, follow-up, enquiries ---
    #
    # Added when the follow-up, enquiries and outreach features landed.
    # Without these the relevant screens seed empty, which reads as the
    # features being broken rather than simply unused.

    def _seed_shepherds_and_followup(self, bahrain, members):
        """Assign shepherds, check people in to recent services, and
        create follow-up tasks in a realistic mix of states."""
        from members.models import MemberFollowUpTask
        from attendance.models import AttendanceSessionMember

        workers = [m for m in members if m.category == Member.Category.WORKER]
        shepherd_users = list(User.objects.filter(member__isnull=False))
        if not shepherd_users:
            # Link a few worker records to accounts so tasks have somebody
            # to belong to.
            for i, worker in enumerate(workers[:3]):
                user = User.objects.filter(member__isnull=True).first()
                if not user:
                    break
                user.member = worker
                user.save()
                shepherd_users.append(user)
        if not shepherd_users:
            return 0, 0, 0

        # Most members have a shepherd; a couple deliberately do not, so
        # the "Unassigned" count on screen is not always zero.
        assigned = 0
        for i, member in enumerate(members):
            if i % 11 == 0:
                continue
            member.assigned_to = shepherd_users[i % len(shepherd_users)]
            member.save(update_fields=["assigned_to"])
            assigned += 1

        # Named check-in on the most recent tracked sessions, with a few
        # people absent so follow-up has something to act on.
        tracked = list(
            AttendanceSession.objects
            .filter(meeting_type__counts_for_absence=True, status="filled")
            .order_by("-date")[:3]
        )
        checked_in = 0
        absentees = []
        for session in tracked:
            at_location = [m for m in members if m.location_id == session.location_id]
            present = at_location[:max(1, int(len(at_location) * 0.75))]
            missing = at_location[len(present):]
            for member in present:
                AttendanceSessionMember.objects.get_or_create(
                    session=session, member=member,
                    defaults={"mode": "online" if checked_in % 9 == 0 else "in-person"},
                )
                checked_in += 1
            absentees.append((session, missing))

        # Follow-up tasks: some open, some overdue, some completed with a
        # full record, so every filter on the screen shows something.
        tasks = 0
        for session, missing in absentees:
            for i, member in enumerate(missing[:4]):
                due = session.date + datetime.timedelta(days=2)
                task = MemberFollowUpTask.objects.create(
                    member=member,
                    text=f"Missed {session.meeting_type.name}, check in",
                    due_date=due,
                    assigned_to=member.assigned_to,
                    missed_session=session,
                    missed_meeting_name=session.meeting_type.name,
                    missed_date=session.date,
                )
                tasks += 1
                if i % 3 == 0:
                    task.done = True
                    task.contact_date = due
                    task.contact_method = "Home visit"
                    task.contact_goal = "Find out why they missed and reconnect them"
                    task.contact_scripture = "Hebrews 10:25, on not forsaking the assembling together"
                    task.contact_root_cause = "New work shift clashing with the service time"
                    task.contact_next_step = "Attending the midweek study for now, call again next month"
                    task.save()

        self.stdout.write(
            f"Assigned {assigned} shepherd(s), checked in {checked_in}, "
            f"created {tasks} follow-up task(s)."
        )
        return assigned, checked_in, tasks

    def _seed_enquiries(self, members):
        """Online enquiries and the campaigns that produced them."""
        from enquiries.models import EnquirySource, Campaign, Enquiry, EnquiryTask
        from newcomers.models import Newcomer, NewcomerSource

        call_command("seed_enquiry_sources", verbosity=0)
        by_name = {s.name: s for s in EnquirySource.objects.all()}
        instagram = by_name.get("Instagram")
        facebook = by_name.get("Facebook")
        whatsapp = by_name.get("WhatsApp")

        campaigns = [
            Campaign.objects.create(
                name="Christmas Service 2025", source=facebook, spend=Decimal("120.000"),
                started_on=TODAY - datetime.timedelta(days=250),
                ended_on=TODAY - datetime.timedelta(days=220)),
            Campaign.objects.create(
                name="Reels: Why We Gather", source=instagram, spend=Decimal("80.000"),
                started_on=TODAY - datetime.timedelta(days=60)),
            Campaign.objects.create(
                name="None (organic)", spend=Decimal("0")),
        ]

        leaders = list(User.objects.filter(member__isnull=False))
        people = [
            ("Joy Mensah", instagram, "", "@joymensah", "new",
             "Saw your reel, when are your services?", "Riffa", campaigns[1]),
            ("Ahmed Rahman", facebook, "+973 3300 1122", "", "contacted",
             "Clicked the Christmas advert, asking about location", "Manama", campaigns[0]),
            ("Blessing Okoro", whatsapp, "+973 3900 8877", "", "invited",
             "A friend forwarded your number, wants to visit", "", campaigns[2]),
            ("Daniel Okafor", facebook, "+973 3311 4455", "", "attended",
             "Asked about the midweek Bible study", "Muharraq", campaigns[0]),
            ("Sara Ahmed", instagram, "", "@sara_bh", "not-pursuing",
             "Asked if there is a youth group", "", campaigns[2]),
        ]

        created = 0
        for name, source, phone, handle, stage, text, area, campaign in people:
            enquiry = Enquiry.objects.create(
                name=name, source=source or instagram, phone=phone, social_handle=handle,
                enquiry_text=text, area=area, stage=stage, campaign=campaign,
                received_at=TODAY - datetime.timedelta(days=RNG.randint(3, 40)),
                assigned_to=RNG.choice(leaders) if leaders else None,
                not_pursuing_note="Has since joined a church near her home"
                if stage == "not-pursuing" else "",
            )
            created += 1

            # One who actually turned up, so the conversion figures and
            # the outreach report are not all zeroes.
            if stage == "attended":
                source_name = f"{enquiry.source.name} (online enquiry)"
                nc_source, _ = NewcomerSource.objects.get_or_create(name=source_name)
                newcomer = Newcomer.objects.create(
                    name=enquiry.name, source=nc_source, location=enquiry.assigned_to.location
                    if enquiry.assigned_to and enquiry.assigned_to.location
                    else Location.objects.get(id="bahrain"),
                    stage="visiting", created_at=enquiry.received_at,
                    stage_since=TODAY, phone=enquiry.phone, email=enquiry.email,
                )
                enquiry.converted_newcomer = newcomer
                enquiry.save(update_fields=["converted_newcomer"])

            if stage in ("new", "contacted", "invited"):
                task = EnquiryTask.objects.create(
                    enquiry=enquiry, text="Reply and invite to the next service",
                    due_date=TODAY + datetime.timedelta(days=RNG.randint(-4, 5)),
                    assigned_to=enquiry.assigned_to,
                )
                if stage == "invited":
                    task.done = True
                    task.contact_date = TODAY - datetime.timedelta(days=2)
                    task.contact_method = "WhatsApp"
                    task.contact_goal = "Invite them to Friday service"
                    task.contact_scripture = "Psalm 122:1"
                    task.contact_root_cause = "New to Bahrain and looking for a church home"
                    task.contact_next_step = "Coming this Friday, send the address"
                    task.save()

        self.stdout.write(
            f"Seeded {created} online enquiries across {len(campaigns)} campaign(s)."
        )
        return created
