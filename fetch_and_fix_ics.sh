#!/bin/bash
set -euo pipefail

# Logging-Funktion
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_PATH"
}

# Standardwerte setzen
ICS_URL="${ICS_URL:-}"
TZID="${TZID:-Europe/Berlin}"
LOG_PATH="/data/ics-fixer.log"
TMP_PATH="/tmp/calendar_raw.ics"
OUTPUT_PATH="/data/ics-mod/kalender.ics"

# Validierung
if [[ -z "$ICS_URL" ]]; then
  log "ICS_URL ist nicht gesetzt. Bitte als Umgebungsvariable übergeben."
  exit 1
fi

log "Starte ICS-Download von $ICS_URL"
if curl -s "$ICS_URL" -o "$TMP_PATH"; then
  log "ICS-Datei erfolgreich heruntergeladen"
else
  log "Fehler beim Herunterladen der ICS-Datei"
  exit 1
fi

log "Beginne mit der Umwandlung der Zeitzonen mit TZID=$TZID"

{
  echo "BEGIN:VCALENDAR"
  echo "VERSION:2.0"
  echo "PRODID:-//Unraid ICS Fixer//EN"
  echo "BEGIN:VTIMEZONE"
  echo "TZID:$TZID"
  echo "BEGIN:DAYLIGHT"
  echo "TZOFFSETFROM:+0100"
  echo "TZOFFSETTO:+0200"
  echo "DTSTART:19700329T020000"
  echo "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU"
  echo "TZNAME:CEST"
  echo "END:DAYLIGHT"
  echo "BEGIN:STANDARD"
  echo "TZOFFSETFROM:+0200"
  echo "TZOFFSETTO:+0100"
  echo "DTSTART:19701025T030000"
  echo "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU"
  echo "TZNAME:CET"
  echo "END:STANDARD"
  echo "END:VTIMEZONE"

  sed -E \
    -e "s|DTSTART:([0-9TZ]+)Z|DTSTART;TZID=$TZID:\1|" \
    -e "s|DTEND:([0-9TZ]+)Z|DTEND;TZID=$TZID:\1|" \
    -e "/BEGIN:VCALENDAR/d" \
    -e "/VERSION:/d" \
    -e "/PRODID:/d" \
    "$TMP_PATH"
} > "$OUTPUT_PATH"

if [[ -s "$OUTPUT_PATH" ]]; then
  log "ICS-Datei erfolgreich geschrieben nach $OUTPUT_PATH"
else
  log "ICS-Datei ist leer oder konnte nicht geschrieben werden"
  exit 1
fi