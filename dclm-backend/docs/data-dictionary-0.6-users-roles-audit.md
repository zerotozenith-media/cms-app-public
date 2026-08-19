# Data Dictionary: Batch 0.6: Users, Roles & Audit Log

Extracted directly from the working demo code. All four findings below were reviewed and accepted before this document was written.

---

## Table: `users`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | |
| name | Text | Yes | Kept as its own field rather than forced through Members, so non-member staff (e.g. hired admin help who isn't a congregant) don't need a Member record just to have a login |
| email | Text | Yes, unique | New , the demo had no login credential of any kind ("login" was just clicking a name in a list). Email becomes the real login identifier. |
| password_hash | Text | Yes | New , real authentication, replacing the demo's password-free click-to-login |
| role_id | Integer (FK → roles.id) | Yes | |
| location_id | Text (FK → locations.id) | No | Nullable = full access across all locations (matches the demo's Administrator behavior) |
| member_id | Integer (FK → members.id) | No | **New, resolves Finding 1.** Optional link so a staff member who is also a congregant has their two records connected, without forcing every user account to be a member. |
| status | Enum | Yes | New , `Active` / `Inactive`. Lets a departed staff member's login be disabled without deleting the account (see Finding 4). |
| last_login | Timestamp | No | New , standard practice for a real auth system |

---

## Table: `roles`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | |
| name | Text | Yes | e.g. "Location Coordinator" |

## Table: `role_permissions`

**New table, resolves Finding 2.** Replaces the demo's flat "list of visible pages" with real per-module, per-action control.

| Field | Type | Notes |
|---|---|---|
| role_id | Integer (FK → roles.id) | |
| module | Text | e.g. `attendance`, `members`, `finance`, `reports` |
| can_view | Boolean | |
| can_create | Boolean | |
| can_edit | Boolean | |
| can_delete | Boolean | |

**Example of what this fixes:** Viewer can now genuinely be `can_view: true` with everything else `false` on every module , so opening the Reports page no longer leaves the "Submit a testimony" button clickable for someone who's supposed to be read-only.

---

## Hard requirement (not a design choice): server-side enforcement

**Resolves Finding 3.** Every permission and location restriction above must be independently checked by the backend on every single API request , never trusted from what the frontend shows or hides. Disabling a dropdown or hiding a nav item is a convenience for honest users; it is never the actual security boundary. This applies to every module in the app, not just this one.

---

## Table: `audit_log`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | |
| user_id | Integer (FK → users.id, nullable) | No | **New, resolves half of Finding 4.** Was plain text in the demo. Nullable so the log entry survives even if the account is later deleted. |
| user_name_snapshot | Text | Yes | Captured at the moment of the action, so the log stays readable and historically accurate even if the account is later renamed or removed |
| timestamp | Timestamp | Yes | Real timestamp type , the demo stored this as a formatted text string |
| action | Text | Yes | e.g. "Created," "Deleted," "Marked Not Interested" |
| entity_type | Text | Yes | e.g. "Member," "Newcomer," "Expense" |
| entity_name | Text | Yes | |
| details | Text | No | |

---

## Business rules

1. **Deleting a user never deletes their audit history.** The `user_id` link is set to null if the account is removed, but `user_name_snapshot` keeps their past actions readable.
2. **The last remaining Administrator account cannot be deleted.** Resolves the other half of Finding 4 , the demo allowed removing every Administrator with no warning at all.
3. **A user cannot delete their own currently logged-in account** without a distinct confirmation step (to prevent accidental self-lockout).
4. **A location of null/blank on a user means access to all locations** , this is how Administrator behaves in the demo and carries forward as the real rule.

Batch 0.6 is now fully resolved.

---

## Phase 0 status

All six batches (0.1 Members & Households, 0.2 Attendance & Meetings, 0.3 Newcomers & Follow-up, 0.4 Giving/Expenses/Projects, 0.5 Goals & Reports, 0.6 Users/Roles/Audit Log) are now complete. Batch 0.7 consolidates all of the above into one document with a full entity-relationship diagram, for a final whole-schema review before Phase 1 (Django backend) begins.
