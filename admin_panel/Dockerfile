FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# DJANGO PORT BY DEFAULT PLEASE CHANGE IT BY USING ENV VARIABLE 
ENV DJANGO_PORT 8000

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    python3-dev \
    libffi-dev \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY admin_panel/django_requirements.txt /app/
RUN pip install --upgrade pip && pip install -r django_requirements.txt

COPY admin_panel /app/

RUN python manage.py collectstatic --noinput

ENTRYPOINT ["/app/entrypoint.sh"]