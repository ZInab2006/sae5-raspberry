#!/usr/bin/env python3
"""Boucle de pointage pour le Raspberry Pi (lecteur RC522)."""

from pathlib import Path
import sys
import time

from pointage import traiter_uid

DB_PATH = Path(__file__).resolve().parent / "pointage_local.sqlite"


def lire_uid_rc522():
    try:
        from mfrc522 import SimpleMFRC522
    except ImportError:
        print("Module mfrc522 absent. Sur le Pi : sudo pip3 install mfrc522")
        print("En attendant, utilise : python3 simuler_pointage.py 968747738839")
        return None
    reader = SimpleMFRC522()
    print("Présente une carte RFID...")
    uid, _texte = reader.read()
    return str(uid)


def boucle() -> int:
    if not DB_PATH.exists():
        print("Lance d'abord : python3 init_sqlite.py --recreate && python3 import_edt.py --fichier")
        return 1
    print("Borne prête. Ctrl+C pour arrêter.")
    while True:
        uid = lire_uid_rc522()
        if uid is None:
            return 1
        print("UID :", uid)
        print(traiter_uid(uid))
        print("---")
        time.sleep(1)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(boucle())
    except KeyboardInterrupt:
        print("\nArrêt.")
        raise SystemExit(0)
