# Architecture — SAE5.B.01 Pointage NFC

**Projet :** Automatisation de l’appel des étudiants  
**Repo :** [sae5-raspberry](https://github.com/ZInab2006/sae5-raspberry)  
**Phase :** Partie 1 — réflexion et modélisation (avant implémentation)

---

## 1. Contexte et objectifs

L’IUT souhaite automatiser l’appel en cours grâce aux cartes étudiantes et à un lecteur NFC.

Le système doit permettre de savoir **qui** a été présent, dans **quel groupe**, pour **quel enseignement**, dans **quelle salle**, à **quelle date et heure**.

Contraintes principales prises en compte :

- plusieurs dispositifs utilisés en parallèle (cours simultanés) ;
- portabilité du dispositif (Raspberry Pi) ;
- fonctionnement possible **sans connexion réseau** ;
- centralisation des données sur un serveur ;
- démarrage et pointage rapides ;
- simplicité de gestion (étudiants, groupes, consultation).

---

## 2. Vue d’ensemble

Le système est découpé en **trois blocs** :

| Bloc | Composant | Rôle |
|------|-----------|------|
| A | Dispositif de pointage (Raspberry Pi) | Lit le badge, enregistre en local, donne un feedback |
| B | Serveur central + base de données | Centralise les données, reçoit la synchronisation |
| C | Interface web | Gère étudiants/groupes et consulte les pointages |

**Principe clé :** le pointage s’écrit **d’abord en local** sur le Raspberry Pi. Le serveur est la source de vérité **après synchronisation**.

```text
┌─────────────────────────────┐
│        SALLE DE COURS       │
│  Carte NFC → Capteur NFC    │
│           ↓                 │
│      Raspberry Pi           │
│      (agent + SQLite)       │
└──────────────┬──────────────┘
               │ HTTPS (si réseau OK)
               ▼
┌─────────────────────────────┐
│       SERVEUR CENTRAL       │
│  API REST + PostgreSQL      │
│           ↓                 │
│     Interface web           │
└─────────────────────────────┘
```

---

## 3. Composants détaillés

### 3.1 Agent de pointage (Raspberry Pi)

Logiciel exécuté sur le Pi. Il doit :

1. détecter une carte NFC et récupérer son identifiant (≤ 64 caractères) ;
2. identifier l’étudiant via un cache local ;
3. enregistrer le pointage localement avec date/heure ;
4. afficher un retour immédiat (OK / carte inconnue / erreur) ;
5. synchroniser automatiquement dès que le réseau est disponible.

Organisation logicielle prévue :

```text
agent-pointage/
├── reader/        # lecture NFC
├── local_store/   # SQLite (file d’attente + cache)
├── session/       # config séance (groupe, enseignement, salle)
├── sync/          # envoi/réception vers le serveur
├── ui/            # feedback (écran / LED / message)
└── main.py        # démarrage de l’application
```

### 3.2 Serveur central

Expose une API REST pour :

- recevoir les pointages en lot (sync) ;
- fournir le cache étudiants/cartes au dispositif ;
- gérer le CRUD étudiants / groupes ;
- filtrer et consulter les pointages.

### 3.3 Base de données centrale

Stockage unique et partagé par tous les dispositifs et l’interface web.

### 3.4 Interface web

Interface simple pour :

- créer/modifier un étudiant ;
- associer une carte NFC sans saisie manuelle de l’UID ;
- gérer les groupes ;
- consulter et filtrer les pointages.

> Priorité du projet : communication **dispositif ↔ base de données** (offline + sync). L’interface peut rester simple au début.

---

## 4. Modèle de données

### 4.1 Entités principales

| Entité | Contenu principal | Contrainte sujet |
|--------|-------------------|------------------|
| Étudiant | `num_etu`, nom, prénom, groupe, `uid_nfc` | `uid_nfc` ≤ 64 caractères |
| Séance | `id_seance`, `id_ens`, groupe, salle, date, heure_debut, heure_fin | créneau d’emploi du temps |
| Enseignement | `id_ens` / code | ≤ 32 caractères (ex. `R1.01`) |
| Salle | `num_salle` | ≤ 32 caractères |
| Dispositif | `device_id`, nom | un Pi = un `device_id` |
| Pointage | `id_pointage`, `num_etu`, `id_seance`, date, heure | événement unique (UUID) |
> L’emploi du temps est modélisé par l’entité **Séance** : une matière (`R1.01`) peut correspondre à plusieurs séances (dates/horaires différents).
### 4.2 Schéma relationnel (simplifié)
```text
ETUDIANT 1 ─── N POINTAGE N ─── 1 SEANCE
SEANCE N ─── 1 ENSEIGNEMENT
SEANCE N ─── 1 SALLE
DISPOSITIF 1 ─── N POINTAGE
Associations principales :

Effectue : Étudiant (0,n) — Pointage (1,1)
Contient : Séance (0,n) — Pointage (1,1)
Chaque pointage est rattaché à une séance, ce qui permet de savoir le groupe, l’enseignement, la salle et le créneau, puis de calculer les absences.

4.3 Stockage local (Raspberry Pi — SQLite)
Tables locales (“MCD lite”) :

Etudiants_cache : copie pour identifier un badge hors ligne (num_etu, nom, prénom, groupe, uid_nfc)
seances_cache : séances téléchargées (id_seance, id_ens, groupe, salle, date, horaires)
pointage_Locale : file d’attente des pointages (id_pointage, num_etu, id_seance, date, heure, synchronise)
Chaque pointage local possède un UUID (id_pointage) généré sur le Pi.
Cet identifiant sert côté serveur à éviter les doublons à la synchronisation.
---

## 5. Communications

| Lien | Protocole | Usage |
|------|-----------|--------|
| Pi → serveur | HTTPS + API REST | push des pointages, pull du cache étudiants |
| Interface → serveur | HTTPS + API REST | gestion et consultation |
| Auth dispositif | token lié au `device_id` | éviter les écritures anonymes |

Endpoints prévus :

- `POST /api/sync/pointages` — envoi d’un lot de pointages (idempotent sur UUID)
- `GET /api/sync/etudiants` — récupération/mise à jour du cache
- `POST /api/etudiants/...` — association carte ↔ étudiant (enrollment)
- `GET /api/pointages?...` — consultation filtrée

---

## 6. Fonctionnement hors connexion et synchronisation

### 6.1 Pointage hors ligne

1. L’étudiant présente sa carte.
2. Le Pi lit l’UID.
3. Le pointage est écrit en SQLite avec `synced = 0`.
4. Un feedback est affiché immédiatement.
5. Aucune dépendance au serveur à cet instant.

### 6.2 Synchronisation au retour du réseau

1. L’agent détecte que le serveur est joignable.
2. Il envoie les pointages non synchronisés (batch).
3. Le serveur enregistre chaque UUID (ignore si déjà présent).
4. Le Pi marque `synced = 1` uniquement pour les UUID confirmés.
5. En cas d’échec, les données restent en local et seront renvoyées plus tard.

### 6.3 Cas couverts

- interruption de connexion pendant le cours ;
- redémarrage du Raspberry Pi ;
- synchronisation interrompue ;
- erreurs de transmission ;
- doublons (grâce à l’UUID) ;
- plusieurs dispositifs simultanés (chacun avec son `device_id`).

---

## 7. Démarrage du dispositif

Après mise sous tension, l’agent démarre automatiquement (service système).

Avant la séance, l’enseignant sélectionne :

- le **groupe** ;
- l’**enseignement** ;
- la **salle**.

Ces informations sont attachées à chaque pointage local, même hors ligne.

Objectif : mise en service rapide, sans manipulation technique complexe.

---

## 8. Gestion des erreurs

| Situation | Comportement |
|-----------|--------------|
| Carte inconnue | Feedback “inconnu”, pas de faux rattachement étudiant |
| Erreur de lecture NFC | Feedback erreur, aucune écriture |
| Serveur inaccessible | Continuer en local, file d’attente |
| Sync partielle | ACK par UUID ; seul le confirmé passe à `synced = 1` |
| Coupure d’alimentation | Écriture SQLite à chaque pointage pour limiter les pertes |

---

## 9. Choix technologiques (proposés)

| Couche | Technologie | Justification |
|--------|-------------|----------------|
| Agent Pi | Python | Écosystème adapté au Raspberry Pi et aux capteurs NFC |
| Stockage local | SQLite | Léger, sans serveur local, robuste hors ligne |
| API serveur | FastAPI (ou Flask) | API REST claire, adaptée à la sync par lots |
| BDD centrale | PostgreSQL | Multi-clients, contraintes, filtres de consultation |
| Interface | Web simple (HTML/JS ou framework léger) | Suffisante pour la gestion ; priorité au pointage |
| Transport | HTTPS | Intégrité et confidentialité des échanges |

Ces choix pourront être ajustés après validation par l’enseignant, tant que l’architecture (local-first + sync idempotente) est conservée.

---

## 10. Branchement matériel (prévu)

Matériel imposé : Raspberry Pi, capteur NFC, kit de prototypage.

```text
Carte étudiante
      │ (NFC)
      ▼
 Capteur NFC ──(GPIO / USB / SPI)──► Raspberry Pi
                                         │
                                   SQLite locale
                                         │ (réseau)
                                         ▼
                                 Serveur + PostgreSQL
                                         │
                                   Interface web
```

> Le schéma de câblage précis (broches) sera complété après réception et identification exacte du module NFC fourni.

---

## 11. Points d’attention pour la suite

Avant de commencer le code complet :

- [ ] validation orale de cette architecture par l’enseignant ;
- [ ] réception du matériel ;
- [ ] précision du protocole du capteur NFC fourni ;
- [ ] implémentation prioritaire : pointage local → sync → multi-dispositifs → interface.

---

## 12. Synthèse

Cette architecture répond aux exigences du sujet en séparant clairement :

1. **capture rapide** côté dispositif ;
2. **résilience hors ligne** via SQLite ;
3. **centralisation** via API + PostgreSQL ;
4. **consultation** via une interface web simple.

La priorité est donnée à la fiabilité du couple **pointage local + synchronisation**, conformément aux critères d’évaluation de la SAE.
