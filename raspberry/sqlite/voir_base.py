#!/usr/bin/env python3
"""Affiche un résumé de la base SQLite (étudiants, séances, pointages)."""

from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent / "pointage_local.sqlite"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    print("=== Étudiants (cartes liées) ===")
    for row in conn.execute(
        "SELECT num_etu, prenom, nom, groupe, uid_nfc FROM Etudiants_cache WHERE uid_nfc IS NOT NULL"
    ):
        print(" ", row)
    print("=== Pointages ===")
    for row in conn.execute(
        "SELECT date, heure, num_etu, id_ens, num_salle, synchronise FROM pointage_Locale ORDER BY date, heure"
    ):
        print(" ", row)
    n_etu = conn.execute("SELECT COUNT(*) FROM Etudiants_cache").fetchone()[0]
    n_seance = conn.execute("SELECT COUNT(*) FROM seances_cache").fetchone()[0]
    print(f"Total étudiants : {n_etu} | séances EDT : {n_seance}")
    conn.close()


if __name__ == "__main__":
    main()
