# Data Dictionary: Batch 0.1: Members & Households

Extracted directly from the working demo code (not from memory or the earlier pre-demo plan). Every field, relationship, and rule below reflects what was actually built and tested.

---

## Table: `households`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | Auto-increment |
| name | Text | Yes | e.g. "Uguru Household" |
| address | Text | No | Free text (building, road, area) |
| phone | Text | No | Free text, not validated as a phone format in the demo |

**Relationships:**
- One Household → many Members (see `households_id` below)

**Business rule confirmed in the demo:** deleting a Household does **not** delete its Members. Each linked member's `household_id` is simply set to null, and the member record stays intact. This should be replicated as `ON DELETE SET NULL` on the foreign key, not a cascade delete.

---

## Table: `members`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | Auto-increment |
| surname | Text | **Yes** | Enforced as required in the Add Member form |
| first_name | Text | **Yes** | Enforced as required in the Add Member form |
| other_names | Text | No | Optional middle/other names |
| gender | Enum | No | `Male` / `Female` |
| date_of_birth | Date | No | Must not be in the future or implausibly old (see validation rule below) |
| phone | Text | No | **Unique.** Must be a valid phone-number format. International numbers accepted, not restricted to Bahrain only. |
| email | Text | No | Not unique. Must be a valid email format, validated server-side |
| category | Enum | Yes | `General Member` / `Worker in Training` / `Worker`. Defaults to `General Member` on creation. |
| location | Enum/FK | Yes | `bahrain` / `others` (see Locations note below). Defaults to Bahrain. |
| joined_date | Date | Yes | Defaults to the current date at creation, editable |
| household_id | Integer (FK → households.id) | No | Nullable , a member does not need to belong to a household |

**Full name:** the demo never stores a combined name field. Display name is always computed as `first_name + " " + surname` at render time. Recommend either replicating this as a computed/virtual field, or adding a stored `full_name` generated column purely for search indexing performance , but `first_name` and `surname` remain the source of truth either way.

**Locations note:** in the demo, Location is a small fixed lookup (`bahrain`, `others` , with "others" carrying a free-text note of "Qatar"), not an open text field. This should be its own small `locations` reference table, matching the same pattern used for the Attendance and Finance modules (they all filter by this same location list).

---

## Table: `member_category_history`

A member's category changes are never a silent field edit in the demo , every move is a deliberate, logged action.

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | |
| member_id | Integer (FK → members.id) | Yes | |
| from_category | Enum | Yes | Same three values as `members.category` |
| to_category | Enum | Yes | |
| changed_date | Date | Yes | Date the move was made |

**Relationship:** One Member → many `member_category_history` rows (append-only log, never edited or deleted in the demo).

---

## Relationships from other modules (referenced here for completeness)

These foreign keys live on other tables, not on Members, but are worth noting now since they touch this entity:

- `giving.member_id` → `members.id`, nullable. A gift can optionally be attributed to a member (defaults to anonymous/unlinked).
- `attendance_sessions.attendees` , in the demo this is an array of member IDs per session (named attendance). In a real relational schema this becomes its own join table, e.g. `attendance_session_members(session_id, member_id)`.

---

## Business rules confirmed from actual demo behavior

1. **Category is a controlled action, not a plain edit.** Moving a member between General Member / Worker in Training / Worker always creates a `member_category_history` row and updates `members.category` together, in the same action.
2. **Household deletion does not cascade.** Members keep their record; only the link is cleared.
3. **Surname-matching is advisory, not enforced.** When adding or editing a member, the system checks for other members sharing the same surname and suggests linking to the same household. This is a UI hint only , it does not block saving, and does not auto-link anything.
4. **No uniqueness constraint exists in the demo** on name, email, or phone , nothing stops two members from having identical details. This is an open question for you: should email or phone be unique at the database level in the real system, or left open (e.g. for children who share a parent's phone)?

---

## Decisions confirmed

1. **Phone is unique; email is not.** Each member's phone number must be distinct in the system. Email has no uniqueness constraint (family members may share one, or leave it blank).
2. **Locations: Bahrain is a protected core entry.** The real `locations` table seeds Bahrain as a fixed, non-deletable record. Every other location (starting with the demo's "Others/Qatar") is a fully editable, addable, and removable entry managed by an Admin , this applies to the same Locations table used by Attendance and Finance, not just Members.
3. **Plausibility validation applies to date of birth, email, and phone.**
   - Date of birth: reject future dates and anything implausibly old (suggested default: more than ~110 years back , flag later if a different cutoff is wanted).
   - Email: real format validation, enforced server-side.
   - Phone: valid phone-number format required, **international numbers accepted, not restricted to Bahrain only.**
4. **Category-move corrections are allowed, and are not Admin-only.** Whoever already has permission to move a member's category , Administrator, or a Location Coordinator for their own location , can also edit or delete a wrong `member_category_history` entry directly. No separate escalation step.

Batch 0.1 is now fully resolved.

Once you confirm or correct the above, I'll move to Batch 0.2 , Attendance & Meetings.
