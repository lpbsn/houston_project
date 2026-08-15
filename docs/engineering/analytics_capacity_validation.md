# Ticket 35 — Validation capacité/performance Analytics

Date de mesure : 2026-08-15.

## Verdict

**Capacité non validée au volume cible pour les lectures Analytics globales.**

L’architecture reste utilisable au profil intermédiaire (25 établissements, 100 000
Signals, 1 000 Patterns), mais les parcours non filtrés atteignent encore plusieurs
secondes à 100 établissements / 1 million de Signals malgré une optimisation simple
et mesurée.

`token_overlap_v1` est en revanche validé techniquement jusqu’à 10 000 Patterns dans
ce benchmark isolé : p95 205 ms, pic Python 11,6 MB, un seul SELECT, croissance
linéaire attendue. Ce verdict ne couvre pas la concurrence ni la qualité sémantique,
qui sont hors scope de T35.

Les mesures structurées durables sont dans
[`analytics_capacity_results.json`](analytics_capacity_results.json). Les rapports
diagnostiques complets avec SQL et plans `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`
sont générés localement sous `.artifacts/analytics-capacity-eval/`.

## Environnement et méthode

- Docker local via OrbStack, Linux aarch64.
- Python 3.13.13, Django 5.2, PostgreSQL 17.10.
- `shared_buffers=128MB`; base cible mesurée à 927 MB.
- Dataset déterministe, seed 35, namespace local dédié.
- 95 % des Signals ont une `SignalPatternAssignment`; statuts, résolutions,
  business units/non assignés et dates sur 730 jours sont distribués de façon
  déterministe.
- Les premiers Signals assurent qu’un Pattern est observable dans les périodes
  récentes; le reste suit une distribution temporelle uniforme et une distribution
  de Patterns asymétrique.
- Aucun appel OpenAI, classifier ou duplicate guard n’est exécuté.
- Le timing p50/p95 est exécuté sans capture SQL, EXPLAIN ni `tracemalloc`.
- Query capture, mémoire et EXPLAIN sont des runs séparés à une itération.
- Les vues DRF, permissions, parsing, serializers et read paths réels sont exercés
  avec un contexte d’authentification local.

Profils :

- `smoke` : 3 établissements, 3 000 Signals, 100 Patterns.
- `intermediate` : 25 établissements, 100 000 Signals, 1 000 Patterns.
- `target` : 100 établissements, 1 000 000 Signals, 5 000 Patterns.

Les paramètres `--establishments`, `--signals` et `--patterns` permettent de faire
varier ces trois dimensions indépendamment.

## Baseline et croissance

Les p95 principaux avant optimisation :

- Dashboard 7/30/90 jours :
  - smoke : 66,5 / 72,8 / 41,9 ms;
  - intermediate : 310,0 / 348,1 / 428,9 ms;
  - target : 6 075,6 / 9 394,5 / 12 499,6 ms.
- Patterns page 1 sur 7/30/90 jours :
  - smoke : 26,6 / 29,3 / 30,7 ms;
  - intermediate : 170,9 / 184,6 / 257,5 ms;
  - target : 8 219,1 / 9 086,7 / 12 088,4 ms.
- Patterns 30 jours page 2 : 40,6 ms, 344,7 ms, puis 20 748,2 ms.
- Patterns 30 jours récurrents : 29,7 ms, 322,7 ms, puis 21 321,0 ms.
- Détail 30 jours : 23,9 ms, 143,0 ms, puis 3 910,7 ms.
- Drilldown 30 jours page 1 : 7,9 ms, 39,7 ms, puis 1 848,2 ms.
- Filter options reste stable : 35,1 ms au profil cible.

Le nombre de queries est stable avec le volume mais élevé :

- dashboard : 37 queries;
- patterns list : 19 queries;
- détail : 20 queries;
- drilldown : 7 queries;
- filter options : 7 queries.

Il n’y a donc pas de N+1 par item. La croissance vient du coût des agrégations et
scans répétés, multiplié par un fan-out de queries constant.

## Bottlenecks prouvés

### 1. Scope multi-établissements

Le scope Owner/Director construisait une branche `OR` complète par membership.
À 100 établissements, chaque sous-requête répétait 100 fois les prédicats de statut
organisation/établissement et l’établissement ciblé. Les plans montraient :

- des SQL très volumineux répliqués dans les sous-requêtes;
- des scans séquentiels sur `signals_signal` et
  `analytics_signalpatternassignment`;
- jusqu’à des centaines de milliers de lignes rejetées par filtre;
- des dizaines de milliers de blocs lus par agrégation.

### 2. Agrégations répétées

Le dashboard recalcule intégralement les KPI courant et précédent. La list et le
détail exécutent ensuite des agrégations distinctes pour compteurs, actionable,
établissements, distributions et récurrence.

Le coût SQL cumulé reste dominant après optimisation :

- dashboard 90 jours : environ 6,5 s sur le run diagnostique;
- patterns 30 jours page 2 : environ 8,6 s;
- patterns 30 jours récurrents : environ 5,1 s.

### 3. Pagination après agrégation

La page 2 de Patterns doit recalculer et trier l’agrégat complet avant d’appliquer
le curseur. Elle reste le parcours le plus lent, même si le nombre de rows renvoyées
est borné.

### 4. Récurrence à la lecture

La récurrence calcule `timezone(establishment.timezone, created_at)::date` et des
`COUNT(DISTINCT ...)` à chaque lecture. Ce coût apparaît dans dashboard, list et
détail et augmente avec la fenêtre récente.

## Optimisation conservée

Les scopes Owner/Director sont maintenant regroupés en un seul
`establishment_id IN (...)`, avec les prédicats de statuts communs. Les scopes
Manager et leur sémantique business-unit/unassigned restent inchangés.

Gains p95 au profil cible, à matrice identique :

- dashboard 30 jours : 9 394,5 → 5 139,1 ms, **-45 %**;
- dashboard 90 jours : 12 499,6 → 6 692,7 ms, **-46 %**;
- patterns 30 jours page 1 : 9 086,7 → 4 103,3 ms, **-55 %**;
- patterns 30 jours page 2 : 20 748,2 → 9 053,4 ms, **-56 %**;
- patterns récurrents : 21 321,0 → 5 317,0 ms, **-75 %**;
- recherche Patterns : 13 036,6 → 2 835,1 ms, **-78 %**;
- détail 30 jours : 3 910,7 → 1 243,5 ms, **-68 %**;
- détail 90 jours : 10 261,6 → 1 561,1 ms, **-85 %**;
- drilldown page 1 : 1 848,2 → 312,0 ms, **-83 %**.

Le query count ne change pas; le gain vient de SQL/plans plus simples.

## Expérience rejetée

Un index conventionnel `(establishment_id, created_at)` sur Signal a été essayé et
mesuré sur le même dataset. Il a amélioré plusieurs parcours 7 jours, mais les gains
30/90 jours n’étaient pas stables et détail/drilldown ont régressé. L’index et sa
migration ont donc été retirés.

Aucun cache, matérialisation, nouvelle infrastructure, index complexe, pgvector,
semantic retrieval, Architecture C ou D n’a été ajouté.

## token_overlap_v1

Résultats cible, threshold 0,25 et max 5 :

- 100 Patterns : p95 2,7 ms, pic Python 0,11 MB;
- 1 000 Patterns : p95 20,0 ms, pic Python 1,06 MB;
- 5 000 Patterns : p95 148,0 ms, pic Python 5,67 MB;
- 10 000 Patterns : p95 205,0 ms, pic Python 11,59 MB.

`patterns_scanned` correspond à la cardinalité et la mémoire croît linéairement,
ce qui confirme le coût O(N) actuel. Aucun appel au guard ou au classifier n’est
inclus dans ces chiffres.

## Reproduction

```bash
docker compose exec -T api sh -lc \
  'cd /app/apps/api && uv run python manage.py benchmark_analytics_capacity \
  --profile smoke --confirm --archive'

docker compose exec -T api sh -lc \
  'cd /app/apps/api && uv run python manage.py benchmark_analytics_capacity \
  --profile intermediate --confirm --archive'

docker compose exec -T api sh -lc \
  'cd /app/apps/api && uv run python manage.py benchmark_analytics_capacity \
  --profile target --confirm --archive'
```

Le générateur remplace uniquement les organisations du namespace T35 et exige un
PostgreSQL local avec `DEBUG=True`. `--skip-seed` rejoue les mesures sur le dataset
actuel. `--no-explain` permet un run sans plans diagnostiques.

## Risques et restes

- Benchmark mono-processus, sans concurrence ni saturation de pool.
- Résultats dépendants du cache PostgreSQL/OS et de la machine locale; aucun SLA
  absolu n’était demandé.
- Dataset synthétique : il reproduit volumes et distributions utiles, pas toutes
  les corrélations métier réelles.
- Le profil cible n’est pas acceptable pour une interaction utilisateur globale :
  la capacité Analytics reste **non validée**.
- Les prochaines pistes doivent être mesurées séparément : réduire le fan-out des
  agrégations, éviter le recomptage complet en page 2, puis réévaluer la récurrence.
  Cache et matérialisation ne sont pas justifiés par T35 seul.
