# Basis-Image mit Bash und curl
FROM alpine:latest

# Installiere benötigte Tools
RUN apk add --no-cache bash curl sed

# Arbeitsverzeichnis
WORKDIR /app

# Kopiere das Bash-Skript ins Image
COPY fetch_and_fix_ics.sh .

# Setze Ausführungsrechte
RUN chmod +x fetch_and_fix_ics.sh

# Standard-Umgebungsvariablen (optional überschreibbar)
ENV TZID="Europe/Berlin"
ENV ICS_URL=""
ENV HA_WWW_PATH="/mnt/cache/appdata/homeassistant/www/kalender.ics"

# Entry Point
CMD ["/bin/bash", "/app/fetch_and_fix_ics.sh"]