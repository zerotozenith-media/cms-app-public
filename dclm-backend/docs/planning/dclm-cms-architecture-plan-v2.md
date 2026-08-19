# DCLM Bahrain Church Management System
## Architecture and Feature Plan: v2 (expanded with church-specific requirements)

This version incorporates the details you provided about attendance structure, meetings, giving, member categories, follow-up, and reporting. It replaces the module descriptions in v1 (section 5) and extends the data model (section 4). Sections 1, 2, 3, 6, 7, and 9 from v1 still apply and are not repeated in full here.

Guiding principle throughout: capture data once, at the moment it naturally happens (weekly, per service), so the monthly report becomes a compile-and-format step, not a research project.

---

## 1. Locations and meetings (new structure)

### Locations
Locations are configurable, not hardcoded to two fixed countries, so this still works if a third location is ever added. Seeded with:
- Bahrain (primary)
- Others (a free-text note field captures exactly where, e.g. "Qatar" today; can be renamed or split later if that group grows enough to deserve its own entry)

Each location supports two attendance modes: In Person and Online. So every attendance record is tagged Location x Mode, and every report can show Bahrain, Others, and Total, split further by in-person and online. A Location Coordinator role (see section 6) is assigned per location; right now that means one coordinator for Bahrain and one for Others (currently the Qatar group).

### Meeting types
Meetings are configurable, not hardcoded, so adding or retiring one later does not need developer work. Each meeting type stores a name, day, frequency (weekly or occasional), and an attendance detail level.

Two detail levels, matching what you described:

**Simple (Men / Women only):**
- Saturday Workers Meeting
- Tuesday Leadership Development

**Detailed (Men, Women, Youth Boys, Youth Girls, Children Boys, Children Girls):**
- Monday Bible Study
- Wednesday Revival and Evangelism Training Service
- Friday Worship Service
- Friday House Caring Fellowship

**Occasional (not weekly, detail level set per event):**
- Global Crusade with Kumuyi (GCK)
- Ministerial Renewal

When a session is created for a meeting, the app only shows the input fields relevant to that meeting's detail level, so ushers are never confused about which boxes to fill.

### How sessions get created
Not fully manual. Recurring meetings (Bible Study, Revival, Worship, etc.) are set up once with a schedule (day of week, time), and the system automatically generates the upcoming session shell for each occurrence, so the recorder never "creates a meeting" from scratch week to week, they just open that week's session and fill in the numbers. Occasional meetings (GCK, Ministerial Renewal) are created manually when they are announced, since they do not follow a fixed schedule. Either way, once a session exists, entering attendance is the same simple form.

### Attendance entry
For each session: Location, Mode (in person or online), date, and a headcount per applicable category (not necessarily named individuals, since a count is faster to capture weekly than a full roll call). Named check-in against the member list remains available for meetings where you want to know exactly who attended (useful for the "missed three in a row" follow-up flag), and is optional per session.

Totals automatically roll up: by category, by mode, by location, and grand total, for any date range.

---

## 2. Giving (updated)

Per your note, individual giving is not tagged to a name as a default. Structure:

- Entry: date, location, fund/category (Tithe, Offering, Missions, Building, Other, configurable), method (Cash or Online Transfer), amount in BHD.
- Optional link to a member only when you do want to record it that way (some churches want this for a specific fund, e.g., a building pledge). Off by default.
- Totals by fund, by method, by location, by period.

### Expenses (new, needed for your report but not in v1)
Your report requires "Finance: amount generated and expenses and areas of spending," but nothing in v1 captured expenses, only income. Adding a small Expense entity:
- Date, location, category (configurable: Rent, Utilities, Welfare, Outreach, Admin, Other), amount, brief description, recorded by.
- Optional receipt photo or scan attachment. Since receipts are looked at rarely (mostly for audit or dispute, not daily use), they are stored in Azure Blob Storage's cool or archive access tier, which costs a fraction of standard storage for infrequently accessed files, keeping this feature nearly free to include.
- This gives you Income vs Expense vs Net, and a breakdown of spending areas, directly from data instead of someone reconstructing it at month end.

---

## 3. Members: categories and movement

Three categories, exactly as you described:
- General Member
- Worker in Training
- Worker

A member's category is changed through an explicit "Move" action (not just editing a field), which logs: from category, to category, date, moved by, and an optional note. This gives you a full movement history per member and, in aggregate, a report of how many moved into training or became workers in a given period, which is a natural metric for your "Growth Strategies and Metrics" report section.

---

## 4. Newcomer follow-up: spiritual milestones and source tracking

### Spiritual milestone tags
A checklist attached to each newcomer/member, updatable by the assigned follow-up leader as it happens, each with a date when marked:
- Salvation
- Repentance and restitution (matches your doctrinal statement)
- Water baptism
- Holy Ghost baptism
- Sanctification
- Joined a local unit or class (optional, later)

This is a simple checklist, not a rigid pipeline, since people can reach these at different points. It doubles as a spiritual growth report metric ("14 newcomers received salvation this month, 6 were baptized in water").

### A note on scaling named tracking
Named tracking (for members and newcomers specifically, separate from bulk meeting attendance) scales fine as the church grows, because it works the same way established systems with thousands of records handle it: type-ahead search instead of scrolling a full list, filters by category or location, and pagination. This is standard database behavior, not something that gets harder as numbers grow, so there is no redesign needed later. Bulk meeting attendance is different: headcount stays the default there specifically because roll-calling a large room is slow regardless of software, and named check-in for meetings (not just member records) is offered as an opt-in for when you want that detail, with self or QR check-in as the natural upgrade path in a later phase once attendance volume makes manual tapping slow.

### Source of newcomer
A configurable list, tagged at first contact:
- Invited by a member
- Social media
- Paid advertisement
- Church website
- Walk-in
- Outreach or crusade
- Other (free text)

This feeds a simple "where our newcomers come from" chart for the report and for future outreach budget decisions.

---

## 5. Monthly report: structure and how the data gets there

### Report structure (PDF, matching your outline)
1. Cover page (church name, logo, website, phone number, period, generated date)
2. Table of contents
3. Executive summary
4. Attendance (Bahrain / Qatar / Total, in person / online, by meeting, trend vs previous month)
5. Finance (income by fund, expenses by category, net, comparison to previous month)
6. Testimonies
7. Challenges
8. Goals, Growth Strategies, and Metrics
9. Conclusion

Sections 4 and 5 are fully automatic from attendance and giving/expense data already described above. Sections 6, 7, and 8 need new, very light data capture, addressed next.

### Filling the gap: testimonies, challenges, goals
These do not exist anywhere in the app yet, and if left for month-end they become the hardest part of the report to write, exactly the problem you are trying to solve. The fix is small, frequent capture rather than a new heavy module:

**Testimonies:** a short form (who or anonymous, date, service, testimony text) that any leader can submit right after a service, from a phone if needed. Over the month these simply accumulate into a list the report pulls from; the report preparer picks or edits which ones to include.

**Weekly leadership note:** one simple form, filled by a pastor or department head at the end of each week, with three short fields: Highlights, Challenges, Prayer Points or Needs. Five minutes, once a week. At month end these four or five weekly notes are summarized into the report's Challenges section and inform the Executive Summary, instead of trying to remember four weeks of ministry from scratch.

**Goals and metrics:** a small Goals entity: goal description, target metric (for example, "grow Sunday attendance to 120"), target date, current progress value, status (on track, behind, achieved). Leaders update progress whenever it changes, not just at month end. The report pulls current status of all active goals automatically.

This keeps the report autogeneration honest: nothing in the PDF is invented at month end, everything is a compile of things already logged through the month.

### Output
The system fills a report template (cover, TOC, and body) and exports both a formatted PDF and, if useful, the source docx, in the same way already planned for the current monthly report in v1.

---

## 6. User authentication and roles (based on common ChMS practice)

Common practice across established platforms is role-based access with the ability to scope some roles to a location or department, which fits your Bahrain/Qatar split well. Suggested roles:

| Role | Access |
|------|--------|
| Administrator | Full access, user management, settings |
| Pastor / Overseer | Full read access, reports, approves goals and report content |
| Location Coordinator (Bahrain or Others) | Full access scoped to their location's attendance, members, and follow-up |
| Finance | Giving and expenses, financial reports only |
| Attendance Recorder / Usher | Create attendance sessions and headcounts only |
| Follow-up / Care Team | Newcomers, milestones, source tagging, limited member view |
| Department Head | Submits weekly leadership notes and testimonies for their department |
| Viewer | Read-only dashboards and reports |

A member can hold more than one role (for example, a Location Coordinator who is also Finance for that location). Every meaningful change is still written to the audit log from v1.

---

## 7. Note on future mobile app

Confirmed and already aligned with this plan: Django plus Django REST Framework is the core, API-first. The React web app and a future mobile app (Flutter or React Native) both consume the same API and the same permissions and roles, so the mobile app is an additional client later, not a rebuild. No architecture change needed now, just keeping API design generic (not tightly coupled to the web UI) as we build.

---

## 8. Keeping it simple: what stays in MVP vs later

To avoid the app becoming complicated despite the added depth, here is the suggested split:

**MVP (build now):**
- Locations and configurable meeting types, headcount attendance by category
- Giving and expenses (amount-level, category-level)
- Members with three categories and movement history
- Newcomer follow-up with milestone checklist and source tagging
- Weekly leadership note and testimony capture (the two small forms that make reporting possible)
- Goals with progress tracking
- Report generation to PDF from the above
- Auth with the roles above

**Later phase (unchanged from v1):**
- Named check-in for every meeting (optional per session in MVP, full rollout later)
- Automated SMS/WhatsApp follow-up messaging
- Giving statements and pledges
- Small groups, workers rota, child check-in/out safeguarding flow

Nothing above adds a new platform or technology, it is all within the same Django plus React plus PostgreSQL architecture from v1. The complexity is in the data model, not the tech stack, and the weekly-capture habit (testimony and leadership note) is what keeps the monthly report light instead of a scramble.

---

## 9. Status of open questions

1. Location coordinators: resolved. Bahrain and Others (currently Qatar) each have a coordinator now; the role is scoped per location as described in section 6.
2. Named vs headcount attendance: resolved, see the scaling note in section 4. Headcount stays the default for bulk meetings; named tracking is used for members and newcomers directly, and available as an opt-in for meetings where it's wanted.
3. Expense receipts: resolved, optional attachment stored in Azure Blob cool/archive tier (section 2).
4. Meeting list and detail levels: confirmed correct.
5. Sample report for template matching: none available. The report template in section 5 will be designed as a clean, generic layout and can be adjusted once you see the demo.

No open questions remain before the demo.
