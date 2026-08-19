# Project documentation

Four documents cover the system. Read the one that matches what you are
about to do.

- **[BUSINESS-CASE.md](BUSINESS-CASE.md)**, what this system is for, the
  problems it solves, its objectives, and the decisions that shaped it.
  For church leadership, and for any developer who wants to know why
  before changing how.
- **[DEVELOPER-GUIDE.md](DEVELOPER-GUIDE.md)**, everything needed to run,
  understand and extend the system: setup, architecture, permissions,
  conventions, adding a feature end to end, testing, and known gaps.
- **[DEPLOYMENT-RUNBOOK.md](DEPLOYMENT-RUNBOOK.md)**, installing it on a
  real server, step by step, including the two background jobs that must
  be scheduled or the system quietly will not work.
- **[ADMINISTRATOR-MANUAL.md](ADMINISTRATOR-MANUAL.md)**, for whoever
  runs the system for the church: first-week setup, the monthly rhythm,
  and the questions staff will ask.

The full project record , planning, approvals, reference material, and
the public-facing site , kept alongside the code that implements the
CMS itself, rather than living only in chat history.

## Planning (pre-Phase 0)

[`planning/`](planning/) , the two early architecture drafts
(`dclm-cms-architecture-plan.md` and `-v2.md`) written before the
Phase 0 data dictionary formalized the approved schema. Superseded by
the data dictionary below wherever the two disagree; kept for the
history of how the design got there.

## Data dictionary (Phase 0)

Read in order , each batch builds on the approved decisions before it:

1. [Members & Households](data-dictionary-0.1-members-households.md)
2. [Attendance & Meetings](data-dictionary-0.2-attendance-meetings.md)
3. [Newcomers & Follow-up](data-dictionary-0.3-newcomers-followup.md) ,
   includes the Batch 3.5 addendum correcting the schema against the
   real DCLM Bahrain intake slip (address, phone, gender, age group,
   prayer request, the request checkboxes, and "invited by")
4. [Giving, Expenses & Projects](data-dictionary-0.4-giving-expenses-projects.md)
5. [Goals & Reports](data-dictionary-0.5-goals-reports.md)
6. [Users, Roles & Audit Log](data-dictionary-0.6-users-roles-audit.md)
7. [Consolidated (all 26 tables, ER diagram)](data-dictionary-0.7-consolidated.md)
   , the single reference for the full approved schema

## Roadmap

[Full project roadmap](dclm-cms-full-roadmap.md) , Phase 1 through 5,
batch by batch. Each backend/frontend README documents what's actually
been delivered against this plan and where real corrections diverged
from it (search either README for "Finding" or "Batch 3." for the
specific, dated account of each one).

## Reference demo

[`reference-demo/cms-demo-final.html`](reference-demo/cms-demo-final.html)
, the interactive HTML/JS prototype that served as the approved visual
and interaction reference for every real screen built in Phase 3.
Every "ported directly from the demo" note in the frontend README
refers to this exact file. Earlier iterations of the demo existed
during development but aren't kept here , this is the one that was
actually built against.

## Public website

[`public-website/`](public-website/) , the public-facing DCLM Bahrain
site (home, about, contact, events, give, sermons, service times), a
separate deliverable from the internal CMS in this repository. Built
before the CMS work began; not part of the Django/React application and
not deployed by it.

## How this relates to the code

The data dictionary describes what was *approved*. The Django models,
migrations, and tests in this repository are the actual implementation
, and in a few places (documented plainly in both READMEs when it
happened) building the real thing surfaced a genuine gap in what was
approved, which was fixed at the source and recorded back into the
relevant document here, not just patched silently in code.
