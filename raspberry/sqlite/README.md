# Pointage RFID — base SQLite locale (Raspberry Pi)

Prototype SAE5.B.01 

La borne enregistre les badges **en local** (SQLite), même sans Internet.
L’EDT ADE est déjà importé. Une carte inconnue crée une fiche `AUTO001` avec **l’UID lu sur la carte** (on ne fabrique pas l’UID).

## Fichiers

```text
raspberry/sqlite/
├── README.md                 ← ce fichier
├── schema.sql                ← tables SQLite (MCD validé)
├── seed.sql                  ← séances de secours (si pas d'ICS)
├── init_sqlite.py            ← crée la base + charge le groupe B
├── import_edt.py             ← importe l'emploi du temps ADE (.ics)
├── trouver_seance.py         ← trouve le cours selon date/heure/groupe
├── pointage.py               ← logique : UID → étudiant → pointage
├── lire_rfid.py              ← à lancer sur le Pi (lecteur RC522)
├── simuler_pointage.py       ← test sans lecteur (on tape l'UID)
├── associer_carte.py         ← relie un UID à un nom du groupe B
├── voir_base.py              ← affiche étudiants / pointages
├── requirements-pi.txt
└── data/
    ├── etudiants_BUT3-TD3-PB.csv   ← 20 étudiants parcours B
    ├── ADECal.ics                  ← export EDT ADE
    └── edt_url.txt                 ← URL iCal ADE
```

La base créée s’appelle `pointage_local.sqlite` (fichier local, pas Git).

## 1. Copier le dossier sur le Raspberry

Sur ton PC (dans le repo) :

```bash
scp -r raspberry/sqlite admin@IP_DU_PI:~/pointage_sqlite
```

Sur le Pi :

```bash
cd ~/pointage_sqlite
```

## 2. Installer le lecteur (si pas déjà fait)

Quentin a déjà `test_rfid.py` qui affiche :

```text
Présente une carte RFID...
UID : 968747738839
```

Même bibliothèque :

```bash
sudo pip3 install mfrc522 RPi.GPIO
```

SPI doit être activé : `sudo raspi-config` → Interface Options → SPI → Yes.

## 3. Créer la base (groupe B + EDT)

```bash
cd ~/pointage_sqlite
python3 init_sqlite.py --recreate
python3 import_edt.py --fichier
python3 voir_base.py
```

Tu dois voir **20 étudiants** BUT3-TD3-PB et **~179 séances** ADE.

## 4. Tester le pointage avec le RC522

```bash
python3 lire_rfid.py
```

Présente une carte.

- **1er passage** : `Carte inconnue → AUTO00x` + pointage enregistré  
- **2e passage** de la même carte : `Déjà pointé`  
- L’UID affiché doit ressembler à celui de `test_rfid.py` (ex. `968747738839`)

Ctrl+C pour arrêter.

## 5. Relier la carte à un vrai nom (liste groupe B)

Exemple si c’est la carte de Quentin :

```bash
python3 associer_carte.py BOSSUS 968747738839
python3 lire_rfid.py
```

Le prochain scan doit afficher **Quentin BOSSUS**, plus `INCONNU`.

Autres noms : `OUTMANI`, `FREMY`, `KIME`, etc. (voir le CSV).

## 6. Tester sans coller la carte (simulation)

Même logique, UID tapé au clavier :

```bash
python3 simuler_pointage.py 968747738839
python3 trouver_seance.py BUT3-TD3-PB
python3 voir_base.py
```

## Comportement attendu

| Situation | Résultat |
|-----------|----------|
| Carte déjà associée | Pointage au nom de l’étudiant |
| Carte jamais vue | Fiche `AUTO…` + UID de **la carte** + pointage |
| Même carte, même cours | Ignoré (pas de doublon) |
| Hors créneau EDT | Pointage quand même, sans code cours |

Le matching EDT utilise **date + heure + groupe** (`BUT3-TD3-PB`).

## En cas de problème

- `Module mfrc522 absent` → `sudo pip3 install mfrc522`
- `Lance d'abord init_sqlite.py` → étape 3
- UID différent à chaque scan → mauvaise lecture ; réessayer, carte plus près
- 0 séance importée → `python3 import_edt.py --fichier` (le `.ics` est dans `data/`)

Pour recharger EDT depuis ADE (si le Pi a Internet) :

```bash
python3 import_edt.py
```
