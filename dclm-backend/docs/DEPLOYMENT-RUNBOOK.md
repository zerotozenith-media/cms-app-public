# Deployment Runbook

For whoever installs and runs this system on a server. Follow it in
order. Everything you need to decide is called out explicitly.

---

## 1. Choose where to host it

Two workable paths. Pick one before starting.

### Option A: a single VPS (recommended for a church this size)

One small Linux server running everything: Django, PostgreSQL, and the
built frontend behind nginx.

- **Cost:** roughly 5 to 15 USD a month
- **Good because:** cheapest, simplest, cron is already there for the
  absence check, one machine to understand
- **Trade-off:** you patch the server yourself, and backups are your job

Suitable providers: Hetzner, DigitalOcean, Linode, Vultr. A 2GB instance
is comfortable for a church of a few hundred members.

### Option B: Azure App Service

The production settings file is written for this, and includes Azure
Blob Storage for receipts and report PDFs.

- **Cost:** typically 30 to 80 USD a month once App Service, PostgreSQL
  and storage are combined
- **Good because:** managed patching, easy scaling, integrates with
  Key Vault for secrets
- **Trade-off:** more moving parts, more cost, and scheduling the
  absence check needs a separate Azure Function or WebJob

**If you are unsure, choose Option A.** Nothing about the application
requires Azure; only `config/settings/production.py` currently assumes
it, and section 6 shows the one change needed to run without it.

---

## 2. Before you start, gather these

| What | Where it comes from | Notes |
|---|---|---|
| Domain name | Your registrar | e.g. `cms.dclm-bh.org` |
| DNS access | Your registrar | To point the domain at the server |
| Server or Azure subscription | Your provider | See section 1 |
| A long random secret key | Generate it, section 4 | Never reuse, never commit |
| Database password | Generate it | Long and random |
| Email for the first admin account | The church | This becomes login one |

Decide the domain before deploying. Changing it later means reissuing
certificates and updating three settings.

---

## 3. Option A: VPS deployment, step by step

Assumes Ubuntu 24.04 and a domain already pointing at the server's IP.

### 3.1 Create a user and install packages

```bash
adduser dclm
usermod -aG sudo dclm
su - dclm

sudo apt update
sudo apt install -y python3-venv python3-pip postgresql nginx git \
  libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0
```

The last four are required by WeasyPrint, which generates the monthly
report PDFs. Without them report generation fails at runtime with an
unhelpful error, so install them now.

### 3.2 Create the database

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE dclm;
CREATE USER dclmuser WITH PASSWORD 'the-long-random-password-you-generated';
ALTER ROLE dclmuser SET client_encoding TO 'utf8';
ALTER ROLE dclmuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE dclmuser SET timezone TO 'Asia/Bahrain';
GRANT ALL PRIVILEGES ON DATABASE dclm TO dclmuser;
\c dclm
GRANT ALL ON SCHEMA public TO dclmuser;
\q
```

### 3.3 Put the code on the server

```bash
cd /home/dclm
# upload and unzip the delivery package here, or clone from your repo
cd dclm-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

### 3.4 Configure the environment

See section 4 for the values. Create `/home/dclm/dclm-backend/.env`:

```ini
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<your generated key>
DJANGO_ALLOWED_HOSTS=cms.dclm-bh.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://cms.dclm-bh.org
DATABASE_URL=postgres://dclmuser:<password>@localhost:5432/dclm
CORS_ALLOWED_ORIGINS=https://cms.dclm-bh.org
```

Lock it down:

```bash
chmod 600 .env
```

If you are not using Azure Blob Storage, make the change in section 6
now, before continuing.

### 3.5 Migrate and check

```bash
source venv/bin/activate
python manage.py migrate
python manage.py check --deploy
```

`check --deploy` should report at most the HSTS preload advisory. Anything
else, fix before going further.

### 3.6 Create the first administrator

```bash
python manage.py shell
```

```python
from core.models import Location
from accounts.models import Role, RolePermission, User

# Bahrain is the core location and cannot be deleted later.
bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)

role = Role.objects.create(name="Administrator")
for module in ["members", "attendance", "newcomers", "finance", "goals", "reports", "admin"]:
    RolePermission.objects.create(
        role=role, module=module,
        can_view=True, can_create=True, can_edit=True, can_delete=True,
    )

User.objects.create_user(
    email="admin@dclm-bh.org",
    password="a-strong-temporary-password",
    role=role,
    first_name="First",
    last_name="Administrator",
)
```

Tell that person to change the password immediately after first login.

**Do not run `seed_demo_data` on a production server.** It exists for
local development and creates roughly 2.5 years of invented members,
attendance and giving. It refuses to run twice, but there is no undo if
it runs once against real data.

### 3.7 Run Django under gunicorn

Create `/etc/systemd/system/dclm.service`:

```ini
[Unit]
Description=DCLM Bahrain CMS
After=network.target postgresql.service

[Service]
User=dclm
Group=www-data
WorkingDirectory=/home/dclm/dclm-backend
EnvironmentFile=/home/dclm/dclm-backend/.env
ExecStart=/home/dclm/dclm-backend/venv/bin/gunicorn \
  --workers 3 --bind unix:/home/dclm/dclm-backend/dclm.sock \
  config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dclm
sudo systemctl status dclm
```

### 3.8 Build the frontend

```bash
cd /home/dclm/dclm-frontend
# Node 20+ required
npm ci
echo "VITE_API_BASE_URL=https://cms.dclm-bh.org/api" > .env.production
npm run build
```

That produces `dist/`, which nginx serves as static files.

### 3.9 Configure nginx

Create `/etc/nginx/sites-available/dclm`:

```nginx
server {
    listen 80;
    server_name cms.dclm-bh.org;

    client_max_body_size 10M;   # receipt uploads

    location /api/ {
        proxy_pass http://unix:/home/dclm/dclm-backend/dclm.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://unix:/home/dclm/dclm-backend/dclm.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /media/ {
        alias /home/dclm/dclm-backend/media/;
    }

    # The React app handles its own routing, so anything else returns
    # index.html rather than a 404.
    root /home/dclm/dclm-frontend/dist;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/dclm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3.10 Enable HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d cms.dclm-bh.org
```

Certbot renews automatically. The production settings force HTTPS, so
the site will not work correctly until this step is done.

### 3.11 Schedule the two background jobs

**This is the step most easily forgotten, and the system quietly does
not work without it.**

```bash
crontab -e
```

```cron
# Create follow-up tasks for anyone who missed a tracked service.
# Hourly is enough: the command only acts on sessions past their
# threshold, and re-running never creates duplicates.
0 * * * * cd /home/dclm/dclm-backend && ./venv/bin/python manage.py check_absences >> /home/dclm/cron.log 2>&1

# Create the coming week's sessions for recurring meetings.
15 2 * * * cd /home/dclm/dclm-backend && ./venv/bin/python manage.py generate_recurring_sessions >> /home/dclm/cron.log 2>&1
```

**If you want email notifications**, add these two as well. Both are
safe to run when there is nothing to send: the digest skips anyone with
no open follow-ups, and does nothing at all unless a tracked service has
just happened.

```cron
# Shepherd digests, the morning after a service. Runs daily, but only
# actually sends when a tracked meeting happened in the last day.
0 7 * * * cd /home/dclm/dclm-backend && ./venv/bin/python manage.py send_followup_digests >> /home/dclm/cron.log 2>&1

# Weekly summary to leadership, Monday morning.
30 7 * * 1 cd /home/dclm/dclm-backend && ./venv/bin/python manage.py send_leadership_summary >> /home/dclm/cron.log 2>&1
```

Notifications are **off unless switched on**, so nothing is sent until
you add the settings in section 3.12. That is deliberate: a staging copy
of the real database must not be able to email the congregation.

Verify by running both by hand first:

```bash
cd /home/dclm/dclm-backend
./venv/bin/python manage.py check_absences
./venv/bin/python manage.py generate_recurring_sessions
```

Each prints what it did. If `check_absences` reports zero sessions
checked, that is normal when no tracked meeting has passed its threshold
yet.

### 3.12 Email notifications (optional)

Skip this if the church does not want email. Everything else works
without it.

**Choose a provider.** Resend gives 3,000 emails a month free, which is
far more than a church this size needs. Brevo is a good alternative at
300 a day. Note that Mailtrap's free tier is a *testing* inbox that
never delivers to real people, so it is not suitable for production.

**Verify your domain** with the provider. They will give you DNS records
to add at your registrar, which is what stops your emails going to spam.

**Add to `.env`:**

```ini
NOTIFICATIONS_ENABLED=True
APP_BASE_URL=https://cms.dclm-bh.org
DEFAULT_FROM_EMAIL=DCLM Bahrain <noreply@dclm-bh.org>
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=<your API key>
```

`APP_BASE_URL` is what makes the "open your list" button in the emails
point somewhere. Without it the emails still send, just without the link.

**Test before trusting it:**

```bash
source venv/bin/activate
python manage.py send_followup_digests --dry-run
python manage.py send_leadership_summary --dry-run
```

Dry run shows who would be emailed and with what subject, without
sending anything. When that looks right, drop `--dry-run`.

Then add the two cron entries from section 3.11.

### 3.13 Set up backups

The database holds everything. Losing it loses years of pastoral records.

```bash
mkdir -p /home/dclm/backups
crontab -e
```

```cron
# Nightly database dump, keeping 30 days.
30 1 * * * pg_dump -U dclmuser dclm | gzip > /home/dclm/backups/dclm-$(date +\%F).sql.gz && find /home/dclm/backups -name '*.sql.gz' -mtime +30 -delete
```

**Copy these off the server.** A backup on the same machine does not
survive that machine failing. Sync them to object storage or another
host.

Test a restore before you rely on it:

```bash
gunzip -c /home/dclm/backups/dclm-2026-01-01.sql.gz | psql -U dclmuser dclm_test
```

---

## 4. Generating the secrets

**Secret key:**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

**Database password:**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Never commit either. Never reuse them between environments. If a key
leaks, rotate it: every existing session is invalidated, which is the
point.

---

## 5. Option B: Azure App Service

Only the differences from Option A.

1. Create an App Service (Linux, Python 3.12) and an Azure Database for
   PostgreSQL flexible server.
2. Create a Storage Account and a container named `dclm-files`.
3. In App Service configuration, set every variable from section 3.4
   plus `AZURE_CONNECTION_STRING` and `AZURE_STORAGE_CONTAINER`. Use
   Key Vault references for the secret key, database URL and connection
   string.
4. Set the startup command:
   ```
   gunicorn --workers 3 --bind 0.0.0.0:8000 config.wsgi:application
   ```
5. Run `python manage.py migrate` once via SSH or a release step.
6. Deploy the built frontend `dist/` to Azure Static Web Apps, or serve
   it from the same App Service.
7. **Schedule the two commands.** App Service has no cron. Use an Azure
   Function with a timer trigger, or a WebJob, calling the same two
   management commands. Do not skip this.

---

## 6. Running without Azure Blob Storage

`config/settings/production.py` requires `AZURE_CONNECTION_STRING` and
will refuse to start without it. That is deliberate: on Azure App
Service the local disk is not reliably persistent, so a silent fallback
would risk losing uploaded receipts.

On a VPS the local disk is persistent, so local storage is correct.
Edit `config/settings/production.py` and replace the Azure block at the
end with:

```python
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
```

Make sure `/media/` is served by nginx (section 3.9 already does) and
that the `media` directory is included in your backups, since receipts
and generated reports live there.

---

## 7. Go-live checklist

Work through this before telling staff the system is live.

- [ ] Domain resolves to the server
- [ ] HTTPS works and HTTP redirects to it
- [ ] `python manage.py check --deploy` shows only the HSTS preload note
- [ ] `DEBUG` is False (it is, in production settings)
- [ ] `.env` is `chmod 600` and not in version control
- [ ] First administrator can log in
- [ ] That administrator has changed their password
- [ ] A test member, meeting type and session can be created
- [ ] `check_absences` runs by hand without error
- [ ] `generate_recurring_sessions` runs by hand without error
- [ ] Both are in cron and the log file shows them running
- [ ] If using email: `send_followup_digests --dry-run` shows the right
      people, and a real send arrives rather than landing in spam
- [ ] A monthly report generates as a PDF (this proves the WeasyPrint
      system packages are present)
- [ ] A receipt uploads and can be opened again afterwards
- [ ] Nightly backup runs and the file appears
- [ ] A backup has been restored into a scratch database successfully
- [ ] Backups are copied off the server

---

## 8. After go-live

**Turn on HSTS preload** once the site has run on HTTPS without issue
for a few weeks. Add to `config/settings/production.py`:

```python
SECURE_HSTS_PRELOAD = True
```

Deferred deliberately: preload submission is slow to reverse if
anything about your HTTPS setup turns out to be wrong.

---

## 9. Routine operations

**Deploying an update:**

```bash
cd /home/dclm/dclm-backend
source venv/bin/activate
git pull                      # or upload the new package
pip install -r requirements.txt
python manage.py migrate
sudo systemctl restart dclm

cd /home/dclm/dclm-frontend
npm ci && npm run build
```

**Checking the logs:**

```bash
sudo journalctl -u dclm -n 100 --no-pager   # application
tail -50 /home/dclm/cron.log                # scheduled jobs
sudo tail -50 /var/log/nginx/error.log      # web server
```

**Common problems:**

| Symptom | Likely cause |
|---|---|
| No follow-up tasks are ever created | `check_absences` is not scheduled, or no meeting type has `counts_for_absence` and a `start_time` set |
| Notification emails never arrive | `NOTIFICATIONS_ENABLED` is not True, the two commands are not scheduled, or no tracked service happened so the digest correctly sent nothing |
| Emails arrive in spam | The provider's DNS records are not set at your registrar |
| No sessions appear each week | `generate_recurring_sessions` is not scheduled |
| Report PDF generation fails | The WeasyPrint system packages from 3.1 are missing |
| Login works but every request then fails | `CORS_ALLOWED_ORIGINS` or `DJANGO_ALLOWED_HOSTS` does not match the real domain |
| Receipts upload but will not open | nginx is not serving `/media/`, or storage is misconfigured |
| Site unreachable after a certificate change | HSTS is remembered by browsers; fix the certificate rather than reverting to HTTP |
