#!/usr/bin/env python3
"""Trouve la séance en cours (date + heure + groupe) dans seances_cache."""

from datetime import datetime
from pathlib import Path
import sqlite3
import sys

DB_PATH = Path(__file__).resolve().parent / "pointage_local.sqlite"
GROUPE_DEFAUT = "BUT3-TD3-PB"


def trouver(groupe: str, quand: datetime | None = None) -> dict | None:
    quand = quand or datetime.now()
    jour = quand.strftime("%Y-%m-%d")
    heure = quand.strftime("%H:%M")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT id_seance, groupe, id_ens, num_salle, date, heure_debut, heure_fin
        FROM seances_cache
        WHERE date = ?
          AND heure_debut <= ?
          AND heure_fin > ?
          AND (groupe = ? OR groupe = '')
        ORDER BY heure_debut
        LIMIT 1
        """,
        (jour, heure, heure, groupe),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


if __name__ == "__main__":
    groupe = sys.argv[1] if len(sys.argv) > 1 else GROUPE_DEFAUT
    seance = trouver(groupe)
    print("Maintenant :", datetime.now().strftime("%Y-%m-%d %H:%M"), "| groupe :", groupe)
    if seance:
        print(
            f"Séance : {seance['id_ens']} | {seance['num_salle']} | "
            f"{seance['heure_debut']}-{seance['heure_fin']} | {seance['groupe']}"
        )
    else:
        print("Aucune séance en cours pour ce groupe.")
