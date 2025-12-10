#!/usr/bin/env python3
import os
import re
import sys
import requests
import time
from datetime import datetime
from zoneinfo import ZoneInfo

# Standardwerte
ICS_URL = os.getenv("ICS_URL", "")
TZID = os.getenv("TZID", "Europe/Berlin")

# Logdatei mit Datum versehen
today = datetime.now().strftime("%Y-%m-%d")
LOG_PATH = f"/data/ics-fixer-{today}.log"

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

def clear_directories():
    """Löscht .ics-Dateien immer, .log-Dateien nur wenn älter als 7 Tage."""
    dirs_to_clear = [
        os.path.dirname(LOG_PATH),
        os.path.dirname(TMP_PATH),
        os.path.dirname(OUTPUT_PATH),
    ]
    now = time.time()
    max_age = 7 * 24 * 60 * 60  # 7 Tage in Sekunden

    for d in dirs_to_clear:
        if d and os.path.isdir(d):
            log(f"Bereinige Verzeichnis: {d}")
            for filename in os.listdir(d):
                path = os.path.join(d, filename)
                try:
                    if filename.lower().endswith(".ics"):
                        os.remove(path)
                        log(f"ICS gelöscht: {path}")
                    elif filename.lower().endswith(".log"):
                        mtime = os.path.getmtime(path)
                        if now - mtime > max_age:
                            os.remove(path)
                            log(f"Altes Log gelöscht: {path}")
                        else:
                            log(f"Log behalten (jünger als 7 Tage): {path}")
                except Exception as e:
                    log(f"Fehler beim Löschen {path}: {e}")

def download_ics(url: str, target: str):
    log(f"Starte ICS-Download von {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    with open(target, "w", encoding="utf-8") as f:
        f.write(resp.text)
    log("ICS-Datei erfolgreich heruntergeladen")

def normalize_tzid_strings(data: str) -> str:
    return re.sub(r'TZID=W\. Europe Standard Time', f'TZID={TZID}', data)

def convert_event_times(data: str) -> str:
    tz_target = ZoneInfo(TZID)

    def rebuild_params(param_str: str) -> str:
        if not param_str:
            return f";TZID={TZID}"
        parts = [p for p in param_str.split(";") if p]
        parts = [p for p in parts if not p.upper().startswith("TZID=")]
        parts.insert(0, f"TZID={TZID}")
        return ";" + ";".join(parts)

    def repl(match):
        key = match.group(1)
        params = match.group(2) or ""
        timestr = match.group(3)

        if "VALUE=DATE" in params.upper():
            clean_params = ";".join([p for p in params.split(";") if p and not p.upper().startswith("TZID=")])
            if clean_params:
                clean_params = ";" + clean_params
            return f"{key}{clean_params}:{timestr}"

        is_utc = timestr.endswith("Z")
        timestr_noz = timestr[:-1] if is_utc else timestr

        dt = None
        for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
            try:
                dt = datetime.strptime(timestr_noz, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            return f"{key}{rebuild_params(params)}:{timestr}"

        if is_utc:
            dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz_target)
        else:
            dt = dt.replace(tzinfo=tz_target)

        out = dt.strftime("%Y%m%dT%H%M%S")
        return f"{key}{rebuild_params(params)}:{out}"

    pattern = re.compile(r'^(DTSTART|DTEND)(;[^:]*)?:([0-9T]+Z?)\s*$', re.MULTILINE)
    return pattern.sub(repl, data)

def ensure_vtimezone(data: str) -> str:
    # Entferne alle vorhandenen VTIMEZONE-Blöcke
    data = re.sub(r"BEGIN:VTIMEZONE.*?END:VTIMEZONE\r?\n", "", data, flags=re.DOTALL)
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

def finalize_calendar(fixed: str) -> str:
    # Alten Header entfernen
    fixed = re.sub(r"^BEGIN:VCALENDAR.*?PRODID:[^\r\n]*\r?\n", "", fixed, flags=re.DOTALL)
    # Doppelte VERSION entfernen
    fixed = re.sub(r"^VERSION:.*\r?\n", "", fixed, flags=re.MULTILINE)
    header = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//ICS Fixer//EN\r\n"
    fixed = header + fixed
    if not fixed.strip().endswith("END:VCALENDAR"):
        fixed = fixed.rstrip() + "\r\nEND:VCALENDAR\r\n"
    fixed = fixed.replace("\r\n", "\n").replace("\n", "\r\n")
    return fixed

def main():
    if not ICS_URL:
        log("ICS_URL ist nicht gesetzt. Bitte als Umgebungsvariable übergeben.")
        sys.exit(1)

    clear_directories()
    download_ics(ICS_URL, TMP_PATH)

    with open(TMP_PATH, "r", encoding="utf-8") as f:
        raw = f.read()

    log(f"Beginne mit der Umwandlung und Normalisierung mit TZID={TZID}")
    fixed = normalize_tzid_strings(raw)
    fixed = convert_event_times(fixed)
    fixed = ensure_vtimezone(fixed)
    fixed = finalize_calendar(fixed)

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(fixed)

    if os.path.getsize(OUTPUT_PATH) > 0:
        log(f"ICS-Datei erfolgreich geschrieben nach {OUTPUT_PATH}")
    else:
        log("ICS-Datei ist leer oder konnte nicht geschrieben werden")
        sys.exit(1)

if __name__ == "__main__":
    main()
