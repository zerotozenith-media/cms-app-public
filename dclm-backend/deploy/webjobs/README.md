# Scheduled jobs on Azure App Service

Four commands have to run on a schedule. On an ordinary server they go in
cron; App Service has no cron, so they run as **triggered WebJobs**.

Without these the system looks broken while working perfectly:

| Command | How often | What happens if it never runs |
|---|---|---|
| `check_absences` | Hourly | **No follow-up task is ever created.** Workers see an empty list and conclude the feature does not work |
| `generate_recurring_sessions` | Daily | No weekly sessions appear, so there is nothing for ushers to fill in |
| `send_followup_digests` | Daily | Shepherds get no reminder. Only matters once email is switched on |
| `send_leadership_summary` | Weekly | As above |

## Before anything else: check Always On

WebJobs on Linux App Service only run reliably when **Always On** is
enabled. Without it the app sleeps when idle and a scheduled job simply
does not fire, which is worse than having no schedule at all, because it
looks like it works and then quietly does not.

```bash
az webapp config show --name <app> --resource-group <rg> --query alwaysOn
```

- `true` — carry on below.
- `false` — turn it on (Configuration, General settings). It needs Basic
  tier or above.
- **Cannot turn it on?** Do not use WebJobs. Use `../azure-function/`
  instead, which runs independently of whether the web app is awake.

## Installing

Each folder here is one job. Zip its contents and upload:

```bash
cd deploy/webjobs/check_absences
zip -r ../check_absences.zip .
az webapp webjob triggered upload \
  --name <app> --resource-group <rg> \
  --webjob-name check_absences \
  --src ../check_absences.zip
```

Repeat for each. Or drag the folders into
**App Service, WebJobs** in the portal.

## Checking they actually run

Do not assume. After the first scheduled time:

```bash
az webapp log tail --name <app> --resource-group <rg>
```

Or in the portal: **WebJobs**, click the job, then **Logs**. Each run
prints what it did.

The honest test is in the app itself: after `check_absences` has run
following a tracked service, open Members, Follow-up. Tasks should be
there.
