# SPORE — Scalability & production readiness

Évaluation factuelle du repo face au cadrage validé. Le socle est exploitable, mais il n’est pas encore borné, isolé ni certifiable sous panne et saturation.



Conclusion indépendante

Le principal problème n’est pas l’absence de technologies supplémentaires. C’est l’absence d’un contrat cohérent entre état durable, publication, retry, capacité et dégradation. Ajouter RabbitMQ sans corriger ces propriétés déplacerait le risque.

## Priorités structurantes

| Niveau | Écart                           | Fait observé                                                 | Décision pré-plan                                            |
| :----- | :------------------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- |
| P0     | Dispatch post-commit ambigu     | La donnée est commitée, mais l’échec delay() est relancé ; le test 201 simule artificiellement le callback après la réponse. | Arbitrer le contrat HTTP et la représentation durable de publication. |
| P0     | Retry amplification IA          | SDK × Celery × métier : aucun budget provider unique.        | Fixer un propriétaire et un plafond produit explicable.      |
| P0     | Queue unique / Redis multi-rôle | IA, opérationnel, maintenance et realtime partagent une capacité et un point de panne. | L’isolation par workload est un prérequis au scale horizontal. |
| P0     | Idempotence observation absente | Un retry réseau mobile peut créer une seconde observation et un second pipeline. | Décider identité logique et règle de conflit avant le contrat API. |
| P1     | Dashboard sur OLTP              | Agrégations Python et journaux chargés en mémoire ; pas de preuve terrain + 90 jours. | Mesurer avant index/cache/read model, sans présupposer la solution. |
| P1     | CONN_MAX_AGE=60 sous ASGI       | Le réglage actuel contredit la cible et précède tout budget de connexions. | Mesurer puis auditer transaction pooling, migrations et cursors. |

Lecture synthétique

4

écarts P0

10

axes audités

0

capacity envelope

------

Conforme à préserver : PostgreSQL comme vérité, payloads async par identifiants, S3 privé, invalidation → refetch, Beat singleton, harness analytics, feeds bornés.

Dette la plus dangereuse : les garanties partielles donnent une impression de durabilité sans publication traçable ni comportement de panne explicite.

------

## Audit par axe

Fait — Celery utilise Redis comme broker et result backend. Un worker générique consomme tous les workloads, sans routes, queues nommées ni préfetch explicite.

Risque — Une saturation IA ou une panne Redis peut affecter à la fois l’async opérationnel, Channels, le cache et les throttles.

Preuves

`apps/api/config/settings.py:312-317``docker-compose.yml:63-89``infra/railway/celery-worker/railway.toml:18``docs/deploy/railway_architecture.md:40-48`

Fait — Observation et ObservationProcessing(queued) sont atomiques en PostgreSQL, puis la publication est un on_commit → delay. Un sweep horaire redécouvre les orphelins.

Risque — La base conserve le travail requis, mais ne distingue pas requis/publié. Un échec broker peut remonter après commit et le recovery peut attendre près d’une heure.

Preuves

`apps/api/houston/observations/services.py:54-151``apps/api/houston/observations/models.py:89-129``apps/api/config/settings.py:359-363``apps/api/houston/observations/tests/test_submit_on_commit_enqueue.py:50-75`

Fait — Observation et classification analytics empilent retries SDK OpenAI, retries Celery et compteurs/états métier.

Risque — Le nombre maximal d’appels provider n’est pas explicable simplement ; coûts, latence et 429 peuvent être amplifiés.

Preuves

`apps/api/config/settings.py:280-300``apps/api/houston/ai/observation_pipeline.py:255-290``apps/api/houston/signals/tasks.py:26-52``apps/api/houston/analytics/tasks.py:19-49`

Fait — La soumission d’observation n’accepte aucune clé stable et crée systématiquement une nouvelle ligne. Les throttles couvrent surtout l’auth et le ticket chat, pas l’établissement.

Risque — Un retry mobile peut doubler observation et coût IA ; un tenant actif peut monopoliser la capacité globale.

Preuves

`apps/api/houston/observations/api/serializers.py:5-13``apps/api/houston/observations/services.py:100-113``apps/api/config/settings.py:387-399``apps/api/houston/observations/api/views.py:35-41`

Fait — Le modèle invalidation → refetch HTTP est bien établi et scoped par groupes. Il n’existe toutefois aucun événement processing observation ; le client poll toutes les secondes.

Risque — Charge HTTP amplifiée pendant les bursts et risque de fuite si une future invalidation processing réutilise naïvement le groupe établissement.

Preuves

`apps/api/houston/realtime/broadcast.py:20-110``contracts/operational-realtime-invalidation.json:1-114``apps/web/src/features/observations/components/observation-processing-tracker-provider.tsx:26-102``apps/api/houston/observations/permissions.py:8-16`

Fait — L’audio est temporaire, supprimé en finally et le SDK ne retry pas. L’appel OpenAI reste synchrone dans le chemin HTTP ASGI.

Risque — Des transcriptions lentes peuvent monopoliser les slots HTTP ; l’ampleur réelle doit être mesurée avant d’isoler un runtime.

Preuves

`apps/api/houston/uploads/api/transcription_views.py:100-130``apps/api/houston/ai/transcription.py:173-177``apps/api/config/settings.py:253-264`

Fait — Daphne/ASGI tourne avec CONN_MAX_AGE=60 par défaut. PgBouncer, DSN pooled/unpooled et DISABLE_SERVER_SIDE_CURSORS sont absents.

Risque — Multiplier API et workers multiplie les connexions sans budget. Les iterator() runtime devront être validés avant transaction pooling.

Preuves

`apps/api/config/settings.py:115-141``apps/api/config/asgi.py:28-34``apps/api/houston/uploads/services.py:118``apps/api/houston/gamification/tasks.py:38`

Fait — Le dashboard charge des signaux et journaux en mémoire depuis l’OLTP ; rankings et pages reconstruisent le contexte. Les définitions de récurrence sont explicitement divergentes.

Risque — Un dashboard Owner 90 jours peut concurrencer le terrain. Dashboard, pattern list et futures IA peuvent produire des KPI différents.

Preuves

`apps/api/houston/analytics/dashboard.py:450-637``apps/api/houston/analytics/dashboard.py:393-419``apps/api/houston/analytics/recurrence.py:1-24``apps/api/houston/analytics/permissions.py:36-56`

Fait — Le harness analytics reprend les profils 3k/100k/1M et mesure SQL/EXPLAIN ; le feed harness mesure les parcours chauds. Il n’existe pas de harness global HTTP/WS/queues/pannes.

Risque — Aucune capacity envelope reproductible ni preuve des modes dégradés. Les timings locaux ne suffisent pas à certifier Railway.

Preuves

`apps/api/houston/analytics/analytics_capacity_eval.py:48-94``apps/api/houston/core/feed_hardening_baseline.py:112-128``docs/plans/feed_hardening_pr4_comparison_2026-09-29.md:50-105``apps/api/houston/core/observability.py:12-146`

Fait — La topologie documente API publique, Postgres/Redis/workers privés, S3 privé et Beat singleton. RabbitMQ et PgBouncer n’existent pas encore.

Risque — La conformité du Railway réellement déployé, les proxies TCP, sauvegardes/restores et alertes ne sont pas prouvables depuis le repo.

Preuves

`docs/deploy/railway_architecture.md:10-18``docs/deploy/railway_architecture.md:100-127``docs/deploy/railway_deploy_contract.md:240-285``apps/api/houston/core/views.py:17-23`

## Arbitrages avant /create-plan

### Représentation durable observation

Choisir entre enrichir ObservationProcessing et une outbox locale étroite. L’outbox action plans prouve claim/lease/backoff, mais n’est pas un framework générique de publication.

### Sémantique HTTP après commit

Décider si une observation durable avec travail durable retourne toujours 201 même broker down. Le repo actuel peut relancer après commit ; le test API masque ce timing.

### Définitions BI

Le commentaire « Do not unify » sur la récurrence est incompatible avec une métrique portant le même sens métier. Soit nommer deux métriques distinctes, soit définir une canonique.

### Scope realtime processing

L’autorisation HTTP est submitter/roles ; une invalidation établissement serait trop large. Le groupe membership existant est le candidat naturel, à confirmer produit.

### Pooling

Ne pas introduire PgBouncer avant budget. Si retenu, transaction pooling impose un audit runtime des cursors et une voie migrations non poolée.

### Isolation transcription

Ne pas la rendre async durable sans décision de stockage audio. Mesurer d’abord ; isoler la capacité HTTP seulement si la contention est démontrée.

## Inconnues à mesurer ou vérifier



Ne pas transformer ces inconnues en valeurs arbitraires

Elles conditionnent les SLO, pools, quotas, TTL, replicas et éventuels read models.

État Railway live : proxies publics, replicas, volumes, variables et drift dashboard/repo.

Budget de connexions réel sous API + WebSockets + trois pools workers + Beat.

Profondeur/âge des queues, queue_wait_ms, throughput et redeliveries actuels.

p95/p99 transcription et saturation HTTP pendant un burst d’établissement.

Dashboard 15/30/90 jours + rankings sous historique target et trafic terrain concurrent.

Comportement Redis down par usage : Channels, ticket, cache et throttles.

RPM/TPM OpenAI, coût par opération et nombre effectif d’appels avec retries empilés.

État final du chantier Feed contracts & pagination ; les benchmarks définitifs en dépendent.

------

## Dépendances entre lots

| Précurseur     | Ce qu’il conditionne réellement                              |
| :------------- | :----------------------------------------------------------- |
| Feed contracts | Baseline finale Lot 0, profiling DB Lot 4, charge finale Lot 6 |
| Lot 0          | SLO, budgets connexions/provider, concurrency, seuils backlog et décisions analytics |
| Lot 1          | Isolation queues, durable dispatch, modes dégradés RabbitMQ, workers indépendants |
| Lot 2          | Duplicate submit, retry budget, fairness/noisy-neighbor avant scale et certification |
| Lot 3          | Contrat realtime processing, polling fallback, mesure/isolation transcription |
| Lot 4          | Protection OLTP, connexion/pooling, stratégie historique et métriques canoniques |
| Lot 5          | Dépend de l’instrumentation, des queues isolées, de l’idempotence et du budget DB |
| Lot 6          | Certifie les propriétés introduites par Lots 1–5 ; ne doit pas être un test unitaire renommé |

Dépendance cachée majeure : le scale horizontal n’est pas un lot isolé. Sans durable dispatch, idempotence, budget DB et contrôle provider, il amplifie les pannes et les coûts au lieu d’augmenter une capacité sûre.



Recommandation de cadrage

Conserver le monolithe et les composants standards. Challenger en revanche les mécanismes actuels de dispatch, retry, dashboard et connexion : ils ne doivent pas être préservés par défaut. Aucun besoin concret observé ne justifie microservices, Kafka, Kubernetes, warehouse ou scheduler fairness custom.

Sources : implémentation, tests, contrats et configuration du workspace Houston. Aucun code applicatif modifié ; audit fondé sur l’état de travail visible, y compris les diagnostics feed non commités signalés dans le workspace.