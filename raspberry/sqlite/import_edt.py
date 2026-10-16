#!/usr/bin/env python3
"""Importe l'EDT ADE (fichier .ics ou URL) dans seances_cache."""

from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import sqlite3
import sys

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "pointage_local.sqlite"
ICS_PATH = HERE / "data" / "ADECal.ics"
URL_PATH = HERE / "data" / "edt_url.txt"
PARIS = ZoneInfo("Europe/Paris")


def unfold(text: str) -> str:
    return text.replace("\r\n ", "").replace("\n ", "").replace("\r\n", "\n")


def parse_ics_datetime(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        dt = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return dt.astimezone(PARIS)
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=PARIS)


def parse_vevents(text: str) -> list[dict]:
    events = []
    current = None
    for raw in unfold(text).splitlines():
        line = raw.strip()
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT" and current is not None:
            events.append(current)
            current = None
            continue
        if current is None or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.split(";", 1)[0]
        current[key] = val.replace("\\n", "\n").replace("\\,", ",")
    return events


def groupe_depuis_description(description: str) -> str:
    for line in (description or "").splitlines():
        line = line.strip()
        if line.startswith("BUT"):
            return line[:16]
    return ""


def code_enseignement(summary: str) -> str:
    token = (summary or "").split()[0] if summary else ""
    return token[:32]


def vevent_to_seance(evt: dict) -> dict | None:
    if "DTSTART" not in evt or "DTEND" not in evt:
        return None
    debut = parse_ics_datetime(evt["DTSTART"])
    fin = parse_ics_datetime(evt["DTEND"])
    location = (evt.get("LOCATION") or "").split(",")[0].strip()[:32]
    return {
        "id_seance": (evt.get("UID") or f"{debut.isoformat()}-{evt.get('SUMMARY')}")[:80],
        "groupe": groupe_depuis_description(evt.get("DESCRIPTION", "")),
        "id_ens": code_enseignement(evt.get("SUMMARY", "")),
        "num_salle": location or None,
        "date": debut.strftime("%Y-%m-%d"),
        "heure_debut": debut.strftime("%H:%M"),
        "heure_fin": fin.strftime("%H:%M"),
        "libelle": evt.get("SUMMARY", ""),
    }


def telecharger(url: str) -> str:
    req = Request(url, headers={"User-Agent": "SAE5-pointage/1.0"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def importer(ics_text: str, groupe_filtre: str | None = None) -> int:
    seances = []
    for evt in parse_vevents(ics_text):
        row = vevent_to_seance(evt)
        if not row or not row["id_ens"]:
            continue
        if groupe_filtre and row["groupe"] != groupe_filtre:
            continue
        seances.append(row)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM seances_cache")
    conn.executemany(
        """
        INSERT OR REPLACE INTO seances_cache
            (id_seance, groupe, id_ens, num_salle, date, heure_debut, heure_fin)
        VALUES (:id_seance, :groupe, :id_ens, :num_salle, :date, :heure_debut, :heure_fin)
        """,
        seances,
    )
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM seances_cache").fetchone()[0]
    print("Séances importées :", n)
    for g, c in conn.execute(
        "SELECT groupe, COUNT(*) FROM seances_cache GROUP BY groupe ORDER BY COUNT(*) DESC"
    ):
        print(f"  {g or '(sans groupe)'}: {c}")
    conn.close()
    return n


def main() -> int:
    if not DB_PATH.exists():
        print("Lance d'abord : python3 init_sqlite.py --recreate")
        return 1

    url = URL_PATH.read_text(encoding="utf-8").strip() if URL_PATH.exists() else ""
    ics_text = None
    if "--fichier" in sys.argv or not url:
        ics_text = ICS_PATH.read_text(encoding="utf-8")
        print("Source :", ICS_PATH)
    else:
        try:
            print("Téléchargement :", url)
            ics_text = telecharger(url)
            ICS_PATH.write_text(ics_text, encoding="utf-8")
        except Exception as exc:
            print("Téléchargement impossible, fichier local :", exc)
            ics_text = ICS_PATH.read_text(encoding="utf-8")

    filtre = None
    if "--groupe" in sys.argv:
        filtre = sys.argv[sys.argv.index("--groupe") + 1]
    importer(ics_text, filtre)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
