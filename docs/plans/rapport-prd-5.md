## Changed

- Harness PR5D étendu dans [feed_hardening_baseline.py](../../apps/api/houston/core/feed_hardening_baseline.py) : attribution SQL, plans/buffers, scénarios isolés, callbacks et effets persistés.
- Tests read/read et Beat/read ajoutés.
- Rapport publié : [diagnostic PR5D](feed_hardening_pr5d_execution_diagnostic_2026-09-29.md).

Diagnostic représentatif :

- Historique : 94 requêtes, 80,7 ms SQL.
- No-op Cross 1/5/20 : 17/33/89 requêtes, 7,0/15,1/46,8 ms SQL.
- Matérialisation : 56 requêtes, 28,8 ms SQL.
- Disponibilité : 23 requêtes, 18,5 ms SQL.
- Promotion : 32 requêtes, 19,4 ms SQL.
- Principal plan feed : 36,771 ms planning, 0,723 ms executor, 303 buffers hit.

Gate :

- Matérialisation : NO-GO.
- Lifecycle : NO-GO.

Les gains sûrs sont faibles face aux écritures, effets métier et risques de concurrence. Aucune optimisation de `materialization.py` ou `lifecycle_promotion.py` n’a donc été appliquée.

## Validated

- 70 tests ciblés : réussis.
- Suite backend : 3304 réussis, 55 exclus.
- Django check et migrations check : réussis.
- Ruff, diagnostics IDE et documentation : réussis.
- Concurrence vérifiée sans double occurrence, promotion, événement, notification, invalidation ou attribution GAM-04.

## Risks / not verified

Les timings sont locaux et sensibles aux buffers ; la forme stable des 94 requêtes reste le signal principal. La livraison asynchrone externe n’a volontairement pas été exercée, seulement les callbacks et résultats persistés observables.