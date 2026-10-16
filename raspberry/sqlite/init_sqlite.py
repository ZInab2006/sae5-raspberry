#!/usr/bin/env python3
"""Crée la base SQLite locale et charge le groupe BUT3-TD3-PB."""

from pathlib import Path
import csv
import sqlite3
import sys

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "pointage_local.sqlite"
SCHEMA = HERE / "schema.sql"
SEED = HERE / "seed.sql"
ETUDIANTS = HERE / "data" / "etudiants_BUT3-TD3-PB.csv"


def charger_etudiants(conn: sqlite3.Connection) -> int:
    with ETUDIANTS.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    conn.execute("DELETE FROM pointage_Locale")
    conn.execute("DELETE FROM Etudiants_cache")
    for row in rows:
        uid = (row.get("uid_nfc") or "").strip() or None
        conn.execute(
            """
            INSERT INTO Etudiants_cache (num_etu, date_naiss, nom, prenom, groupe, uid_nfc)
            VALUES (?, NULL, ?, ?, ?, ?)
            """,
            (
                row["num_etu"].strip(),
                row["nom"].strip(),
                row["prenom"].strip(),
                row["groupe"].strip(),
                uid,
            ),
        )
    return len(rows)


def main() -> int:
    recreate = "--recreate" in sys.argv
    if DB_PATH.exists() and recreate:
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    n_etu = charger_etudiants(conn)
    n_seance = conn.execute("SELECT COUNT(*) FROM seances_cache").fetchone()[0]
    if n_seance == 0:
        conn.executescript(SEED.read_text(encoding="utf-8"))
        n_seance = conn.execute("SELECT COUNT(*) FROM seances_cache").fetchone()[0]
    conn.commit()

    n_cartes = conn.execute(
        "SELECT COUNT(*) FROM Etudiants_cache WHERE uid_nfc IS NOT NULL"
    ).fetchone()[0]
    print(f"Base : {DB_PATH}")
    print(f"  étudiants : {n_etu} (cartes associées : {n_cartes})")
    print(f"  séances   : {n_seance}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
