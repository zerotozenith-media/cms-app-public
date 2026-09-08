#!/bin/bash
#
# generate_recurring_sessions, run on a schedule by Azure App Service.
#
# Exits non-zero on failure so a broken job shows as failed in the portal
# rather than sitting there looking green while doing nothing.
set -euo pipefail

# App Service deploys the site to /home/site/wwwroot and builds the
# virtual environment at antenv. Falling back to plain python means the
# job still runs if that layout ever changes, rather than failing silently.
cd /home/site/wwwroot

if [ -f antenv/bin/activate ]; then
    source antenv/bin/activate
elif [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

echo "$(date -u +'%Y-%m-%d %H:%M:%S UTC')  starting generate_recurring_sessions"
python manage.py generate_recurring_sessions
echo "$(date -u +'%Y-%m-%d %H:%M:%S UTC')  finished generate_recurring_sessions"
