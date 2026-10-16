-- Base locale Raspberry Pi (SQLite)
-- Conforme au MCD validé : Etudiants_cache / seances_cache / pointage_Locale
-- Pas besoin de matériel : cette base sert de cache + file d'attente hors ligne.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Cache des étudiants (copie du serveur, pour identifier un badge hors ligne)
CREATE TABLE IF NOT EXISTS Etudiants_cache (
    num_etu     TEXT PRIMARY KEY,
    date_naiss  TEXT,
    nom         TEXT NOT NULL,
    prenom      TEXT NOT NULL,
    groupe      TEXT NOT NULL CHECK (length(groupe) <= 16),
    uid_nfc     TEXT UNIQUE CHECK (uid_nfc IS NULL OR length(uid_nfc) <= 64)
);

-- Cache des séances (EDT téléchargé depuis le serveur, optionnel sur la borne)
CREATE TABLE IF NOT EXISTS seances_cache (
    id_seance    TEXT PRIMARY KEY,
    groupe       TEXT NOT NULL CHECK (length(groupe) <= 16),
    id_ens       TEXT NOT NULL CHECK (length(id_ens) <= 32),
    num_salle    TEXT CHECK (num_salle IS NULL OR length(num_salle) <= 32),
    date         TEXT NOT NULL,
    heure_debut  TEXT NOT NULL,
    heure_fin    TEXT NOT NULL
);

-- File d'attente des pointages locaux (source de vérité tant que non synchronisés)
CREATE TABLE IF NOT EXISTS pointage_Locale (
    id_pointage  TEXT PRIMARY KEY,
    num_etu      TEXT NOT NULL,
    num_salle    TEXT CHECK (num_salle IS NULL OR length(num_salle) <= 32),
    date         TEXT NOT NULL,
    heure        TEXT NOT NULL,
    synchronise  INTEGER NOT NULL DEFAULT 0 CHECK (synchronise IN (0, 1)),
    id_ens       TEXT CHECK (id_ens IS NULL OR length(id_ens) <= 32),
    FOREIGN KEY (num_etu) REFERENCES Etudiants_cache(num_etu)
);

CREATE INDEX IF NOT EXISTS idx_etudiants_uid
    ON Etudiants_cache(uid_nfc);

CREATE INDEX IF NOT EXISTS idx_pointage_sync
    ON pointage_Locale(synchronise);

CREATE INDEX IF NOT EXISTS idx_pointage_etu_date
    ON pointage_Locale(num_etu, date);
