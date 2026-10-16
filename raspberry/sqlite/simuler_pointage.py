#!/usr/bin/env python3
"""Simule un scan en tapant l'UID (comme celui affiché par test_rfid.py)."""

from pathlib import Path
import sys

from pointage import traiter_uid

DB_PATH = Path(__file__).resolve().parent / "pointage_local.sqlite"

if __name__ == "__main__":
    if not DB_PATH.exists():
        print("Lance d'abord : python3 init_sqlite.py")
        raise SystemExit(1)
    if len(sys.argv) < 2:
        print("Usage : python3 simuler_pointage.py <UID>")
        print("Exemple : python3 simuler_pointage.py 968747738839")
        raise SystemExit(1)
    print(traiter_uid(sys.argv[1]))
