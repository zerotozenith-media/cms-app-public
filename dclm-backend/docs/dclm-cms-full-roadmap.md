# DCLM Bahrain CMS: Full Build Roadmap
## From validated demo to a completed, deployed real application

Guiding principle throughout: the demo we built and tested is the spec. Every batch below extracts requirements from what was actually built and confirmed working, not from memory or the original pre-demo planning doc. Each batch is reviewed and approved before the next one starts , nothing moves forward on assumption.

---

## Phase 0: Diligence: Data Dictionary (documentation only, no code)

Goal: a complete, reviewable description of every table, field, and relationship, extracted directly from the demo, before a single line of Django is written.

| Batch | Covers | Deliverable |
|---|---|---|
| 0.1 | Members & Households | Fields, relationships, movement history, surname-matching logic |
| 0.2 | Attendance & Meetings | Meeting types, sessions, category breakdown, named attendance |
| 0.3 | Newcomers & Follow-up | Pipeline stages, milestones, tasks, Not Interested/Reactivate logic |
| 0.4 | Giving, Expenses & Projects | Funds, methods, member linking, receipts, project targets |
| 0.5 | Goals & Reports | Goal tracking (auto vs manual), testimonies, weekly notes, report export |
| 0.6 | Users, Roles & Audit Log | Role permissions, location scoping, login, audit trail |
| 0.7 | Consolidated review | Full ER diagram, cross-entity relationships, final sign-off on the whole schema |

Each batch is a short document: table name, every field with type and constraints, relationships to other tables, and any business rule that affects the data (e.g. "a Not Interested newcomer keeps their record, stage just changes"). You review and correct each one before I move to the next.

---

## Phase 1: Backend Foundation (Django)

No user-facing features yet , this is the skeleton everything else sits on.

| Batch | Covers |
|---|---|
| 1.1 | Project scaffold: Django + DRF setup, environment config (local/staging/production), Azure PostgreSQL connection |
| 1.2 | Models and migrations for the full approved schema from Phase 0 |
| 1.3 | Django admin panel wired up (internal data-checking tool, not the real UI) |
| 1.4 | Real authentication: login, JWT tokens, role and location-based permissions enforced server-side |
| 1.5 | Audit logging as a real backend mechanism (signals/middleware), not the demo's manual log calls |

---

## Phase 2: Backend API

Each batch builds the real endpoints for one part of the app, with tests, matching what the demo already proved is needed.

| Batch | Covers |
|---|---|
| 2.1 | Members & Households API |
| 2.2 | Attendance & Meetings API |
| 2.3 | Newcomers & Follow-up API |
| 2.4 | Finance API (Giving, Expenses, Projects) |
| 2.5 | Goals API, including the auto-tracked calculations |
| 2.6 | Reports API (Testimonies, Weekly Notes, real server-generated PDF) |
| 2.7 | Users, Admin config, and Audit Log API |
| 2.8 | File storage (Azure Blob) for receipts and any future photos |

---

## Phase 3: Frontend (React)

Rebuilding the validated demo as a real app that talks to the live API instead of mock arrays. Visually it should feel like the demo you already approved , this phase is about making it real, not redesigning it.

| Batch | Covers |
|---|---|
| 3.1 | Project scaffold (Vite + React + TypeScript), porting the demo's design system (colours, components, layout patterns) |
| 3.2 | Real auth flow, routing, role-based navigation against the live API |
| 3.3 | Dashboard |
| 3.4 | Members & Households |
| 3.5 | Attendance |
| 3.6 | Newcomers & Follow-up |
| 3.7 | Finance |
| 3.8 | Goals |
| 3.9 | Reports |
| 3.10 | Admin (Users, Meeting Types, Households, config lists, Audit Log) |

---

## Phase 4: Integration, QA, and Data

| Batch | Covers |
|---|---|
| 4.1 | End-to-end testing of every flow against the real backend (not mock data) |
| 4.2 | Data seeding/import scripts for the church's actual starting data (real members, real meeting schedule, etc.) |
| 4.3 | Security and performance review |
| 4.4 | User acceptance testing with actual church staff using real accounts |

---

## Phase 5: Deployment (Azure)

| Batch | Covers |
|---|---|
| 5.1 | Azure infrastructure: App Service, Static Web Apps, PostgreSQL, Blob Storage, Key Vault |
| 5.2 | CI/CD pipeline (GitHub Actions) |
| 5.3 | Staging deployment and smoke testing |
| 5.4 | Production deployment and go-live |
| 5.5 | Monitoring setup (Application Insights) |

---

## Phase 6: Handover

| Batch | Covers |
|---|---|
| 6.1 | Training materials for staff (how to use the real system) |
| 6.2 | Documentation handover (data dictionary, architecture doc, admin guide) |

---

## What starts now

Phase 0, Batch 0.1: **Members & Households.** I'll extract everything from the demo , every field, the surname-matching hint, the movement history mechanic, household linking , into a reviewable document. You confirm or correct it, then we move to 0.2.
