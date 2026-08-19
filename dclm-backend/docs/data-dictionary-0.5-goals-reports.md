# Data Dictionary: Batch 0.5: Goals & Reports

Extracted directly from the working demo code. Two findings already reviewed and accepted are applied below. One further finding surfaced while assembling this batch , flagged at the end, not yet decided, awaiting your review before it's treated as resolved.

---

## Table: `goals`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | |
| horizon | Enum | Yes | `Short-term` / `Medium-term` / `Long-term` / `Spiritual growth` |
| name | Text | Yes | |
| target | Decimal | Yes | |
| current | Decimal | Yes | Only meaningful for `manual` goals , ignored/overridden for `auto` goals, which compute their value live instead |
| unit | Text | No | e.g. `%`, or blank for a plain count |
| tracking | Enum | Yes | `auto` / `manual` |
| period_type | Enum | Conditional | **New field, added to fix Finding 1 below.** `month` / `quarter` / `year` / `none`. Required for any `auto` goal whose name claims a time period; `none` for goals like "latest session" that aren't time-boxed. |
| source | Text | Yes | Plain-language description shown to users of where the number comes from |
| link_route, link_tab | Text | No | Where the "View data" link on an auto goal navigates to |

**Business rule confirmed:** a manual goal's `current` value is a plain number someone updates by hand. An auto goal's displayed value is never read from `current` at all , it's computed fresh every time from the real underlying data (attendance sessions, member history, newcomer milestones, etc.).

---

## Finding 1: accepted, now applied: auto-tracked goals must actually filter by their stated time period

Six of the nine auto-tracked goals name a time period ("this month," "this quarter," "this year") but the demo's calculation counted all-time totals regardless , e.g. "Salvations recorded this month" counted every salvation ever recorded, not just August's. Two goals ("Workers in Training moved to Worker (quarter)" and "New workers raised and deployed (year)") were running the identical all-time calculation despite claiming different time windows.

**Applied fix:** every auto-tracked goal calculation now filters its underlying data (attendance sessions, member history entries, newcomer milestone dates, testimony dates) to fall within the correct window relative to today, based on its `period_type`:
- `month` → current calendar month
- `quarter` → current calendar quarter (Jan–Mar, Apr–Jun, Jul–Sep, Oct–Dec)
- `year` → current calendar year
- `none` → no filtering (e.g. "latest filled session" goals, which aren't measuring a period at all)

This also corrects the monthly PDF report, whose "Goals and Growth" section pulls these same numbers directly.

---

## Table: `testimonies`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | |
| member_name | Text | No | Null when anonymous |
| is_anonymous | Boolean | Yes | |
| date | Date | Yes | |
| service_id | Integer (FK → services) | Yes | **Changed per Finding 2** , was free text in the demo, now a controlled list |
| text | Text | Yes | |

## Table: `weekly_notes`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | |
| department_id | Integer (FK → departments) | Yes | **Changed per Finding 2** , was free text in the demo, now a controlled list |
| week_label | Text | Yes | Display label, e.g. "04–10 Aug 2026" |
| week_start | Date | Yes | The actual sortable/filterable date behind the label |
| highlights | Text | No | |
| challenges | Text | No | |
| prayer_points | Text | No | |

## Finding 2: accepted, now applied: Service and Department become controlled lists

Both `services` (for testimonies) and `departments` (for weekly notes) become small admin-configurable lists , same pattern as Funds and Newcomer Sources , instead of free text prone to typos and inconsistent entries fragmenting the filter dropdowns.

---

## Reports: what a "monthly report" actually is

The demo builds a report from live data at the moment of export , it is not a stored document. Sections, all confirmed from the actual export logic: Cover, Table of Contents, Executive Summary, Attendance, Finance, Testimonies, Challenges, Goals and Growth, Other Additions (free text typed in at export time), Conclusion. Export works via the browser's native print-to-PDF.

**Technical note for the real system:** browser print-to-PDF is a reasonable mechanism for a no-backend demo, but the real system should generate PDFs server-side (so reports can be produced reliably regardless of the user's browser, and without requiring anyone to sit through a print dialog).

---

## Finding 3: accepted, now applied: reports get a real stored history

Every export in the demo was a one-time, in-the-moment action with nothing saved , no way to look back at a past month's report later. This is now fixed with a real table:

## Table: `reports`

| Field | Type | Required | Notes |
|---|---|---|---|
| id | Integer (PK) | Yes | |
| period_month | Integer | Yes | |
| period_year | Integer | Yes | |
| generated_by | Integer (FK → users.id) | Yes | |
| generated_at | Timestamp | Yes | |
| other_additions | Text | No | The free-text comment, now actually saved instead of existing only inside the one exported PDF |
| pdf_file_url | Text | Yes | Stored file reference, same Azure Blob pattern as receipts |

Past reports are now browsable from within the app instead of depending on someone's downloads folder.

Batch 0.5 is now fully resolved.
