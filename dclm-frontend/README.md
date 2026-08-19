# DCLM Bahrain CMS: Frontend

React + TypeScript + Vite. Built against the real Django backend from
Phase 2, using the exact design system (colors, typography, component
patterns) already validated and approved in the HTML demo , this is a
faithful port, not a redesign.

## Member Attendance Follow-up: complete

Every screen for this feature is built against the real API and verified
end to end, not just compiled.

**Live check-in** (`/attendance/:id/check-in`). Tap a name to check
someone in; each tap is its own request so several ushers on different
doors cannot overwrite each other. In-person and online are per attendee,
so one hybrid service can have both.

**Member follow-up** (`/members/follow-up`). Open / Completed / All
filter, shepherd and sort filters, stat row. Completing a task requires
four fields (goal, scripture shared, root cause, next step agreed);
`done` is read-only on the API so a task cannot be ticked without a
record. Completed entries can be edited or deleted.

**Newcomer follow-up** (`/newcomers/follow-up`). The same components, not
a second implementation, so a leader who has learned one screen already
knows the other.

**Shepherd assignment.** Row checkboxes and bulk assign, plus auto-assign
with preview-before-apply. Households are kept with one shepherd, then
the rest balance by load. Only Workers are offered, drawn from the same
source the engine uses so the dropdown can never suggest someone the API
would reject.

**Help.** Clickable `?` markers on the things people hesitate over, and a
14-section guide written by job rather than by menu, visible to every
role. Searchable across headings, steps and notes.

**Intake.** First and last name split on both the staff Manual Entry form
and the public QR form, joined on submit since the API stores one name.

Verified at 1400/768/390/360px with no horizontal overflow and no
console errors on any screen.

## Phase 4.3: Dashboard updated for real permission-gated sections

The backend security review (see backend README) confirmed the
Dashboard should restrict each section by the viewer's real per-module
permission, not show every section to any logged-in user. The response
shape changed accordingly , each section's fields are now genuinely
optional, present only alongside its own `*_access: true` flag, so
`DashboardSummary`'s type and every place reading it needed updating,
not just the obvious one.

Rebuilt the stat row and every panel to conditionally include only the
sections the viewer actually has access to , restricted sections are
omitted entirely, not shown empty or disabled, since a card with no
data and a "go to X" link to a page the route guard would just redirect
away from adds confusion without value. Found and fixed one other real
consumer of the old always-present shape while auditing for this: the
Attendance page's own stat row also read `friday_worship` directly and
needed the same optional-chaining fix.

Verified through the real browser, not just the type checker: an
Administrator's dashboard is completely unchanged, while a genuine
Members-only test user's dashboard now shows only her welcome banner
and nothing else , confirmed with zero trace of "Giving" or "Friday
Worship" text anywhere on her actual rendered page.

## Status: Batch 3.10: Admin, and Phase 3 is complete

The final module batch of Phase 3, and the largest one , Users with
real email/password creation, a genuine Roles & Permissions matrix
editor, Meeting Types, Households, Locations (including the protected
Bahrain safeguard from Batch 0.1), seven admin-configurable lists built
on one reusable component, and the Audit Log and Login Security views.
More than the demo showed , it never had real Roles & Permissions
management at all, or visibility into the login security log , because
the real backend has real capabilities the mock data never needed to
represent.

### The most important thing tested this batch: does configuring a permission actually work, end to end

Not just "does the checkbox toggle." Created a new role, granted it
exactly "Members: view + create" through the real matrix, created a
real user with that role, logged out, logged back in as that user, and
confirmed her nav showed precisely Dashboard and Members , nothing
else. That's the entire chain , Batch 3.2's authentication, this
batch's permission configuration, and the backend's enforcement ,
proven to work together, not just each piece in isolation.

### A real, alarming-looking result that needed careful tracing before concluding anything

An early test of the permission matrix showed a checkbox that appeared
not to save correctly , the kind of result that's tempting to either
panic over or wave away. Did neither: checked the actual database
directly and found the real cause was contaminated test data , an
earlier test attempt had partially executed (its click handler fired
before an unrelated selector assertion crashed the script) and left a
duplicate role with different permissions behind, all in a database
file reused across several test attempts without resetting it. Redid
the entire sequence with a guaranteed-fresh database and confirmed the
matrix genuinely works correctly , a create-then-update sequence that
correctly preserves prior values while applying the new one.

### A real, separate finding: investigated fully rather than dismissed once confirmed safe

While confirming the permission end-to-end proof above, found that a
user could navigate directly to `/admin` by URL , bypassing the fact
that the link is correctly hidden from her nav , and land on a page
showing an empty, confusing shell (zeros everywhere, no rows). Checked
carefully whether this was a real data-leakage problem before doing
anything else: it wasn't , the backend correctly rejected every one of
her API calls, so no real data was ever exposed. But `ProtectedRoute`
only ever checked "is this person logged in," never "does their role
actually have permission for this specific module," which is a real gap
worth closing properly rather than leaving as "technically safe, but
confusing." Extended it with a `requiredModule` check using the
`hasPermission` function already built in Batch 3.2, and applied it to
every route in the app, not just Admin. Verified with a fresh database:
the same user is now cleanly redirected to her real dashboard instead
of hitting the broken shell, while routes she genuinely has access to
are completely unaffected.

### Cleanup, now that every module has a real screen

Removed `PlaceholderPage` and the routing helper that referenced it ,
dead code once the last placeholder route was replaced. Every route in
`App.tsx` now points at a real page.

### Verified end to end across every tab

Meeting Types and Households confirmed creating and listing correctly.
Config Lists confirmed adding and removing chips correctly, and
specifically confirmed the protected-location safeguard still holds
through the real UI , Bahrain shows a "Protected" badge with no delete
button available at all, not just a disabled one. The Audit Log
confirmed showing a real, complete history spanning the whole test
session , correctly distinguishing system-seeded actions from real
browser actions , and Login Security correctly tracked every real
login attempt made along the way. Mobile layout confirmed correct
throughout.

## Status: Batch 3.9: Reports, real screens end to end

Ported directly from the demo's `viewReports()`, `viewReportGenerate()`,
`viewWeeklyNotes()`, and `viewTestimonies()` , checked against the
source file, not memory. One deliberate departure from the demo worth
being direct about: the demo's "Generate" tab was a fake client-side
preview panel, since it had no real backend to generate anything.
The real backend (Batch 2.6) actually generates a real PDF, so this
batch builds the honest version , a form that calls the real generate
endpoint and shows the actual resulting file, not a decorative preview
mimicking one. The demo's "Included sections" checkboxes were also
non-functional placeholders (always checked, no real effect); since the
real backend doesn't support toggling individual sections, this batch
states plainly what's included rather than showing fake, inert controls
suggesting a capability that doesn't exist.

Also corrected two fields the demo left as free text but the approved
schema (Batch 0.5, Finding 2) made admin-configurable lists: Weekly
Note's Department and Testimony's Service are real dropdowns here, not
text inputs.

### A real bug found by generating an actual PDF and reading its actual content

Didn't stop at "the file downloads." Generated a real report against
real seeded attendance and giving data, then used `pypdf` to extract
the PDF's actual text and initially found what looked like three
separate bugs at once: wrong attendance count, a giving amount that
matched nothing in the database, and a completely missing "other
additions" field I'd definitely typed in. Rather than assume the
backend was broken, checked the actual stored `Report` database record
directly , which had the *correct* data , proving the bug had to be
somewhere between the database and the PDF file I was reading. Found
it: multiple PDF files had accumulated in the test media directory from
earlier attempts in the same session, all matching the same glob
pattern, and an unsorted `glob()[0]` had picked an arbitrary older one.
Re-checked using the exact filename the Report record actually
referenced, and confirmed all three pieces of data were correct in the
real file all along , a test methodology mistake on my part, not a
backend bug, but not one I want to gloss over either, since dismissing
three real-looking discrepancies without tracing them properly would
have been worse than finding them.

### A real backend gap, caught by checking a claim before writing it down

Nearly delivered this batch with "no backend changes needed." Before
writing that into the README, checked it directly instead of assuming
, and found the `service`/`department` filter dropdowns on Testimonies
and Weekly Notes were sending real query params the backend silently
ignored, since neither `TestimonyViewSet` nor `WeeklyNoteViewSet` had
ever been given a `get_queryset()` override for them. The dropdown
would visibly change selection, giving every appearance of working,
while nothing was actually being filtered server-side. Fixed on the
backend (see its README), then confirmed through the real UI:
submitted two testimonies tagged to different services, filtered by
one, and watched only the matching entry remain.

### Verified end to end with real submissions across all three tabs

Weekly notes and testimonies both confirmed persisting correctly
through the real form, editable and deletable against live data. Mobile
layout confirmed correct throughout. One minor, pre-existing display
quirk worth noting rather than silently fixing: a testimony submitted
non-anonymously with no name shows a blank before the comma in the
byline , this exactly mirrors the original demo's own logic for that
same edge case, not a regression introduced here.

## Status: Batch 3.8: Goals, real screens end to end

Ported directly from the demo's `viewGoals()` and `newGoalForm()` ,
checked against the source file, not memory. Stat-row, all four
horizon sections, progress bars with the same green/red thresholds as
the original (≥90% achieved, <60% behind), inline-editable progress for
manual goals, and calculation errors surfaced plainly rather than
silently showing 0 for a misconfigured auto-tracked goal.

Goals didn't need a dedicated backend stats endpoint the way the last
three batches did , it's a small, curated, admin-managed list (14
approved goals), not data that accumulates indefinitely. The existing
`current_value`/`calculation_error` fields from Batch 2.5 were already
exactly what this screen needed.

### A real bug, found by actually submitting the form, not by reading the code

Adding a new goal failed with a 400 on the very first real attempt. I
didn't guess , reproduced it directly against the API and got the exact
validation message: `source` is a required field on the backend, and my
form never sent one. Went back to the demo's actual `createGoal()` and
found it never asked the user for this either , it silently supplied a
sensible default text for every manually-created goal. My frontend
carried over the form fields but missed that one auto-supplied value.
Fixed by matching the demo's exact behavior, then re-tested the same
failing flow and confirmed a real goal now gets created successfully.

### Two things that looked like bugs during testing but weren't

A manual goal's progress update appeared not to persist in one test ,
checked the database directly rather than trust the UI text alone, and
confirmed it had actually saved correctly both times. The real issue
was that `.inner_text()` doesn't capture `<input>` element values at
all; checking the input's actual value property (and the database
independently) showed the feature was correct the whole time. Separately,
an "Add goal" button click timed out because the test tried to select a
button that didn't exist at that index , a plain test-selector mistake,
distinct from the real `source` bug found in the same session and not
conflated with it.

### Verified end to end with the real seed command and real underlying data

Ran the actual `seed_default_goals` management command, then seeded
real attendance, member category moves, and newcomer milestones so the
auto-tracked goals would compute genuine non-zero values , not just
zeros. Confirmed the exact distinction Batch 2.5 was built to prove is
still holding through the real UI: "Workers in Training moved to Worker
(quarter)" and "New workers raised and deployed (year)" correctly
diverge based on real data, not coincidentally showing the same number.
Confirmed "View data →" correctly navigates to the linked module, and
the mobile layout stacks correctly throughout.

## Status: Batch 3.7: Giving & Finance, real screens end to end

Ported directly from the demo's `viewFinance()`, `renderGivingList()`,
and `renderExpenseList()` , checked against the source file, not
memory. Stat-row, income-by-fund and expenses-by-category breakdowns
(now backed by a real dedicated summary endpoint , see the backend
README), project progress bars, both entry forms with inline
edit-in-place, and both filtered/sortable/paginated lists.

Applied the `htmlFor`/`id` lesson from Batch 3.6 correctly from the
start this time , every field in this batch's new form was built with
proper label association from the first draft, not fixed afterward.

### A real bug found through actually using the feature, not just testing the API

Uploaded a real receipt file through the live form , the upload
succeeded, the UI showed a "📎 View" link , but clicking it returned a
404. Didn't assume the frontend was at fault: fetched the link's `href`
directly and confirmed it was Django's own local media URL, then traced
it to a genuine gap in the backend's local dev configuration (see the
backend README for the fix). Re-uploaded after the fix and confirmed
the link now returns the actual file content, not just a success status
, proof the whole path works, not just the upload half of it.

### Verified end to end with real seeded data, including a genuine edge case

Seeded real giving and expense records across two locations, including
a fund with deliberately zero activity, and confirmed every number
matched: BHD 7,160 total income, correctly excluding a July gift from
"this month," the zero-activity fund correctly showing BHD 0 instead of
disappearing, and a project's progress bar correctly reflecting only
the giving tagged to it. Recorded a new giving entry linked to a real
member, edited an existing entry and confirmed the change persisted,
deleted an expense and confirmed it was actually gone, and confirmed
the mobile layout stacks correctly throughout.

## Status: Batch 3.6: Newcomers & Follow-up, including a real public form

The largest frontend batch so far. Ported directly from the demo's
`viewNewcomers()`, `viewNewcomerProfile()`, and the kanban/list/QR/manual
functions , checked against the source file, not memory. But this batch
also went meaningfully beyond a straight port: the demo's "QR
Registration" tab was just a static image linking to a URL that didn't
exist, and "Manual Entry" was a bare 3-field placeholder. Both are real
now, matching the actual DCLM Bahrain intake slip.

- **Kanban board** , real HTML5 drag-and-drop, confirmed persisting to
  the backend and correctly refreshing the board afterward
- **Newcomer profile** , milestones, tasks, and the Not
  Interested/Reactivate flow, all against live data
- **Manual Entry** , the full real intake form (address, city, phone,
  email, gender, age bracket, the five request checkboxes, invited-by,
  prayer request), not the demo's placeholder
- **QR Registration** , a real, client-side-generated QR code (chosen
  specifically so it could be visually verified in this sandbox, rather
  than trust an external image API) pointing at an actual working page
- **`/register`** , the real public self-registration form itself,
  completely outside the authenticated app (no sidebar, no login),
  submitting to the new public backend endpoint (see the backend README)

### Two real bugs caught and fixed before they shipped, not found by luck

**A completely broken kanban drag handler.** My first version called an
unused mutation hook with a placeholder id that was never used, then
tried to refresh the board with `window.dispatchEvent()` on a custom
event nothing was listening for. A card would have visually snapped
back to its original column after every successful drag. Fixed with a
correctly-shaped hook , the id varies per card being dragged, so it
takes `{id, to_stage}` as mutate() arguments rather than binding a fixed
id at hook-creation time, which the profile page's version correctly does.

**A stub function that would have silently hidden every follow-up
task.** `require_useNewcomerTasks` was placeholder code that always
returned an empty array , the add/complete/delete task handlers were
all built correctly around a function that could never actually show
anything. Caught before testing, replaced with a real hook (which also
needed a genuine backend addition , task filtering by newcomer didn't exist).

### A real, wider finding: unassociated form labels across the whole app

While testing the public registration form with Playwright's
label-based locator, discovered every form field built since Batch 3.4
, Members, Attendance, and this batch's own new intake fields , used
visually-adjacent but structurally unassociated `<label>` and `<input>`
elements, with no `htmlFor`/`id` pairing. `LoginPage` (Batch 3.2) got
this right; every form after it regressed. This isn't just a testing
inconvenience , a screen reader would have hit the exact same problem.
Fixed properly across the entire frontend, not just the new code: swept
every `.tsx` file for the pattern and corrected all of it, confirmed by
re-running the sweep until it came back clean.

### Verified end to end with a real, complete public submission

Filled out and submitted the actual public form as an anonymous visitor
would , a separate, unauthenticated flow , then logged in as staff and
confirmed the real database record: correct name, address, phone,
gender, prayer request, the auto-created "Schedule a home visit" task,
location forced to Bahrain, and source auto-tagged, exactly as designed.

## Status: Batch 3.5: Attendance, real screens end to end

Ported directly from the demo's `viewAttendance()`, `viewNewSessionForm()`,
`viewAttendanceSession()`, and `stackedBarsHTML()` , checked against the
source file, not memory. List, new session, and the full record view,
all working against the real API.

- **List page** , stat-row backed by a real dedicated stats endpoint
  (see the backend README), the Friday Worship age-group stacked bar
  chart with real historical data, and server-side filter/sort/pagination
  on the sessions table
- **Record page** , the exact fix worth calling out: I initially wrote a
  broken placeholder for choosing which headcount fields to show
  (`men.toLowerCase().includes('')`, always evaluating to the same
  branch), which would have silently shown all 6 detailed fields even
  for a "simple" (Men/Women only) meeting. Caught it before testing,
  fixed it to actually look up the real meeting type's `detail_level`,
  then verified directly: opened both a detailed and a simple session
  and confirmed the rendered fields were genuinely different , 6 fields
  vs. 2 , not just that the code looked right.
- **Named attendance** , real debounced search against the live Members
  API, no location restriction. Verified directly: searched for and
  checked in a Qatar-based member on a Bahrain session, confirming the
  Batch 0.2 approved decision (any member, any location) actually holds
  through the real UI, not just the backend test suite. The outdated
  demo copy ("Showing members based in [location]") was corrected to
  match the real, current behavior rather than carried forward as-is.

### Verified end to end, including confirming an edit correctly pre-loads existing data

Seeded five weeks of real Friday Worship history plus a detailed and a
simple pending session, and drove the actual UI: the stat-row and chart
numbers matched the seeded data exactly, headcount entry and named
attendance both saved correctly, and reopening an already-filled session
correctly pre-populated the form with its existing values rather than
resetting to blank , confirmed by partially re-editing a saved session
and seeing the untouched fields retain their prior values. Mobile layout
confirmed correctly stacking throughout.

## Status: Batch 3.4: Members & Households, real screens end to end

Ported directly from the demo's `viewMembers()`, `viewMemberProfile()`,
and `viewNewMemberForm()` , checked against the source file, not memory.
List, profile, add, and inline edit, all working against the real API.

- **List page** , stat-row (now backed by a real dedicated stats
  endpoint, see the backend README), server-side search/filter/sort/
  pagination, all wired to real query params rather than the demo's
  client-side array manipulation
- **Profile page** , full detail view, the household card (showing
  linked family members), movement history, and a real `Giving` total
- **`Move to category`** , the atomic backend action, wired directly;
  confirmed the badge, movement history, and the dropdown's remaining
  options all update correctly from one action, including the exact
  Batch 2.3 stale-cache fix still holding
- **Add Member** , a real async surname-match hint, debounced (the demo's
  version queried a synchronous in-memory array; this queries the live
  API and needs to account for real network latency)
- **Inline edit** , toggled on the profile page itself, matching the
  demo exactly rather than a separate route

### This batch drove more real backend work than any frontend batch so far

Six genuine gaps surfaced while building this , see the backend README
for the full account, including one where a bug was caught and fixed
*before* it ever reached the frontend: an early version of the stat-row
would have silently shown wrong member counts for any church over 100
members, caught by re-checking my own pagination change rather than
assuming it still worked.

### Verified end to end with real seeded data, including two real test-script mistakes caught and corrected

Seeded real members and households (including two people sharing a
surname and a household, mirroring the Uguru family example from the
original demo) and drove the actual UI:

- List, search, category filter, and sort all confirmed against live
  results
- The surname-match hint correctly found and displayed both existing
  Uguru members with their household, via a real debounced API call
- `Move to category` confirmed working atomically , badge, history, and
  the dropdown's available options all updated correctly from a single click
- Inline edit confirmed persisting a real field change
- Mobile layout confirmed correctly stacking into cards

**Two things went wrong during testing that were worth telling apart
carefully, both my own test mistakes, not application bugs:** first, a
`page.click("text=Chinedu Uguru")` silently clicked the topbar's user
chip instead of the intended table row, since that name legitimately
appears twice on the page , the URL not changing was the tell, fixed by
scoping the selector to the table. Second, an edit-field test indexed
into the form's `<input>` elements assuming Gender would occupy a slot,
forgetting it's a `<select>` and doesn't count , landed on the wrong
field entirely. Fixed by selecting on the phone field's unique
placeholder instead of a positional guess. Neither was the application
misbehaving; both were resolved by checking the actual rendered HTML
before concluding anything was broken.

## Status: Batch 3.3: Real Dashboard, live data end-to-end

The first fully real screen , no more placeholders. Ported directly from
the demo's `viewDashboard()`, `ringSVG()`, `donutHTML()`, and
`barsHTML()` (checked against the source file, not memory): the hero
banner, the combined stat-row with its per-stat ring/trend-chip pattern,
the giving-by-fund donut, the attendance trend bars, follow-ups due, and
the short-term goals ring grid.

**Required a real backend addition, not just frontend consumption** , see
the backend README for the full account. In short: several dashboard
numbers need aggregation across records that `GivingViewSet`'s
pagination makes impractical to sum client-side, so a dedicated
`/api/dashboard/summary/` endpoint was built rather than working around
it here.

### Verified with real, meaningful seeded data: not zeros

Seeded a realistic dataset (5 weeks of Friday Worship attendance, 4
funds, a newcomer with an open task, 4 short-term goals) and confirmed
every number on the rendered page traces back correctly: BHD 3,240 total
giving (1,450 + 970 + 410 + 410), Net BHD 2,640, the trend bars showing
the exact seeded sequence (113 → 121 → 129 → 134 → 159), and each goal's
ring computing its own independent percentage.

**The most important check reused the backend's own critical distinction,
now confirmed visually, not just asserted in a test:** logged in as both
an Administrator and a Location Coordinator side by side. The
Coordinator's own Friday Worship stat correctly shows her location's
real number (142, ring at 95%) , genuinely different from the
Administrator's all-location total (159, ring at 100%). But her
Short-term Goals ring grid shows the *identical* values as the
Administrator's, because goals are church-wide regardless of who's
viewing , exactly the distinction the backend test was built to prove,
now visible end-to-end through the real UI rather than only in an
assertion. Also confirmed the mobile layout renders correctly (2×2 stat
grid, stacked cards, all charts legible).

## Status: Batch 3.2: Real auth flow, routing, and role-based navigation

**A deliberate departure from the demo, flagged clearly:** the demo's
login screen was an explicit, stated mock , "no password required for
this prototype." That real system now exists (Batch 1.4), so this batch
replaces the demo's "click your account" list with a genuine email/
password form, wired to actually exercise the backend's real security
checks (honeypot field, submission-timing capture), not just visually
resemble a login screen.

- `AuthContext` , real login/logout against the live API, with the
  session (tokens + user identity) persisted so a page refresh doesn't
  silently log someone out
- `apiClient` , attaches the JWT access token to every request, and on
  a 401, transparently refreshes it once and retries before giving up,
  with concurrent 401s coalesced into a single refresh call rather than
  one per request
- `ProtectedRoute` , redirects to `/login` if not authenticated,
  remembering where the user was headed so they land there after signing in
- **Real role-based navigation** , the sidebar now filters against actual
  `RolePermission` data from the backend, not a hardcoded per-role list

### This batch required real backend changes too, not just frontend work

Building this exposed that the login response only returned the user's
role as a name string , no way to get real permission data without
either an extra round-trip or the exact kind of fragile name-matching
already ruled out in Batch 2.5. Fixed at the source: the backend's login
response now includes `role_permissions` and `location_name` directly.
See the backend README for the full account, including a real gap this
also closed (the login endpoint had zero permanent automated tests
despite extensive manual verification back in Batch 1.4).

### Verified with a genuine two-server integration test, not just each side in isolation

Booted the real Django backend and this frontend together and drove an
actual browser through the real flow , not mocked, not stubbed:

- Visiting a protected route while logged out redirects to `/login`
- A wrong password shows a clean error and stays on the login page
- **A real login as an Administrator** shows their actual name, role,
  and location in the topbar, pulled from the database, with every nav
  item visible
- **A real login as a Location Coordinator** shows only the modules her
  actual role permissions grant , Finance, Reports, and Admin are
  genuinely absent, not hidden by a client-side hack , and her location
  correctly shows "Bahrain," not "All locations"
- Logout clears the session, and a protected route immediately redirects
  to login again afterward , proving the session was actually
  invalidated, not just hidden from view

**One thing worth being fully honest about, since it looked like a bug
at first:** the very first version of this test showed a *correct*
password failing with a 401. Rather than assume the credentials or
guess, I checked Django's `authenticate()` directly at the shell level ,
it worked perfectly with the exact same credentials. That meant the
issue lived in `LoginView`'s pre-checks, not authentication itself.
Traced it to the "too-fast" bot-detection logic built in Batch 1.4,
requiring at least 1.5 seconds between the login form appearing and being
submitted , which Playwright's near-instant automated form-filling
correctly triggered. Not an application bug; my own security feature
working exactly as intended, just tripped by a test that itself looked
like a bot. Confirmed by re-running with realistic human-like pauses
between actions, which then succeeded cleanly. Worth recording precisely
because it's the kind of result that's easy to misdiagnose in either
direction , dismissing a real bug as "just a timing fluke," or chasing
a phantom bug that was actually a feature working correctly.

## Status: Batch 3.1: Project scaffold and design system port

What exists right now:
- Vite + React 18 + TypeScript, React Router, TanStack Query, Axios
- **The design system CSS ported directly from the demo's source file**
  (`cms-demo-v2.html`), not reconstructed from memory , every color
  token, component class, and responsive breakpoint is exactly what was
  already reviewed and approved
- The Icon component, ported the same way , extracted directly from the
  demo's `ICONS` object, all 13 icons including the ones added during
  the later gap-filling work (`user`, `alert`)
- The full app shell: sidebar (with the real logo asset), topbar, mobile
  drawer with backdrop dismissal, routing across all 8 modules
- Reusable primitives matching the demo's established patterns:
  `Button`, `Badge`, `Card`, `IconBadge`, `StatRow`

**A real bug was found and fixed while verifying this, not assumed
correct from a visual screenshot alone.** The ported CSS makes
`.backdrop` hidden by default, requiring a `.show` class to actually
become visible (`.backdrop.show{display:block}`) , matching how the
original demo's vanilla JS toggled it. My first version of the React
Sidebar component conditionally *rendered* the backdrop div instead
(present only when open), which looked identical in a static screenshot
but meant the backdrop's own CSS was still hiding it , it was
technically in the DOM but invisible and unclickable. A real Playwright
click test caught this ("element is not visible"), not a screenshot
review. Fixed by always rendering the backdrop and toggling `show`,
matching the CSS's actual contract, then re-ran the exact same test to
confirm.

A second, unrelated finding while testing the fix: clicking the exact
center of the backdrop element failed too, but for a completely
different and *correct* reason , the drawer sits on top of part of the
backdrop by design (same z-index stacking as the original demo), so a
center-click lands on the drawer's own nav links, not the darkened area
around it. Confirmed this by clicking a point in the actually-visible
region instead, which worked correctly , a test methodology issue, not
an application bug, and worth telling apart from the real one above.

**Batch boundary, deliberately held:** every page currently shows a
placeholder confirming routing and the shell work correctly. Real
screens with live data from the Phase 2 API start in Batch 3.3
(Dashboard) , this batch is the shell and design system only, matching
the same scaffold-first discipline used throughout the backend.

## Local setup

```bash
npm install
cp .env.example .env.local
npm run dev
```

Requires the Phase 2 Django backend running at the URL in `.env.local`
(defaults to `http://localhost:8000/api`) for any page beyond this
batch's placeholders to eventually show real data.

## Verified

- Production TypeScript build (`npm run build`) , zero errors
- Full click-through of all 8 routes , zero console/page errors
- Mobile drawer: opens via menu button, closes via the X button and via
  backdrop click, both confirmed with real interaction tests, not just
  visual inspection
