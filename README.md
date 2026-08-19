# DCLM Bahrain Church Management System

Church management system for Deeper Christian Life Ministry Bahrain:
members, attendance, pastoral follow-up, newcomers, giving, goals and
reporting, across multiple locations.

---

## Where to start

**If you are a developer picking this up:**

1. [dclm-backend/docs/BUSINESS-CASE.md](dclm-backend/docs/BUSINESS-CASE.md)
   Why this exists and what it is trying to achieve. Several design
   decisions only make sense with this context, and undoing them without
   it would be easy.
2. [dclm-backend/docs/DEVELOPER-GUIDE.md](dclm-backend/docs/DEVELOPER-GUIDE.md)
   Setup, architecture, permissions, conventions, adding a feature end
   to end, testing, and known gaps.

**If you are deploying it:**
[dclm-backend/docs/DEPLOYMENT-RUNBOOK.md](dclm-backend/docs/DEPLOYMENT-RUNBOOK.md)
Step by step for a VPS or Azure, including the two background jobs that
must be scheduled.

**If you are administering it for the church:**
[dclm-backend/docs/ADMINISTRATOR-MANUAL.md](dclm-backend/docs/ADMINISTRATOR-MANUAL.md)
First-week setup, the monthly rhythm, and what staff will ask you.

**If you are using it day to day:** the in-app Help and Guide, reachable
from the sidebar once signed in. Written by job rather than by menu, so
an usher gets usher steps.

---

## What is here

```
dclm-backend/     Django 5 + Django REST Framework API
  docs/           Business case, developer guide, data dictionaries,
                  planning history, the approved demo, public website
dclm-frontend/    React 18 + TypeScript + Vite
OUTSTANDING.md    What is done, what is left, deferred items
```

33 models, 50 registered routes, 246 backend tests.

---

## Running it locally

Two terminals.

**Backend:**
```bash
cd dclm-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

**Frontend:**
```bash
cd dclm-frontend
npm install
cp .env.example .env.local
npm run dev
```

The app is on `http://localhost:5173`, the API on
`http://localhost:8000/api/`.

You will need an account to log in. The developer guide has a snippet
that creates one, along with the location and role it depends on.

**Tests:**
```bash
cd dclm-backend && source venv/bin/activate && python manage.py test
```

---

## One thing that must be scheduled

Absence follow-up is created by a management command:

```bash
python manage.py check_absences
```

**Nothing runs this automatically.** Until it is scheduled on the server,
no follow-up tasks will ever be created and the feature will appear
broken while being entirely functional. Plain cron on the app host is
free and sufficient; a cloud timer works equally well.

---

## Requirements

- Python 3.12+
- Node 20+
- PostgreSQL in production; SQLite is used locally with no setup
