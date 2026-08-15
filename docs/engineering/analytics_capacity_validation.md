# Validation capacité/performance Analytics

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

## T36 — Réduction des lectures redondantes

T36 réutilise exactement le profil cible, le seed 35 et la matrice T35. Le dataset
de 100 établissements, 1 000 000 de Signals et 5 000 Patterns a été seedé une fois,
puis réutilisé pour tous les lots. Chaque baseline et chaque état conservé a été
mesuré trois fois. Les chiffres ci-dessous sont les médianes des p95 de run et des
`sql_total_ms` diagnostiques; le premier run de baseline, exécuté juste après le
reseed, était nettement plus froid que les deux suivants.

Lots conservés :

- un scope RBAC immuable est maintenant résolu une fois par read path et partagé
  entre les querysets default, actionable, résolution et récurrence. Les branches
  Manager restent séparées par établissement et conservent leurs contraintes
  business-unit/non assigné;
- le dashboard consolide population/actionable, assignments/classification et les
  trois lectures de durée de résolution;
- la liste calcule `total_count` avec un `COUNT(DISTINCT pattern_id)` dédié sans
  reproduire le groupement, les annotations et le tri de la page;
- le détail dérive identité, compte courant, dernière occurrence et distribution
  de statuts d’une même agrégation groupée.

Gains médians baseline T36 → état final :

- dashboard 30 jours : p95 5 697,6 → 3 590,2 ms (**-37,0 %**),
  SQL 5 435,3 → 3 435,4 ms, 37 → 13 queries;
- dashboard 90 jours : p95 7 338,3 → 4 757,8 ms (**-35,2 %**),
  SQL 6 609,1 → 4 575,1 ms, 37 → 13 queries;
- liste 30 jours page 1 : p95 3 821,5 → 3 032,0 ms (**-20,7 %**),
  SQL 3 744,7 → 2 809,8 ms, 19 → 11 queries;
- liste 30 jours page 2 : p95 8 787,2 → 8 511,7 ms (**-3,1 %**),
  SQL 8 425,8 → 7 582,0 ms, 19 → 11 queries;
- liste récurrents : p95 6 599,5 → 5 246,9 ms (**-20,5 %**),
  SQL 6 398,0 → 4 994,0 ms, 19 → 11 queries;
- recherche Patterns : p95 2 869,2 → 1 985,3 ms (**-30,8 %**);
- détail 30 jours : p95 1 552,0 → 1 260,1 ms (**-18,8 %**),
  SQL 1 313,7 → 1 061,5 ms, 20 → 13 queries;
- détail 90 jours : p95 1 809,6 → 1 419,8 ms (**-21,5 %**),
  SQL 1 632,2 → 1 357,6 ms, 20 → 13 queries.

Les gardes non ciblées restent cohérentes avec la variance locale : filter options
33,2 → 29,7 ms p95; drilldown page 1 359,9 → 358,9 ms avec un temps SQL médian
303,1 → 273,8 ms. Les p95 isolés proches ou au-dessus de +10 % n’ont pas été
rejetés automatiquement : un troisième run et les temps SQL/plans ont été utilisés
pour distinguer les outliers des régressions reproductibles.

Les plans confirment les effets qui ne ressortent pas du query count seul :

- le count de page 1 passe d’environ 1 327 à 476 ms et de 475 000 à 92 000
  blocs partagés;
- le plan dominant de page 2 reste à environ 6,6 s et 1,74 million de blocs
  partagés : la pagination keyset ne supprime pas l’agrégation et le tri globaux;
- les plans détail stables restent autour de 153–161 ms à 30 jours, avec environ
  59 600 blocs lus. Les pics p95 du premier run RBAC ne se reproduisent pas et ne
  correspondent pas à une hausse des buffers;
- la sous-expérience détail rejetée avait au contraire un plan à 1 577 ms et un
  spill de 4 696 blocs temporaires lus / 8 375 écrits.

Une sous-expérience a été rejetée : fusionner previous count et actionable current
du détail dans une agrégation conditionnelle a réduit le query count, mais le
premier run isolé a fait passer le détail 30 jours d’environ 1,37 s à 2,39 s p95 et
le SQL d’environ 1,2 s à 2,19 s. Les deux requêtes sélectives ont été restaurées.

Le verdict capacité reste **non validé** : la page 2 recalcule toujours l’agrégat et
le tri globaux (8,51 s p95 médian), et la récurrence timezone-aware reste calculée
à la lecture (5,25 s pour la liste récurrente). Dans le run final, les requêtes
portant la récurrence représentent environ 63 % du SQL dashboard 30 jours et 85 %
du SQL de la liste récurrente. Toutefois, le tri des 39 108 lignes de récurrence
ne coûte qu’environ 10–15 ms : les scans répétés du scope, des assignments et des
jointures dominent. Remplacer isolément les `COUNT(DISTINCT ...)` n’apporterait donc
pas de gain plausible et n’a pas été expérimenté. Une amélioration substantielle
supplémentaire demanderait de supprimer ces scans via une pré-agrégation ou un
cache explicitement justifié; T36 n’introduit ni index, ni migration, ni
matérialisation, ni dépendance.

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
