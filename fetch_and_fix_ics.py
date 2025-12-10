#!/usr/bin/env python3
import os
import re
import sys
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Standardwerte
ICS_URL = os.getenv("ICS_URL", "")
TZID = os.getenv("TZID", "Europe/Berlin")
LOG_PATH = os.getenv("LOG_PATH", "/data/ics-fixer.log")
TMP_PATH = os.getenv("TMP_PATH", "/tmp/calendar_raw.ics")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "/data/ics-mod/kalender.ics")

def log(msg: str):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def download_ics(url: str, target: str):
    log(f"Starte ICS-Download von {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    with open(target, "w", encoding="utf-8") as f:
        f.write(resp.text)
    log("ICS-Datei erfolgreich heruntergeladen")

def convert_event_times(data: str) -> str:
    tz_target = ZoneInfo(TZID)

    def repl(match):
        key, tzid, timestr = match.groups()
        timestr_noz = timestr.rstrip("Z")
        try:
            dt_utc = datetime.strptime(timestr_noz, "%Y%m%dT%H%M%S")
        except ValueError:
            dt_utc = datetime.strptime(timestr_noz, "%Y%m%dT%H%M")

        if timestr.endswith("Z"):
            # UTC → lokale Zeit
            dt_utc = dt_utc.replace(tzinfo=ZoneInfo("UTC"))
            dt_local = dt_utc.astimezone(tz_target)
        else:
            # schon lokale Zeit → nur TZID setzen
            dt_local = dt_utc.replace(tzinfo=tz_target)

        out = dt_local.strftime("%Y%m%dT%H%M%S")
        return f"{key};TZID={TZID}:{out}"

    # Regex: fängt DTSTART/DTEND mit optionalem TZID ab
    pattern = re.compile(r'^(DTSTART|DTEND)(?:;TZID=[^:]+)?:([0-9T]+Z?)$', re.MULTILINE)
    return pattern.sub(lambda m: repl((m.group(1), m.group(2), m.group(2))), data)

def ensure_vtimezone(data: str) -> str:
    if "BEGIN:VTIMEZONE" in data:
        return data
    vtz = f"""BEGIN:VTIMEZONE
TZID:{TZID}
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
TZNAME:CEST
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
TZNAME:CET
END:STANDARD
END:VTIMEZONE
"""
    return data.replace("BEGIN:VEVENT", vtz + "\r\nBEGIN:VEVENT", 1)

def main():
    if not ICS_URL:
        log("ICS_URL ist nicht gesetzt. Bitte als Umgebungsvariable übergeben.")
        sys.exit(1)

    download_ics(ICS_URL, TMP_PATH)

    with open(TMP_PATH, "r", encoding="utf-8") as f:
        raw = f.read()

    log(f"Beginne mit der Umwandlung der Zeitzonen mit TZID={TZID}")
    fixed = convert_event_times(raw)
    fixed = ensure_vtimezone(fixed)

    # Header/Trailer sicherstellen
    header = f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//ICS Fixer//EN\r\n"
    fixed = re.sub(r"BEGIN:VCALENDAR.*?PRODID:[^\r\n]*\r?\n", "", fixed, flags=re.DOTALL)
    fixed = header + fixed
    if not fixed.strip().endswith("END:VCALENDAR"):
        fixed = fixed.strip() + "\r\nEND:VCALENDAR\r\n"

    # Zeilenenden normalisieren
    fixed = fixed.replace("\n", "\r\n")

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(fixed)

    if os.path.getsize(OUTPUT_PATH) > 0:
        log(f"ICS-Datei erfolgreich geschrieben nach {OUTPUT_PATH}")
    else:
        log("ICS-Datei ist leer oder konnte nicht geschrieben werden")
        sys.exit(1)

if __name__ == "__main__":
    main()
