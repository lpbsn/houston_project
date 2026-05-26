# 1. Décision globale

Stack retenue :

```txt
Backend : Python + Django + Django REST Framework
Frontend : Django Templates + HTMX + TypeScript ciblé via Vite
Architecture : event-driven modular monolith
IA : pipeline async contrôlé par le backend
Realtime : WebSockets via Django Channels + refetch partiel HTMX
Jobs async : Celery + Redis
DB : PostgreSQL
PWA : manifest + service worker minimal
```

Pourquoi ce choix : ton projet sera développé très fortement par IA — Claude Code / Codex — donc il faut privilégier une stack **documentée, conventionnelle, populaire, stricte et facile à contrôler par tests**.

FloorPower n’est pas une app CRUD classique : ton product overview décrit un système **AI-augmented, event-driven, realtime, signal-oriented**, où le backend garde l’autorité métier et où les événements pilotent le runtime.

------

# 2. Backend retenu

## Stack backend

```txt
Python 3.13
Django 5.2 LTS
Django REST Framework
PostgreSQL
Celery
Redis
Django Channels
Pydantic
OpenAI / Claude API via adapter interne
S3-compatible object storage
Docker Compose local
```

## Rôle de chaque brique

| Besoin FloorPower                  | Choix                              |
| ---------------------------------- | ---------------------------------- |
| Backend principal                  | Django                             |
| API REST                           | Django REST Framework              |
| Auth / users / permissions de base | Django auth                        |
| Base de données                    | PostgreSQL                         |
| Jobs async                         | Celery                             |
| Broker queue/cache                 | Redis                              |
| WebSockets                         | Django Channels                    |
| Validation IA                      | Pydantic                           |
| IA structurée                      | OpenAI / Claude structured outputs |
| Upload photos/audio                | S3-compatible storage              |
| Dev local                          | Docker Compose                     |

Django est pertinent ici parce qu’il fournit déjà users, groupes, permissions et sessions, ce qui réduit les zones où l’IA pourrait réinventer un système fragile. ([Django Project](https://docs.djangoproject.com/en/6.0/topics/auth/?utm_source=chatgpt.com)) DRF est retenu parce que c’est le toolkit standard pour construire des Web APIs avec Django. ([django-rest-framework.org](https://www.django-rest-framework.org/?utm_source=chatgpt.com))

------

# 3. Pourquoi Django plutôt que FastAPI

FastAPI est très bon, mais plus libre.

Pour un projet développé à 100% par IA, **trop de liberté = plus de risque d’architecture incohérente**.

Django impose davantage :

```txt
apps
models
migrations
admin
settings
auth
permissions
management commands
tests
```

Donc le choix retenu est :

```txt
Django + DRF > FastAPI
```

pour FloorPower, car tu veux limiter les hallucinations et maximiser les patterns connus.

------

# 4. Architecture backend

Structure recommandée :

```txt
apps/api/
├── config/
├── houston/
│   ├── core/
│   ├── accounts/
│   ├── organizations/
│   ├── establishments/
│   ├── observations/
│   ├── signals/
│   ├── actions/
│   ├── checklists/
│   ├── comments/
│   ├── notifications/
│   ├── realtime/
│   ├── ai/
│   ├── events/
│   └── uploads/
```

Chaque app Django doit représenter un domaine métier clair.

À éviter :

```txt
utils/
helpers/
common/
services fourre-tout
```

À privilégier :

```txt
observations/services.py
signals/services.py
actions/services.py
ai_pipeline/services.py
domain_events/services.py
```

------

# 5. Architecture event-based retenue

FloorPower doit être **event-based / event-driven**, mais pas en microservices au MVP.

Architecture retenue :

```txt
Event-driven modular monolith
+
Transactional Outbox
+
Celery consumers
```

Flux standard :

```txt
User Action
    ↓
Django / DRF API
    ↓
Business Service
    ↓
DB Transaction
    ├── State mutation
    └── DomainEvent inserted
    ↓
Outbox Dispatcher
    ↓
Celery Workers
    ├── AI Pipeline
    ├── Notifications
    ├── Realtime Broadcast
    ├── Media Cleanup
    └── Audit / Analytics
```

Ton overview prévoit déjà que les événements coordonnent feeds, notifications, websockets, escalades, traitements IA et workers async.

## À faire

```txt
Domain Events
Transactional Outbox
Async Consumers
Idempotent workers
Retry
Dead-letter / failed state
```

## À ne pas faire au MVP

```txt
Kafka
RabbitMQ obligatoire
EventStoreDB
Event sourcing complet
CQRS complet
Microservices
```

------

# 6. Domain Events

Table recommandée :

```txt
domain_events
├── id: uuid
├── event_type
├── aggregate_type
├── aggregate_id
├── establishment_id
├── actor_id
├── payload: jsonb
├── status
├── occurred_at
├── available_at
├── processed_at
├── attempts
├── last_error
└── created_at
```

Exemples d’events :

```txt
ObservationCreated
ObservationQueuedForAI
AIProcessingStarted
SemanticAnalysisCompleted
SignalCreated
SignalAggregated
ObservationLinkedToSignal
ProcessingCompleted
ProcessingFailed
ActionCreated
ActionAssigned
ActionAccepted
ActionPendingValidation
ActionValidated
SignalResolved
NotificationRequested
RealtimeBroadcastRequested
```

Ton product overview liste déjà un pipeline d’events IA : `ObservationCreated`, `ObservationQueued`, `AIProcessingStarted`, `SemanticAnalysisCompleted`, `SignalCreated`, `SignalAggregated`, `ProcessingCompleted`.

------

# 7. Jobs async

Stack retenue :

```txt
Celery + Redis
```

Celery est adapté car c’est une task queue distribuée orientée traitement temps réel et scheduling. ([docs.celeryq.dev](https://docs.celeryq.dev/?utm_source=chatgpt.com))

Jobs nécessaires :

```txt
ProcessObservationJob
AnalyzeObservationJob
ApplyAIResultJob
DispatchNotificationJob
BroadcastRealtimeEventJob
CleanupAudioJob
CleanupMediaJob
CheckEscalationsJob
ArchiveResolvedSignalsJob
```

Règles :

```txt
Une Observation est persistée immédiatement.
L’IA travaille après.
Les erreurs IA ne suppriment jamais l’Observation.
Les jobs doivent être idempotents.
Les retries doivent être contrôlés.
```

------

# 8. Realtime backend

Stack retenue :

```txt
Django Channels
```

Django Channels étend Django au-delà du HTTP pour gérer WebSockets et autres protocoles ASGI. ([channels.readthedocs.io](https://channels.readthedocs.io/?utm_source=chatgpt.com))

Channels à prévoir :

```txt
SignalFeedConsumer
ExecutionFeedConsumer
NotificationConsumer
PresenceConsumer
```

Règle critique :

```txt
Realtime never bypasses backend runtime rules.
```

Ton overview dit explicitement que le realtime repose sur des business events backend, que les broadcasts appliquent establishment filtering, subscription filtering, permission validation et runtime visibility.

------

# 9. IA backend

Stack IA retenue :

```txt
Pydantic schemas
+
OpenAI / Claude structured outputs
+
Backend business validation
+
Human validation when needed
```

Pydantic sert à définir et valider les données en Python avec des type hints. ([Pydantic](https://pydantic.dev/docs/validation/latest/get-started/?utm_source=chatgpt.com)) OpenAI Structured Outputs permet de faire respecter un JSON Schema à la sortie du modèle. ([OpenAI Developers](https://developers.openai.com/api/docs/guides/structured-outputs?utm_source=chatgpt.com))

Flux IA Observation :

```txt
ObservationCreated
    ↓
ObservationProcessing(status=queued)
    ↓
Celery AI job
    ↓
RuntimeContextBuilder
    ↓
PromptBuilder
    ↓
LLM structured output
    ↓
Pydantic validation
    ↓
Backend business validation
    ↓
SignalCreated / SignalAggregated
    ↓
RealtimeBroadcastRequested
```

Règles IA :

```txt
L’IA ne persiste rien directement.
L’IA ne décide pas des permissions.
L’IA ne décide pas de la visibilité.
L’IA ne modifie pas l’Observation.
L’IA propose, le backend valide.
```

C’est aligné avec ton overview : l’IA agit comme moteur d’interprétation/structuration/suggestion, mais le backend reste l’autorité runtime unique.

------

# 10. Base de données

DB retenue :

```txt
PostgreSQL
```

Usages :

```txt
données métier canonique
domain_events
payloads JSONB
audit
jobs metadata
runtime context
```

PostgreSQL supporte `jsonb`, utile pour payloads d’events, metadata et snapshots IA. ([PostgreSQL](https://www.postgresql.org/docs/current/datatype-json.html?utm_source=chatgpt.com))

Extensions recommandées :

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

Règle :

```txt
JSONB pour payloads/events/metadata.
Tables relationnelles pour le métier.
```

------

# 11. Auth backend

Choix retenu :

```txt
Opaque access token
+
Refresh token hashé
+
Session table
```

Pas de JWT stateless long-lived.

Pourquoi :

```txt
révocation
multi-établissement
changement de rôle
permissions runtime
websocket sécurisé
audit
```

DRF permet de brancher authentication, permissions et throttling sur les credentials entrants. ([django-rest-framework.org](https://www.django-rest-framework.org/api-guide/authentication/?utm_source=chatgpt.com))

------

# 12. Frontend retenu

## Stack frontend

```txt
Django Templates
HTMX
TypeScript ciblé via Vite
Alpine.js léger ou Stimulus si nécessaire
Tailwind CSS ou CSS simple structuré
PWA manifest
Service worker minimal
TypeScript
Vite
React Router
TanStack Query
React Hook Form
Zod
Tailwind CSS
shadcn/ui ou Radix UI
vite-plugin-pwa
OpenAPI generated client
WebSocket client
```

React recommande de démarrer une app avec un build tool comme Vite, Parcel ou Rsbuild. ([React](https://react.dev/learn/build-a-react-app-from-scratch?utm_source=chatgpt.com)) Vite est adapté car il fournit dev server et build de production optimisé. ([vitejs](https://vite.dev/guide/?utm_source=chatgpt.com))

------

# 13. Pourquoi éviter React au MVP

React est refusé pour le MVP car il ajoute trop tôt :

```txt
client-side routing
state management
form state duplication
API client generation dependency
cache invalidation complexity
auth/session complexity
frontend/backend validation duplication
larger Codex error surface
```

Houston n’a pas besoin d’une SPA pour valider son MVP terrain.

Le cœur du produit est :

```
Observation → Signal → Action → Execution → Validation → Feed update
```

Donc la priorité est :

```
backend métier robuste
permissions fiables
feeds corrects
workflow terrain rapide
UI mobile simple
```

Choix retenu :

```
Django Templates + HTMX > React SPA
```

React pourra être réévalué plus tard si :

- l’interface devient très interactive ;
- le produit nécessite une vraie app offline-first ;
- une app web séparée devient nécessaire ;
- une équipe frontend dédiée apparaît.

------

# 14. Server state frontend

Le server state reste côté backend.

Le frontend ne maintient pas de copie métier complexe.

Stratégie MVP :

```
Django views/selectors prepare authorized data
Django templates render pages/fragments
HTMX requests partial updates
WebSocket events trigger partial refetch
```

À éviter :

```
client-side store métier
Redux
TanStack Query obligatoire
duplication des permissions frontend
reconstruction locale des feeds
```

Règle :

```
Backend = source de vérité.
Templates = rendu initial.
HTMX = interactions partielles.
TypeScript = comportements ciblés.
```

------

# 15. Realtime frontend

Stratégie retenue :

```txt
WebSocket event received
    ↓
event shape validated
    ↓
targeted HTMX refetch
    ↓
partial HTML update
```

Exemple :

```
SignalFeedUpdated → refresh signal feed fragment
ExecutionFeedUpdated → refresh execution feed fragment
NotificationCreated → refresh notification badge/list
SignalDetailUpdated → refresh visible detail panel
```

À éviter :

```txt
WebSocket event received
    ↓
mutate complex local frontend state
```

Le frontend ne doit pas être source de vérité.

Règle :

```txt
Realtime = invalidation/refetch.
Backend = permission authority.
Frontend = no business reconstruction.
```

------

# 16. PWA

Stack retenue :

```txt
PWA manifest
service worker minimal
static assets cache
offline fallback simple
```

## PWA MVP oui

```txt
installable app
manifest
service worker minimal
cache assets statiques
draft local Observation
network status
retry upload
mobile-first UI
```

## PWA MVP non

```txt
offline complet
sync offline complexe
conflit multi-device
actions offline
event replay côté client
full offline-first architecture
```

------

# 17. OpenAPI

Il sert à :

```
documenter les endpoints JSON
sécuriser les contrats API
préparer le futur mobile
préparer des modules TypeScript ciblés
permettre des tests de contrat
```

Flux :

```txt
Django REST Framework OpenAPI schema
    ↓
drf-spectacular
    ↓
schema versioned
    ↓
optional TypeScript client for JSON API consumers
```

`@hey-api/openapi-ts` génère du code TypeScript depuis une specification OpenAPI, avec SDKs, Zod schemas et hooks TanStack Query possibles. ([Hey API](https://heyapi.dev/docs/openapi/typescript/get-started?utm_source=chatgpt.com))

Règles

```
OpenAPI documents product APIs.
HTMX screens do not require generated TypeScript client.

```

Objectif :

```txt
L’IA ne devine pas les endpoints.
L’IA ne devine pas les payloads.
L’IA ne duplique pas les types backend.
```

------

# 18. Structure frontend

```txt
apps/api/
├── templates/
│   ├── base.html
│   ├── auth/
│   ├── onboarding/
│   ├── observations/
│   ├── signals/
│   ├── actions/
│   ├── checklists/
│   ├── notifications/
│   └── partials/
│
├── static/
│   ├── css/
│   ├── js/
│   ├── icons/
│   └── pwa/
│
├── frontend/
│   ├── ts/
│   │   ├── app.ts
│   │   ├── htmx-events.ts
│   │   ├── audio-recorder.ts
│   │   ├── uploads.ts
│   │   └── realtime.ts
│   └── styles/
│       └── app.css
```

Ne pas faire :

```txt
components/
hooks/
utils/
services/

React app
client-side router
global frontend store
feature-based SPA structure
```

A privilegier

```
templates par domaine
partials HTMX
TypeScript ciblé
CSS mobile-first
```

------

# 19. Monorepo

Structure globale :

```txt
houston/
├── apps/
│   └── api/              # Django + DRF + Templates + HTMX
├── docs/
├── infra/
├── docker-compose.yml
├── AGENTS.md
├── CLAUDE.md
└── README.md
```

------

# 20. Environnement local

```txt
Django API
Django ASGI server
Vite only for TypeScript/CSS build if needed
PostgreSQL
Redis
Celery worker
Celery beat
Django Channels / ASGI
MinIO
Mailpit
```

Docker Compose :

```txt
PostgreSQL
Redis
MinIO
Mailpit
```

L’API et le frontend peuvent tourner en local natif pour garder un cycle de dev rapide.

------

# 21. Règles IA / Claude Code / Codex

À stocker dans `CLAUDE.md` et `.cursor/rules`.

## Backend rules

```txt
Use Django + DRF.
Use modular Django apps.
No business logic in views.
Views call services.
Models contain fields, relations, constraints, small invariants.
Every important mutation emits a DomainEvent.
DomainEvents are persisted in the same DB transaction.
Use Celery for async side effects.
AI never writes directly to business tables.
Backend validates all AI outputs.
Permissions are always backend-resolved.
Realtime never bypasses permissions.
No microservices before MVP validation.
No Kafka before MVP validation.
```

## Frontend rules

```txt
Do not create a React SPA.
Use Django Templates for product screens.
Use HTMX for partial updates and form workflows.
Use TypeScript only for isolated frontend modules.
Use Vite only to bundle TypeScript/CSS if needed.
Do not introduce client-side routing.
Do not introduce Redux or global client-side business state.
Do not duplicate backend business validation in frontend state.
Realtime events trigger partial refetch, not local business mutations.
Frontend never resolves permissions.
Frontend never decides visibility.
No Next.js.
No full offline-first MVP.
```

------

# 22. Stack finale synthétique

```txt
BACKEND
Python 3.12/3.13
Django
Django REST Framework
PostgreSQL
Celery
Redis
Django Channels
Pydantic
OpenAI / Claude structured outputs
S3-compatible storage

FRONTEND
Django Templates
HTMX
TypeScript ciblé
Vite for TS/CSS bundling if needed
Alpine.js or Stimulus only if needed
Tailwind CSS or structured CSS
PWA manifest
Service worker minimal
Optional OpenAPI TypeScript client for JSON consumers

ARCHITECTURE
Event-driven modular monolith
Domain Events
Transactional Outbox
Async consumers
Backend-controlled AI
Backend-resolved visibility
Realtime via WebSockets
PostgreSQL canonical state
```

------

# 23. Formulation finale à stocker

```txt
Houston utilise une architecture event-driven modular monolith.

Le backend est développé en Python avec Django et Django REST Framework.
PostgreSQL reste la source canonique.
Chaque mutation métier importante produit un DomainEvent persisté via un pattern Outbox.
Celery consomme les events pour déclencher les traitements async : pipeline IA, notifications, broadcasts realtime, media cleanup, analytics et audit.

Le frontend MVP est une web app server-rendered avec Django Templates, HTMX et TypeScript ciblé.
Le backend reste la source de vérité du server state.
Les WebSocket events ne mutent pas directement un état métier frontend : ils déclenchent un refetch partiel HTMX des fragments autorisés.

L’IA est utilisée comme moteur de structuration.
Elle ne persiste jamais directement.
Elle ne décide jamais des permissions.
Elle ne décide jamais de la visibilité.
Ses sorties sont validées par Pydantic puis par les règles métier backend.
```

