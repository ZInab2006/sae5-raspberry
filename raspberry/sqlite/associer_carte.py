#!/usr/bin/env python3
"""Associe un UID de carte à un étudiant de la liste (groupe B)."""

from pathlib import Path
import sqlite3
import sys

DB_PATH = Path(__file__).resolve().parent / "pointage_local.sqlite"


def associer(nom: str, uid_nfc: str) -> None:
    uid_nfc = str(uid_nfc).strip()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT num_etu, nom, prenom, uid_nfc FROM Etudiants_cache WHERE nom LIKE ?",
        (nom.strip().upper(),),
    ).fetchall()
    if not rows:
        print(f"Aucun étudiant trouvé pour : {nom}")
        conn.close()
        return
    if len(rows) > 1:
        print("Plusieurs étudiants, précise le nom :")
        for r in rows:
            print(f"  {r['num_etu']}  {r['prenom']} {r['nom']}")
        conn.close()
        return

    etu = rows[0]
    deja = conn.execute(
        "SELECT num_etu, nom, prenom FROM Etudiants_cache WHERE uid_nfc = ?",
        (uid_nfc,),
    ).fetchone()
    if deja and deja["num_etu"] != etu["num_etu"]:
        if deja["nom"] == "INCONNU" or str(deja["num_etu"]).startswith("AUTO"):
            conn.execute(
                "UPDATE pointage_Locale SET num_etu = ? WHERE num_etu = ?",
                (etu["num_etu"], deja["num_etu"]),
            )
            conn.execute("DELETE FROM Etudiants_cache WHERE num_etu = ?", (deja["num_etu"],))
            print(f"Fiche temporaire {deja['num_etu']} fusionnée vers {etu['prenom']} {etu['nom']}")
        else:
            print(f"UID déjà lié à {deja['prenom']} {deja['nom']}")
            conn.close()
            return

    conn.execute(
        "UPDATE Etudiants_cache SET uid_nfc = ? WHERE num_etu = ?",
        (uid_nfc, etu["num_etu"]),
    )
    conn.commit()
    conn.close()
    print(f"Carte {uid_nfc} associée à {etu['prenom']} {etu['nom']} ({etu['num_etu']})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage : python3 associer_carte.py NOM UID")
        print("Exemple : python3 associer_carte.py BOSSUS 968747738839")
        raise SystemExit(1)
    associer(sys.argv[1], sys.argv[2])
