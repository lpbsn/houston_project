# Action plan schedule materialization

**Statut:** Décision verrouillée (Lot 4)

## Objectif

Définir comment les exécutions récurrentes sont créées à partir d'un `ActionPlanSchedule`, sans reproduire aveuglément la dette MAT-01 du legacy checklist (read-path sur chaque GET feed).

## Chemins de materialization (Lot 4)

| Chemin | Actif Lot 4 | Détail |
|--------|-------------|--------|
| Celery Beat proactif | Oui | Horizon 14 jours (`MATERIALIZATION_HORIZON_DAYS`), cron daily UTC (`HOUSTON_ACTION_PLAN_HORIZON_BEAT_*`) |
| Sync on schedule create | Oui | Occurrences **visibles** dans l'horizon (`visible_from <= now`) |
| Read-path sur GET feed legacy | **Non** | Legacy `execution-feed/` inchangé ; pas de write-on-read |
| Read-path sur `GET action-plan-execution-feed/` | **Oui (Lot 5)** | Horizon 3 jours (`READ_PATH_MATERIALIZATION_HORIZON_DAYS`), stale guard 30 min |
| `ensure_visible_action_plan_executions_materialized` | **Oui (Lot 5)** | Branché **uniquement** sur `GET /establishments/{id}/action-plan-execution-feed/` via `build_action_plan_execution_feed_page` — jamais sur legacy `execution-feed/` |
| WebSocket / notifications | **Oui (Lot 7)** | `action_plan_execution.created` (+ lifecycle events §22) ; notifications in-app created / pending_validation / canceled / reopened — pas de `reassigned` (V1) |

## Chronologie partagée vs individuelle (§9)

- **`use_shared_chronology=True`:** une exécution par `occurrence_date`, tous les assignés du schedule sur la même exécution.
- **`use_shared_chronology=False`:** une exécution par `(occurrence_date, assigné)` ; clé `schedule_source_membership` sur l'exécution.

## Idempotence

- Contraintes uniques partielles en base (migration `0003`).
- Check-then-create + retry sur `IntegrityError` en concurrence.
- Pas de resnapshot assignés/tâches sur exécution existante.

## `occurrence_date` immuable

Fixée à la création de l'exécution. Un PATCH schedule ne déplace jamais une exécution existante : cancel si hors nouvelle règle, sinon sync fenêtre (`start_at` / `end_at` / `visible_from`) uniquement.

## Réactivation des exécutions `canceled` (Lot 4)

Champ interne `cancel_origin` sur `ActionPlanExecution` :

| Valeur | Signification | Réactivable par PATCH / materialize ? |
|--------|---------------|--------------------------------------|
| `null` | jamais annulée, ou réactivée / reopen | non |
| `schedule_sync` | annulée par sync schedule (`_cancel_schedule_future_execution`) | **oui** (si occurrence encore valide, futur, assigné présent) |
| `manual` | annulée via API (`cancel`) ou résolution signal | **non** |

Seules les lignes `cancel_origin=schedule_sync` peuvent être remises en `in_progress` par PATCH schedule ou `materialize_schedule_occurrences_in_horizon`. Une annulation manuelle reste `canceled` jusqu'à un `reopen` API explicite (hors materialize).

## PATCH `use_shared_chronology`

Interdit si le schedule a déjà ≥1 exécution matérialisée (`400`).

## API

- **Récurrent:** `POST /action-plans/{id}/schedule/` (`recurrence_days` non vide requis).
- **Ponctuel:** `POST /action-plans/{id}/use/` (inchangé Lot 3).

## Rapport MAT-01 / roadmap

Le nouveau domaine absorbe une stratégie **beat + sync-on-create** explicite. La dette MAT-01 sur le legacy checklist (`execution_feed` read-path) reste ouverte jusqu'au Lot 10.
