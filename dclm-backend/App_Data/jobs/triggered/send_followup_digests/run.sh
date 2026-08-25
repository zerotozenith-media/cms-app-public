#!/bin/bash
cd /home/site/wwwroot
source antenv/bin/activate
python manage.py send_followup_digests
