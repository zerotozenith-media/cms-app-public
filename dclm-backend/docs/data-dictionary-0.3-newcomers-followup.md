# Data Dictionary: Batch 0.3: Newcomers & Follow-up

Extracted directly from the working demo code.

---

## Flag: "assigned" follow-up leader is not a real relationship in the demo

The `assigned` field (who's following up with a newcomer) is stored as a plain text string , e.g. `'Sarah Osei'` , matched only by name, not linked to any actual user or member record. There's no foreign key behind it at all in the demo.

This should become a real `assigned_to_user_id` (FK → users.id) in the real database, not free text. Flagging this as the clear correct fix rather than an open question , say so if you'd rather keep it as free text for some reason, otherwise I'll treat this as settled.

---

## Table: `newcomers`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | |
| name | Text | Yes | Single field , not split into surname/first name the way Members is |
| source | Text (from a configurable list) | Yes | Same list-management pattern as Funds/Expense Categories in Admin , editable list, not a hardcoded enum |
| stage | Enum | Yes | `new` / `contacted` / `visiting` / `integrated` / `not-interested` |
| assigned_to | **See flag above** | No | Defaults to "Unassigned" |
| location_id | Text (FK → locations.id) | Yes | |
| created_at | Date | Yes | First-contact date, set once at creation and never changed |
| stage_since | Date | Yes | Updates every time `stage` changes , this is what drives the "days in stage" urgency indicator |
| not_interested_note | Text | No | Only meaningful when stage is `not-interested`. **Currently cleared to null on reactivation , see open question 1.** |

---

## Table: `newcomer_milestones`

Milestone types are admin-configurable (see decision 2 below) , this table records which ones apply to a given newcomer and when.

| Field | Type | Notes |
|---|---|---|
| newcomer_id | Integer (FK) | |
| milestone_type_id | Integer (FK → milestone_types.id) | Demo seeds this list with `Salvation`, `Water Baptism`, `Holy Ghost Baptism`, `Sanctification` , Admin can add more |
| achieved_date | Date, nullable | Null = not yet reached |

## Table: `newcomer_tasks`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | |
| newcomer_id | Integer (FK) | Yes | |
| text | Text | Yes | Free text description |
| due_date | Date | Yes | |
| done | Boolean | Yes | Defaults false |
| assigned_to | Integer (FK → users.id) | No | Own assignee, independent of the newcomer's overall leader (see decision 3 below). Defaults to the newcomer's primary `assigned_to` if not set individually. |

---

## Business rules confirmed from actual demo behavior

1. **Stage changes always update `stage_since`.** Every transition , dragging a kanban card, marking Not Interested, reactivating , resets this date, which is what the "days in stage" indicator is built on.
2. **"Days in stage" urgency is colour-coded per stage, with Admin-adjustable thresholds:**
   - `new`: amber at 3 days, red at 6 (seeded default)
   - `contacted`: amber at 5 days, red at 10 (seeded default)
   - `visiting`: amber at 15 days, red at 30 (seeded default)
   - `integrated` and `not-interested`: no urgency colour, always neutral
   These are the demo's numbers, now used only as the initial seeded defaults , Admin can change them without a developer (see decision 4).
3. **"Not Interested" is reversible and non-destructive to the record** , the person's full history (milestones, tasks, source) stays intact; only `stage` and `stage_since` change, plus the note being set.
4. **Reactivating clears the not-interested note entirely.** The action is still recorded in the general Audit Log (who reactivated, when, to what stage), but the newcomer's own record loses the note and the fact that this episode happened. See open question 1.
5. **The summary counts on the Newcomers page are computed as:**
   - "In the pipeline" = everyone except `not-interested`
   - "New this month" = `created_at` falls in the current calendar month (note: this one *does* include `not-interested` people, since it's about arrivals, not current pipeline status)
   - "Overdue follow-ups" = open (`done = false`) tasks with `due_date` in the past, counted only for non-`not-interested` people
   - "Unassigned" = `assigned_to` is empty AND stage is not `integrated`, counted only for non-`not-interested` people
6. **Source is captured two ways**, both landing in the same table: a public QR-code self-registration form, or manual staff entry from a paper form. The QR path automatically tags the source as "Church website (QR self-registration)".

---

## Decisions confirmed

1. **Not Interested episodes stay visible on the newcomer's own profile, even after reactivation.** This needs a small `newcomer_status_history` table (same pattern as `member_category_history` from Batch 0.1): one row per stage change, so a profile can show a real trail like *"Marked Not Interested , 15 Jul → Reactivated , 3 Sep"* without anyone needing to dig through the general Audit Log.
2. **Milestones become admin-configurable**, the same way Funds and Newcomer Sources already work. `newcomer_milestones.milestone` changes from a fixed 4-value enum to a foreign key against a new `milestone_types` list that Admin can add to or remove from at any time (e.g. adding "Completed New Believers Class" without needing a developer).
3. **Tasks can be assigned to different people, not just the newcomer's one overall leader.** Each `newcomer_task` gets its own `assigned_to` (FK → users), independent of the newcomer's primary follow-up leader. The newcomer-level `assigned_to` stays as the default/overall owner, but any individual task can be handed to someone else , e.g. Jane Dosumu's overall leader is Sarah Osei, but one specific task can still be reassigned to Grace Thomas without changing who owns Jane overall.
4. **Urgency day-thresholds become Admin-adjustable**, not hardcoded. A new small settings table (e.g. `follow_up_urgency_settings`: stage, amber_days, red_days) drives the colour logic, editable from Admin instead of requiring a developer to change code. The demo's current numbers (New: 3/6, Contacted: 5/10, Visiting: 15/30) become the seeded defaults, not permanent fixed values.

Batch 0.3 is now fully resolved.

## Addendum: Batch 3.5 (post-approval correction, real intake slip)

While building the Newcomers frontend, the actual DCLM Bahrain intake
slip (both the paper form used for manual entry and the QR
self-registration form must capture the same fields) was reviewed
directly, and the approved schema above was found to be missing several
fields the real church actually collects. Corrected in the backend
(with real tests) before any frontend work depended on the incomplete
model, rather than building UI against a schema that didn't match the
real intake process.

**New fields added to `newcomers`:**
- `address`, `city_governorate` , free text, matching the slip
- `phone`, `email` , not unique (may share a household's contact info)
- `gender` (Male/Female), `age_group` (Under 20 / 20 and above) , matches
  the slip's coarse bracket, not an exact date of birth
- `prayer_request` , free text
- `meeting_attended` , FK to `meeting_types`, kept consistent with the
  rest of the schema rather than free text
- `is_first_timer`, `is_new_resident` , independent flags, confirmed
  a newcomer can be both at once, not mutually exclusive
- `invited_by_member` (FK → members, nullable) + `invited_by_name` (text
  snapshot) , the slip's "Invited by" is a person's name; this tries to
  match an existing Member by exact full name, but only links if the
  match is unambiguous (two members sharing the same name are left
  unlinked, text-only, rather than guessing). `invited_by_name` always
  stores the raw name regardless, matching the audit-log's snapshot
  pattern from Batch 0.6.

**Distinguished from the existing `source` field:** the slip has two
separate questions , "Invited by" (who) and "Learnt about the church
from" (how/channel). The second maps to the already-approved `source`
field; the first is the new `invited_by_name`/`invited_by_member` pair.
Neither field overwrites the other.

**New business rule:** the three request checkboxes on the slip (would
like a visit / would like to know more / wants to know about being a
Christian) each auto-create a real `newcomer_tasks` entry at creation
time , "Schedule a home visit," "Share more about the church," "Have a
salvation conversation" , assigned to the newcomer's primary leader.
Confirmed explicitly: this is task creation only, not automated
messaging or email , no content is sent by the system itself, a human
still carries out the actual visit or conversation.

