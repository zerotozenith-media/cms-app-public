# Data Dictionary: Batch 0.4: Giving, Expenses & Projects

Extracted directly from the working demo code. Three real gaps found this time , flagged clearly with examples before the tables, same as the assigned-leader gap in Batch 0.3.

---

## Flag 1: Projects has no management screen at all

Every other configurable list in the app (Funds, Expense Categories, Newcomer Sources, Meeting Types, Users, Households) has a real Add/Delete screen in Admin. Projects does not , it's a single hardcoded entry in the code with no way to add a second one without a developer changing it.

*Example:* Today there's one project, "Qatar Church Building Project." If the church starts a second one next year , say a new vehicle fund, or a building project in Bahrain , nobody on staff can add it themselves. It has to come back to a developer.

## Flag 2: There's no way to actually tag a new gift to a project

Even for the one project that exists, the Record Giving form has no "Project" field at all , only Fund, Method, Amount, Location, and Member. The one link that exists (a BHD 970 gift tagged to the building project) only exists because it was written directly into the starting data, not because a staff member selected it through the form.

*Example:* If someone gives BHD 500 today specifically toward the building project, staff currently have no way to record that connection , the gift would just go in as an untagged "Building" fund entry, indistinguishable from ordinary Building-fund giving that isn't meant for the project specifically.

## Flag 3: Expenses can never be linked to a project

Only Giving can be tagged to a project. Expenses have no equivalent field, so a project's page can only ever show money raised, never money spent against it.

*Example:* If the church pays a contractor BHD 5,000 from the building project's funds, that expense has nowhere to go , it just becomes an ordinary "Other" expense, with no way to see it as building-project spending. The project would show BHD 970 raised, but there'd be no way to see any of it as spent.

---

## Table: `funds` and `expense_categories`

Both are simple admin-configurable text lists (same pattern already established for Newcomer Sources) , not separate specialized structures. Demo seeds:
- Funds: Tithe, Offering, Missions, Building
- Expense Categories: Rent, Utilities, Welfare, Outreach, Admin, Other

## Table: `giving`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | |
| date | Date | Yes | |
| fund_id | Text (FK → funds) | Yes | |
| method | Text (from a configurable list) | Yes | Same list-management pattern as Funds , demo seeds `Cash` and `Online Transfer`; Admin can add more (e.g. Benefit Pay, Fawri) |
| amount | Decimal | Yes | Stored as a plain number in the demo , must be a real Decimal type in the database, never float, to avoid rounding errors |
| location_id | Text (FK → locations.id) | Yes | |
| project_id | Text (FK → projects.id) | No | Nullable , now a real field with a real Project selector in the Record Giving form, resolving Flag 2 |
| member_id | Integer (FK → members.id) | No | Nullable , optional link to who gave, confirmed from earlier gap-filling work |

## Table: `expenses`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | |
| date | Date | Yes | |
| category_id | Text (FK → expense_categories) | Yes | |
| amount | Decimal | Yes | Same note as above , real Decimal type |
| location_id | Text (FK → locations.id) | Yes | |
| description | Text | No | Free text |
| receipt_file_url | Text | No | **See technical note below** |
| project_id | Text (FK → projects.id) | No | New field, resolving Flag 3 , Expenses can now be tagged to a project too, so a project shows spending, not just income |

## Technical note: receipt files need real storage

In the demo, a selected receipt file is converted to a base64 text blob and stored directly inside the record itself (fine for a browser-only demo with no backend). In the real system this must instead be a real uploaded file (Azure Blob Storage, per the original architecture plan) with only a URL or reference stored in the `expenses` table , not the raw file data inline in the database.

## Table: `projects`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Text/Slug (PK) | Yes | |
| name | Text | Yes | |
| description | Text | No | New , short context for what the project is; the demo had none at all |
| location_id | Text (FK → locations.id) | Yes | |
| target_amount | Decimal | Yes | |
| target_date | Date | No | New , optional fundraising deadline |
| status | Enum | Yes | New , `Active` / `Completed` / `Archived`, defaults to `Active` |

**Business rule confirmed:** a project's "amount raised" is never stored as its own running total , it's always calculated live by summing every Giving entry tagged to that project. This is good practice and should stay the same in the real system (single source of truth, no risk of the stored total drifting out of sync).

---

## Decisions confirmed

1. **Method becomes an editable list, the same way Funds already works.** Reasoning: Bahrain has locally common electronic payment methods (Benefit Pay, Fawri/Fawri+) that don't fit neatly as generic "Online Transfer" , a Bahrain church is realistically going to want one of these as a named option before long, and the editable-list pattern already exists, so reusing it costs almost nothing extra.
2. **Flags 1–3 are all fixed:** Projects gets a real Admin management screen (add/edit/delete, matching Funds/Households), the Record Giving form gets a Project selector, and Expenses gets its own Project field. This follows standard "budget vs. actual" practice in church and nonprofit fund accounting , a project should show money raised *and* spent against it, not income only.
3. **Projects gains three fields beyond the original scope**, added as a best-practice recommendation rather than something the demo prompted directly:
   - `description` (Text, optional) , short context for what the project is, which the demo never had at all
   - `status` (Enum: `Active` / `Completed` / `Archived`) , so finished projects stop cluttering the active list
   - `target_date` (Date, optional) , an optional deadline, standard practice for creating real fundraising urgency

Batch 0.4 is now fully resolved.
