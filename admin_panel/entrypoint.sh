#!/bin/bash

# Apply database migrations
python manage.py migrate

# Init initial data like statuses
python manage.py init_data

# Start Gunicorn
exec gunicorn --bind 0.0.0.0:$DJANGO_PORT \
    --workers 2 \
    --threads 2 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 30 \
    --keep-alive 2 \
    --log-level info \
    --access-logfile - \
    admin_panel.wsgi:application
