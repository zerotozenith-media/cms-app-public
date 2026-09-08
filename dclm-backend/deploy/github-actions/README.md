# Scheduled jobs from GitHub

The cheapest way to schedule the four commands, and the one to use unless
there is a reason not to.

**Why not Azure.** App Service has no cron. WebJobs need Always On, which
needs a paid tier. Azure Functions needs a Storage Account. GitHub
already runs the repository, and scheduled workflows cost nothing on the
plans a church would be on.

## Setting it up

1. Copy `scheduled-tasks.yml` to `.github/workflows/` in the repository.

2. Generate a secret:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

3. Set it on the App Service as `DCLM_TASK_SECRET`, in Configuration,
   Application settings. Restart the app.

4. Set two repository secrets in GitHub, under Settings, Secrets and
   variables, Actions:

   - `DCLM_BASE_URL` , for example `https://dclm-bahrain.azurewebsites.net`
   - `DCLM_TASK_SECRET` , the same value as step 3

5. Confirm it works without waiting an hour: Actions tab, Scheduled
   tasks, Run workflow, choose `check_absences`.

## Confirming it keeps working

Every run is written to the audit log, so **Admin, Audit Log** in the app
shows scheduled runs alongside everything else. A day after setting this
up there should be entries. If there are none, it is not running.

## Two things worth knowing

**GitHub's scheduler is not punctual.** A job set for the hour may run
several minutes late when GitHub is busy. That does not matter for any of
these: the absence check looks at a window, it does not need to fire at a
precise second.

**Scheduled workflows are disabled after 60 days of no repository
activity.** GitHub emails first. If the repository goes quiet for two
months, check this still runs.

## A backup as well

None of this backs up the database. That still needs arranging, and it is
the one job whose absence is unrecoverable.
