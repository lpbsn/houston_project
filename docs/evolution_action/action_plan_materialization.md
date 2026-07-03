# Action plan schedule materialization

**Statut:** Décision verrouillée (Lot 4)

## Objectif

Définir comment les exécutions récurrentes sont créées à partir d'un `ActionPlanSchedule`, sans reproduire aveuglément la dette MAT-01 du legacy checklist (read-path sur chaque GET feed).

## Chemins de materialization (Lot 4)

| Chemin | Actif Lot 4 | Détail |
|--------|-------------|--------|
| Celery Beat proactif | Oui | Horizon 14 jours (`MATERIALIZATION_HORIZON_DAYS`), cron daily UTC (`HOUSTON_ACTION_PLAN_HORIZON_BEAT_*`) |
| Sync on schedule create | Oui | Occurrences **visibles** dans l'horizon (`visible_from <= now`) |
| Read-path sur GET feed | **Non** | Legacy `execution_feed.py` inchangé ; pas de write-on-read |
| `ensure_visible_action_plan_executions_materialized` | Implémenté, **non branché** | Branchement réservé au feed unifié Lot 5 |
| WebSocket / notifications | **Non** | Lot 7 (`action_plan_execution.created`) |

## Chronologie partagée vs individuelle (§9)

- **`use_shared_chronology=True`:** une exécution par `occurrence_date`, tous les assignés du schedule sur la même exécution.
- **`use_shared_chronology=False`:** une exécution par `(occurrence_date, assigné)` ; clé `schedule_source_membership` sur l'exécution.

## Idempotence

- Contraintes uniques partielles en base (migration `0003`).
- Check-then-create + retry sur `IntegrityError` en concurrence.
- Pas de resnapshot assignés/tâches sur exécution existante.

## `occurrence_date` immuable

Fixée à la création de l'exécution. Un PATCH schedule ne déplace jamais une exécution existante : cancel si hors nouvelle règle, sinon sync fenêtre (`start_at` / `end_at` / `visible_from`) uniquement.

## PATCH `use_shared_chronology`

Interdit si le schedule a déjà ≥1 exécution matérialisée (`400`).

## API

- **Récurrent:** `POST /action-plans/{id}/schedule/` (`recurrence_days` non vide requis).
- **Ponctuel:** `POST /action-plans/{id}/use/` (inchangé Lot 3).

## Rapport MAT-01 / roadmap

Le nouveau domaine absorbe une stratégie **beat + sync-on-create** explicite. La dette MAT-01 sur le legacy checklist (`execution_feed` read-path) reste ouverte jusqu'au Lot 10.
