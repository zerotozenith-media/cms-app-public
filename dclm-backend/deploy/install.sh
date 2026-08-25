#!/usr/bin/env bash
#
# DCLM Bahrain CMS, server install.
#
# Run once on a fresh Ubuntu 24.04 server, as a user with sudo.
# It asks three questions, then does everything up to HTTPS.
#
#   bash deploy/install.sh
#
# Safe to re-run: every step checks whether it has already been done.
# Nothing here is destructive, and it never touches an existing database.

set -euo pipefail

# ---------------------------------------------------------------- helpers

BOLD=$'\033[1m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; OFF=$'\033[0m'
step()  { echo; echo "${BOLD}==> $*${OFF}"; }
ok()    { echo "${GREEN}    ok${OFF} $*"; }
warn()  { echo "${YELLOW}    note${OFF} $*"; }
fail()  { echo "${RED}    stopped${OFF} $*"; exit 1; }

APP_USER="${SUDO_USER:-$USER}"
APP_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND="$APP_HOME/dclm-backend"
FRONTEND="$APP_HOME/dclm-frontend"

[ -d "$BACKEND" ] || fail "Cannot find dclm-backend next to this script. Run it from inside the unpacked project."

# ---------------------------------------------------------------- questions

echo "${BOLD}DCLM Bahrain CMS, server install${OFF}"
echo
echo "Three questions, then this runs on its own for a few minutes."
echo

read -rp "1. Domain the church will use (e.g. cms.dclm-bh.org): " DOMAIN
[ -n "$DOMAIN" ] || fail "A domain is needed. Point it at this server's IP address first."

read -rp "2. Email for the first administrator account: " ADMIN_EMAIL
[ -n "$ADMIN_EMAIL" ] || fail "An email is needed for the first login."

read -rsp "3. Password for that first administrator: " ADMIN_PASSWORD; echo
[ ${#ADMIN_PASSWORD} -ge 10 ] || fail "Use at least 10 characters. This account can see everything."

DB_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')"

echo
echo "Installing for user ${BOLD}${APP_USER}${OFF} at ${BOLD}${APP_HOME}${OFF}"
echo "Domain: ${BOLD}${DOMAIN}${OFF}"
echo

# ---------------------------------------------------------------- packages

step "Installing system packages"
sudo apt-get update -qq
# Report PDFs are drawn with ReportLab, which is pure Python, so no
# graphics libraries are needed. This is why the system runs on managed
# hosts that do not let you install system packages.
sudo apt-get install -y -qq \
  python3-venv python3-pip postgresql nginx curl
ok "python, postgresql, nginx"

if ! command -v node >/dev/null || [ "$(node -v | cut -c2- | cut -d. -f1)" -lt 20 ]; then
  step "Installing Node 20"
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - >/dev/null 2>&1
  sudo apt-get install -y -qq nodejs
fi
ok "node $(node -v)"

# ---------------------------------------------------------------- database

step "Setting up PostgreSQL"
if sudo -u postgres psql -lqt | cut -d\| -f1 | grep -qw dclm; then
  warn "database 'dclm' already exists, leaving it alone"
else
  sudo -u postgres psql -q <<SQL
CREATE DATABASE dclm;
CREATE USER dclmuser WITH PASSWORD '${DB_PASSWORD}';
ALTER ROLE dclmuser SET client_encoding TO 'utf8';
ALTER ROLE dclmuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE dclmuser SET timezone TO 'Asia/Bahrain';
GRANT ALL PRIVILEGES ON DATABASE dclm TO dclmuser;
SQL
  sudo -u postgres psql -q -d dclm -c "GRANT ALL ON SCHEMA public TO dclmuser;"
  ok "database and user created"
fi

# ---------------------------------------------------------------- backend

step "Installing the backend"
cd "$BACKEND"
[ -d venv ] || python3 -m venv venv
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt
./venv/bin/pip install -q gunicorn
ok "python packages installed"

if [ -f .env ]; then
  warn ".env already exists, leaving it alone"
else
  cat > .env <<ENV
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=${SECRET_KEY}
DJANGO_ALLOWED_HOSTS=${DOMAIN}
DJANGO_CSRF_TRUSTED_ORIGINS=https://${DOMAIN}
CORS_ALLOWED_ORIGINS=https://${DOMAIN}
APP_BASE_URL=https://${DOMAIN}
DATABASE_URL=postgres://dclmuser:${DB_PASSWORD}@localhost:5432/dclm

# Email is off until you set this to True and fill in the details.
# See .env.production.example for which provider to use.
NOTIFICATIONS_ENABLED=False
DEFAULT_FROM_EMAIL=DCLM Bahrain <noreply@${DOMAIN}>
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=

AZURE_CONNECTION_STRING=
AZURE_STORAGE_CONTAINER=
ENV
  chmod 600 .env
  ok ".env written and locked to this user"
fi

# On a normal server the local disk is persistent, so local file storage
# is correct. The Azure block in production.py is only right on App
# Service, where the disk is not.
if grep -q "AZURE_CONNECTION_STRING = env(" config/settings/production.py 2>/dev/null; then
  if ! grep -q "LOCAL FILE STORAGE" config/settings/production.py; then
    cat >> config/settings/production.py <<'PYEOF'

# ---- LOCAL FILE STORAGE ----
# Added by deploy/install.sh. On a normal server the disk is persistent,
# so receipts and generated reports belong on it. Remove this block only
# if you move to Azure App Service, where the local disk is not reliably
# persistent.
if not env("AZURE_CONNECTION_STRING", default=""):
    MEDIA_ROOT = BASE_DIR / "media"
    MEDIA_URL = "/media/"
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
PYEOF
    ok "local file storage enabled"
  fi
fi

set -a; . ./.env; set +a
./venv/bin/python manage.py migrate --no-input -v 0
./venv/bin/python manage.py collectstatic --no-input -v 0 >/dev/null 2>&1 || true
ok "database migrated"

./venv/bin/python manage.py seed_enquiry_sources >/dev/null
ok "enquiry sources seeded"

step "Creating the first administrator"
DJANGO_ADMIN_EMAIL="$ADMIN_EMAIL" DJANGO_ADMIN_PASSWORD="$ADMIN_PASSWORD" \
  ./venv/bin/python manage.py bootstrap_admin

# ---------------------------------------------------------------- frontend

step "Building the frontend"
cd "$FRONTEND"
echo "VITE_API_BASE_URL=https://${DOMAIN}/api" > .env.production
npm ci --silent 2>/dev/null || npm install --silent
npm run build --silent
ok "built to dist/"

# ---------------------------------------------------------------- services

step "Configuring gunicorn and nginx"
sed -e "s|/home/dclm|${APP_HOME}|g" -e "s|^User=dclm|User=${APP_USER}|" \
  "$BACKEND/deploy/dclm.service" | sudo tee /etc/systemd/system/dclm.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now dclm >/dev/null 2>&1
sudo systemctl restart dclm
ok "gunicorn running as a service"

sed -e "s|cms.dclm-bh.org|${DOMAIN}|g" -e "s|/home/dclm|${APP_HOME}|g" \
  "$BACKEND/deploy/nginx.conf" | sudo tee /etc/nginx/sites-available/dclm >/dev/null
sudo ln -sf /etc/nginx/sites-available/dclm /etc/nginx/sites-enabled/dclm
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t >/dev/null 2>&1 || fail "nginx rejected the config. Run: sudo nginx -t"
sudo systemctl reload nginx
ok "nginx serving ${DOMAIN}"

# ---------------------------------------------------------------- schedule

step "Scheduling the background jobs"
mkdir -p "$APP_HOME/backups"
CRON_TMP="$(mktemp)"
crontab -l 2>/dev/null > "$CRON_TMP" || true
if grep -q "check_absences" "$CRON_TMP"; then
  warn "cron entries already present, leaving them alone"
else
  sed "s|/home/dclm|${APP_HOME}|g" "$BACKEND/deploy/crontab.example" >> "$CRON_TMP"
  crontab "$CRON_TMP"
  ok "absence check, session generation, digests and backups scheduled"
fi
rm -f "$CRON_TMP"

# ---------------------------------------------------------------- done

echo
echo "${GREEN}${BOLD}Installed.${OFF}"
echo
echo "Two things left, both quick:"
echo
echo "  1. Turn on HTTPS. The site will not work properly until you do,"
echo "     because production settings force it:"
echo
echo "       sudo apt install -y certbot python3-certbot-nginx"
echo "       sudo certbot --nginx -d ${DOMAIN}"
echo
echo "  2. Check everything is right:"
echo
echo "       cd ${BACKEND} && ./venv/bin/python manage.py preflight"
echo
echo "Then sign in at https://${DOMAIN} as ${ADMIN_EMAIL}"
echo "and change that password."
echo
warn "Copy ${APP_HOME}/backups off this server regularly. A backup on the"
warn "same machine does not survive that machine failing."
echo
