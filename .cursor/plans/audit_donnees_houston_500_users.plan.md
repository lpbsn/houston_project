---
name: Audit donnees Houston 500 users
overview: "Audit gestion/retention/croissance Houston — 500 users/6 mois. P0 : remplacer private_media local Railway par bucket S3 prive partage + PendingStorageDeletion. Pas de worker Celery dans api-web."
todos:
  - id: lot1-storage-backend
    content: "Lot 1 — Backend stockage objet (django-storages/S3, Railway Bucket, checks prod, upload/preview/delete, tests securite)"
    status: pending
  - id: lot1-spike-railway-bucket
    content: "Lot 1 — Spike faisabilite Railway Bucket (credentials, CORS, limites lifecycle/versioning) avant figer config"
    status: pending
  - id: lot2-pending-deletion
    content: "Lot 2 — PendingStorageDeletion + drain Celery worker standard + retries/leases/reconcile"
    status: pending
  - id: lot3-migration-volume
    content: "Lot 3 — Migration volume vers bucket (inventaire, copie, cutover, fallback lecture temporaire, retrait volume)"
    status: pending
  - id: lot4-retention-p1
    content: "Lot 4 — Retention PostgreSQL P1 (auth, notifications, push, outbox, compteurs)"
    status: pending
isProject: false
---

# Audit donnees Houston — gestion, retention et croissance

**Scenario principal : 500 utilisateurs pendant 6 mois (180 jours).**

Contexte : Django / DRF / PostgreSQL, Celery / Beat / Redis, Railway, fichiers prives (actuellement `private_media` local), OpenAI (pipeline observation + transcription).

Sources verifiees : `apps/api/houston/`, `apps/api/config/settings.py`, `pyproject.toml`, `docs/deploy/railway_*.md`, `infra/railway/`, `docker-compose.yml`.

---

## 1. Resume executif

Houston dispose d'une purge chat fonctionnelle (7 jours) et d'aucune purge production pour auth, notifications, push, outbox ni AI logs. La purge uploads temporaires met a jour la DB mais **ne supprime pas fiablement les fichiers** sur Railway avec la topologie volume actuelle.

Le risque bloquant avant ouverture a 500 utilisateurs n'est **pas** la capacite PostgreSQL (~1 a ~12 Go estimes) ni Redis (< 1 Go operationnel). C'est la **desynchronisation PostgreSQL ↔ stockage fichier** : chemins Celery mettent la DB a jour alors que les fichiers restent sur un volume accessible uniquement par `api-web`.

**Correction P0 retenue (robuste, production, 500 users / 6 mois)** :

1. **Remplacer** le stockage local `private_media` / volume Railway par un **bucket S3-compatible prive** (Railway Storage Bucket en option principale), accessible depuis `api-web`, `celery-worker` et `celery-beat` via credentials.
2. **Conserver** une file de suppression durable PostgreSQL (`PendingStorageDeletion`) pour garantir la coherence DB ↔ objet, avec drain par le **worker Celery standard** (pas de processus supplementaire dans `api-web`).
3. **Migrer** les fichiers existants du volume vers le bucket avant retrait du volume (lot dedie, sans dual-write permanent).

**Explicitement exclu** : worker Celery dans `start-api-web.sh`, thread Daphne, middleware, traitement lie au trafic HTTP, maintien durable du volume local comme source de verite.

---

## 2. Verdict pour 500 utilisateurs / 6 mois

> **Houston n'est pas prete en l'etat pour une ouverture maitrisee a 500 utilisateurs pendant 6 mois**, principalement parce que la suppression de `private_media` n'est pas fiable avec la topologie Railway actuelle (volume local non partageable entre services).

### Nuances

| Dimension | Verdict |
|---|---|
| **PostgreSQL** | Semble pouvoir absorber l'ordre de grandeur estime (~1 a ~12 Go) sur 6 mois. **Pas** le facteur bloquant immediat. |
| **Redis** | Non bloquant (< 200 Mo a ~1 Go). Broker transitoire, tickets WS TTL 60 s. |
| **Croissance non bornee (P1)** | Auth, notifications, push, outbox, AI logs : retention a planifier avant montee effective. |
| **Blocage P0** | Coherence **PostgreSQL ↔ stockage fichier** sur volume local Railway + echecs silencieux (`OSError` avale dans `media_services.py`). |

### Correction P0

Le **stockage objet prive partage** est la correction structurelle du P0 — **pas** une amelioration future. Le volume local Railway est incompatible avec des replicas `api-web`, des suppressions Celery fiables et une exploitation a 500 users / 6 mois.

Le P0 reste **structurel et immediat** : chaque suppression Celery sur le filesystem actuel peut desynchroniser DB et disque, independamment du delai avant saturation.

---

## 3. Hypotheses de capacite

### Parametres fixes

| Parametre | Valeur | Source |
|---|---|---|
| Utilisateurs `U` | 500 | Scenario |
| Duree `D` | 180 jours | Scenario |
| Etablissements `E` | 50 | **Hypothese** |

### Ancres code

| Parametre | Valeur | Fichier |
|---|---|---|
| Photos max / observation | 3 | `observations/constants.py` |
| Taille max photo | 10 MiB | `HOUSTON_OBSERVATION_PHOTO_MAX_BYTES` |
| TTL upload temporaire | 24 h | `HOUSTON_TEMPORARY_UPLOAD_TTL_HOURS` |
| Retention chat | 7 jours | `HOUSTON_CHAT_MESSAGE_RETENTION_DAYS` |
| Candidats AI max / obs | 5 | `signals/constants.py` |
| AIUsageLog / tentative pipeline | 1 ligne | `ai/observation_pipeline.py` |
| Access token TTL | 15 min | `HOUSTON_AUTH_ACCESS_TOKEN_TTL` |
| Purge auth / notif / outbox | Aucune prod | Exploration codebase |

### Trois scenarios (hypotheses explicites)

| Parametre | Faible | Realiste | Eleve |
|---|---|---|---|
| `U_dau` | 100 | 200 | 300 |
| Obs / user actif / jour | 1 | 2,5 | 5 |
| Obs avec photo | 30 % | 50 % | 70 % |
| Photos moy / obs | 1 | 1 | 1,5 |
| Taille moy photo (Mo) | 1,5 | 2 | 2,5 |
| Agregation Celery (% photos liees) | 25 % | 35 % | 45 % |
| Uploads abandonnes | 5 % | 10 % | 12 % |
| Chat msgs / user actif / jour | 5 | 15 | 25 |
| Notifications / user / jour | 4 | 10 | 18 |
| Refresh / user actif / jour | 4 | 8 | 12 |

### Tableau recapitulatif

| Domaine | Faible | Realiste | Eleve | Formule dominante |
|---|---|---|---|---|
| Observations | ~18 k | ~90 k | ~270 k | `U_dau x obs/j x D` |
| Fichiers orphelins (etat actuel, cumul 6m) | ~2 Go | ~42 Go | ~417 Go | `P x agg x size` + abandon TTL |
| Chat (regime 7j) | ~3,5 k | ~21 k | ~52 k | `U_dau x msgs/j x 7` |
| Notifications | ~360 k | ~900 k | ~1,6 M | `U x notif/j x D` |
| AccessToken | ~360 k | ~1,6 M | ~4,3 M | sessions x jours x refresh/j |
| PostgreSQL | ~1 Go | ~3-5 Go | ~8-12 Go | tokens + notifications |
| Redis | < 200 Mo | 200-500 Mo | < 1 Go | transitoire |

**Avec bucket S3** : les orphelins disque du volume local deviennent une **dette de migration** a traiter au lot 3 ; les nouvelles suppressions Celery deviennent fiables une fois le backend objet + `PendingStorageDeletion` en place. Le bucket lui-meme ne supprime pas automatiquement les objets orphelins (pas de lifecycle Railway documente).

---

## 4. Estimations faible / realiste / elevee

(Voir section 3 — chiffres conserves ; facteur dominant orphelins = chemins Celery + volume non partage, corrige par architecture cible.)

---

## 5. Inventaire des donnees

| Modele | Retention actuelle | Purge prod | Risque |
|---|---|---|---|
| `TemporaryUpload` | TTL 24h | Celery (DB partiel Railway) | Moyen |
| `ObservationMedia` | Tant que signal actif | Via services media | Eleve |
| `ChatMessage` | 7 jours | Celery daily | **Borne** |
| `UserSession` / tokens | Indefinie | Non | **Eleve** |
| `Notification` / `PushDelivery` | Indefinie | Non | **Eleve** |
| `ActionPlanMixedOutboxEntry` | PROCESSED conserve | Non | Eleve |
| `AIUsageLog` | Indefinie | Non | Eleve |
| Donnees metier (`Observation`, `Signal`, `ActionPlanExecution`) | Indefinie | Non (intentionnel) | Eleve |

42 modeles dans 12 fichiers `apps/api/houston/*/models.py`.

---

## 6. Purges existantes

| Purge | Cadence | Railway actuel |
|---|---|---|
| `purge_chat_messages_task` | 04:00 UTC | DB OK si beat actif |
| `cleanup_expired_uploads_task` | 05:00 UTC | **DB OK, fichiers NON** (volume split) |
| Auth / notifications / outbox / AI | — | **Aucune** |

Beat : `CELERY_BEAT_SCHEDULE` dans `apps/api/config/settings.py` L176-215.

---

## 7. Analyse `private_media` (etat actuel)

### Code actuel

| Element | Etat | Fichier |
|---|---|---|
| Backend | `PrivateMediaStorage(FileSystemStorage)` | `uploads/private_storage.py` |
| Racine | `HOUSTON_PRIVATE_MEDIA_ROOT` | `settings.py` |
| Upload | `TemporaryUpload.file` FileField | `uploads/models.py` |
| Reference media | `ObservationMedia.storage_key` (copie de `file.name`) | `observations/models.py` |
| Preview | API `FileResponse(storage.open())` + token signe | `observations/api/media_views.py`, `media_access.py` |
| Suppression | `_delete_storage_file_idempotent` + `Path` fallback local | `observations/media_services.py` |
| Transcription | `tempfile` ephemere, **hors** private_media | `uploads/api/transcription_views.py` |
| Dependances S3 | **Aucune** (`boto3`, `django-storages` absents de `pyproject.toml`) | `pyproject.toml` |
| Checks prod | `uploads.E001/E002` — filesystem writable | `uploads/checks.py` |

### Topologie Railway actuelle

| Affirmation | Statut |
|---|---|
| Volume persistant uniquement sur `api-web` | **Confirme doc** `railway_deploy_contract.md` |
| Worker : `/tmp/houston-private-media` | **Confirme doc** `railway_variables.md` |
| Volumes non partageables entre services | **Confirme doc** |
| `start-api-web.sh` = Daphne + nginx seulement | **Confirme code** |
| Volume monte en prod | **A verifier deploiement** (config UI Railway) |

### Local Docker

`docker-compose.yml` : volume `private_media` partage entre `api` et `celery` — **masque le bug Railway** dans les tests.

### Hypothese P0 confirmee

> DB mise a jour, fichier persistant reste sur le volume web.

**Confirme** pour chemins Celery. `_delete_storage_file_idempotent` avale `OSError` (L20-21 `media_services.py`).

---

## 8. Chemins de suppression (etat actuel)

| Chemin | Entree | Processus | DB | Fichier | Volume reel |
|---|---|---|---|---|---|
| Cleanup uploads expires | `cleanup_expired_uploads_task` | celery-worker | `DELETED` | sync `file.delete` | **Non** |
| Agregation observation | `aggregate_candidate_into_signal` | celery-worker | media supprime | `on_commit` | **Non** |
| Resolve signal | `resolve_signal` | api-web | idem | `on_commit` | **Oui** |
| Cancel signal | `cancel_signal` | api-web | idem | `on_commit` | **Oui** |
| DELETE upload user | `delete_temporary_upload` | api-web | `DELETED` | sync | **Oui** |

**Apres architecture cible** : tous les chemins enqueue `PendingStorageDeletion` ; le worker Celery standard execute `DELETE` objet sur le bucket partage.

---

## 9. Risques P0 / P1 / P2

### P0 — avant ouverture

| Risque | Mitigation cible |
|---|---|
| Volume local non partage | Bucket S3 prive partage |
| Suppressions Celery sur mauvais FS | Backend objet + credentials sur tous les workers |
| Echecs silencieux | Ne plus avaler les erreurs ; statut FAILED + logs |
| DB / stockage desynchronises | `PendingStorageDeletion` + reconciliation |
| Pas de reconciliation | Commands `reconcile_storage --dry-run` |
| Dependance a un seul replica api-web avec volume | Retrait volume ; api-web scalable |

### P1 — avant 500 users effectifs

Auth tokens, notifications, push, outbox : retention + compteurs (lot 4).

### P2

AI logs, invitations, push revokes, conversations chat vides, optimisations presigned URL.

---

## 10. Faisabilite stockage objet (analyse code)

### Ce que le code permet sans refonte majeure

| Point | Faisabilite | Notes |
|---|---|---|
| Remplacer `FileSystemStorage` | **Oui** | `get_private_media_storage()` point d'injection unique |
| Conserver `storage_key` | **Oui** | Deja une string ; mappe directement a object key S3 |
| Conserver chemin `establishments/{id}/temporary/{uuid}.ext` | **Oui** | `temporary_upload_path()` — pas de nom user-controlled |
| Preview via API | **Oui** | `storage.open()` fonctionne avec backend S3 ; **conserve le contrat** URL signee existante |
| Preview via presigned URL | **Possible** | Optimisation optionnelle ; Railway documente presigned GET (max 90 j) |
| Upload via API multipart actuel | **Oui** | `upload.file.save()` via storage Django |
| Suppression Celery | **Oui** | `storage.delete(key)` depuis n'importe quel worker avec credentials |
| Tests locaux | **A requirir** | MinIO / moto / fake storage — pas de provider Railway en CI |
| `media_services.py` fallback `Path` | **A retirer** | Incompatible S3 ; tout passe par storage abstraction |
| Checks `uploads.E001/E002` | **A remplacer** | Checks credentials bucket en prod |
| Migration FileField | **Non requise** | `storage=` callable ; keys en DB |

### Strategie lecture / preview (recommandation)

| Mode | Usage | Contrat |
|---|---|---|
| **API proxy (retenu lot 1)** | Preview observation media | Conserve `build_observation_media_preview_url` + token `TimestampSigner` + RBAC etablissement — **aucun changement frontend** |
| Presigned URL courte duree | Optimisation future (lot P2) | Reduire egress service ; meme autorisation en amont |
| URL publique permanente | **Interdit** | Railway : buckets prives uniquement |

Transcription : reste hors bucket (tempfile) — inchangé.

### Railway Storage Bucket — limites a verifier au spike (lot 1)

**Ne pas supposer** ces fonctionnalites (doc Railway, fev. 2026) :

| Fonctionnalite | Statut Railway Buckets |
|---|---|
| Buckets publics | **Non supportes** |
| Lifecycle automatique | **Non supporte** |
| Versioning objets | **Non supporte** |
| Object lock | **Non supporte** |
| Chiffrement cote serveur configurable | **Non supporte** (chiffrement at-rest plateforme oui) |
| Backups / snapshots bucket | **Non supportes** |
| Explorateur fichiers integre | **Non** |

**Supporte** : Put, Get, Head, Delete, List, Copy, Multipart, Presigned URLs, tagging.

**Implication** : pas de purge automatique bucket — suppression applicative via `PendingStorageDeletion` obligatoire.

**Alternative** : autre provider S3 (R2, AWS) si limitation bloquante decouverte au spike — meme abstraction Django.

### Variables Railway attendues (a documenter lot 1)

Exemples (noms a figer au spike, jamais en repo) :

- `HOUSTON_OBJECT_STORAGE_BACKEND=s3`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (injectes Railway Bucket)
- `AWS_STORAGE_BUCKET_NAME` (separe par environnement)
- `AWS_S3_ENDPOINT_URL` (ex. `https://storage.railway.app`)
- `AWS_S3_REGION_NAME`
- Optionnel : `HOUSTON_OBJECT_STORAGE_PREFIX` par env (`prod/`, `staging/`)

Retirer progressivement `HOUSTON_PRIVATE_MEDIA_ROOT` comme source de verite prod.

### Environnement local Docker

- Remplacer ou completer volume `private_media` par **MinIO** (service Compose) ou filesystem local en dev uniquement (`HOUSTON_OBJECT_STORAGE_BACKEND=filesystem`).
- `api` et `celery` doivent partager le **meme** backend configure.

---

## 11. Solution P0 recommandee

### Comparaison des options (transitoires exclues)

| Option | Verdict |
|---|---|
| Worker Celery dans `api-web` / `start-api-web.sh` | **Rejete** — couple au web, empeche replicas, fragile |
| Queue Redis seule | **Insuffisant** — pas de durabilite ni reconciliation |
| Table `PendingStorageDeletion` seule sans bucket | **Insuffisant** — ne resout pas l'acces volume |
| Management command seule | **Insuffisant** — pas de scheduling fiable in-repo |
| **Bucket S3 prive + PendingStorageDeletion + worker Celery standard** | **Retenu** |

### Architecture cible

```text
transaction metier
  → INSERT PendingStorageDeletion (status=PENDING) [on_commit ou dans transaction selon chemin]
  → commit PostgreSQL
  → (optionnel) enqueue drain_pending_storage_deletions_task
celery-worker (credentials bucket)
  → claim lignes PENDING (SELECT FOR UPDATE SKIP LOCKED)
  → status=PROCESSING + lease_expires_at
  → DELETE objet S3 (storage.delete ou boto3)
  → verifier objet absent (HeadObject 404 ou not exists)
  → status=DONE + processed_at
  → ou attempts++, backoff available_at, status=FAILED si max
```

**Tous les workers** (`api-web` si tache locale, `celery-worker`) partagent les credentials bucket via variables Railway. **Aucune queue consommable uniquement par api-web.**

### Modele `PendingStorageDeletion`

| Champ | Role |
|---|---|
| `storage_key` | Object key S3 (unicite partielle pending/processing) |
| `source` | `upload_cleanup`, `observation_media`, `reconcile`, etc. |
| `status` | `PENDING`, `PROCESSING`, `DONE`, `FAILED` |
| `attempt_count` | Retries |
| `last_error` | Derniere erreur (sans secrets) |
| `available_at` | Backoff |
| `lease_expires_at` | Claim concurrent |
| `processed_at` | Fin succes |

**Idempotence** : suppression reussie si objet deja absent. **Unicite** : une seule ligne active par `storage_key`.

**Protection** : refuser suppression si `storage_key` encore reference par `TemporaryUpload` (LINKED/VALIDATED) ou `ObservationMedia` — reconciliation et replay respectent cette garde.

**Transaction metier rollback** : `PendingStorageDeletion` cree en `on_commit` uniquement — rollback = aucune demande.

**Erreurs** : ne plus avaler silencieusement ; logger + `last_error` + retry ou FAILED.

### Drain Celery

| Element | Valeur |
|---|---|
| Tache | `drain_pending_storage_deletions_task` |
| Queue | `celery` (defaut) — **pas** de queue dediee api-web |
| Processus | `celery-worker` service Railway existant |
| Beat | Entree periodique (ex. 1-2 min) dans `CELERY_BEAT_SCHEDULE` |
| Claim | `select_for_update(skip_locked=True)` batch |
| Lease expire | Reset `PROCESSING` → `PENDING` si `lease_expires_at` depasse |
| Backoff | 1m, 5m, 15m, 1h, 6h |
| Max attempts | Configurable (defaut 5) |

### Metriques et logs

- `storage_deletion_enqueued`, `storage_deletion_drained`, `storage_deletion_failed`
- Compteurs : pending / processing / failed (log structure ou commande `storage_deletion_stats`)
- Alerte si `FAILED` > seuil ou pending age > N heures

### Commands ops

| Commande | Role |
|---|---|
| `drain_pending_storage_deletions` | Drain manuel |
| `replay_failed_storage_deletions` | Rejouer FAILED |
| `reconcile_storage --dry-run` (defaut) | DB ↔ bucket ; orphelins ; references cassees |
| `reconcile_storage --apply` | Suppression orphelins confirmes (avec gardes) |

---

## 12. Lot 3 — Migration volume vers bucket

Strategie (pas de dual-write permanent) :

```text
1. Deploy backend bucket (lot 1) — nouveaux uploads → bucket uniquement
2. Inventaire volume api-web (manage.py inventory_private_media_volume)
3. Mapping TemporaryUpload.file + ObservationMedia.storage_key
4. Detection orphelins (fichier sans ref DB, ref DB sans fichier)
5. Copie vers bucket (memes object keys quand possible)
6. Verification taille + existence (+ checksum MD5/ETag si disponible)
7. Lecture fallback local temporaire (CompositeStorage ou flag HOUSTON_STORAGE_READ_FALLBACK_LOCAL) — lecture seule, duree limitee
8. Reconciliation 100 % references DB pointent vers objets bucket existants
9. Desactiver fallback local
10. Supprimer volume Railway api-web — uniquement apres validation complete
```

### Etapes detaillees

| Etape | Action | Securite |
|---|---|---|
| Inventaire | Lister volume + compter refs DB | `--dry-run` |
| Copie | `aws s3 cp` ou storage.copy ; skip si deja present meme taille | Pas d'ecrasement sans flag |
| Cutover upload | Feature flag `HOUSTON_OBJECT_STORAGE_BACKEND=s3` | Rollback flag possible |
| Fallback lecture | Si objet absent bucket, tenter local une fois | Retire apres migration |
| Validation | 0 ref DB cassee ; echantillon preview OK | Smoke checklist |
| Retrait volume | Railway UI | Apres 7j sans fallback en prod-test |

### Orphelins historiques

Fichiers deja orphelins (DB DELETED, fichier present) : inventorier au lot 3 ; supprimer via `reconcile_storage --apply` apres validation, ou laisser en quarantaine bucket prefix `orphan/`.

---

## 13. Garde-fous obligatoires

| Garde-fou | Implementation |
|---|---|
| Config validee au demarrage | Remplacer `uploads.E001/E002` par checks bucket credentials en `DJANGO_DEBUG=0` |
| Refus demarrage prod sans credentials | `check_object_storage_configured` — Error bloquant |
| Buckets separes par environnement | `AWS_STORAGE_BUCKET_NAME` distinct prod/staging/local |
| Aucune cle dans le repo | Variables Railway + `.env.example` sans secrets |
| Timeouts reseau S3 | `boto3` config `connect_timeout`, `read_timeout` |
| Retries bornes | `attempt_count` max + backoff |
| Taille / MIME valides | `validate_observation_photo_upload` conserve (`uploads/validators.py`) |
| Object keys non user-controlled | `temporary_upload_path()` + UUID |
| Pas d'URL publique permanente | Bucket prive ; preview via API token |
| Isolation etablissements | Tests RBAC preview ; prefix path `establishments/{id}/` |
| Reconcile `--dry-run` par defaut | Command flag |
| Pas de suppression si encore reference | Garde dans drain + reconcile |
| Alerte FAILED / pending ancien | Logs + metriques |
| Compteurs pending/processing/failed | Command `storage_deletion_stats` |
| Procedure restauration | Runbook : restore depuis copie bucket externe (backups non natifs Railway — **export periodique a planifier**) |

---

## 14. Lots d'implementation

### Lot 1 — Backend stockage objet

- Ajouter `django-storages[s3]` + `boto3` (`pyproject.toml` — approbation dependance)
- `PrivateMediaStorage` → backend S3 configurable (`uploads/private_storage.py`)
- Settings : backend filesystem (dev) / s3 (prod) ; variables Railway
- Spike Railway Bucket : credentials, endpoint, CORS si upload direct futur, limites documentees section 10
- Upload (`create_temporary_photo_upload`), link observation, preview API, delete via storage
- Retirer fallback `Path` dans `media_services.py`
- Checks prod bucket
- Tests securite : upload/read, refus inter-etablissement, validation MIME/taille
- Doc : `railway_deploy_contract.md`, `railway_variables.md`, `.env.example`

### Lot 2 — Suppression durable

- Modele `PendingStorageDeletion` + migration
- `storage_deletion.py` : enqueue, claim, drain, gardes reference
- Brancher `uploads/services.py`, `observations/media_services.py`
- `drain_pending_storage_deletions_task` sur **celery-worker**
- Beat schedule ; commands replay / stats / reconcile
- Tests : Celery delete, idempotence, retry, FAILED, lease, rollback transaction, refus si reference

### Lot 3 — Migration fichiers existants

- `inventory_private_media_volume`, `migrate_private_media_to_bucket`
- Fallback lecture temporaire
- Validation + retrait volume
- Tests migration + orphelin dry-run

### Lot 4 — Retention PostgreSQL P1

- Purge sessions/tokens expires
- Purge notifications + push
- Purge outbox PROCESSED
- Settings retention + compteurs logs

---

## 15. Tests necessaires

| Test | Lot |
|---|---|
| Upload puis lecture fichier prive | 1 |
| Refus acces inter-etablissement preview | 1 |
| Suppression depuis tache Celery | 2 |
| Suppression idempotente objet deja absent | 2 |
| Erreur reseau puis retry | 2 |
| Passage FAILED apres max attempts | 2 |
| Reprise ligne PROCESSING abandonnee (lease expire) | 2 |
| Rollback transaction : aucune PendingStorageDeletion | 2 |
| Objet encore reference : suppression refusee | 2 |
| Migration fichier local → bucket | 3 |
| Detection fichier orphelin | 3 |
| Reconcile `--dry-run` sans suppression | 3 |
| Backend S3 fake / MinIO en CI | 1-3 |
| Tests unitaires provider-independent (mock storage) | 1-2 |

Fichiers existants a etendre : `uploads/tests/test_cleanup.py`, `signals/tests/test_signal_detail_media.py`, `uploads/tests/test_checks.py`.

---

## 16. Verifications Railway

### Avant implementation

- [ ] Confirmer Railway Bucket disponible sur le projet
- [ ] Documenter credentials injectes et endpoint S3
- [ ] Verifier limites (pas de lifecycle — section 10)
- [ ] Plan backup externe (export periodique ou replication — non natif Railway)

### Apres lot 1

- [ ] Nouvel upload → objet present dans bucket (HeadObject)
- [ ] Preview API fonctionne
- [ ] `celery-worker` a les memes variables bucket que `api-web`

### Apres lot 2

- [ ] Agregation pipeline → objet supprime du bucket
- [ ] Cleanup upload expire → objet supprime
- [ ] Logs `storage_deletion_drained` ; pas d'echec silencieux
- [ ] `reconcile_storage --dry-run` propre sur echantillon

### Apres lot 3

- [ ] 100 % refs DB resolues vers bucket
- [ ] Fallback local desactive
- [ ] Volume `api-web` retire
- [ ] `api-web` peut scaler sans volume

### Etat actuel (pre-migration)

- [ ] Mesurer `du -sh` volume existant
- [ ] Inventaire orphelins pre-migration

---

## 17. Risques et elements non verifiables

| Element | Statut |
|---|---|
| Split volume api-web / worker | **Confirme** doc + code |
| `boto3` / `django-storages` absents aujourd'hui | **Confirme** `pyproject.toml` |
| Railway Bucket credentials et quotas projet | **A verifier** spike lot 1 |
| Lifecycle / versioning / backups bucket | **Non disponibles** Railway (doc externe) |
| CORS bucket pour upload navigateur direct | **A evaluer** — upload actuel passe par API (pas urgent) |
| Cout bucket 500 users (~42 Go realiste) | ~$0.63/mois stockage Railway ($0.015/GB-mo) — **estimation**, hors egress service si proxy API |
| Frequences usage section 3 | **Hypotheses** |
| Taille volume prod actuelle | **A verifier** shell api-web |

---

## 18. Fichiers a modifier (apercu)

### Lot 1

| Fichier | Changement |
|---|---|
| `pyproject.toml` | `django-storages`, `boto3` |
| `apps/api/houston/uploads/private_storage.py` | Backend S3 + factory |
| `apps/api/config/settings.py` | Config storage, variables |
| `apps/api/houston/uploads/checks.py` | Checks bucket prod |
| `apps/api/houston/observations/media_services.py` | Retirer fallback Path |
| `apps/api/houston/observations/api/media_views.py` | Adapter si redirect presigned (optionnel) |
| `docker-compose.yml` | MinIO ou config dev |
| `.env.example` | Variables bucket (sans secrets) |
| `docs/deploy/railway_deploy_contract.md` | Remplacer section volume par bucket |
| `docs/deploy/railway_variables.md` | Matrix credentials bucket tous services |
| `infra/docker/railway/start-api-web.sh` | Retirer dependance volume (chown media) a terme |

### Lot 2

| Fichier | Changement |
|---|---|
| `apps/api/houston/uploads/models.py` | `PendingStorageDeletion` |
| `apps/api/houston/uploads/storage_deletion.py` | **Nouveau** |
| `apps/api/houston/uploads/storage_deletion_tasks.py` | **Nouveau** |
| `apps/api/houston/uploads/services.py` | Enqueue on_commit |
| `apps/api/config/settings.py` | Beat drain, limites retry |
| `apps/api/houston/uploads/management/commands/*.py` | drain, replay, reconcile, stats |

### Lot 3

| Fichier | Changement |
|---|---|
| `apps/api/houston/uploads/management/commands/migrate_private_media_to_bucket.py` | **Nouveau** |
| `apps/api/houston/uploads/management/commands/inventory_private_media_volume.py` | **Nouveau** |
| `apps/api/houston/uploads/storage_backends.py` | Fallback lecture temporaire (si necessaire) |

### Lot 4

| Fichier | Changement |
|---|---|
| `apps/api/houston/accounts/purge.py` | **Nouveau** |
| `apps/api/houston/notifications/purge.py` | **Nouveau** |
| `apps/api/houston/action_plans/outbox_purge.py` | **Nouveau** |

### Explicitement hors scope

- Modifier `start-api-web.sh` pour lancer un worker Celery
- Queue `storage_deletion` consommable uniquement par api-web
- Dual-write permanent volume + bucket

---

## Annexe — chemins de suppression detailles (etat actuel, pre-migration)

### Cleanup uploads expires

- **Entree** : `cleanup_expired_uploads_task` (`uploads/tasks.py`)
- **Service** : `cleanup_expired_uploads` (`uploads/services.py` L78)
- **Processus** : `celery-worker`
- **DB** : `status=DELETED` dans `@transaction.atomic`
- **Fichier** : sync `upload.file.delete()` — ROOT worker `/tmp/...` Railway
- **Echec** : commit DB souvent quand meme ; pas de retry Celery (`max_retries=0`)
- **Idempotence DB** : oui ; **fichier volume** : non

### Agregation

- **Entree** : `process_observation_task` → `aggregate_candidate_into_signal` (`signals/services.py` L245)
- **Processus** : `celery-worker`
- **DB** : `delete_observation_media_permanently` dans transaction
- **Fichier** : `on_commit` → `_delete_storage_file_idempotent`
- **Echec** : OSError avale

### Resolve / cancel signal

- **Entree** : `signals/api/views.py` → `resolve_signal` / `cancel_signal`
- **Processus** : `api-web`
- **Fichier** : `on_commit` — acces volume **oui** (etat actuel)

---

*Plan mis a jour : architecture cible bucket S3 prive + PendingStorageDeletion. Aucune recommandation de worker Celery embarque dans api-web.*
