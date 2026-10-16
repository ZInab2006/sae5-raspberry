"""Enregistre un scan à partir de l'UID lu sur la carte."""

from datetime import datetime
from pathlib import Path
import sqlite3
import uuid

from trouver_seance import GROUPE_DEFAUT, trouver

DB_PATH = Path(__file__).resolve().parent / "pointage_local.sqlite"


def prochain_num_auto(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT num_etu FROM Etudiants_cache WHERE num_etu LIKE 'AUTO%' ORDER BY num_etu DESC LIMIT 1"
    ).fetchone()
    n = int(row["num_etu"].replace("AUTO", "")) + 1 if row else 1
    return f"AUTO{n:03d}"


def traiter_uid(uid_nfc) -> str:
    uid_nfc = str(uid_nfc).strip()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    etu = conn.execute(
        "SELECT num_etu, nom, prenom, groupe FROM Etudiants_cache WHERE uid_nfc = ?",
        (uid_nfc,),
    ).fetchone()

    nouveau = False
    if etu is None:
        num_etu = prochain_num_auto(conn)
        conn.execute(
            """
            INSERT INTO Etudiants_cache (num_etu, date_naiss, nom, prenom, groupe, uid_nfc)
            VALUES (?, NULL, 'INCONNU', ?, ?, ?)
            """,
            (num_etu, num_etu, GROUPE_DEFAUT, uid_nfc),
        )
        etu = conn.execute(
            "SELECT num_etu, nom, prenom, groupe FROM Etudiants_cache WHERE uid_nfc = ?",
            (uid_nfc,),
        ).fetchone()
        nouveau = True

    now = datetime.now()
    seance = trouver(etu["groupe"], now)
    id_ens = seance["id_ens"] if seance else None
    num_salle = seance["num_salle"] if seance else None

    deja = conn.execute(
        """
        SELECT id_pointage FROM pointage_Locale
        WHERE num_etu = ? AND date = ? AND IFNULL(id_ens, '') = IFNULL(?, '')
        """,
        (etu["num_etu"], now.strftime("%Y-%m-%d"), id_ens),
    ).fetchone()
    if deja:
        conn.commit()
        conn.close()
        return f"Déjà pointé : {etu['prenom']} {etu['nom']}"

    pid = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO pointage_Locale
            (id_pointage, num_etu, num_salle, date, heure, synchronise, id_ens)
        VALUES (?, ?, ?, ?, ?, 0, ?)
        """,
        (
            pid,
            etu["num_etu"],
            num_salle,
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            id_ens,
        ),
    )
    conn.commit()
    conn.close()
    statut = "NOUVEAU" if nouveau else "OK"
    cours = f"{id_ens} {num_salle}" if seance else "hors séance EDT"
    prefix = f"Carte inconnue → {etu['num_etu']} | " if nouveau else ""
    return f"{prefix}{statut} {etu['prenom']} {etu['nom']} ({etu['num_etu']}) | {cours}"
