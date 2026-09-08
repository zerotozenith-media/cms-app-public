# Scheduled jobs as an Azure Function

Use this **only if Always On cannot be enabled** on the App Service.
Otherwise use `../webjobs/`, which is simpler and needs no extra service.

A WebJob lives inside the web app, so it only runs while the app is
awake. A Function on a timer runs whether the web app is awake or not,
which is why it is the fallback when Always On is unavailable.

## The catch worth knowing before you start

A Function is a separate application. It does **not** have the Django
code or the database settings. There are two ways round that, and they
are not equally good:

**Preferred: call the app over HTTP.** The Function wakes the web app
with a request to a protected endpoint, and the web app does the work.
The Django code stays in one place.

**Alternative: deploy the code twice.** The Function gets its own copy of
the project and its own database credentials. It works, but there are now
two copies to keep in step, and the day they drift is the day something
quietly stops matching.

This folder implements the first.

## What to deploy

`function_app.py` here defines four timers. Each calls
`POST /api/tasks/run/` on the web app with a shared secret, naming the
command to run.

Set on the Function App:

- `DCLM_BASE_URL` , for example `https://dclm-bahrain.azurewebsites.net`
- `DCLM_TASK_SECRET` , the same value as on the web app

Set the same `DCLM_TASK_SECRET` on the App Service. Generate it with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Without that secret the endpoint refuses every request, so a misconfigured
Function fails loudly rather than doing nothing.

## Checking it runs

The Function logs each call and the response. The endpoint also writes to
the audit log, so `Admin, Audit Log` shows scheduled runs alongside
everything else and you can see at a glance whether they are happening.
