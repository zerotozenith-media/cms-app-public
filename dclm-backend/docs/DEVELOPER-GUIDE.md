# Developer Guide

Everything needed to run, understand, and extend this system without
asking anyone. If something here is wrong or missing, that is a bug in
this document.

Read [BUSINESS-CASE.md](BUSINESS-CASE.md) first if you have not. Several
design decisions only make sense once you know what the church is trying
to achieve.

---

## 1. Getting it running

### What you need
- Python 3.12+
- Node 20+
- No database server for local work; SQLite is used by default

### Backend

```bash
cd dclm-backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

The API is now on `http://localhost:8000/api/`.

### Frontend

In a second terminal:

```bash
cd dclm-frontend
npm install
cp .env.example .env.local
npm run dev
```

The app is on `http://localhost:5173`. If your backend is not on port
8000, edit `VITE_API_BASE_URL` in `.env.local`.

### Getting data to look at

There is no seed command in the repository, deliberately: the church's
real data should not be mixed with fixtures. Create what you need:

```bash
python manage.py shell
```

```python
from core.models import Location
from accounts.models import Role, RolePermission, User
from members.models import Member
import datetime

bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)

role = Role.objects.create(name="Administrator")
for module in ["members", "attendance", "newcomers", "finance", "goals", "reports", "admin"]:
    RolePermission.objects.create(
        role=role, module=module,
        can_view=True, can_create=True, can_edit=True, can_delete=True,
    )

user = User.objects.create_user(
    email="you@example.com", password="ChangeMe123!", role=role,
    first_name="Your", last_name="Name",
)
member = Member.objects.create(
    surname="Name", first_name="Your", location=bahrain,
    joined_date=datetime.date(2020, 1, 1), category="Worker",
)
user.member = member
user.save()
```

Log in with that email and password. Note the category must be exactly
`"Worker"`, `"Worker in Training"` or `"General Member"`; these are the
stored values, not slugs.

### Running the tests

```bash
python manage.py test          # all 246
python manage.py test members  # one app
python manage.py test members.tests_assignment.EligibleShepherdsEndpointTestCase
```

The full suite takes roughly three and a half minutes. It uses an
in-memory database and needs no setup.

---

## 2. How it is put together

```
dclm-backend/          Django 5 + Django REST Framework
  accounts/            Users, roles, permissions, audit log
  attendance/          Meeting types, sessions, check-in
  core/                Locations, dashboard, app settings
  finance/             Funds, giving, expenses, projects
  goals/               Goals and their calculations
  members/             Members, households, follow-up, assignment
  newcomers/           Newcomer pipeline, tasks, milestones
  enquiries/           Online enquiries and their conversion to newcomers
  reports/             Monthly reports, testimonies, weekly notes
  config/settings/     base.py, local.py, production.py
  deploy/              install.sh, plus ready-made systemd, nginx and cron files
  docs/                This guide, the business case, data dictionaries

dclm-frontend/         React 18 + TypeScript + Vite
  src/api/             One module per domain: hooks wrapping the API
  src/components/      Reusable pieces, grouped by area
  src/pages/           One folder per module, matching the nav
  src/types/           TypeScript shapes mirroring API responses
  src/help/            Help topics and guide content
  src/context/         Auth context
  src/styles/          design-system.css holds every shared class
```

39 models, 56 registered routes.

### Data flow

The frontend never calls `fetch` directly. Every request goes through a
hook in `src/api/`, which uses the shared `apiClient` (axios with the
JWT attached) and TanStack Query for caching.

```
Component  ->  hook in src/api/  ->  apiClient  ->  Django view
                                                       |
                                                    serializer
                                                       |
                                                     model
```

Mutations invalidate the query keys they affect, which is how a screen
refreshes after a change. **This is the single most common source of
"the save worked but nothing updated" bugs.** A key that does not match
the one a query registered under fails silently, with no error anywhere.
If a screen will not refresh, check the key first.

---

## 3. Permissions

Nearly every rule in the system flows from this, so it is worth
understanding properly.

A **User** has one **Role**. A Role has **RolePermission** rows, one per
module, each carrying `can_view`, `can_create`, `can_edit`, `can_delete`.

The modules are: `members`, `attendance`, `newcomers`, `finance`,
`goals`, `reports`, `outreach`, `admin`.

### On the backend

A ViewSet declares its module and uses `ModulePermission`:

```python
class MemberViewSet(LocationScopedQuerySetMixin, viewsets.ModelViewSet):
    module = "members"
    permission_classes = [ModulePermission]
```

`ModulePermission` maps the HTTP method to the right flag: GET needs
`can_view`, POST needs `can_create`, PATCH/PUT need `can_edit`, DELETE
needs `can_delete`.

**A view that forgets to declare `module` is denied, not allowed.** That
is deliberate: an accidental 403 is a bug report, an accidental leak is
a breach.

For code outside a ViewSet, use `user_can_view_module(user, "finance")`
from `accounts.permissions`.

### On the frontend

Two layers, both needed:

1. `NAV_ITEMS` in `src/lib/nav.ts` gives each item a `module`; the
   sidebar hides what the role cannot view.
2. Routes pass `requiredModule` to `ProtectedRoute`, so typing a URL
   directly redirects rather than showing an empty shell.

Neither is a security control. The backend is. These exist so the app
does not show people doors that will not open.

### Location scoping

A user with a `location` set sees only that location's data. A user with
none sees everything. `LocationScopedQuerySetMixin` applies this
automatically to any ViewSet whose model has a `location` field.

Deliberate exception: **check-in has no location restriction.** Any
member can be checked into any session, because visiting members are
normal.

---

## 4. Conventions worth following

### Status changes go through dedicated actions, never PATCH

Three fields cannot be changed by a plain PATCH, and this is enforced by
making them read-only on the serializer:

| Field | Change it via | Why |
|---|---|---|
| `Member.category` | `POST /api/members/{id}/move-category/` | Writes a dated history entry at the same time |
| `Newcomer.stage` | `POST /api/newcomers/{id}/change-stage/` | Records who moved them and when |
| `*.done` on tasks | `POST .../complete/` | Requires the four outcome fields |

A PATCH of `{done: true}` returns 200 and changes nothing. That is worse
than an error, so the frontend must never attempt it.

### Names come from one place

`accounts.names.display_name(user)` prefers the linked member's name,
then the account's first and last name, then the email. Use it
everywhere. Calling `user.get_full_name() or user.email` directly will
show an email address on screens where a person's name belongs, because
accounts are often created without name fields filled in.

### Aggregates belong on the queryset

`Member.total_given` is annotated in `MemberViewSet.get_queryset()`, not
computed per object in the serializer. A per-object `.aggregate()` looks
harmless and turns into one query per row.

If you add an aggregate annotation, **re-apply `.order_by()`
explicitly.** Django silently drops the model's default ordering once a
GROUP BY is involved, and unordered pagination can repeat or skip rows.

### Dates use `timezone.localdate()`

Never `timezone.now().date()`. That returns the UTC date, so for roughly
three hours every night it is a day behind Bahrain time. Every "today"
in this codebase uses `localdate()`.

### Every form field needs a real label association

`htmlFor` on the label, matching `id` on the input. Screen readers need
it, and Playwright's label-based locators refuse to match without it, so
tests catch this.

### No em dashes

Anywhere. Use a colon, a comma, a full stop, or an en dash for empty
table cells.

---

## 5. Adding a feature, end to end

Say you are adding a "prayer request" record.

**1. Model** in the app it belongs to:

```python
class PrayerRequest(models.Model):
    member = models.ForeignKey("members.Member", on_delete=models.CASCADE,
                               related_name="prayer_requests")
    text = models.TextField()
    created_at = models.DateField(default=timezone.localdate)
    answered = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
```

**2. Migration:** `python manage.py makemigrations && python manage.py migrate`

**3. Serializer.** Make anything with side effects read-only.

**4. ViewSet,** declaring the module:

```python
class PrayerRequestViewSet(viewsets.ModelViewSet):
    module = "members"
    permission_classes = [ModulePermission]
    queryset = PrayerRequest.objects.select_related("member")
    serializer_class = PrayerRequestSerializer
```

`select_related` on every foreign key the serializer reads, or you get
one query per row.

**5. URL** in that app's `urls.py`. Register specific paths *before* any
`:id` route, or the parameter route swallows them.

**6. Tests.** Cover the happy path, permission denial, and any rule that
matters. Aim to test behaviour rather than implementation.

**7. Types** in `src/types/`, matching the serializer exactly.

**8. Hooks** in `src/api/`, with correct query keys and invalidation.

**9. Component,** reusing what exists in `src/components/`.

**10. Route and nav** if it needs them, with `requiredModule` set.

**11. Verify in a browser**, not just by compiling. Check desktop and
390px, watch for console errors, and confirm the change persists after a
reload.

---

## 6. The parts most likely to surprise you

### The absence check

`python manage.py check_absences`

Finds sessions past their threshold (three hours after the meeting's
`start_time`), treats anyone not checked in as absent, and creates a
follow-up task for their shepherd.

Rules it applies:
- Only meeting types with `counts_for_absence=True`
- Only those with a `start_time` set; without one there is nothing to
  measure against, so it is skipped rather than guessed
- One task per member per session, so re-running is safe
- A member with an existing open task does not get a second one, but
  once that is resolved a later absence does create a new task

**Nothing runs this automatically.** It needs scheduling at deployment.
See the deployment runbook.

### Shepherd assignment

`members/assignment.py` holds the logic. Two rules in order: household
first so families stay together, then whoever carries the fewest people.

Preview and apply are separate requests. The preview writes nothing.
This is why the endpoint is a GET that returns proposed changes, and a
POST that accepts them back.

Only users whose linked member is in the Worker category are eligible.
`/api/members/eligible-shepherds/` returns exactly that set, so the UI
cannot offer someone the API would reject.

### The four required outcome fields

`contact_goal`, `contact_scripture`, `contact_root_cause`,
`contact_next_step`. All required by `complete()`.

There is also a legacy `contact_notes` field. Records created before the
structured fields existed only have that, and the display component
falls back to it. Do not write to it in new code.

### Online enquiries

Someone who contacted the church online but has not attended. Kept in
its own app rather than folded into newcomers, because an enquirer has
no location, no meeting attended, and the pipeline ends at "attended"
rather than "integrated". Mixing them would inflate newcomer figures
with people who were never in the room.

`Enquiry.convert` creates the linked Newcomer, records the source as
"Instagram (online enquiry)" or similar, and keeps the enquiry with a
`converted_newcomer` link. Keeping it is the whole point: it is what
makes "how many online enquiries became members" answerable.

Governed by the `newcomers` module permission, not its own: the same
people do both jobs, and a separate module would be one more thing for
every church to configure for no benefit.

`python manage.py seed_enquiry_sources` creates the usual platforms.
Without it an administrator opens the add form to an empty dropdown.

**Campaigns and the `outreach` permission.** A `Campaign` records an
advert and what it cost. It is behind its own module rather than
`admin`, because whoever runs the church's adverts is not necessarily an
administrator and should be able to see performance without also being
able to create accounts.

`EnquirySerializer.to_representation` removes the campaign fields
entirely for a role without `outreach`, rather than blanking them: an
empty field invites the question, an absent one does not. The frontend
hides the tab and `ProtectedRoute` blocks the URL, but the serializer is
the actual control.

Cost per newcomer is `None` until someone converts. Reporting zero would
read as free.

### Notifications

`core/notifications.py` holds the single `send_notification` function.
Nothing else touches an email API directly, so adding WhatsApp later
means writing one more backend there rather than editing every place
that notifies someone.

`core/digests.py` holds what the emails say, kept apart from both
sending and scheduling so wording can change in one place.

Two commands: `send_followup_digests` (shepherds, morning after a
tracked service) and `send_leadership_summary` (weekly). Neither emails
per task; that would be unreadable within a week.

Sending never raises. A bad address must not stop the rest of a run.

`NOTIFICATIONS_ENABLED` defaults to False, so a staging copy of the real
database cannot email the congregation by accident. Local development
sets it True with the console backend, so digests print to the terminal.

### App settings

`AppSetting` is a small key/value store for church-wide switches an
administrator changes from the UI, reached at `/api/settings/`. Reading
is open to any authenticated user; only `admin` can change anything.

It is deliberately not a `settings.py` constant. These are operational
choices the church owns, not deployment configuration.

---

## 7. Testing approach

Tests live in each app: `tests.py`, plus a separate file where a
subject deserves one (`members/tests_assignment.py`,
`attendance/tests_check_absences.py`,
`newcomers/tests_public_registration.py`).

What is worth testing here:

- **Permission denial**, not just the happy path. Several tests exist
  purely to prove a role cannot reach something.
- **Rules with judgment in them.** The no-duplicate-task rule, the
  household rule, and the distinction between blocking a second open
  task and allowing a genuinely new absence.
- **Query counts** where an N+1 would hurt. `assertNumQueries` at two
  different data sizes proves the count stays constant rather than
  pinning an exact number that changes whenever a field is added.
- **Dates relative to today**, never hardcoded. A test with a fixed date
  passes today and fails next month.

For frontend work there is no test runner configured. Verify in a real
browser: click the thing, confirm it persisted after a reload, watch the
console, and check 390px. Compiling is not evidence that anything works.

---

## 8. Settings and environment

Three settings files. `base.py` holds shared configuration; `local.py`
and `production.py` import from it.

Local development uses SQLite and needs no environment variables beyond
what `.env.example` provides.

Production requires:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Long random string, never committed |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames |
| `DATABASE_URL` | PostgreSQL connection string |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Where the frontend is served from |

Production settings already enable SSL redirect, secure cookies and HSTS.
Verify with:

```bash
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check --deploy
```

JWT access tokens last 8 hours, refresh tokens 14 days, and refresh
tokens rotate.

---

## 8b. Deploying

`bash deploy/install.sh` on a fresh Ubuntu server does everything:
packages, database, .env with generated secrets, migrations, the first
administrator, the frontend build, gunicorn, nginx, and the scheduled
jobs. It asks three questions and is safe to re-run.

Two commands support it:

- `bootstrap_admin` creates the first administrator plus the location
  and role it needs. Reads credentials from the environment rather than
  arguments, so the password stays out of shell history. Idempotent.
- `preflight` checks a server is genuinely ready: DEBUG off, real secret
  key, PostgreSQL not SQLite, WeasyPrint's system libraries present, the
  cron jobs actually scheduled, tracked meetings having start times,
  backups configured. Exits non-zero on problems, so it works in a
  pipeline.

`preflight` exists because several of these fail silently in ways that
look like broken software. An unscheduled absence check means no
follow-up task is ever created, and missing PDF libraries only surface
when someone tries to generate a monthly report.

The `deploy/` folder holds `dclm.service`, `nginx.conf` and
`crontab.example`, so config is copied rather than retyped.

## 9. Known gaps

Honest list, not hidden in a backlog:

- **No way to log a planned absence.** Someone who has told the church
  they will be away still generates a task. The shepherd closes it,
  noting the absence was known.
- **No bulk assign for newcomers.** Members only.
- **No undo for auto-assign.** The preview step exists precisely because
  of this.
- **No frontend test suite.** Verification is manual browser testing.
- **The main JS bundle is around 517KB.** Fine over a normal connection,
  worth code-splitting if it grows much further.
- **HSTS preload is off.** Deliberate, to be enabled a few weeks after
  go-live once HTTPS is proven stable.
