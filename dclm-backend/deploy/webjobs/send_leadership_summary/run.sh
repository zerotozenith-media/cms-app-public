#!/bin/bash
#
# send_leadership_summary, run on a schedule by Azure App Service.
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

echo "$(date -u +'%Y-%m-%d %H:%M:%S UTC')  starting send_leadership_summary"
python manage.py send_leadership_summary
echo "$(date -u +'%Y-%m-%d %H:%M:%S UTC')  finished send_leadership_summary"
