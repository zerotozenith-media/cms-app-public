#!/bin/bash
cd /home/site/wwwroot
source antenv/bin/activate
python manage.py generate_recurring_sessions
