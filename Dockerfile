FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends tzdata && \
    rm -rf /var/lib/apt/lists/*

# Installiere Python-Abhängigkeiten
RUN pip3 install --no-cache-dir requests

WORKDIR /app
COPY fetch_and_fix_ics.py .

ENV ICS_URL=""
ENV HA_WWW_PATH="/mnt/cache/appdata/homeassistant/www/kalender.ics"
ENV TZID="Europe/Berlin"

CMD ["python", "/app/fetch_and_fix_ics.py"]
