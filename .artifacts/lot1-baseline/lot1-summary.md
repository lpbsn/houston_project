# Lot 1 baseline — synthèse chiffrée

Date: 2026-07-15 | Environnement local: Docker Compose (OrbStack), marqueurs PR identiques CI

## Backend pytest (suite PR)

| Mesure | Valeur |
|--------|--------|
| Tests passés | **1614** |
| Tests désélectionnés (slow/smoke) | **50** |
| Durée pytest (rapport) | **360.65 s** (~6m01) |
| Durée wall-clock mesurée | **364 s** |
| CI GitHub Actions (step pytest, run 29397589248) | **639 s** (~10m39) |

**Écart local vs CI** : CI ~1.77× plus lent (DJANGO_DEBUG=0, runner ubuntu-latest natif uv, services containers — facteurs non isolés).

## Domaines ciblés

| Domaine | Tests | Durée pytest | Wall-clock |
|---------|-------|--------------|------------|
| establishments | 376 | 87.80 s | 90 s |
| action_plans | 332 | 96.65 s | 98 s |
| signals | 205 (+35 deselected) | 59.28 s | 62 s |
| notifications | 210 | 72.91 s | 74 s |

## imported_catalog (establishments)

| Sous-ensemble | Tests | Durée | Observation |
|---------------|-------|-------|-------------|
| 8 fichiers avec fixture `imported_catalog` | 65 | **16.02 s** | Setup max **2.96 s** (1er import catalogue) |
| Reste establishments (8 fichiers ignorés) | 311 | **64.08 s** | |
| Moyenne par test (approx.) | — | ~0.25 s vs ~0.21 s | Écart faible ; coût marginal **non dominant** vs setup DB général |

Références fixture: **35** occurrences du nom `imported_catalog` dans le code establishments (param + pytestmark).

## v3 golden isolé

| Mesure | Valeur |
|--------|--------|
| Tests | 9 |
| Durée totale | **4.01 s** |
| Durée call max | **0.12 s** (G1) |
| Setup max | **3.04 s** (premier test, coût DB partagé) |

**Constat** : v3 golden **n'est pas lent** en runtime PR ; gain CI Lot 2 serait marginal (~4 s max).

## Top 10 tests backend les plus lents (setup+call+teardown)

1. 3.39s setup — `test_csrf_endpoint_sets_csrf_cookie` (accounts)
2. 1.36s call — `test_send_push_for_notification_task_registered_by_celery_autodiscovery`
3. 1.02s call — `test_ws_smoke_supports_multiple_authenticated_connections` (chat)
4. 1.02s call — `test_ws_auth_timeout` (chat)
5. 1.01s call — `test_concurrent_mixed_submit_is_idempotent` (action_plans)
6. 0.95s call — `test_reply_notifies_root_mention_on_subsequent_reply` (notifications)
7. 0.83s teardown — `test_private_media_root_configured_check_skipped_in_debug`
8. 0.83s call — `test_ws_message_send_does_not_leak_across_conversations`
9. 0.80s call — `test_individual_chronology_one_execution_per_occurrence_per_assignee`
10. 0.78s call — `test_chat_conversations_list_query_count_grows_with_list_size`

Liste complète top 50: `.artifacts/lot1-baseline/pytest-pr-suite-d50-20260715T082447Z.txt`

## Vitest (local)

| Mesure | Valeur |
|--------|--------|
| Fichiers | 164 |
| Tests | 1060 |
| Somme durées fichiers | **32.9 s** |
| CI step « Run frontend tests » | **61 s** |
| Fichier le plus lent | `use-chat-websocket.test.ts` — **11.3 s** |
| Test le plus lent | reconnect auth timeout — **5.1 s** (fake timers) |

Détail: `.artifacts/lot1-baseline/vitest-summary.txt`

## Inventaires statiques

| Inventaire | Résultat |
|------------|----------|
| Imports croisés `test_*.py` | **19** lignes, **17** fichiers importeurs |
| EventEnvelope runtime | **0** import prod ; **3** tests |
| Golden v3↔v4 | **0** mapping 1:1 ; **1** chevauchement partiel (stock bar) |
| RBAC action_plans overlap | **9** règles testées dans **2–3** couches (voir matrix TSV) |
