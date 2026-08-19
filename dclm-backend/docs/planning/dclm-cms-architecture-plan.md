# DCLM Bahrain Church Management System
## Architecture and Feature Plan (v1)

Prepared for: cms.dclm-bh.org
Scope of this document: system architecture, data model, MVP feature breakdown, roles, security, and a delivery roadmap. No application code yet.

---

## 1. Goals and scope

The system is a private, staff-facing web application (not public) that helps a small church run day to day. The first version (MVP) covers four working modules plus a foundation layer:

Foundation (required for everything else): user accounts, roles and permissions, and an audit trail.

MVP modules:
1. Members and newcomer follow-up
2. Attendance
3. Tithes and offering
4. Monthly report generation from a template

Out of scope for the MVP (planned for later phases): automated SMS/WhatsApp campaigns, small groups and rotas, giving statements and pledges, expense tracking, and child check-in and check-out. These are listed in the roadmap so the data model can accommodate them without rework.

Design principle: keep it small and low cost to match a small church, but structure the data and code so it can grow.

---

## 2. High level architecture

The system is a single-page React front end talking to a Django REST API, backed by a managed PostgreSQL database, all on Azure.

Components:
- Front end: React with Vite and TypeScript, hosted on Azure Static Web Apps. Served at cms.dclm-bh.org.
- Back end: Django with Django REST Framework, hosted on Azure App Service (Linux, Python). Served at api.dclm-bh.org (or proxied under cms.dclm-bh.org/api).
- Database: Azure Database for PostgreSQL Flexible Server (Burstable tier is enough at this size).
- File storage: Azure Blob Storage for generated reports, exports, and any attachments.
- Secrets and config: Azure Key Vault, with settings supplied through environment variables.
- Scheduled jobs: for monthly report reminders and follow-up due dates. Kept simple with a lightweight task runner (Django-Q2 or APScheduler) or an Azure scheduled job hitting a protected endpoint.
- Notifications (later phase): a provider such as the WhatsApp Cloud API, Twilio, or Azure Communication Services for SMS and email.
- CI/CD: GitHub Actions building and deploying both apps to Azure.

Why this shape: Django gives a strong admin, mature auth, and excellent Python libraries for the report generation you already work with (python-docx and openpyxl). React gives a clean, modern staff interface. Static Web Apps plus App Service plus a Burstable database keeps monthly cost low.

Text diagram:

    Browser (staff)
        |
        v
    cms.dclm-bh.org  ->  Azure Static Web Apps (React SPA)
        |  (HTTPS, JWT)
        v
    api.dclm-bh.org  ->  Azure App Service (Django + DRF)
        |            \
        v             \--> Azure Blob Storage (reports, exports)
    Azure PostgreSQL (Flexible Server)
        ^
        |
    Azure Key Vault (secrets)   GitHub Actions (CI/CD)

---

## 3. Authentication and roles

Authentication: email and password with JWT access and refresh tokens (djangorestframework-simplejwt). Enforce strong passwords, lockout after repeated failures, and optional two factor for admin accounts. Azure AD B2C is an alternative if you later want single sign on, but plain Django auth is simpler for a small team.

Roles (start with these, all permissions are per role and enforced on the API):

| Role | Purpose | Typical access |
|------|---------|----------------|
| Administrator | Full control, user management | Everything, including settings and audit log |
| Pastor / Leader | Oversight and reports | Read most data, run reports, manage follow-up |
| Finance | Money handling | Tithes and offering, financial reports |
| Attendance / Usher | Records attendance | Create attendance, view members |
| Follow-up team | Newcomer care | Newcomers, follow-up tasks, limited member view |
| Viewer | Read only | Dashboards and reports only |

Every create, update, and delete is written to an audit log (who, what, when, before and after) so financial and member changes are traceable.

---

## 4. Data model (core entities)

Fields below are the important ones, not exhaustive. Money is stored in minor units or as decimals in BHD with a currency field to allow future flexibility.

| Entity | Key fields | Notes |
|--------|-----------|-------|
| User | email, name, role, is_active, last_login | Staff accounts only |
| Household | name, address, phone | Groups members into families |
| Member | first_name, last_name, gender, dob, phone, email, status, join_date, household_id, photo | status: visitor, newcomer, member, inactive |
| Newcomer | member_id, first_visit_date, source, assigned_to, stage | stage: new, contacted, visiting, integrated |
| FollowUp (task) | newcomer_id, assigned_to, due_date, channel, notes, status | status: open, done, missed |
| AttendanceSession | date, service_type, notes | one row per service or meeting |
| AttendanceRecord | session_id, member_id, present, is_first_time | supports quick check-in |
| Fund | name, type | e.g. Tithe, Offering, Missions |
| Contribution | member_id (optional), fund_id, amount, currency, method, date, recorded_by | anonymous offering allowed (no member) |
| ReportTemplate | name, file, period_type | the docx or xlsx template |
| Report | template_id, period, generated_file, generated_by, created_at | stored in Blob |
| AuditLog | user_id, action, entity, entity_id, before, after, timestamp | immutable |

This model already leaves room for the later phases (pledges, expenses, groups, child check-in) without breaking changes.

---

## 5. MVP feature breakdown

### 5.1 Members and newcomer follow-up
- Member directory with search and filters (status, household, join date).
- Add and edit member profiles, group them into households.
- Capture a newcomer at first visit, assign a follow-up owner, and set a stage.
- Follow-up task list with due dates and simple statuses so nobody is dropped.
- A newcomer pipeline view (new, contacted, visiting, integrated).
- Manual logging of contact for now; automated messaging comes in a later phase.

### 5.2 Attendance
- Create a service or meeting session for a date.
- Quick check-in: mark present from the member list, flag first time visitors.
- Optional headcount for services where you do not record every name.
- Attendance history and simple trends per member and per service.
- QR or self check-in can be added later on the same session model.

### 5.3 Tithes and offering
- Record contributions against a fund, with amount in BHD, method, and date.
- Support named giving (linked to a member) and anonymous offering.
- Daily and weekly totals, and per member giving history.
- Finance-only access, with every entry captured in the audit log.
- Receipts and annual statements are a later phase but the data supports them.

### 5.4 Monthly report generation
- Upload a report template (docx or xlsx) with placeholders.
- Pick a month, and the system fills the template with the period's figures (attendance, giving totals, new members, follow-up outcomes).
- Generated file is saved to Blob storage and downloadable.
- This reuses the python-docx and openpyxl approach you already use, so the church keeps its exact report format.

### 5.5 Dashboard
- A simple home dashboard: attendance this month, giving this month, newcomers and their stages, and follow-ups due. Read according to role.

---

## 6. Security, privacy, and backups

- HTTPS everywhere, secrets in Key Vault, no credentials in code.
- Role based access enforced on the server, not just hidden in the UI.
- Audit log for all sensitive changes, especially money and member data.
- Personal data handling: Bahrain has a Personal Data Protection Law (PDPL). Treat the guidance here as general practice and confirm the specifics with someone qualified. Practical steps: collect only what is needed, record consent where appropriate, restrict who can see contact and giving data, and allow data export and deletion.
- Backups: automated database backups (the managed PostgreSQL service provides point in time restore), plus periodic exports to Blob. Test a restore before go live.

---

## 7. Environments and delivery

- Environments: local, staging, production, each with its own database and settings.
- CI/CD: GitHub Actions runs tests, builds the React app, and deploys both apps.
- Configuration through environment variables, secrets from Key Vault.
- Basic monitoring and error logging (Azure Application Insights).

---

## 8. Roadmap

Phase 1 (MVP): foundation (auth, roles, audit), members and newcomer follow-up, attendance, tithes and offering, monthly reports, dashboard.

Phase 2: automated follow-up messaging (SMS, WhatsApp, email) with templates, giving receipts and annual statements, pledges, and expense tracking.

Phase 3: small groups and units, volunteer and workers rotas, child check-in and check-out for safeguarding, and richer analytics.

---

## 9. Indicative hosting cost (small church)

Kept low with entry tiers: Static Web Apps free or low tier for the front end, a small App Service plan for the API, and a Burstable PostgreSQL instance, plus minimal Blob storage. Exact figures depend on current Azure pricing and region, so confirm before committing.

---

## 10. Assumptions and open questions

Assumptions made for this plan:
- Staff-facing only; members do not log in during the MVP.
- English interface, single congregation, single currency (BHD).
- Small scale (well within entry tier limits).

Questions to confirm before build:
1. Roughly how many staff users and how many members, so we size correctly.
2. Do you want members themselves to log in later (a member portal), which affects auth choices now.
3. For the monthly report, can you share the exact template so placeholders are designed around it.
4. Which contact channel matters most for later follow-up automation (WhatsApp, SMS, or email).
5. Do you want the API under cms.dclm-bh.org/api or a separate api.dclm-bh.org subdomain.
