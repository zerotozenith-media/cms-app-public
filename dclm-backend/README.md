# DCLM Bahrain CMS: Backend

Django + Django REST Framework backend, built against the Phase 0 data
dictionary approved before this code was written , see
[`docs/`](docs/README.md) for the full planning record, now shipped
alongside the code rather than living only in chat history.

## Member Attendance Follow-up (demo approved, backend verified)

The demo for this feature was reviewed and approved before this backend
was finalised. Everything below matches what was signed off.

**What it covers (229 backend tests passing):**
- `Member.assigned_to` (shepherd), `MeetingType.counts_for_absence` and
  `start_time`, `AttendanceSessionMember.mode` (per attendee, so a hybrid
  service can have some people in person and others online)
- Real-time single-tap check-in
  (`POST/DELETE/PATCH /api/attendance-sessions/{id}/check_in/`), kept
  separate from the batch headcount form so concurrent ushers on
  different doors cannot overwrite each other
- `MemberFollowUpTask`, mirroring `NewcomerTask`, with a durable snapshot
  of what was missed
- Four structured completion fields on both member and newcomer tasks
  (goal, scripture shared, root cause, next step agreed). `done` is
  read-only and only settable through `complete()`, which requires all
  four, matching how `category` and `stage` are already handled
- `check_absences` management command: the automatic no-button-needed
  detection. Idempotent on re-run, and distinguishes "block a new task
  while one is still open" from "allow a genuinely new absence once the
  earlier one is resolved"
- Shepherd assignment: `GET/POST /api/members/assign-shepherds/` for
  preview-then-apply, and `POST /api/members/bulk-assign-shepherd/`.
  Household pairing takes priority, then load balancing. Only users
  linked to a Worker-category member can be shepherds. Preview never
  writes anything
- `AppSetting` flag controlling whether newcomers are included in
  auto-assign

**Still to arrange outside the code:** `check_absences` needs scheduling
to run on its own. Plain cron on the app host is the cheapest option and
costs nothing. See the deployment notes when Phase 5 begins.

## Member Attendance Follow-up: complete

246 tests passing. Verified from a clean install: fresh venv, migrate,
full suite.

**Models.** `Member.assigned_to` (shepherd), `MeetingType.counts_for_absence`
and `start_time`, `AttendanceSessionMember.mode`, `MemberFollowUpTask`
with a durable snapshot of what was missed, and four structured outcome
fields on both member and newcomer tasks.

**Endpoints.** Real-time check-in (POST/DELETE/PATCH), member follow-up
tasks with filters and stats, `complete()` actions that require all four
outcome fields, shepherd assignment preview and apply, bulk assign,
eligible shepherds, and church-wide app settings.

**Automation.** `check_absences` treats anyone not checked in as absent a
few hours after a tracked meeting starts and creates a task for their
shepherd. Idempotent on re-run, and distinguishes "block a new task while
one is still open" from "allow a genuinely new absence once the earlier
one is resolved".

**Naming.** `accounts.names.display_name` is the single rule for how a
person's name appears, used by serializers, the audit log, the assignment
engine and PDF reports, so no screen falls back to showing an email
address where a name is expected.

**Still to arrange outside the code.** `check_absences` needs scheduling.
Plain cron on the app host costs nothing and is the simplest option;
GitHub Actions or a cloud timer also work.

## Phase 4.3 , security and performance review

Systematic audit, not spot-checking. Every ViewSet across every app was
checked for `permission_classes` coverage , all correctly declare
`ModulePermission`, with only three deliberate, correctly-scoped
exceptions (login, health check, the hardened public registration
endpoint). Found two real gaps neither test coverage nor manual
exploration had caught, both fixed with real regression tests, not
just patched and moved on.

**A genuine, confirmed-exploitable authorization gap.**
`finance_summary` was a plain function view with only `IsAuthenticated`
, any logged-in user, regardless of their role's actual Finance
permission, could hit it directly and see the Finance page's own
detailed income/expense breakdown. Didn't just reason about this ,
proved it: authenticated as a real Members-only user and confirmed a
200 with real BHD 5,000 in the response, before touching any code.
Fixed by converting it to a class-based view specifically so it could
reuse `ModulePermission` unchanged, the same enforcement every other
endpoint in the app already relies on, rather than write new
permission-checking logic to verify separately. Re-confirmed after the
fix: the same attack now returns 403, and a genuinely authorized user
still gets correct data.

**A real design question, put to the person building this, not decided
unilaterally.** The Dashboard showed the same real finance and
attendance data to any logged-in user , architecturally different from
the `finance_summary` case, since a shared "org overview" home page is
a defensible, common pattern in real systems. Asked rather than
assumed: confirmed the intended behavior is to restrict each section by
the viewer's real per-module permission. Rebuilt accordingly , each of
the four data sections (attendance, finance, newcomers, goals) is now
entirely omitted from the response, not just hidden or zeroed, when the
viewer lacks permission, with an explicit `*_access` flag so the
frontend can tell "restricted" apart from "genuinely empty." A new
`user_can_view_module()` helper reuses the same rule `ModulePermission`
already enforces, rather than duplicating that logic. Verified through
the real browser, not just the API: a Members-only user's dashboard now
shows nothing but her welcome banner and the sections she's actually
permitted , confirmed with zero trace of "Giving" or "Friday Worship"
anywhere in the page, while the Administrator's dashboard is completely
unaffected.

Four new tests confirm the exact contract: a restricted user gets
`false` flags and the real data keys entirely absent (not present with
zero values), a user with only one permission sees only that section,
and a superuser bypasses every check , the same rule every other
permission check in the app already follows.

175 backend tests passing (168 from Phase 4.1 plus 7 new security
tests), verified from a completely clean install.

## Phase 4.1 , end-to-end testing against realistic data volume

Every test throughout Phase 3 used 2-5 hand-crafted records per
feature. With Phase 4.2's ~2.5-year seed data in place, this pass
tested every major flow against real volume instead , and found three
genuine, distinct problems that small test fixtures had made invisible.

**A real N+1 query problem, measured precisely, not assumed.** The
newcomers list , used by the kanban board, fetching all 55 seeded
newcomers at once , took 86.5ms against a ~10ms baseline for every
comparable endpoint. Rather than guess at a fix, counted the actual
queries with `CaptureQueriesContext`: 171 queries for 55 rows. Found
three compounding causes in `NewcomerSerializer`: `get_urgency()` and
`get_milestones()` were each re-querying a tiny static table on every
single object instead of once, and `get_open_tasks_count()` called
`.filter()` on a related manager , which always issues a fresh query,
silently bypassing the viewset's own `prefetch_related`. Fixed by
caching the two static tables once per serialization pass and filtering
the already-prefetched tasks in Python. Confirmed: 171 → 8 queries,
86.5ms → ~27ms. Locked in with a real regression test ,
`assertNumQueries` at both 5 and 50 newcomers, proving the query count
stays constant rather than growing with the list, which is the
invariant that actually matters going forward.

**A second, related fix , caught while checking whether the first fix
generalized, not left as a known gap.** The same category of problem
existed in `Member.total_given` (a live per-object `.aggregate()` call)
and was measurably real at the actual Finance page usage pattern (all
42 members fetched for the giving-entry dropdown): 47 queries, ~37ms.
Fixed by moving the sum to a queryset-level annotation instead ,
one query with a `GROUP BY` rather than one query per member.

**A real correctness regression the performance fix itself would have
introduced, caught before it shipped.** Adding an aggregate
`.annotate()` to the Members queryset silently dropped the model's
default ordering , confirmed directly by inspecting the generated SQL,
which had no `ORDER BY` clause at all. Without one, paginated results
have no guaranteed stable order across pages, which risks duplicate or
skipped rows. Fixed by explicitly re-applying `.order_by("surname",
"first_name")`, then verified two ways: that a client's own explicit
`?ordering=` still correctly overrides the default, and , since this
exact class of bug is specifically about page-to-page consistency ,
by walking every page of the real seeded Members list through the
actual UI and confirming no genuine duplicate ID appeared across pages.
One same-name collision did show up (two distinct members named
"Ahmed Balogun") , checked by ID, not name, and confirmed to be a real,
harmless data coincidence from the seed script's small name pool at
42 members, not a pagination bug.

**A genuine, systemic timezone bug, found via a test that should never
have failed.** A newcomer test asserting `days_in_stage` , a value with
no reasonable way to be anything but deterministic , failed. Traced it
rather than dismissed it: `timezone.now().date()` returns the UTC
calendar date, not the business's configured local date (`TIME_ZONE =
"Asia/Bahrain"`), even with `USE_TZ = True` set correctly. For roughly
3 hours every night (UTC 21:00–24:00, Bahrain's first 3 hours of the
next day), every "today" calculation using this pattern would compute
against the wrong calendar day. Found 13 real occurrences across
attendance, finance, newcomers, members, and goals , recurring session
generation, "income this month," newcomer stage timestamps, follow-up
task due dates, category-change dates, and the goals calculation
engine's reference date. Replaced every one with Django's own correct
built-in, `timezone.localdate()`. Verified directly, not just via tests
passing: confirmed `localdate()` now matches the system's local date
where the old pattern didn't, and confirmed the fix visibly changed
real application output , the seeded Dashboard's follow-up due dates
shifted by exactly the one day they should have.

168 backend tests passing (167 plus the new N+1 regression test),
verified from a completely clean install.

## Phase 4.2 , realistic seed data for local development

`python manage.py seed_demo_data` generates ~2.5 years of internally
consistent, realistic demo data across every app: 42 members with real
category-progression history, ~400 attendance sessions with organic
week-to-week variation (not flat numbers), 55 newcomers spread
realistically across the real pipeline stages, ~300 giving entries and
~80 expenses, testimonies, weekly notes, and three real staff accounts
across roles. Confirmed scope: no real church data exists yet, so this
is synthetic-but-realistic, not an import/migration script , that's a
different, later task if real data ever needs bringing in.

Safe to re-run , checks one anchor record up front and refuses outright
rather than trying to reconcile partial state.

**A real bug caught before delivery, not after:** the first run
produced 1,493 audit log entries , nearly all synthetic seeding noise,
since the automatic audit signal (Batch 1.5) fires on every model save
across the app, and this command creates on that order of rows. A
freshly-seeded system would have shown a completely misleading "history"
of thousands of System actions before any real staff member had ever
logged in. Fixed by disconnecting the audit signal for the whole
seeding pass and reconnecting it in a guaranteed `finally` block, rather
than restructuring the (already correct, already-refined) generation
logic itself. Confirmed: audit log entries after seeding dropped from
1,493 to 14 , all genuinely legitimate (the goal-seeding step that runs
afterward, once signals are back on).

## Batch 3.10 (frontend) , Phase 3 complete, no backend changes needed

The final module batch of Phase 3. The Users, Roles, RolePermissions,
Locations, Households, MeetingTypes, and every simple config-list
endpoint (Funds, Payment Methods, Expense Categories, Newcomer Sources,
Milestone Types, Services, Departments) from earlier batches already
covered everything the real Admin screen needed , including the
protected-core-location safeguard (Batch 0.1) still correctly blocking
deletion of Bahrain. Every real gap found this batch was on the
frontend side , see its README for the full account, including a
route-level permission gap found and fixed that applies across the
whole app, not just Admin.

With this batch, every route in the frontend now has a real screen
behind it , there is no module left showing a placeholder.

## Status: Batch 3.9 (frontend) , a real filter gap caught before it shipped, not after

Almost delivered this one with a "no backend changes needed" note , the
`services`, `departments`, `testimonies`, `weekly-notes`, and
`reports`/`generate` endpoints from Batch 2.6 covered the actual screen
correctly. But before writing that claim down, checking it directly
turned up a real gap: `TestimonyViewSet` and `WeeklyNoteViewSet` had no
`get_queryset()` override at all, meaning the frontend's `service`/
`department` filter dropdowns were sending real query params the
backend silently ignored. The dropdown selection would visibly change,
but nothing would actually filter , exactly the kind of gap that's easy
to miss because the UI *looks* like it's working.

Fixed both, added direct tests for each, then went back and confirmed
it through the actual browser rather than trust the fix from the test
suite alone: submitted two testimonies tagged to different services,
filtered by one, and confirmed only the matching entry showed. 167
backend tests passing.

## Batch 3.8 (frontend) , no backend changes needed

The first frontend batch in a while that didn't surface a real backend
gap. Goals is a small, curated, admin-managed list (14 approved goals),
not the kind of unbounded data that needed a dedicated stats endpoint
the way Members, Attendance, and Finance did , the existing
`GoalSerializer`'s `current_value` and `calculation_error` fields
(Batch 2.5) were already exactly what the real screen needed. The one
real bug this batch found was entirely on the frontend side , see the
frontend README.

## Status: Batch 3.7 (frontend) , finance summary endpoint, and a real local-dev gap fixed

Same pattern as the last three frontend batches: `GivingViewSet` and
`ExpenseViewSet` already had `project`/`category` filtering and
`date`/`amount` ordering, but a `method` filter was missing, and the
stat-row's totals needed a real dedicated aggregation endpoint ,
`GET /api/finance/summary/` , for the same reason as Members/Attendance/
Dashboard: Giving and Expense records accumulate indefinitely, so
"income all-time" can't be a client-side sum of one paginated page.

**One deliberate asymmetry, tested explicitly so it doesn't look like an
inconsistency:** `income_by_fund` shows every fund, including ones with
zero giving , a fund with nothing given yet should show BHD 0, not
disappear, matching the original demo's intent of surfacing inactive
funds as a real signal. `expenses_by_category` does the opposite , only
categories with actual spending are shown. Both behaviors are correct
and intentional; a test for each confirms it, so a future change can't
accidentally "fix" one into matching the other.

**A real bug found through the frontend's file upload, not backend
testing alone.** Uploading a receipt through the real UI succeeded ,
the file saved correctly, the API returned a valid reference , but
clicking "View" 404'd. Traced it to a genuine gap: local dev's
`urls.py` never added Django's standard media-serving pattern, so
nothing was actually serving uploaded files back through the local
dev server. This is specifically a *local development* gap, not a
production one , Azure Blob (Batch 2.8) serves files directly there,
Django never needs to , but it's real: anyone testing locally with the
default SQLite/local-storage setup would hit this exact 404. Fixed with
Django's standard `DEBUG`-guarded static-serving pattern, verified by
re-uploading a real file and confirming the URL now actually returns
the real content, not just a 200.

165 backend tests passing.

## Status: Batch 3.6 (frontend) , real public self-registration endpoint

Building the real Newcomers screen required a genuinely new kind of
backend work: a real, working public self-registration form (confirmed
scope: Bahrain-only , DCLM Bahrain is the main church, Qatar is a
supporting location expected to eventually be phased out). This is a
real unauthenticated write endpoint , a genuine attack surface , so it
got the same class of scrutiny as login.

`POST /api/public/newcomer-registration/`:
- Honeypot field, minimum-submit-timing check, and per-IP rate limiting
  (5 per day), mirroring the proven login pattern from Batch 1.4, with a
  dedicated `PublicRegistrationAttempt` log matching `LoginAttempt`'s design
- Location, source, and stage are never client-controlled , always
  forced server-side (Bahrain, "Church website (QR self-registration)",
  "New"), tested directly by attempting to override them from the client
- The response never leaks the created record's internal ID or fields ,
  just a plain thank-you message
- Shared logic, not duplicated: the invited-by-member matching and
  auto-task-creation logic was factored into `newcomers/intake.py` so
  the authenticated and public paths are provably identical, not just
  similar, and both get tested against the same behavior

**A real bug caught and fixed before it shipped, not after:** an early
version of the validation-failure branch was genuinely garbled , a
meaningless chain of `if False else` conditions that would have logged
every ordinary mistake (like a visitor leaving their name blank) as a
"honeypot" hit, corrupting the security log's accuracy for anyone
reviewing it later. Fixed and given its own regression test.

158 backend tests now passing in total, including a dedicated 14-test
suite specifically for the public endpoint covering the honeypot,
timing, rate-limiting, and the auto-set-field guarantees.

## Status: Batch 3.5 (frontend) added attendance filtering, sorting, and stats

Same category of gap as Members in Batch 3.4 , `AttendanceSessionViewSet`
had no `meeting_type` or `status` query param filtering, and no way to
sort by total headcount at all.

**The sorting gap was more interesting than a missing filter.** `total`
on `AttendanceSession` is a Python property (summing the six headcount
fields), not a database column , so it can't be sorted by by default.
Rather than skip "sort by highest total" or fake it by sorting the
current page client-side (which would only reorder what's already
loaded, not the true dataset), added a real database-level annotation
(`total_computed`, via `F()` expressions) so `?ordering=-total_computed`
sorts correctly across the whole result set. Tested directly: created a
low-total and a high-total session and confirmed the API actually
returns them in the right order, not just that the query doesn't error.

**A second dedicated stats endpoint**, same reasoning as Members: session
history accumulates indefinitely over years of weekly meetings, so
"sessions this month / filled / pending" needed a real aggregate query,
not a client-side count. While building it, caught a portability risk
before it shipped rather than after: an early draft filtered "this
month" using `date__startswith` , a string-prefix match on a `DateField`
that could behave differently between SQLite (local dev) and PostgreSQL
(production, per the approved Azure architecture). Replaced with the
portable `date__year`/`date__month` lookups, and added a specific
regression test , a session from exactly 5 years ago sharing the same
day number , to prove no false match.

## Status: Real intake slip correction (ahead of Batch 3.5)

The user shared the actual DCLM Bahrain newcomer intake slip , the real
paper form used for manual entry (and the QR self-registration form must
capture the same fields, for consistency). Comparing it against the
approved Newcomers schema found several genuinely missing fields: the
approved model never had address, city/governorate, phone, email,
gender, age bracket, or a prayer request field at all, despite the real
church collecting all of these on every single newcomer intake.

Fixed properly, not just patched: `address`, `city_governorate`, `phone`,
`email`, `gender`, `age_group`, `prayer_request`, and `meeting_attended`
(FK to `meeting_types`) added directly to `Newcomer`.

**Two real design decisions, confirmed before building, not assumed:**

1. **`invited_by`** , the slip asks for a person's name. This tries to
   match an existing Member by exact full name, but **only links if the
   match is unambiguous** , tested directly with two members sharing the
   same name, confirming the system correctly declines to guess and
   keeps the name as text-only rather than risk misattributing a
   referral to the wrong person. `invited_by_member` is read-only on the
   API , a client can't set the link directly, only the server-side
   matching logic can, preventing a submitted form from claiming a false
   referral.
2. **The three request checkboxes** (visit / know more / salvation
   interest) each auto-create a real `NewcomerTask` at creation ,
   confirmed explicitly this means task creation only, no automated
   messaging. Tested that the salvation-interest task is genuinely due
   sooner than the other two, reflecting real pastoral urgency, and that
   checking nothing creates nothing.

Also distinguished from the existing `source` field: the slip has two
separate questions ("Invited by" vs. "Learnt about the church from") ,
confirmed these map to two different fields, neither overwriting the
other, rather than conflating them.

## Status: Batch 3.4 (frontend) drove six real backend additions

Building the real Members screen surfaced more genuine gaps than any
frontend batch so far , each one caught and fixed before it caused a
real problem, not after.

1. **Category filtering + category ordering** on `MemberViewSet` , the
   demo's filtering was entirely client-side against a small mock array;
   a real member list needed real server-side filtering.
2. **`total_given`** computed field on `Member`, the same live-aggregate
   pattern already proven safe for `Project.amount_raised` in Batch 2.4.
3. **A global pagination fix.** DRF's default `PageNumberPagination`
   silently ignores a client-supplied `page_size` unless
   `page_size_query_param` is explicitly set , the Members list needed
   page size 8 (matching the demo), the backend default is 25. Fixed
   project-wide with a shared `StandardPagination` class, since every
   future list screen has the same need, not just this one.
4. **A dedicated `/api/members/stats/` endpoint , and a bug caught before
   it shipped, not after.** The first version of the frontend's stat-row
   fetched a large page and counted client-side. After adding the
   `max_page_size=100` cap in the same batch, that approach would have
   silently returned **wrong counts** for any church with more than 100
   members. Caught this by re-reading my own change rather than assuming
   it still worked, and replaced it with a real aggregate-query endpoint
   before it ever reached the frontend.
5. **Household filtering** on `MemberViewSet`, needed for the profile
   page's "other household members" list , referenced in frontend code
   before confirming it existed on the backend; caught and added.
6. **Composed-filter testing**: a Coordinator filtering by category must
   still only see their own location's members , tested this
   composition explicitly, not just each filter independently.

## Status: Batch 3.3 (frontend) added a real backend endpoint too

Building the real Dashboard exposed a genuine architectural need: several
of its numbers (all-time giving/expense totals, Friday Worship's latest
session) require aggregating across potentially many records, and
`GivingViewSet` paginates at 25 per page , a client-side "fetch every
page and sum" approach would be both wasteful and fragile. Added
`GET /api/dashboard/summary/`, a dedicated aggregation endpoint, rather
than working around this on the frontend.

**Location scoping required real care, and got a dedicated test for the
distinction that matters most:** every stat on this endpoint respects
the requesting user's location , a Location Coordinator's Friday Worship
total is genuinely their own location's number, not the church-wide one
, *except* Goals, which have no location field in the approved schema
and represent church-wide progress regardless of who's viewing. Wrote
`test_goals_are_not_location_filtered_even_for_a_scoped_coordinator`
specifically to prove a Coordinator's goal progress matches the
Administrator's, not their own location-scoped subset , this is exactly
the kind of subtle distinction that's easy to get wrong silently, so it
got explicit, direct verification rather than assumed correct by
similarity to the other stats.

## Status: Batch 3.2 (frontend) touched this backend too

While building the real frontend auth flow, two genuine backend gaps
surfaced and were fixed here, not worked around in the frontend:

1. **The login response only returned the role as a name string.** The
   frontend needed real permission data to filter navigation by role ,
   matching by name string would have been exactly the fragile pattern
   deliberately avoided in Batch 2.5's goal `calculation_type` redesign.
   Fixed by enriching the response directly with `role_permissions` and
   `location_name`, avoiding both the fragile-matching risk and an extra
   round-trip after every login.
2. **The login endpoint itself had zero permanent automated tests**,
   despite Batch 1.4 verifying honeypot/lockout/rate-limiting extensively
   at the time , that verification was all manual shell scripts, never
   converted into real coverage. Added a proper `LoginFlowAPITestCase`
   while touching this same code, closing a real gap rather than adding
   only what the immediate task strictly required.

While adding these, an editing mistake on my own part briefly merged two
test classes together (a class declaration line was accidentally deleted
during an edit, causing a later `setUp()` to silently override an
earlier one of the same name) , caught immediately because the new
test's assertions failed with data that didn't match what was expected,
traced to the actual cause rather than just re-running until it passed,
and fixed before it went anywhere. All 107 backend tests pass, including
the new ones.

## Status: Batch 2.8 , Real Azure Blob Storage, and the backend is complete

**The real constraint worth being upfront about: there's no Azure account
provisioned for this project yet** , that's genuinely Phase 5
infrastructure work. So instead of writing the storage configuration and
hoping it's correct, I installed **Azurite** (Microsoft's own official
local Azure Storage emulator) in this sandbox and tested against it ,
the real Azure SDK talking to something that speaks the identical Azure
Blob API protocol, not a guess.

- `Expense.receipt_file` and `Report.pdf_file` (a placeholder URL field
  and local-filesystem field respectively, from Batches 2.4 and 2.6) now
  both use Django's real storage abstraction, swappable via one setting
  , `AZURE_CONNECTION_STRING` , with no code changes required either way
- Local development still defaults to filesystem storage, zero setup,
  exactly as before

**Verified in layers, each one genuinely proven, not assumed from the
one before it:**
1. Raw Azure SDK talking directly to Azurite , real upload, real
   download, byte-for-byte match
2. Django's storage abstraction saving through `default_storage` , then
   independently confirmed via the raw SDK, bypassing Django entirely,
   that the exact same content actually landed in the blob
3. **The identical automated tests that already passed against local
   storage in Batches 2.4 and 2.6 , re-run with zero code changes,
   against real Azure Blob instead.** Both passed. This is the property
   that actually matters: the storage backend is a genuinely clean swap,
   proven by running the same test twice against two different backends,
   not just two separately-written code paths that both happen to compile.

**A real, useful finding from doing this properly instead of assuming:**
the Azure container must already exist before the app can write to it ,
`django-storages` does not auto-create it, which is correct behavior
(container provisioning belongs in infrastructure setup, not application
runtime). This is now a concrete, documented requirement for Phase 5:
the Blob Storage container has to be created as part of Azure
infrastructure setup, before the app is deployed, or every file upload
will fail with a clear `ContainerNotFound` error.

**Phase 2 , the entire backend API , is now complete.** All 8 modules,
real authentication and permissions, automatic audit logging, real PDF
generation, and real cloud file storage, all genuinely tested rather
than assumed correct.

## Local setup

**Testing Azure storage locally (optional):** install and run Azurite
(`npm install -g azurite`), pre-create the container once via the Azure
SDK or Azure Storage Explorer, then set `AZURE_CONNECTION_STRING` in
`.env` to point at it. Not required for normal development , local
filesystem storage is the default.

**One extra step beyond earlier batches:** PDF generation (Batch 2.6)
needs system libraries, not just Python packages. On Debian/Ubuntu:
```bash
sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0
```
Without these, `pip install -r requirements.txt` still succeeds, but
report generation will fail at runtime , this is exactly why the note
above exists for Phase 5 as well.

```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Then visit `http://127.0.0.1:8000/api/health/` , should return:
```json
{"status": "ok", "database": "connected", "database_error": null}
```

## Switching to Postgres locally

Set `DATABASE_URL` in `.env` to a real Postgres connection string and
re-run `python manage.py migrate`. No code changes needed , the settings
already read this from the environment.

## Deploying

Production settings are selected via `DJANGO_SETTINGS_MODULE=config.settings.production`.
All secrets (database URL, allowed hosts, storage keys) come from environment
variables , see `.env.example` for the full list. Real Azure deployment
configuration is Phase 5 of the project roadmap.
