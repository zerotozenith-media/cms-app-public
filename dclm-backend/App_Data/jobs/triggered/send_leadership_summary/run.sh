#!/bin/bash
cd /home/site/wwwroot
source antenv/bin/activate
python manage.py send_leadership_summary
