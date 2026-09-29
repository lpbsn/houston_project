# SPORE — Scalability, async pipelines, data serving & production load readiness
## Document de cadrage de référence — V1

**Statut :** validé pour préparation du plan d’implémentation  
**Projet :** SPORE / Houston  
**Contexte :** application mobile iOS/Android via Capacitor + version desktop, backend Django/DRF/ASGI, PostgreSQL, Celery, Redis, Channels, S3, Railway  
**Date :** 28 septembre 2026  
**Audience :** solo developer / agents Cursor / revue technique  
**Nature du document :** cadrage architectural et fonctionnel. Ce document fixe les besoins, invariants, frontières et critères d’acceptation. Il ne doit pas être interprété comme un plan de modifications fichier par fichier.

---

## 1. Objet du chantier

SPORE entre dans une phase charnière : le produit est déjà en production, va accueillir de vrais utilisateurs, et doit pouvoir augmenter rapidement en nombre d’établissements, utilisateurs simultanés, données historiques et traitements IA.

Le chantier vise à rendre SPORE :

- scalable sans changer inutilement de stack ;
- prévisible sous charge ;
- résilient aux pannes partielles ;
- performant sur les parcours opérationnels ;
- capable d’accueillir davantage de workloads IA ;
- capable de servir durablement dashboards, visualisations de données et futurs usages BI ;
- sûr dans un contexte multi-tenant ;
- simple à exploiter pour un solo developer.

Le chantier n’a pas pour objectif de préserver l’architecture existante telle quelle. Toute décision actuelle peut être remise en cause lorsqu’une solution plus simple, plus sûre, plus maintenable ou plus adaptée aux besoins réels de SPORE existe.

Inversement, aucune nouvelle technologie, abstraction ou infrastructure ne doit être introduite au seul motif d’une scalabilité hypothétique.

Le principe directeur est :

> **On protège SPORE, pas le code existant. Chaque changement architectural doit résoudre un problème concret, mesurable ou structurel du produit.**

---

## 2. Contexte produit à préserver

SPORE est une application opérationnelle multi-tenant utilisée à l’échelle d’un établissement.

Les parcours critiques comprennent notamment :

- saisie et traitement d’observations ;
- génération et gestion de signaux ;
- action plans et exécutions ;
- notifications ;
- commentaires et collaboration ;
- feeds opérationnels ;
- realtime ;
- analytics et dashboards ;
- médias privés ;
- traitements IA.

Le produit va également accueillir de plus en plus d’IA. Des évolutions futures pourront inclure un assistant IA, des résumés de données, des fonctionnalités BI générées par IA ou d’autres workloads IA.

Ces futures fonctionnalités **ne font pas partie du scope fonctionnel de ce chantier**.

En revanche, l’architecture mise en place doit permettre de les ajouter sans :

- compromettre les parcours opérationnels ;
- créer une nouvelle architecture de queue par feature ;
- dupliquer les définitions de métriques ;
- donner aux LLM un accès incontrôlé aux données transactionnelles ;
- remettre en cause la séparation multi-tenant.

---

## 3. État architectural de départ

Le socle actuel est globalement adapté à SPORE et doit être conservé sauf preuve contraire :

- monolithe Django modulaire ;
- Django REST Framework ;
- ASGI / Daphne ;
- PostgreSQL comme base relationnelle principale ;
- Celery pour les traitements asynchrones ;
- Redis actuellement utilisé pour Channels, broker/result Celery, cache et throttling ;
- Django Channels pour le realtime ;
- S3 privé pour les médias ;
- React / TypeScript / Vite / TanStack Query ;
- Capacitor pour mobile ;
- Railway en production.

Le problème n’est pas une mauvaise architecture globale. Le problème est que plusieurs simplifications adaptées au lancement du produit deviennent maintenant des risques de production :

- broker Celery partagé avec le Redis realtime/cache ;
- queue Celery unique ;
- dispatch observation non durable après commit DB ;
- couches de retry superposées ;
- polling agressif du statut d’observation ;
- transcription OpenAI dans le chemin HTTP ;
- connexions persistantes Django sous ASGI ;
- absence de séparation explicite entre charge OLTP et charge analytique ;
- dashboards calculés directement à partir des tables transactionnelles ;
- exposition réseau publique résiduelle de services qui devraient rester internes ;
- absence de contrat global clair sur la dégradation et la fairness multi-tenant.

---

## 4. Principes architecturaux validés

### 4.1 PostgreSQL est la source de vérité

PostgreSQL détient :

- l’état métier ;
- les données tenant-scoped ;
- l’état durable des traitements importants ;
- les informations nécessaires à la reprise après incident ;
- les données dérivées durables nécessaires à l’analytics lorsqu’elles sont introduites.

Un composant éphémère ne doit jamais devenir nécessaire pour déterminer si une opération métier a été acceptée ou non.

### 4.2 RabbitMQ transporte le travail

RabbitMQ remplace Redis comme broker Celery.

Sa responsabilité est :

- recevoir les jobs ;
- les router ;
- les livrer aux workers ;
- permettre l’isolation des workloads.

RabbitMQ n’est pas la source de vérité métier.

La perte du broker ne doit pas rendre impossible la reconstruction des traitements requis depuis PostgreSQL.

### 4.3 Celery exécute le travail

Celery reste le moteur d’exécution async.

Il ne doit pas devenir le stockage métier des états de traitements.

Le result backend Celery doit être supprimé après vérification exhaustive qu’aucune dépendance fonctionnelle n’utilise `AsyncResult` ou un équivalent.

### 4.4 Redis devient exclusivement de l’état éphémère partagé

Redis reste pertinent pour :

- Django Channels / realtime ;
- throttling distribué ;
- cache ciblé.

Redis ne doit plus contenir :

- le broker Celery ;
- le result backend Celery ;
- une vérité métier ;
- une donnée impossible à reconstruire.

Une panne Redis ne doit jamais remettre en cause une mutation métier déjà validée dans PostgreSQL.

### 4.5 Les services internes restent privés

PostgreSQL, Redis, RabbitMQ, PgBouncer et les workers communiquent sur le réseau privé Railway.

L’API publique est la frontière internet normale de l’application.

Les TCP proxies publics permanents vers PostgreSQL ou Redis doivent être supprimés sauf besoin opérateur explicitement justifié.

### 4.6 Les messages async transportent des références, pas la donnée métier complète

Les messages RabbitMQ doivent rester petits et minimaux.

Exemple souhaité :

```json
{
  "observation_id": "..."
}
```

Ils ne doivent pas embarquer par défaut :

- texte brut d’observation ;
- prompts complets ;
- photos ;
- noms utilisateurs ;
- contexte complet d’établissement ;
- données sensibles non nécessaires au routing.

Les workers récupèrent les données nécessaires depuis PostgreSQL et S3, en respectant le scope tenant.

Le même principe s’applique au realtime : les WebSockets transportent des invalidations minimales et non des snapshots métier complets.

---

## 5. Architecture cible

```text
                    MOBILE / DESKTOP
                           │
                           ▼
                     ┌─────────┐
                     │ API Web │ × N
                     └────┬────┘
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
     PostgreSQL          Redis             S3
   source de vérité   état éphémère      médias
          │           realtime/cache
          │           /throttling
          │
   état durable du travail
          │
          ▼
      RabbitMQ
          │
      ┌───┼───────────────┐
      │   │               │
      ▼   ▼               ▼
 ai_interactive      operational       background
      │                  │        ai_background +
      │                  │         maintenance
      ▼                  ▼               ▼
 Worker AI          Worker Core      Worker Background
 Interactive

                Celery Beat × 1
```

À terme, uniquement si les mesures le justifient :

```text
PostgreSQL
    │
    ├── OLTP
    │
    └── analytical serving
          ├── SQL optimisé
          ├── cache ciblé
          ├── tables dérivées
          └── materialized views

                         ↓ plus tard si nécessaire

                 read replica / warehouse
```

---

## 6. Taxonomie durable des workloads

Les queues ne doivent pas être organisées par module Django ni par feature.

La classification durable est basée sur les caractéristiques opérationnelles du workload.

### `ai_interactive`

Travaux IA dont le résultat est attendu par un utilisateur ou influence rapidement son parcours.

Exemples actuels :

- pipeline d’analyse d’observation.

Exemples futurs possibles :

- certaines opérations d’un assistant IA.

Caractéristiques :

- faible latence recherchée ;
- capacité protégée ;
- retry budget court ;
- saturation visible mais ne bloque pas le core ;
- priorité sur les workloads IA background.

### `ai_background`

Travaux IA qui peuvent être différés sans dégrader immédiatement le terrain.

Exemples actuels :

- classification analytics.

Exemples futurs possibles :

- résumés BI ;
- synthèses périodiques ;
- enrichissements différés.

Caractéristiques :

- priorité plus basse ;
- backoff plus long acceptable ;
- traitements potentiellement volumineux ;
- aucune capacité réservée prise à `ai_interactive`.

### `operational`

Travaux nécessaires à la continuité du produit et aux effets métier asynchrones.

Exemples :

- notifications ;
- action-plan lifecycle ;
- planning/outbox ;
- recovery de traitements ;
- durable dispatch sweeps ;
- effets async nécessaires au bon fonctionnement.

Un job de recovery n’est pas une simple tâche de maintenance : il fait partie de la liveness opérationnelle.

### `maintenance`

Travaux différables qui ne doivent pas dégrader l’expérience immédiate.

Exemples :

- purge ;
- cleanup ;
- rollover ;
- opérations périodiques non urgentes.

---

## 7. Topologie workers initiale

Le déploiement initial cible trois pools de workers :

### Worker AI Interactive

Consomme uniquement `ai_interactive`.

Objectif :

- empêcher l’IA background de monopoliser les slots interactifs ;
- protéger la latence des traitements IA visibles par l’utilisateur.

Pour les longues tâches I/O-bound, un prefetch faible — typiquement `worker_prefetch_multiplier=1` — est la cible initiale, à confirmer par mesure.

### Worker Operational

Consomme `operational`.

Objectif :

- isoler notifications, dispatch, recovery et effets métier des traitements IA ou maintenance ;
- maintenir le système vivant même si l’IA est saturée.

### Worker Background

Consomme :

- `ai_background` ;
- `maintenance`.

Ces deux familles peuvent partager un pool tant que les mesures ne démontrent pas de contention problématique.

Aucune queue par tenant n’est introduite.

Aucune queue par feature n’est introduite sans besoin mesuré.

---

## 8. RabbitMQ : cible d’exploitation

La première version cible :

- un RabbitMQ dédié ;
- un seul nœud ;
- stockage persistant/volume Railway ;
- réseau privé uniquement ;
- queues classiques durables ;
- messages persistants pour les jobs qui doivent survivre au redémarrage ;
- publisher confirms sur le durable dispatch.

Les quorum queues ne sont pas introduites sur le premier déploiement.

La haute disponibilité RabbitMQ multi-nœuds n’est pas nécessaire tant que :

- PostgreSQL reste la vérité ;
- les travaux requis peuvent être redécouverts et republiés ;
- le niveau de disponibilité réel ne justifie pas la complexité supplémentaire.

---

## 9. Durable dispatch : contrat système

Le pattern actuel :

```text
DB commit
→ transaction.on_commit
→ Celery.delay()
```

n’est pas une garantie suffisante pour les travaux dont l’exécution finale est nécessaire.

Une panne broker juste après le commit peut laisser :

- une donnée durable ;
- aucun job réellement publié ;
- un client recevant éventuellement une erreur trompeuse.

Le contrat cible est :

> Toute conséquence asynchrone dont l’exécution finale est nécessaire possède une représentation durable en PostgreSQL avant que le succès métier soit considéré comme acquis.

L’implémentation exacte n’est pas imposée par le cadrage.

Cursor doit évaluer la solution la plus simple entre :

- enrichissement ciblé d’un état existant ;
- outbox locale ;
- réutilisation des patterns déjà présents dans le domaine action plans.

Il ne faut pas créer de framework générique `EventBus`, `JobPlatform` ou `UniversalOutbox` sans preuve qu’il réduit réellement la complexité.

Le système doit pouvoir distinguer conceptuellement :

```text
travail requis
→ travail publié
→ travail commencé
→ travail terminé
```

La représentation exacte de ces états peut varier selon le domaine.

---

## 10. Contrat de succès d’une observation

Dès que SPORE confirme une observation au client :

- l’observation existe durablement en PostgreSQL ;
- ses médias liés sont cohérents ;
- le travail IA requis existe durablement ;
- une panne RabbitMQ après commit ne transforme pas l’opération en “perdue” ;
- une panne OpenAI ne demande pas à l’utilisateur de resoumettre l’observation.

Le produit doit pouvoir indiquer :

- analyse en attente ;
- analyse en cours ;
- retrying si utile à l’UX ;
- analyse terminée ;
- analyse en échec terminal.

Le succès de la saisie métier et le succès de l’analyse IA sont deux choses différentes.

---

## 11. Sémantique de livraison : at-least-once, pas exactly-once

SPORE ne doit pas chercher à simuler une garantie `exactly once` distribuée.

Le modèle cible est :

```text
durable state PostgreSQL
+
delivery at-least-once
+
consommateurs idempotents
```

Une publication RabbitMQ dupliquée doit être tolérable.

Une reprise après crash peut republier un travail déjà publié si son exécution n’est pas confirmée fonctionnellement.

Les effets métier doivent donc être conçus pour :

- détecter l’état déjà appliqué ;
- éviter les créations en double ;
- respecter les contraintes DB ;
- converger vers un résultat unique.

---

## 12. `acks_late` et crash workers

Aucun réglage global `acks_late=True` ou `task_reject_on_worker_lost=True` n’est autorisé par défaut.

Ces options sont évaluées tâche par tâche lorsque :

- l’idempotence est prouvée ;
- le bénéfice de redelivery est réel ;
- les effets partiels sont correctement gérés ;
- les risques de redelivery loops sont maîtrisés.

La recovery PostgreSQL reste le filet de sécurité principal.

---

## 13. Retry ownership IA

SPORE doit avoir un seul propriétaire de la politique de retry IA.

Le modèle cible est :

```text
SDK provider
max_retries = 0
        │
        ▼
une tentative provider
        │
        ▼
classification de l’erreur
permanent / transient
        │
        ▼
policy SPORE
```

Il ne doit plus être possible de multiplier implicitement :

- retries SDK ;
- retries Celery ;
- attempts métier ;
- recovery.

L’équipe doit pouvoir répondre simplement à :

> Combien d’appels provider maximum une opération peut-elle provoquer ?

### IA interactive

Les retries doivent être :

- peu nombreux ;
- courts ;
- avec backoff et jitter ;
- plafonnés par un budget métier clair.

Le nombre exact d’essais est calibré à partir des mesures et de l’UX, pas arbitrairement.

### IA background

Les workloads différables peuvent avoir un backoff beaucoup plus long.

Pour les délais significatifs :

```text
PostgreSQL
next_retry_at
↓
dispatcher
↓
RabbitMQ lorsque l’élément devient éligible
```

La queue ne doit pas servir de base de données de planification longue durée.

---

## 14. Backpressure

Le système doit être borné.

Lorsque la capacité IA est saturée :

### Observation

SPORE :

- accepte et persiste l’observation ;
- conserve le travail à accomplir ;
- affiche un état d’attente ;
- traite lorsque la capacité redevient disponible.

Il ne rejette pas une observation métier valide simplement parce qu’OpenAI est lent.

### IA background

Les travaux peuvent rester différés sans impact sur le terrain.

### Transcription

Le contrat est différent car l’audio brut n’est pas persisté.

La transcription ne doit pas être transformée artificiellement en async durable si cela nécessite de changer silencieusement cette propriété de confidentialité.

---

## 15. Idempotence des commandes mobiles

Le premier cas prioritaire est la soumission d’observation.

Le client génère une clé stable, par exemple `client_submission_id`, pour une soumission donnée.

Le scope d’unicité doit inclure au minimum le contexte tenant et l’acteur approprié.

Comportement attendu :

### Même clé + même commande logique

Le retry retourne le résultat existant.

Il ne crée pas :

- une seconde Observation ;
- un second pipeline ;
- un double coût IA ;
- des effets métier en double.

### Même clé + contenu incohérent

Le serveur renvoie un conflit explicite.

Il ne réutilise pas silencieusement l’ancienne opération.

Le contrôle doit prendre en compte les dimensions utiles de la commande :

- texte ;
- médias ;
- origine ;
- contexte action plan lorsque présent.

Le cadrage pose le principe global, mais V1 n’introduit pas un framework universel d’idempotency.

---

## 16. Fairness multi-tenant

Un établissement très actif ne doit pas pouvoir monopoliser durablement la capacité globale.

V1 repose sur :

- throttle utilisateur lorsque pertinent ;
- throttle établissement lorsque pertinent ;
- concurrency workers bornée ;
- files globales par classe de workload ;
- observabilité de la queue age par tenant ;
- scénarios noisy-neighbor dans les tests.

Aucun scheduler custom weighted-fair / round-robin par tenant n’est construit à ce stade.

Les throttles DRF/Redis sont considérés comme :

- garde-fous UX ;
- anti-abus ;
- protection approximative.

Ils ne remplacent pas une vraie limite de capacité provider ou une défense DDoS.

---

## 17. Realtime

Le modèle realtime existant est conservé et renforcé.

Le WebSocket transporte des invalidations minimales :

```json
{
  "subject_type": "...",
  "reason": "...",
  "entity_id": "..."
}
```

Il ne devient pas la source de vérité de l’état métier.

Après invalidation :

```text
WebSocket
→ invalidation
→ client
→ HTTP fetch autorisé
```

### Propriété importante

Le realtime est **best-effort**.

Si Redis/Channels est indisponible après qu’une mutation DB a été committée :

- la mutation reste un succès ;
- l’erreur realtime est loggée ;
- le client se resynchronise ultérieurement ;
- la réponse métier ne doit pas être transformée en échec.

### Scope

Les invalidations de traitement observation doivent respecter le scope de visibilité.

Une information réservée au submitter ou à certains rôles ne doit pas être diffusée naïvement à tout le groupe établissement.

### Polling

Le polling agressif du processing observation n’est plus le chemin nominal.

Le polling devient :

- fallback quand le WebSocket est indisponible ;
- resynchronisation après reconnect ;
- mécanisme de récupération à fréquence modérée.

---

## 18. Redis : cache, realtime et throttling

Une instance Redis initiale peut continuer à servir :

- Channels ;
- throttling ;
- cache ciblé.

Les bases logiques Redis ne sont pas considérées comme une isolation de ressources.

Elles partagent :

- mémoire ;
- CPU ;
- processus ;
- politique d’eviction.

Si plus tard le cache analytique crée une pression qui affecte Channels, une séparation physique pourra être introduite :

```text
Redis realtime
Redis cache/throttle
```

Pas avant mesure.

### Règles cache

Tout cache ajouté doit :

- avoir un TTL ;
- être reconstructible ;
- ne jamais être source de vérité ;
- pouvoir être bypassé ;
- être justifié par un coût mesuré.

Le cache n’est pas ajouté “parce que Redis est disponible”.

### Redis down

Le comportement attendu est différencié :

- Channels down → HTTP continue ;
- cache down → fallback DB lorsque possible ;
- throttle down → stratégie explicite selon la criticité de l’endpoint.

Les endpoints opérationnels authentifiés doivent privilégier la continuité du métier lorsque cela reste sûr.

Les endpoints de sécurité/authentification peuvent adopter un comportement plus conservateur.

Aucun comportement fail-open/fail-closed ne doit être laissé à un accident de configuration.

---

## 19. Transcription

La propriété actuelle est maintenue :

> L’audio brut n’est pas persisté.

Il existe uniquement temporairement pendant la transcription puis est supprimé.

Conséquences :

- ne jamais mettre les fichiers audio dans RabbitMQ ;
- ne pas supposer un filesystem partagé entre services Railway ;
- ne pas introduire de stockage S3 temporaire sans décision produit/sécurité explicite ;
- ne pas exposer la clé provider au client.

Le lot concerné ne s’appelle plus “Async transcription”.

Il devient :

> **Transcription isolation & capacity**

Le besoin est d’empêcher une transcription lente de monopoliser la capacité HTTP nécessaire au reste de SPORE.

La solution est déterminée après mesure.

Une isolation runtime/service peut être envisagée si nécessaire, mais n’est pas imposée par le cadrage.

Un véritable async transcription ne sera envisagé que si le produit accepte explicitement une nouvelle sémantique de stockage temporaire du fichier audio.

---

## 20. PostgreSQL et ASGI

La cible est :

```text
CONN_MAX_AGE = 0
```

pour l’API ASGI.

Les connexions persistantes Django ne constituent pas la stratégie cible de SPORE sous ASGI.

Avant changement, la configuration et la compatibilité doivent être validées dans les tests et sous charge.

---

## 21. PgBouncer

PgBouncer est la cible de pooling lorsque le besoin de pooling devient réel, particulièrement avant une multiplication significative de :

- replicas API ;
- processus workers ;
- services backend.

Le mode cible est **transaction pooling**, sous réserve d’un audit de compatibilité.

Le repo doit être vérifié pour toute dépendance à :

- état de session PostgreSQL ;
- advisory locks session-scoped ;
- temporary tables ;
- `SET` persistant ;
- server-side cursors ;
- autres primitives incompatibles.

Les migrations ne passent pas par le pool transactionnel.

Cible :

```text
runtime API/workers
→ DATABASE_POOLED
→ PgBouncer
→ PostgreSQL

preDeploy migrations
→ DATABASE_UNPOOLED
→ PostgreSQL
```

Le pool size exact n’est pas décidé dans le cadrage.

Il résulte du connection budget du Lot 0 / Lot 4.

---

## 22. Séparation OLTP / charge analytique

SPORE possède deux catégories de lecture très différentes.

### OLTP / opérationnel

Exemples :

- feeds ;
- observations ;
- action plans ;
- notifications ;
- chat ;
- mutations terrain.

### Analytique

Exemples :

- dashboard ;
- rankings ;
- patterns ;
- comparaisons de périodes ;
- séries historiques ;
- futures métriques BI.

Principe :

> Les lectures analytiques ne doivent jamais dégrader les opérations terrain au-delà des SLO validés.

Un Owner ouvrant un dashboard lourd sur 90 jours ne doit pas rendre l’application lente pour les équipes terrain.

---

## 23. Fondation BI

Le chantier intègre une **fondation BI**, mais pas un data warehouse.

La première couche analytique reste dans PostgreSQL.

Aucune plateforme supplémentaire n’est introduite par défaut.

### 23.1 Définitions canoniques de métriques

Une métrique SPORE doit avoir une définition unique et réutilisable.

Une définition doit pouvoir préciser :

- identifiant / nom ;
- grain ;
- timezone ;
- fenêtre temporelle ;
- numérateur ;
- dénominateur ;
- exclusions ;
- scope d’autorisation ;
- fraîcheur attendue ;
- provenance ;
- éventuellement version de définition lorsqu’elle évolue.

Objectif :

```text
dashboard
résumé IA
assistant
export
comparaison BI
```

ne doivent pas produire des valeurs différentes pour un même KPI à cause de définitions dupliquées.

### 23.2 Read models dérivés

SPORE doit pouvoir évoluer progressivement vers :

- tables dérivées ;
- agrégats journaliers ;
- materialized views ;
- autres read models reconstruisibles.

Ces structures :

- ne sont pas source de vérité ;
- doivent être reconstructibles ;
- doivent préserver le tenant scope ;
- doivent préserver le grain nécessaire à l’autorisation ;
- doivent être créées seulement lorsque les mesures le justifient.

### 23.3 Fraîcheur

Toutes les données analytiques n’ont pas besoin du même niveau de fraîcheur.

Deux classes conceptuelles doivent être distinguées :

- indicateur opérationnel proche du temps réel ;
- métrique BI compatible avec une cohérence éventuelle contrôlée.

Le contrat de fraîcheur doit être explicite par métrique/read model.

### 23.4 Timezone

Une journée BI est une journée civile dans la timezone de l’établissement concerné, sauf définition contraire explicite.

Les agrégations ne doivent pas dériver silencieusement vers des buckets UTC incorrects pour l’usage métier.

### 23.5 Autorisations

Une optimisation analytique ne peut jamais élargir le scope de données observable.

Un manager ou utilisateur restreint ne doit pas accéder indirectement à une métrique agrégée construite à partir de données qu’il ne pouvait pas lire au niveau source.

---

## 24. Pas de data warehouse maintenant

Sont explicitement hors scope :

- Snowflake ;
- BigQuery ;
- ClickHouse ;
- Redshift ;
- lakehouse ;
- stack dbt complète ;
- ETL générique ;
- Kafka ;
- event streaming distribué ;
- copie complète du PostgreSQL dans un système analytique séparé.

La trajectoire est :

```text
requête PostgreSQL directe
        ↓
SQL / indexes
        ↓ si nécessaire
cache ciblé
        ↓ si nécessaire
table dérivée / pré-agrégation
        ↓ si nécessaire
materialized view / read model
        ↓ beaucoup plus tard si besoin réel
read replica / warehouse
```

---

## 25. Futurs usages IA des données

Le chantier ne construit pas l’assistant IA ni les futures fonctions BI générées par IA.

Il doit toutefois empêcher une architecture future où chaque LLM reconstruit ses propres métriques directement à partir des tables transactionnelles.

La direction souhaitée est :

```text
LLM
  │
  ▼
outils métier en lecture
  │
  ▼
métriques / read models canoniques
  │
  ▼
données vérifiables
```

Le futur assistant doit pouvoir consommer les mêmes définitions métier que les dashboards sans dupliquer la logique de calcul.

---

## 26. Data growth

La scalabilité doit être évaluée selon trois axes distincts.

### Concurrency growth

Davantage d’utilisateurs actifs simultanément.

### Multi-tenant growth

Davantage d’organisations et d’établissements.

### Historical growth

Davantage de données par établissement et davantage d’années d’historique.

Un système performant à 50 utilisateurs simultanés mais qui dégrade après trois ans de données n’est pas considéré scalable.

Le Lot 4 doit analyser les grandes tables append-heavy ou history-heavy, notamment :

- observations ;
- signals ;
- lifecycle events ;
- CandidateSignal ;
- analytics assignments/events/sightings ;
- notifications ;
- PushDelivery ;
- action-plan history ;
- chat ;
- AI usage logs.

Le partitionnement PostgreSQL n’est pas introduit par principe.

Il n’est envisagé que sur preuve issue de la croissance réelle et du profiling.

---

## 27. Observabilité

Les métriques doivent permettre de raisonner sur le système réel, pas uniquement CPU/RAM.

### HTTP

- request rate ;
- p50 / p95 / p99 par endpoint critique ;
- erreurs ;
- saturation ;
- DB time lorsque disponible.

### PostgreSQL

- connexions actives ;
- connection budget ;
- query duration ;
- lock waits ;
- rows scanned / returned ;
- requêtes lentes ;
- CPU / mémoire / I/O ;
- hot queries.

### RabbitMQ / Celery

- queue depth par classe ;
- âge du plus vieux job ;
- `queue_wait_ms` ;
- task runtime ;
- success/failure/retry ;
- redeliveries ;
- throughput ;
- worker concurrency utilisée.

### IA

- provider latency ;
- status/provider errors ;
- 429 ;
- timeout ;
- appels par opération ;
- tokens ;
- coût ;
- backlog ;
- délai bout-en-bout.

### Realtime

- connexions WebSocket ;
- reconnect rate ;
- ticket rate ;
- invalidations ;
- échecs de broadcast ;
- reconnect storms.

### Redis

- mémoire ;
- latency ;
- connexions ;
- eviction ;
- erreurs.

### Analytics

- dashboard latency ;
- query count ;
- DB time ;
- cardinalité ;
- croissance historique ;
- performance par période ;
- coût des rankings ;
- cache hit rate lorsqu’un cache existe.

---

## 28. SLO et capacity envelope

Le cadrage ne fixe pas arbitrairement de chiffres SLO définitifs.

Le Lot 0 établit la baseline.

Ensuite les SLO sont définis comme décisions produit/tech sur des dimensions mesurées :

- latence API classique ;
- latence soumission observation ;
- queue wait IA interactive ;
- observation → résultat ;
- disponibilité des parcours core ;
- dashboard p95 selon période ;
- reconnect realtime ;
- délai maximum acceptable de traitement background.

Le résultat attendu n’est pas :

> SPORE supporte X utilisateurs inscrits.

Le résultat attendu est une capacité du type :

> Sous scénario de charge Y, avec N utilisateurs simultanés, M observations/minute, K connexions WebSocket et telle profondeur historique, les SLO restent respectés et le backlog reste borné.

---

## 29. Scénarios de charge minimum

### Parcours normal

- signal feed ;
- execution feed ;
- notifications ;
- pagination ;
- WebSocket ;
- navigation courante.

### Burst établissement

Pendant un changement de shift :

- plusieurs utilisateurs actifs ;
- refresh de feeds ;
- observations ;
- photos ;
- transcription ;
- notifications.

### Noisy neighbor

- établissements A et B en activité normale ;
- établissement C en burst ;
- A/B doivent rester dans leurs SLO.

### Reconnect storm mobile

Plusieurs devices reviennent au foreground ou récupèrent le réseau :

- demande de ticket ;
- WebSocket reconnect ;
- refresh/invalidation ;
- DB/Redis doivent rester stables.

### Analytics concurrence

Charge terrain normale pendant que plusieurs Owners/Directors ouvrent :

- dashboards 30 jours ;
- dashboards 90 jours ;
- rankings ;
- patterns.

### IA saturée

Backlog IA important pendant que :

- notifications ;
- action plans ;
- feeds ;
- realtime ;
- dashboard ;
- mutations opérationnelles

continuent à fonctionner.

---

## 30. Harness analytics existant

Le repo possède déjà une infrastructure de capacity evaluation analytics.

Elle doit être réutilisée et étendue, pas remplacée par un second système.

Profils actuels identifiés :

### Smoke

- 3 établissements ;
- 3 000 signals ;
- 100 patterns.

### Intermediate

- 25 établissements ;
- 100 000 signals ;
- 1 000 patterns.

### Target existant

- 100 établissements ;
- 1 000 000 signals ;
- 5 000 patterns ;
- shortlist cardinalities jusqu’à 10 000.

Le harness mesure déjà notamment :

- timing ;
- requêtes SQL ;
- `EXPLAIN` ciblé.

Le Lot 0 / Lot 4 doit capitaliser dessus.

---

## 31. Modes dégradés attendus

| Dépendance / incident | Comportement attendu |
|---|---|
| OpenAI indisponible | Le core SPORE continue ; les traitements IA attendent, retry ou passent en état terminal explicite |
| RabbitMQ indisponible | Les commandes métier durables continuent lorsque possible ; les travaux requis restent en DB et seront republiés |
| Worker AI indisponible | Les observations restent durables et en attente |
| Worker operational indisponible | Les effets async opérationnels restent récupérables |
| Redis / Channels indisponible | HTTP continue ; realtime indisponible temporairement |
| Redis cache indisponible | Fallback DB lorsque possible |
| Redis throttle indisponible | Politique explicite selon criticité endpoint |
| Celery Beat indisponible | Aucun état métier déjà durable n’est perdu ; scheduled dispatch/recovery sont retardés |
| PgBouncer indisponible | Runtime DB indisponible ; monitoring/alerting nécessaire |
| PostgreSQL indisponible | SPORE est indisponible pour les opérations métier |
| RabbitMQ perd ses données | PostgreSQL permet de retrouver les travaux incomplets à republier |
| API replica crash | Les nouvelles requêtes passent par un autre replica ; les WebSockets reconnectent |
| AI background saturée | Pas de dégradation de `operational` ou `ai_interactive` |
| Dashboard lourd | Pas de dégradation excessive du terrain ; les SLO définissent la limite |
| Provider 429 | Backoff borné et jitter ; pas de retry storm |

---

## 32. Horizontal scaling

Le scale horizontal n’est introduit qu’après :

1. instrumentation ;
2. workload isolation ;
3. durable dispatch ;
4. retry ownership ;
5. idempotence des commandes critiques ;
6. contrôle DB ;
7. contrôle des principaux hot paths.

Une topologie initiale possible, à valider par Lot 0 :

```text
api-web ×2
worker-ai-interactive ×1
worker-operational ×1
worker-background ×1
celery-beat ×1
postgres ×1
redis ×1
rabbitmq ×1
```

Cette topologie est une hypothèse de départ, pas un objectif obligatoire.

### API scaling

Décision basée notamment sur :

- p95/p99 HTTP ;
- saturation ;
- concurrent requests ;
- WebSocket count ;
- DB budget.

### Worker AI scaling

Ne pas utiliser le CPU comme signal principal.

Les tasks IA sont largement I/O-bound.

Les signaux pertinents sont :

- queue depth ;
- oldest-job age ;
- queue wait ;
- provider latency ;
- provider rate limits ;
- throughput ;
- 429 ;
- coût.

### Worker operational scaling

Basé sur :

- queue age ;
- délai des jobs critiques ;
- backlog ;
- throughput.

### Provider capacity

Multiplier les replicas IA multiplie également la concurrence vers OpenAI.

Avant un scale IA important, il faut réévaluer :

- RPM ;
- TPM ;
- limites provider ;
- coût ;
- besoin d’un contrôle global de concurrence.

Aucun distributed rate limiter provider custom n’est construit tant qu’il n’est pas nécessaire.

---

## 33. Railway et statelessness

Railway peut distribuer le trafic entre plusieurs replicas sans sticky sessions.

SPORE ne doit donc dépendre d’aucun état métier uniquement stocké en mémoire d’un replica API.

Les WebSockets peuvent reconnecter sur un autre replica.

Le système doit rester cohérent grâce à :

- PostgreSQL ;
- Redis Channels ;
- authentification/tickets ;
- refetch HTTP.

### Celery Beat

Celery Beat reste un singleton logique.

Il ne doit pas être multiplié comme un worker horizontal standard.

---

## 34. Réseau et sécurité

La cible réseau est :

```text
Internet
   │
   ▼
API SPORE
   │
Railway private network
   ├── PostgreSQL
   ├── PgBouncer
   ├── Redis
   ├── RabbitMQ
   ├── workers
   └── services internes éventuels
```

### Invariants

- pas de Redis public permanent ;
- pas de RabbitMQ public permanent ;
- pas de PostgreSQL public permanent sauf opération ponctuelle explicitement contrôlée ;
- pas de management UI RabbitMQ publique en permanence ;
- clés provider backend-only ;
- S3 privé ;
- accès médias via API autorisée ;
- messages broker minimaux ;
- logs sans données sensibles inutiles.

---

## 35. Dépendance avec le chantier `Feed contracts & pagination`

Le chantier en cours `Feed contracts & pagination` n’est pas remis en cause.

Il doit être terminé et mergé avant :

- le benchmark final de Lot 0 ;
- le profiling DB définitif de Lot 4 ;
- les tests de charge finaux de Lot 6.

Raison :

- les hot paths feeds sont encore en évolution ;
- une baseline réalisée avant leur stabilisation serait rapidement obsolète.

Le nouveau chantier ne doit pas recréer une seconde logique de :

- pagination ;
- cache ;
- invalidation ;
- refresh des feeds.

Le realtime doit s’intégrer aux contrats feed validés, pas les contourner.

---

# 36. Lots d’implémentation validés

## Lot 0 — Measurement, SLO & capacity envelope

### Objectif

Mesurer la capacité réelle de SPORE avant optimisation.

### Doit couvrir

- HTTP ;
- PostgreSQL ;
- Redis ;
- realtime ;
- Celery actuel / futur ;
- IA ;
- feeds finalisés ;
- dashboards ;
- profondeur historique ;
- noisy neighbor ;
- reconnect storm.

### Doit réutiliser

Le harness analytics existant.

### Livrables attendus

- baseline documentée ;
- métriques observables ;
- hot paths identifiés ;
- connection budget ;
- scénarios de charge reproductibles ;
- premiers SLO proposés ;
- capacité envelope ;
- liste des inconnues restant à mesurer.

### Non-objectif

Faire des optimisations opportunistes pendant la mesure sauf correction indispensable au benchmark.

---

## Lot 1 — Queue architecture & durable dispatch

### Objectif

Découpler l’async critique de Redis et rendre le dispatch fiable.

### Cible

- RabbitMQ privé ;
- queues durables ;
- publisher confirms ;
- suppression broker Redis ;
- suppression result backend après audit ;
- routing par workload ;
- trois pools workers ;
- durable dispatch sur les chemins qui le nécessitent ;
- Beat singleton ;
- message payload minimal.

### Critères d’acceptation

- RabbitMQ indisponible au moment d’une observation n’entraîne pas la perte de la donnée ;
- un travail durable peut être redécouvert/republié ;
- AI background ne peut pas monopoliser AI interactive ;
- l’IA ne peut pas bloquer operational ;
- Redis n’est plus sur le chemin Celery.

---

## Lot 2 — Backpressure, idempotency, retry ownership & tenant fairness

### Objectif

Rendre la charge bornée et les reprises prévisibles.

### Cible

- retries provider centralisés dans la policy SPORE ;
- SDK retries désactivés ;
- classification retryable/permanent ;
- jitter/backoff ;
- budgets distincts interactive/background ;
- `next_retry_at` pour long backoff ;
- idempotence observation mobile ;
- conflict sur réutilisation incohérente d’une idempotency key ;
- admission/throttle tenant-aware ;
- absence de scheduler custom par tenant.

### Critères d’acceptation

- aucune retry amplification ;
- nombre d’appels provider par opération explicable ;
- mobile retry ne duplique pas l’observation ;
- tenant burst ne monopolise pas durablement la plateforme ;
- le backlog reste observable et borné.

---

## Lot 3 — Transcription isolation & realtime completion

### Objectif

Éliminer les pressions inutiles sur le chemin HTTP et remplacer le polling agressif du processing observation.

### Cible

- realtime invalidation pour les changements de processing ;
- scope membership/tenant correct ;
- HTTP comme source de vérité ;
- polling seulement en fallback ;
- aucune erreur realtime ne transforme une mutation DB réussie en échec ;
- mesure réelle du coût transcription ;
- isolation de capacité si nécessaire ;
- audio toujours non persisté.

### Non-objectif

Rendre la transcription async durable en stockant implicitement l’audio.

---

## Lot 4 — Data scalability & analytical serving

### 4A — OLTP scalability

- `CONN_MAX_AGE=0` sous ASGI ;
- connection budget ;
- PgBouncer si justifié ;
- runtime pooled / migrations unpooled ;
- hot queries ;
- indexes ciblés ;
- lock contention ;
- feeds ;
- observation processing status ;
- notifications ;
- action plans ;
- chat.

### 4B — Analytical scalability

- dashboard 3/7/15/30/90 ;
- rankings ;
- patterns ;
- historical growth ;
- query count ;
- rows scanned ;
- Python-side aggregation ;
- cache ciblé si justifié ;
- materialization/read models si justifié ;
- protection OLTP vs analytical reads.

### 4C — BI foundation

- métriques canoniques ;
- grain ;
- timezone ;
- freshness ;
- permissions ;
- read models reconstruisibles ;
- réutilisation future par IA ;
- aucune divergence dashboard/BI/IA.

### Critères d’acceptation

- analytique ne dégrade pas excessivement le terrain ;
- aucune optimisation ne contourne les permissions ;
- aucun warehouse ajouté sans nécessité ;
- stratégie data growth documentée.

---

## Lot 5 — Controlled horizontal scaling

### Objectif

Permettre l’augmentation indépendante des capacités.

### Cible

- API stateless horizontalement ;
- workers indépendamment scalables ;
- WebSocket reconnect entre replicas ;
- DB connection budget sous replicas ;
- provider concurrency maîtrisée ;
- pas d’autoscaling aveugle au CPU.

### Critères d’acceptation

- ajout d’un replica API sans changement métier ;
- ajout d’un worker d’une classe sans augmenter les autres ;
- reconnect WS cohérent ;
- pas d’explosion de connexions Postgres ;
- pas d’explosion incontrôlée des appels provider.

---

## Lot 6 — Production resilience certification

### Objectif

Prouver le comportement sous panne et saturation.

### Scénarios obligatoires

- RabbitMQ down pendant soumission observation ;
- worker kill pendant provider call ;
- OpenAI 429 ;
- OpenAI timeout ;
- OpenAI 5xx ;
- output IA invalide ;
- noisy tenant ;
- AI queue saturation ;
- worker operational saturation ;
- Redis/Channels unavailable ;
- reconnect storm ;
- API deploy/restart ;
- duplicate observation submit ;
- dashboard lourd + trafic terrain ;
- profondeur historique importante ;
- perte/restart RabbitMQ ;
- PgBouncer restart ;
- Beat interruption ;
- recovery après panne.

### IA de test

Utiliser principalement un provider fake/simulé capable de générer :

- latence ;
- 429 ;
- timeout ;
- 500 ;
- invalid output.

Ne pas déclencher des milliers d’appels OpenAI réels.

Un petit nombre de tests d’intégration provider réels suffit.

---

## 37. Garde-fous Cursor

Les agents Cursor doivent être autorisés à remettre en cause le code existant.

Ils ne doivent pas être autorisés à inventer une architecture future sans justification.

### Interdit sans preuve mesurée ou décision explicite

- microservices ;
- Kafka ;
- Kubernetes ;
- Temporal ;
- EventBus générique ;
- Universal Job Platform ;
- queue par tenant ;
- queue par module Django ;
- scheduler fairness custom ;
- distributed semaphore provider custom ;
- data warehouse ;
- ClickHouse ;
- BigQuery ;
- dbt stack complète ;
- partitionnement PostgreSQL par défaut ;
- PgBouncer sans connection budget ;
- cache global “pour accélérer” ;
- autoscaling basé seulement sur CPU ;
- audio durablement stocké ;
- payload métier sensible dans RabbitMQ ;
- result backend Celery réintroduit sans usage fonctionnel ;
- `acks_late` global ;
- `task_reject_on_worker_lost` global.

### Exigence

Toute nouvelle abstraction doit démontrer qu’elle :

- supprime une duplication réelle ;
- réduit la complexité totale ;
- possède plusieurs usages concrets actuels ;
- n’anticipe pas uniquement un futur hypothétique.

---

## 38. Principes de maintenabilité

SPORE est développé par un solo developer.

L’architecture doit optimiser :

- compréhension ;
- observabilité ;
- débogage ;
- reprise manuelle ;
- nombre limité de services ;
- conventions explicites ;
- outils standards ;
- faible coût cognitif.

Une architecture légèrement moins théorique mais beaucoup plus exploitable seul est préférable à une plateforme distribuée sophistiquée.

Les composants ajoutés doivent avoir une responsabilité claire :

```text
PostgreSQL → vérité
RabbitMQ   → transport async
Celery     → exécution
Redis      → état éphémère partagé
S3         → médias privés
```

---

## 39. Migration et compatibilité

Le projet est en production mais ne possède pas encore de base importante d’utilisateurs réels.

Le plan d’implémentation doit donc privilégier :

- simplicité ;
- corrections franches ;
- suppression du legacy ;
- migrations compréhensibles.

Il ne doit pas inventer :

- des semaines de dual-write ;
- des compatibilités legacy inutiles ;
- des migrations “zéro downtime” sophistiquées

si le risque réel ne les justifie pas.

Cela ne dispense pas de :

- préserver les données existantes ;
- valider les migrations ;
- disposer d’un rollback/recovery pertinent pour les changements d’infrastructure.

---

## 40. Décisions volontairement reportées aux mesures

Les points suivants ne sont pas des trous de cadrage.

Ils dépendent volontairement de Lot 0 / Lot 4 :

- valeurs numériques finales des SLO ;
- concurrency exacte de chaque worker ;
- nombre de replicas ;
- pool size PgBouncer ;
- thresholds de queue/backlog ;
- quotas utilisateur/établissement ;
- TTL des caches analytiques ;
- widgets dashboard à matérialiser ;
- choix table dérivée vs materialized view ;
- nécessité réelle d’un runtime transcription isolé ;
- séparation future Redis realtime / Redis cache ;
- besoin futur de read replica ;
- besoin futur de warehouse ;
- contrôle provider distribué éventuel.

Aucun agent ne doit inventer ces valeurs sans mesure ou décision explicite.

---

## 41. Definition of Done globale

Le chantier est considéré terminé lorsque :

1. Les parcours métier critiques ne dépendent plus de la disponibilité immédiate du broker après commit.
2. RabbitMQ transporte les workloads Celery et Redis n’est plus broker/result backend.
3. Les workloads `ai_interactive`, `operational` et background disposent d’une isolation réelle.
4. Les retries IA ont un propriétaire unique et un budget explicable.
5. Les retries mobiles ne créent pas de doublons métier sur les commandes ciblées.
6. Le realtime est best-effort et n’altère jamais la réussite d’une mutation DB.
7. Le polling processing observation n’est plus le mécanisme nominal.
8. La transcription ne peut pas faire dériver silencieusement la politique de conservation audio.
9. PostgreSQL est utilisé correctement sous ASGI.
10. La stratégie de pooling est mesurée et compatible.
11. Les principaux hot paths OLTP sont profilés.
12. Les dashboards sont testés sous profondeur historique et concurrence.
13. Les définitions de métriques BI critiques peuvent être centralisées et réutilisées.
14. Les optimisations analytiques conservent les permissions tenant.
15. Les services internes Railway ne sont pas exposés publiquement sans justification.
16. Les scénarios noisy-neighbor et panne provider sont validés.
17. Le système possède une capacity envelope documentée.
18. Les modes dégradés sont testés et observables.
19. Le scaling horizontal n’explose ni les connexions DB ni la concurrence provider.
20. Aucun composant ou abstraction non nécessaire n’a été introduit.

---

## 42. Ordre de travail recommandé avec Cursor

Ce document est la référence fonctionnelle et architecturale.

Le workflow attendu est :

### Étape 1 — Audit Cursor

Demander une revue factuelle du repo par rapport à ce cadrage :

- contradictions ;
- écarts ;
- points déjà conformes ;
- legacy ;
- dépendances cachées ;
- risques non couverts.

Aucun code.

### Étape 2 — Revue humaine de l’audit

Arbitrer seulement les nouvelles questions réellement découvertes.

Ne pas rouvrir les décisions déjà validées sans preuve nouvelle.

### Étape 3 — `/create-plan`

Cursor produit le plan d’implémentation à partir :

- de ce cadrage ;
- de l’audit ;
- de l’état réel du repo.

Le plan doit respecter les lots et leurs dépendances, mais reste libre sur les détails techniques tant qu’il respecte les invariants.

### Étape 4 — `/implement-change`

Implémenter lot par lot.

Chaque lot doit terminer avec :

- tests ;
- mesures pertinentes ;
- documentation mise à jour ;
- nettoyage du legacy remplacé ;
- absence de mécanismes concurrents inutiles.

### Étape 5 — Revue finale d’hygiène

À la fin du chantier :

- dead code ;
- anciennes variables ;
- anciennes queues ;
- config Redis Celery ;
- result backend ;
- tests obsolètes ;
- docs d’architecture ;
- Railway variables ;
- Docker/local parity ;
- commentaires devenus faux.

---

## 43. Relation avec les autres chantiers SPORE

### Feed contracts & pagination

À terminer avant les benchmarks définitifs.

Le présent chantier ne doit pas modifier leur contrat sans besoin explicite.

### UI mobile / desktop

Hors scope.

Les changements backend/realtime doivent préserver une expérience cohérente sur les deux surfaces.

### Assistant IA futur

Hors scope fonctionnel.

L’architecture de workloads et la fondation BI doivent simplement permettre son ajout futur sans refonte du cœur.

### Résumés BI / IA futurs

Hors scope fonctionnel.

Ils devront s’appuyer sur les mêmes métriques canoniques que les dashboards lorsque ces métriques existent.

---

## 44. Décision architecturale finale

La direction validée de SPORE est :

> **PostgreSQL détient la vérité et l’état durable du travail. RabbitMQ transporte les traitements. Celery les exécute. Redis coordonne le temps réel, les throttles et les caches éphémères. S3 détient les médias privés. Les workloads sont isolés selon leur criticité et leur latence, pas selon les modules du code. Les lectures analytiques peuvent évoluer vers des read models canoniques sans dégrader le cœur opérationnel.**

La scalabilité recherchée n’est pas seulement la capacité à absorber davantage de trafic.

Elle doit garantir qu’à mesure que SPORE grandit :

- un tenant ne monopolise pas les ressources ;
- une panne IA ne casse pas le produit ;
- une panne broker ne fait pas apparaître une donnée acceptée comme perdue ;
- une saturation analytics ne bloque pas le terrain ;
- les retries ne multiplient pas les effets ;
- les dashboards et futures IA parlent le même langage métier ;
- les services internes restent privés ;
- les composants peuvent être scalés indépendamment ;
- l’architecture reste exploitable par un solo developer.

C’est cette propriété — **un système borné, prévisible, récupérable et compréhensible** — qui constitue la cible du chantier.
