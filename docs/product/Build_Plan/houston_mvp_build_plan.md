# Houston — MVP Build Plan v0.2

**Version:** v0.2
**Statut:** Plan de build MVP
**Périmètre:** Houston MVP complet — P0 pilote Mama Shelter Nice
**Objectif:** construire le P0 complet, dans un ordre strict, sans déplacer les règles métier côté frontend ni créer de dette structurelle.

---

# 1. Purpose

Ce document définit :

* l’objectif MVP ;
* le périmètre P0 complet ;
* l’ordre de construction ;
* les responsabilités backend/frontend ;
* les phases de build ;
* les gates de validation ;
* les critères d’acceptation ;
* la structure des tickets ;
* les règles de Definition of Done ;
* les risques ;
* le protocole pilote Mama Shelter Nice.

Ce document n’est pas :

* une roadmap long terme ;
* un planning commercial ;
* un chiffrage ;
* un backlog exhaustif.

---

# 2. MVP objective

```txt
MVP objective =
permettre à une équipe terrain de signaler, structurer, assigner, exécuter, valider et suivre des situations opérationnelles en conditions réelles.
```

Le cœur du MVP reste :

```txt
Observation → Signal → Action → Execution → Validation → Feed update
```

Critère principal :

```txt
A user submits an Observation.
System creates or aggregates a Signal.
Manager creates an Action.
Staff executes the Action.
Manager validates the Action.
Feeds update correctly.
```

---

# 3. P0 complete scope

Le P0 est complet pour le pilote.

Le P0 inclut :

```txt
- Auth / sessions / memberships / RBAC
- Runtime config / onboarding minimal
- Observation text
- Optional photos
- Audio transcription with text fallback
- Temporary upload lifecycle
- AI pipeline fake + real provider adapter
- Signal creation
- Signal aggregation
- no_signal_created
- Signal Feed
- Signal detail
- Action lifecycle
- Execution Feed
- In-app notifications
- Notification Center
- Minimal realtime invalidation/refetch
- Shared Checklists
- Personal Checklists
- Task → Observation
- Security baseline
- Cleanup jobs
- Mobile QA
- Mama Shelter Nice pilot readiness
```

---

# 4. P0 sequencing principle

```txt
P0 complet ne signifie pas développement simultané.
```

Règle :

```txt
Tout reste P0.
Tout n’est pas construit au même moment.
La boucle opérationnelle pilote l’ordre.
Les modules terrain viennent se brancher progressivement sur cette boucle.
```

Donc :

```txt
1. Construire l’autorité backend et les permissions.
2. Construire le socle frontend API-driven.
3. Construire Observation + media/audio.
4. Construire Observation → Signal.
5. Construire Signal → Action → Validation.
6. Ajouter notifications.
7. Ajouter realtime.
8. Ajouter checklists.
9. Durcir pour pilote.
```

---

# 5. Pilot scope

## 5.1 Pilote initial

```txt
Pilot MVP = Mama Shelter Nice.
```

## 5.2 Exclusion

```txt
Nancy pilot = post-Mama Shelter stabilization.
Not part of initial MVP build acceptance.
```

## 5.3 Implication produit

Le build doit optimiser pour :

* usage mobile terrain ;
* hôtel / restauration ;
* managers opérationnels ;
* staff non technique ;
* rapidité de saisie ;
* clarté des feeds ;
* sécurité des données opérationnelles.

---

# 6. Stack ownership matrix

## 6.1 Backend ownership

```txt
Django = business authority.
PostgreSQL = persisted source of truth.
Redis = temporary technical state only.
Celery = async execution only.
Channels = realtime invalidation only.
Pydantic = structured AI/technical payload validation.
OpenAPI = API contract.
```

Conséquences :

* les workflows métier vont dans `services.py` ;
* les lectures complexes vont dans `selectors.py` ;
* les règles d’autorisation vont dans `permissions.py` ;
* les views DRF restent fines ;
* les serializers ne pilotent pas les workflows ;
* les modèles ne pilotent pas les transitions métier ;
* aucun workflow métier ne va dans `core/`.

---

## 6.2 Frontend ownership

```txt
React = UI layer.
TanStack Query = server state.
Zustand = UI/client state only.
OpenAPI generated client = API access.
Realtime messages = invalidation triggers only.
Framer Motion = functional UX transitions and feedback only.
```

Conséquences :

* pas de business workflow dans React ;
* pas de calcul réel de permissions dans React ;
* pas de données serveur stockées dans Zustand ;
* pas de `fetch` direct dans les composants ;
* pas d’usage d’endpoint non documenté par OpenAPI ;
* les composants affichent, composent et déclenchent des hooks ;
* TanStack Query gère reads, mutations, cache, loading/error/success, invalidation.

---

## 6.3 API/OpenAPI ownership

```txt
OpenAPI owns the API contract.
```

Règles :

* toute API produit doit être documentée ;
* les types frontend viennent du client généré ;
* si les types générés sont faux, corriger le backend/schema puis régénérer ;
* ne pas modifier manuellement les fichiers générés ;
* ne pas inventer de commande de génération.

Si aucune commande OpenAPI n’existe :

```txt
OpenAPI generation command is not defined yet.
```

Créer alors un ticket dédié de setup OpenAPI.

---

## 6.4 Async ownership

```txt
Celery tasks are execution wrappers, not business services.
```

Règles :

* les tâches Celery reçoivent des IDs ;
* elles rechargent les records côté serveur ;
* elles appellent des services ;
* elles ne reçoivent pas de texte Observation brut ;
* elles ne contiennent pas de workflow métier directement ;
* elles ne deviennent pas source de vérité métier.

---

## 6.5 Realtime ownership

```txt
Channels = invalidation/refetch only.
```

Règles :

* websocket payload léger ;
* pas de payload métier complet ;
* pas de mutation métier depuis Channels ;
* authentification + vérification membership ;
* vérification du droit de souscription ;
* frontend invalide les queries TanStack Query ;
* frontend refetch via REST API.

---

# 7. Backend structure standard

Chaque app domaine suit cette structure quand pertinent :

```txt
models.py
services.py
selectors.py
permissions.py
api/
  serializers.py
  views.py
  urls.py
tests/
```

`core/` est autorisé uniquement pour les primitives techniques partagées.

Interdit dans `core/` :

```txt
- business workflows
- domain-specific services
- catch-all utilities
- cross-domain shortcuts
```

---

# 8. Frontend structure standard

Structure attendue :

```txt
src/
  api/
    generated/
  app/
  components/
    ui/
    domain/
    layout/
  features/
  stores/
  lib/
```

Usage :

```txt
src/api/generated/ = generated OpenAPI client
src/app/ = bootstrap, providers, routing, layout shell
src/components/ui/ = primitives shadcn/ui
src/components/domain/ = composants Houston réutilisables
src/components/layout/ = layout primitives
src/features/ = screens et flows métier
src/stores/ = Zustand UI/client state only
src/lib/ = petites utilities frontend
```

Interdit :

```txt
- nouveau top-level folder sans justification
- server state dans Zustand
- business workflow dans React
- permissions réelles calculées côté frontend
- direct fetch dans les composants feature
```

---

# 9. Build strategy

## 9.1 Principe

```txt
Build by domain-sequenced full-stack slices.
```

Chaque phase doit produire une preuve vérifiable :

* backend ;
* API ;
* OpenAPI ;
* frontend si concerné ;
* tests ;
* permissions ;
* commandes de validation.

## 9.2 Feed update levels

```txt
Feed update Level 1 = API/refetch correctness.
Feed update Level 2 = realtime invalidation/refetch.
```

Level 1 est requis avant validation de la boucle opérationnelle.

Level 2 est requis avant pilote.

## 9.3 UI principle

```txt
Mobile-first.
Operational clarity first.
No dense desktop-first UX.
No hidden critical actions.
```

---

# 10. Phase overview

```txt
0. Full-stack foundation
1. Identity / Memberships / RBAC
2. Runtime config / Onboarding minimal
3. Observation / Media / Transcription
   3A. Observation text
   3B. Temporary uploads + photos
   3C. Audio transcription + editable text
   3D. Cleanup jobs + signed media access
4. AI Pipeline / Signal Feed
5. Actions / Execution Feed
6. Notifications
7. Checklists
8. Realtime invalidation
9. Hardening
10. Pilot readiness
```

---

# 11. Phase 0 — Full-stack foundation

## Objective

Créer le socle technique backend/frontend sans encore construire les workflows métier avancés.

## Backend scope

```txt
- Django project baseline
- DRF baseline
- PostgreSQL connection
- Redis connection
- Celery setup
- Channels baseline configuration only if required by project boot
- no realtime business flow before Phase 7
- pytest
- Ruff
- project settings
- base model if needed
- OpenAPI generation command setup
```

## Frontend scope

```txt
Frontend scope:
- React + Vite + TypeScript app
- Tailwind CSS
- shadcn/ui base
- TanStack Query provider
- minimal Zustand setup
- Framer Motion setup
- src/api/generated/ folder
- app shell mobile-first
- routing baseline
```

Motion / Animation policy:

Framer Motion is part of the MVP frontend stack.

Purpose:
- improve mobile usability
- improve perceived responsiveness
- make screen transitions clearer
- provide feedback after important user actions
- make drawers, modals, sheets, and feed updates feel natural

Allowed:
- page/screen transitions
- mobile sheet/drawer transitions
- modal transitions
- toast entrance/exit
- feed item insertion animation
- button/action feedback
- loading-to-success transitions
- small status change feedback
- audio recording visual feedback
- upload/transcription progress feedback

Forbidden:
- decorative animations with no UX value
- heavy animation sequences
- complex animation state machines
- animations that slow down operational actions
- animations that hide loading/error states
- animations that hide business status changes
- animations used instead of clear text feedback

Principle:
Motion supports operational clarity.
Motion never replaces clear state, copy, or backend truth.

## CI scope

```txt
Backend:
- lint
- format check
- tests
- migration check
- OpenAPI generation if command exists

Frontend:
- typecheck
- lint
- build
```

## Acceptance

```txt
- Backend starts locally.
- Frontend starts locally.
- PostgreSQL works.
- Redis works.
- Celery worker can boot.
- Channels baseline can boot.
- OpenAPI generation command exists or dedicated setup ticket is created.
- Frontend has React/Vite/TypeScript shell.
- TanStack Query provider installed.
- Zustand reserved for UI/client state only.
- CI commands documented.
```

## Gate Phase 0

Can move to Phase 1 only if:

```txt
- backend foundation works
- frontend foundation works
- OpenAPI strategy is explicit
- CI baseline passes or missing commands are tracked
- no secrets in repo
```

---

# 12. Phase 1 — Identity / Memberships / RBAC

## Objective

Sécuriser l’accès avant les domaines métier.

## Backend scope

```txt
- User model
- email identity
- username identity for Staff
- Organization
- Establishment
- EstablishmentMembership
- membership statuses
- auth endpoints
- token/session lifecycle
- refresh token rotation
- permission services
- establishment access helpers
```

## Frontend scope

```txt
- login screen
- session handling
- protected route shell
- establishment selection if multiple memberships
- expired session handling
- permission-denied UI state
```

## Ownership rules

```txt
- Backend owns permissions.
- Frontend may display backend-provided permission flags.
- Frontend must not compute real permissions from role/domain data.
```

## Contract order

```txt
1. backend endpoint/service/selector
2. OpenAPI schema generated
3. TypeScript client generated
4. frontend hook
5. frontend screen
```

## Acceptance

```txt
- User can authenticate.
- User can belong to one or more establishments.
- Active membership gives access.
- Deactivated membership removes access.
- Backend permission functions are tested.
- Frontend protected routes work.
- Frontend handles forbidden response gracefully.
- No frontend-side RBAC authority.
```

## Gate Phase 1

Can move to Phase 2 only if:

```txt
- auth works
- memberships work
- permissions tested
- protected frontend shell works
- establishment scoping is enforced
```

---

# 13. Phase 2 — Runtime config / Onboarding minimal

## Objective

Initialiser un établissement réel et ses domaines opérationnels.

## Backend scope

```txt
- create organization
- create establishment
- submit establishment description
- operational modules
- operational domains
- operational units
- runtime vocabulary if MVP
- onboarding validation service
- establishment activation
- Mama Shelter Nice seed dataset
```

## Frontend scope

```txt
- onboarding flow
- establishment setup screens
- modules/domains/units validation UI
- activation state
- simple user invitation UI if in scope
```

## Contract order

```txt
1. backend endpoint/service/selector
2. OpenAPI schema generated
3. TypeScript client generated
4. frontend hook
5. frontend screen
```

## Acceptance

```txt
- Organization can be created.
- Establishment can be created.
- Establishment description can be submitted.
- Modules/domains/units can be validated.
- Establishment can become active.
- Mama Shelter Nice seed exists.
- Frontend can display and validate runtime config.
```

## Gate Phase 2

Can move to Phase 3 only if:

```txt
- Mama Shelter runtime seed exists
- operational domains assigned
- establishment active
- frontend onboarding flow works for MVP needs
```

---

# 14. Phase 3 — Observation / Media / Transcription

## Objectif

Permettre à un utilisateur terrain de créer une Observation exploitable avec texte, photos optionnelles et transcription audio, sans exposer de contenu sensible ni bloquer la suite du pipeline.

```
Phase 3 is split into:
3A. Observation text
3B. Temporary uploads + photos
3C. Audio transcription + editable text
3D. Cleanup jobs + signed media access
```

------

# Phase 3A — Observation text

## Objective

Construire le flux minimal de création d’Observation texte.

## Backend scope

```
- Observation model
- ObservationProcessing model/status
- submit Observation service
- ObservationCreated event if event system already exists
- ObservationProcessing queued state
- text validation
- establishment scoping
- author scoping
- source = direct/checklist-ready if checklist context is already modeled
- no raw Observation exposure in product API
```

## Frontend scope

```
- +Signaler text screen
- textarea input
- submit button
- basic frontend validation for visible required text
- backend validation error display
- loading state
- success state
- error state
- local non-durable draft if already planned
```

## Rules

```
- Text is required.
- Photo-only Observation is impossible at this stage.
- Frontend validation improves UX only.
- Backend remains source of validation truth.
- Observation submit must go through backend service.
- DRF view must stay thin.
- Raw Observation text must not be returned in product APIs outside the authorized submit/result flow.
```

## Acceptance

```
- User can submit a valid text Observation.
- Empty text is rejected.
- Too-short/invalid text is rejected according to domain rules.
- ObservationProcessing is created in queued status.
- Observation is scoped to establishment.
- Unauthorized user cannot submit for another establishment.
- API response does not expose unnecessary raw Observation content.
- Frontend handles loading/error/success states.
```

## Tests

```
Backend:
- service success test
- service invalid text test
- API success test
- API validation error test
- permission/establishment scoping test
- no raw Observation leak test

Frontend:
- submit valid text
- display validation error
- display loading state
- display success feedback
```

## Gate 3A

Can move to 3B only if:

```
- text Observation submit works end-to-end
- ObservationProcessing queued works
- establishment scoping is tested
- raw Observation exposure rules are tested
```

------

# Phase 3B — Temporary uploads + photos

## Objective

Ajouter les photos optionnelles sans permettre d’Observation photo-only.

## Backend scope

```
- temporary upload model or technical upload record
- upload initialization endpoint
- upload attach/link service
- photo validation
- max 3 photos per Observation
- allowed MIME types
- max file size validation
- temporary upload ownership
- temporary upload establishment scope
- media linked to Observation on submit
- orphan upload status or expiry metadata
```

## Frontend scope

```
- photo picker
- photo preview
- remove photo
- upload progress
- upload retry
- upload error state
- max 3 photos UI constraint
- submit Observation with linked temporary upload IDs
```

## Rules

```
- Photos are optional.
- Photo-only Observation is forbidden.
- Temporary upload is not business truth.
- Media is linked to Observation only on submit.
- Frontend must not bypass backend media limits.
- Backend must revalidate upload ownership and establishment scope.
```

## Acceptance

```
- User can attach up to 3 photos.
- User can remove a selected photo before submit.
- Upload error is displayed clearly.
- Observation with text + photos is accepted.
- Observation with photos but no valid text is rejected.
- More than 3 photos is rejected.
- Upload belonging to another user/establishment cannot be attached.
- Linked media count appears where needed without exposing raw Observation.
```

## Tests

```
Backend:
- upload init success
- invalid MIME rejected
- max size rejected
- max 3 photos enforced
- attach valid upload to Observation
- reject upload owned by another user
- reject upload from another establishment
- photo-only Observation rejected

Frontend:
- add photo
- remove photo
- max 3 photos UI behavior
- upload failure state
- submit with text + photo IDs
```

## Gate 3B

Can move to 3C only if:

```
- temporary uploads work
- photo validation works
- photo-only Observation is rejected
- media ownership and establishment scope are tested
```

------

# Phase 3C — Audio transcription + editable text

## Objective

Permettre à l’utilisateur de dicter une Observation, transformer l’audio en texte éditable, puis soumettre uniquement du texte validé.

## Backend scope

```
- temporary audio upload endpoint
- audio validation
- supported audio formats
- max duration validation if available
- max audio size validation
- transcription service abstraction
- transcription Celery task or sync service depending architecture
- transcription status/result endpoint if async
- audio deletion after success
- audio deletion after final failure
- AIUsageLog metadata for transcription if in scope
- no transcribed text stored before Observation submit except short-lived technical response if needed
```

## Frontend scope

```
- record audio UI
- recording state
- cancel recording
- upload audio state
- transcribing state
- transcription success state
- transcription failure state
- editable transcribed text
- retry once if allowed
- fallback to manual text input
```

## Rules

```
- Audio is temporary.
- Audio never creates Observation by itself.
- Audio only produces editable text.
- User submits validated text.
- The Observation pipeline receives text only.
- Audio content is deleted after transcription success or final failure.
- Celery payloads pass IDs only.
- Standard logs must not contain audio content, full transcription, or raw prompt/content.
```

## Acceptance

```
- User can record or upload audio.
- Audio is transcribed into editable text.
- User can edit transcription before submit.
- User can submit edited transcription as Observation text.
- Failed transcription does not block manual text submit.
- Audio is deleted after success/final failure.
- Unsupported audio is rejected.
- Too-large audio is rejected.
- Frontend displays recording/uploading/transcribing/failed states.
```

## Tests

```
Backend:
- valid audio accepted
- unsupported format rejected
- too-large audio rejected
- transcription success path
- transcription failure path
- audio deletion after success
- audio deletion after final failure
- Celery task receives IDs only
- logs do not contain raw audio/transcription content

Frontend:
- recording state
- transcription loading state
- transcription success into editable text
- transcription failure fallback
- submit edited transcription
```

## Gate 3C

Can move to 3D only if:

```
- audio transcription works
- text fallback works
- audio deletion is tested
- frontend transcription states work
- Observation submit still uses text only
```

------

# Phase 3D — Cleanup jobs + signed media access

## Objective

Sécuriser le cycle de vie des fichiers temporaires et l’accès aux médias liés.

## Backend scope

```
- cleanup job for orphan temporary uploads
- cleanup job for expired temporary audio
- media access permission service
- signed media URL generation if used
- media metadata endpoint if needed
- retention metadata
- cleanup event/log metadata without sensitive content
```

## Frontend scope

```
- display linked photo thumbnails where product UI allows it
- handle expired media URL
- retry media URL fetch if needed
- display media loading/error state
```

## Rules

```
- Redis must not store durable media truth.
- PostgreSQL stores persisted media metadata.
- Object storage stores file content.
- Signed URLs must be authorized.
- Expired temporary uploads must not remain usable.
- Cleanup jobs must not delete linked valid media.
```

## Acceptance

```
- Orphan temporary uploads expire.
- Expired temporary audio is deleted.
- Linked Observation media remains accessible to authorized users.
- Unauthorized user cannot access media.
- Signed URL generation enforces establishment and visibility scope.
- Expired media URL is handled gracefully by frontend.
- Cleanup jobs are idempotent.
```

## Tests

```
Backend:
- orphan upload cleanup
- expired audio cleanup
- linked media not deleted
- authorized media access
- unauthorized media access denied
- signed URL generated only for authorized user
- cleanup job idempotency

Frontend:
- media loading state
- media error state
- expired URL recovery if implemented
```

## Gate Phase 3

Can move to Phase 4 only if all Phase 3 gates pass:

```
- 3A Observation text works
- 3B temporary uploads/photos work
- 3C audio transcription works
- 3D cleanup/media access works
- no raw Observation leaks are tested
- ObservationProcessing queued works
```

# 15. Phase 4 — AI Pipeline / Signal Feed

## Objective

Transformer les Observations validées en Signals visibles et actionnables.

## Backend scope

```txt
- Pydantic AI schemas
- fake deterministic AI provider
- real provider adapter behind same interface
- AI usage logging metadata
- pipeline Celery task
- candidate validation
- Signal create service
- Signal aggregate service
- no_signal_created outcome
- detected_domains validation
- Signal Feed selector
- Signal detail selector
- last_activity_at management
- RBAC-scoped feed queries
```

## Frontend scope

```txt
- Signal Feed
- Signal detail
- processing state
- no_signal_created state if exposed
- Signal status badges
- domain badges
- urgency badge
- pinned display if in scope
- feed filters/view modes if in scope
```

## Rules

```txt
- AI does not mutate the database directly.
- Django validates business rules.
- AI does not decide permissions.
- AI does not decide urgency in MVP.
- Images are not sent to AI.
- Prompt/content logs are forbidden in standard logs.
- Signal visibility is backend-owned.
- Feed sorting is backend-owned.

Real AI provider integration starts only after fake provider passes:
- candidate schema validation
- Signal creation
- Signal aggregation
- no_signal_created
- RBAC-safe Signal Feed
```

## Contract order

```txt
1. backend endpoint/service/selector
2. OpenAPI schema generated
3. TypeScript client generated
4. frontend hook
5. frontend screen
```

## Acceptance

```txt
- Fake provider returns deterministic candidates.
- Real provider can be plugged behind same interface.
- AI JSON validates through Pydantic.
- Backend validates domains.
- Max 5 candidates per Observation.
- Signal is created if candidate is distinct.
- Signal is aggregated if candidate matches active similar Signal.
- no_signal_created works.
- Signal Feed works.
- Signal detail works without raw Observation.
- Signal.last_activity_at updates.
- Signal Feed respects RBAC and establishment scope.
- Frontend uses generated API types.
```

## Gate Phase 4

Can move to Phase 5 only if:

```txt
- fake AI pipeline creates/aggregates Signals
- no_signal_created works
- Signal Feed works
- Signal detail works
- RBAC feed tests pass
- frontend Signal Feed consumes OpenAPI client
```

---

# 16. Phase 5 — Actions / Execution Feed

## Objective

Fermer la boucle opérationnelle principale.

## Backend scope

```txt
- create Action from Signal
- assign Action
- accept Action
- mark Action done
- validate Action
- reopen Action
- cancel Action
- reassign Action if MVP
- Signal status transitions from Action lifecycle
- Execution Feed selector
- Action detail selector
- domain events
- notification triggers prepared if needed
```

## Frontend scope

```txt
- create Action from Signal
- Action assignment UI
- Execution Feed
- Action detail
- accept action
- mark done
- validate
- reopen
- cancel
- conflict/error states
```

## Rules

```txt
- No generic PATCH status endpoint.
- All business transitions use explicit service methods.
- All transitions check backend permission.
- All transitions validate current state.
- Multiple-write transitions use transaction.atomic.
- React never encodes transition authority.
```

## Contract order

```txt
1. backend endpoint/service/selector
2. OpenAPI schema generated
3. TypeScript client generated
4. frontend hook
5. frontend screen
```

## Acceptance

```txt
- Manager can create Action from authorized Signal.
- Action can be assigned to active user.
- Assignee can accept Action.
- Assignee can mark Action done.
- Manager/Director/Owner can validate according to permissions.
- Reopen works.
- Cancel works.
- Signal moves in_progress/resolved according to rules.
- Execution Feed shows relevant Actions.
- Unauthorized users cannot view or mutate forbidden Actions.
- Frontend handles forbidden/conflict responses.
```

## Gate Phase 5

Can move to Phase 6 only if:

```txt
- Action lifecycle complete
- Execution Feed works
- Signal status transitions work
- validation/reopen/cancel tested
- frontend Action flow works
- operational loop works with API/refetch feed update
```

---

# 17. Phase 6 — Notifications

## Objective

Créer les notifications in-app nécessaires au pilote.

## Backend scope

```txt
- Notification model
- Notification service
- Notification Matrix MVP
- Notification Center selector
- ActionAssigned notification
- pending validation notification
- mention notification
- important Signal event notification
- read/unread if MVP
```

## Frontend scope

```txt
- Notification Center
- unread badge
- notification list
- notification detail or navigation target
- empty state
- loading state
- error state
```

## Rules

```txt
- No raw Observation in notifications.
- Notification payloads stay minimal.
- Notification recipients are backend-owned.
- Frontend only displays what backend returns.
- Each notification must be traceable to a source event.
- Notification service consumes domain/application events.
- No notification should be created directly from React or DRF views.
```

## Contract order

```txt
1. backend endpoint/service/selector
2. OpenAPI schema generated
3. TypeScript client generated
4. frontend hook
5. frontend screen
```

## Acceptance

```txt
- In-app notification created for ActionAssigned.
- In-app notification created for pending validation.
- Mention notification works if mentions are MVP.
- Important Signal event notification works.
- Notification Center displays user-scoped notifications.
- No unauthorized notification is visible.
- No raw Observation leaks into notification payload.
```

## Gate Phase 6

Can move to Phase 7 only if:

```txt
- Notification Center works
- P0 notification triggers work
- notification RBAC/scoping tested
- no raw Observation leak tested
```

---

# 18. Phase 7 — Checklists

## Objective

Brancher les routines terrain sur le moteur Observation → Signal.

## Backend scope

```txt
- Shared ChecklistTemplate
- ChecklistTaskTemplate
- ChecklistExecution
- ChecklistTaskExecution
- Personal ChecklistTemplate
- Personal ChecklistExecution
- assign checklist execution
- start checklist execution
- complete task
- skip task
- task → contextual Observation
- checklist execution completion
- checklist cancellation
```

## Frontend scope

```txt
- Shared Checklist execution UI
- Personal Checklist UI
- checklist task list
- task status controls
- task → +Signaler contextual flow
- Execution Feed integration
- checklist empty/error/loading/success states
```

## Rules

```txt
- Checklist is not an Action.
- ChecklistExecution appears in Execution Feed.
- Personal Checklists are private to creator.
- Task → Observation goes through Observation submit service.
- Signal creation still goes through AI pipeline/backend processing.
- Action and Signal detail responses may expose backend-computed available_actions / available_transitions.
- Frontend may use these flags to display or hide action buttons.
- Frontend must not recompute transition authority from role/domain/status.
```

## Contract order

```txt
1. backend endpoint/service/selector
2. OpenAPI schema generated
3. TypeScript client generated
4. frontend hook
5. frontend screen
```

## Acceptance

```txt
- Shared ChecklistTemplate can be created/activated.
- Shared ChecklistExecution can be assigned.
- Assignee can execute checklist.
- Personal Checklist can be created and executed by creator.
- Checklist task can create contextual Observation.
- ChecklistExecution appears in Execution Feed.
- Personal Checklist visibility is private.
- Permissions are tested.
```

## Gate Phase 8

Can move to Phase 9 only if:

```txt
- Shared Checklist flow works
- Personal Checklist flow works
- task → Observation works
- Execution Feed integration works
- checklist permissions tested
```

---

# 19. Phase 8 — Realtime invalidation

## Objective

Rendre les feeds et détails vivants sans transformer websocket en source métier.

## Backend scope

```txt
- Channels authentication
- subscription permission checks
- channel/group naming rules
- lightweight event broadcast
- Signal Feed invalidation event
- Execution Feed invalidation event
- Notification Center invalidation event
- detail invalidation event
- unauthorized websocket tests
```

## Frontend scope

```txt
- websocket connection lifecycle
- reconnect behavior if MVP
- event type routing
- TanStack Query invalidation
- refetch through REST API
- expired session handling
- unauthorized event handling
```

## Rules

```txt
- Realtime messages are invalidation/refetch triggers only.
- Do not use websocket payloads as business truth.
- Do not store full websocket payloads as domain state.
- Do not bypass REST API after realtime events.
- Channels consumers must not perform business workflows.
- Each realtime event type must map to explicit TanStack Query keys to invalidate.
```

## Acceptance

```txt
- Signal Feed invalidates/refetches after relevant event.
- Execution Feed invalidates/refetches after relevant event.
- Notification Center invalidates/refetches after relevant event.
- Signal/Action detail invalidates/refetches after relevant event.
- Unauthorized websocket user receives no forbidden event.
- Frontend does not store domain state from websocket payload.
```

## Gate Phase 7

Can move to Phase 8 only if:

```txt
- realtime invalidation works
- REST refetch remains source of truth
- unauthorized realtime tests pass
- frontend query invalidation works
```

---

# 20. Phase 9 — Hardening

## Objective

Durcir le produit techniquement avant le pilote, sans ajouter de nouvelles fonctionnalités métier.

## Scope

```
Phase 9 is technical hardening only.
It must not introduce new product scope.
It validates reliability, security, data lifecycle, logs, performance, and operational readiness.
```

## Backend scope

```
- RBAC API test review
- RBAC realtime test review
- tenant/establishment scoping audit
- no raw Observation exposure audit
- no raw Observation in realtime audit
- no raw Observation in notifications audit
- no sensitive content in logs audit
- token/session behavior verification
- cleanup jobs verification
- temporary uploads expiration verification
- audio deletion verification
- AI structured outputs retention verification
- Celery retry behavior verification
- failed task visibility/logging
- backup/restore smoke test
- performance smoke tests on key feeds
```

## Frontend scope

```
- critical flow QA
- mobile viewport QA
- touch-friendly interaction check
- loading/error/empty/success state review
- expired session UX
- permission denied UX
- network error UX
- critical action feedback
- Framer Motion usage review
- animation does not hide loading/errors/business statuses
- PWA-ready checks
```

## API/OpenAPI scope

```
- OpenAPI schema generation works
- generated TypeScript client is up to date
- no undocumented product endpoint is used by frontend
- API response shapes match frontend expectations
```

## Realtime scope

```
- websocket authentication verified
- subscription permission checks verified
- unauthorized event delivery test
- realtime payloads remain lightweight
- frontend invalidates TanStack Query keys
- frontend refetches REST API after realtime events
```

## Security acceptance

```
- RBAC API tests pass.
- RBAC realtime tests pass.
- No raw Observation is exposed in product API.
- No raw Observation is exposed in realtime.
- No raw Observation is exposed in notifications.
- Logs contain no raw Observation, full comments, audio content, photo content, secrets, tokens, full AI prompts, or full AI outputs with business content.
- No frontend-side RBAC authority exists.
- No server state is stored in Zustand.
```

## Ops acceptance

```
- Cleanup jobs pass.
- Temporary uploads expire correctly.
- Audio deletion works after success/final failure.
- AI structured outputs retention is verified.
- Backup/restore smoke test is documented.
- Feed performance is acceptable for pilot volume.
- Celery retry/failure behavior is verified.
```

## Frontend acceptance

```
- Main flows work on smartphone viewport.
- Critical actions have clear feedback.
- Loading/error/empty/success states are present where needed.
- Expired session is handled clearly.
- Forbidden responses are handled clearly.
- Framer Motion is used only for functional transitions/feedback.
- Animations do not hide business state, loading, or errors.
```

## Gate Phase 9

Can move to Phase 10 only if:

```
- security acceptance passes
- ops acceptance passes
- frontend acceptance passes
- OpenAPI/client generation is clean
- known risks/debts are documented
- no new product scope was added during hardening
```

------

# 21. Phase 10 — Pilot readiness

## Objective

Préparer l’exécution terrain du pilote Mama Shelter Nice.

Cette phase n’est pas une phase de construction produit.
Elle valide que le P0 complet peut être testé en conditions réelles.

## Scope

```
Phase 10 is product/field readiness.
It prepares the pilot environment, pilot users, scenarios, success metrics, feedback loop, and support path.
```

## Pilot environment scope

```
- Mama Shelter Nice organization ready
- Mama Shelter Nice establishment ready
- operational modules configured
- operational domains configured
- operational units configured if used
- test users created
- roles assigned
- memberships active
- sample Signals/Actions/Checklists seeded only if useful for demo/training
- clean pilot dataset available before real usage
```

## Pilot users scope

```
- Owner/Director pilot user identified
- Manager pilot users identified
- Staff pilot users identified
- username identity users prepared if needed
- login/activation instructions prepared
- establishment selection tested if user has multiple memberships
```

## Pilot scenarios

```
- room issue
- maintenance issue
- restaurant rush issue
- lost/found or guest issue
- checklist round
- audio Observation scenario
- photo Observation scenario
- Signal aggregation scenario
- Action validation scenario
- notification scenario
- realtime feed update scenario
```

## Pilot success metrics

```
Usage:
- Observations submitted/day
- active users by role
- checklist completion rate

Workflow:
- Signals created vs aggregated
- no_signal_created rate
- Actions created
- Actions completed
- Actions validated
- time from Observation to Action
- time from Action assignment to completion

Quality:
- manager corrections of domains
- invalid/noisy Signals
- failed transcriptions
- failed uploads
- notification usefulness
- realtime update reliability

Safety:
- permission issue count
- data leak issue count
- blocked user flow count
```

## Feedback protocol

```
- feedback questions prepared
- feedback collection owner assigned
- daily or end-of-shift feedback rhythm defined
- issue severity levels defined
- support contact/path defined
- bug triage process defined
- rollback or pause procedure defined
```

## Pilot acceptance

```
- Pilot users can log in.
- Pilot users have correct roles and memberships.
- Mama Shelter runtime config is ready.
- Pilot scenarios are documented.
- Success metrics are defined.
- Feedback questions are ready.
- Incident support path is ready.
- Mobile QA has passed on target devices/browsers.
- P0 Master Gate has passed.
```

## Gate Phase 10

Pilot can start only if:

```
- Phase 9 hardening gate passed
- P0 Master Gate passed
- Mama Shelter pilot environment is ready
- pilot users are ready
- pilot scenarios are ready
- success metrics are ready
- support/incident process is ready
```

# 23. P0 Master Gate

Le pilote Mama Shelter Nice peut démarrer uniquement si :

## Operational loop

```txt
- Observation → Signal → Action → Execution → Validation works end-to-end.
- Signal Feed is correct.
- Execution Feed is correct.
- Signal statuses update from Action lifecycle.
```

## Field input

```txt
- Text Observation works.
- Optional photos work.
- Audio transcription works.
- Text fallback works.
- Photo-only Observation is forbidden.
- Cleanup jobs work.
```

## AI

```txt
- Fake provider works.
- Real provider works behind same interface.
- Pydantic JSON validation works.
- Backend domain validation works.
- Signal creation works.
- Signal aggregation works.
- no_signal_created works.
```

## Notifications

```txt
- P0 in-app notifications work.
- Notification Center works.
- No raw Observation leaks.
```

## Realtime

```txt
- Signal Feed invalidation works.
- Execution Feed invalidation works.
- Notification Center invalidation works.
- Detail invalidation works.
- Unauthorized websocket tests pass.
```

## Checklists

```txt
- Shared Checklist execution works.
- Personal Checklist works.
- Checklist task can create contextual Observation.
```

## Security

```txt
- RBAC API tests pass.
- RBAC realtime tests pass.
- No frontend-side RBAC authority.
- No secrets in repo.
- Logs contain no raw sensitive operational content.
```

## Pilot

```txt
- Mama Shelter seed ready.
- Pilot scenarios ready.
- Mobile QA passed.
- Backup/restore smoke test done.
```

---

# 24. Backend Definition of Done

Backend work is done only when:

```txt
- service/selector/permission ownership is respected
- views remain thin
- serializers do not orchestrate workflows
- status transitions are explicit
- no generic PATCH status endpoint is introduced
- transaction boundaries are correct
- tenant/establishment scoping is enforced
- sensitive payload rules are respected
- Celery payloads pass IDs only when sensitive content is involved
- Channels payloads are lightweight invalidation events only
- migrations exist for model changes
- OpenAPI is updated when API shape changes
- tests cover changed behavior
- relevant backend commands were run or a reason is given
- risks/debt are stated
```

Backend commands:

```bash
cd apps/api && uv sync
cd apps/api && uv run ruff check .
cd apps/api && uv run ruff format --check .
cd apps/api && uv run pytest
cd apps/api && uv run python manage.py makemigrations --check --dry-run
```

OpenAPI:

```txt
Use the project-defined OpenAPI command if it exists.
If missing, do not invent it.
Create a setup ticket instead.
```

---

# 25. Frontend Definition of Done

Frontend work is done only when:
- generated API types are used when applicable
- no direct fetch is added inside feature components
- TanStack Query handles server state
- Zustand is limited to UI/client state
- React does not contain business workflows
- React does not compute real permissions
- loading/error/empty/success states are handled when relevant
- mobile-first behavior is preserved
- permissions are backend-driven
- realtime events invalidate/refetch instead of carrying business truth
- Framer Motion is used only for functional transitions/feedback
- animations do not hide loading, errors, or business state changes
- relevant frontend commands were run or a reason is given
- tests are added/updated when behavior changes
- risks/debt are stated

Frontend commands:

```bash
cd apps/web && npm install
cd apps/web && npm run typecheck
cd apps/web && npm run lint
cd apps/web && npm run build
```

API client generation:

```txt
Use the project-defined API client generation command if it exists.
If missing, do not invent it.
Create a setup ticket instead.
```

---

# 26. Ticket template

```txt
Ticket title:

Phase:
Domain:
Backend / Frontend / Full-stack:

Context:
Why this ticket exists.

Scope:
What must be implemented.

Out of scope:
What must not be changed.

Dependencies:
Previous tickets/domains required.

Backend ownership:
- services.py impact:
- selectors.py impact:
- permissions.py impact:
- models/migrations impact:
- api serializers/views/urls impact:

Frontend ownership:
- generated API client impact:
- TanStack Query hooks impact:
- Zustand UI state impact:
- components/pages/forms impact:
- loading/error/empty/success states:

API/OpenAPI impact:
- endpoint added/changed:
- schema changed:
- generated TS types updated:

Async/realtime impact:
- Celery tasks:
- Redis usage:
- Channels events:
- Query invalidation keys:

Security/RBAC:
- who can do what:
- who can view what:
- forbidden cases:

Business rules:
- status transitions:
- validations:
- idempotency/retry behavior:

Events:
- emitted domain/application events:

Acceptance criteria:
Concrete behavior to validate.

Tests:
- service tests:
- selector tests:
- permission tests:
- API tests:
- frontend hook/component tests:
- realtime tests if applicable:

Commands:
- backend commands run:
- frontend commands run:
- OpenAPI/client generation command run:

Risks/debt:
Known limitation or follow-up.
```

---

# 27. Critical dependencies

```txt
Critical dependency #1:
Auth + EstablishmentMembership + permissions.
```

```txt
Feeds require:
- operational domains
- membership domains
- signal detected domains
- last_activity_at
- backend-owned sorting
- backend-owned visibility
```

```txt
Actions require:
- Signal Domain
- Accounts/Memberships
- RBAC
- explicit transition services
```

```txt
Notifications require:
- domain/application events
- Notification Matrix
- recipient resolution
- user/membership scope
```

```txt
Realtime requires:
- authenticated Channels connection
- subscription permission checks
- lightweight event payloads
- TanStack Query invalidation frontend side
```

```txt
Checklists require:
- Users
- operational domains
- Execution Feed
- Observation submit flow
```

---

# 28. Risk register

## Risk 1 — P0 too wide

```txt
Risk:
P0 contains many modules and can become difficult to sequence.

Mitigation:
P0 stays complete, but phases are strictly ordered.
Each phase has a gate.
P0 Master Gate decides pilot readiness.
```

## Risk 2 — business logic leaks into frontend

```txt
Risk:
React starts encoding permissions, statuses, or workflow rules.

Mitigation:
Backend owns business rules.
Frontend consumes backend-provided permissions and transition availability.
```

## Risk 3 — backend ownership becomes blurred

```txt
Risk:
Workflows leak into serializers, views, models, signals, or core utilities.

Mitigation:
Writes go to services.py.
Reads go to selectors.py.
Authorization goes to permissions.py.
DRF views stay thin.
```

## Risk 4 — realtime becomes source of truth

```txt
Risk:
Websocket payloads start carrying business state.

Mitigation:
Channels only sends invalidation events.
Frontend refetches REST APIs through TanStack Query.
```

## Risk 5 — AI instability

```txt
Risk:
AI output breaks workflow predictability.

Mitigation:
Fake deterministic provider first.
Pydantic validates JSON.
Django validates business rules.
AI never mutates DB directly.
```

## Risk 6 — sensitive data leak

```txt
Risk:
Raw Observation, comments, audio/photo content, prompts, or tokens leak into API/logs/realtime/notifications.

Mitigation:
No raw Observation in product API/realtime/notifications.
Logs contain technical metadata only.
Celery payloads pass IDs only.
```

## Risk 7 — field UX friction

```txt
Risk:
Terrain users find the app too slow or complex.

Mitigation:
Mobile-first UI.
Touch-friendly interactions.
Fast flows.
Clear feedback.
No hidden critical actions.
```

---

# 29. Pilot validation protocol

## Scripted scenarios

```txt
- room issue
- maintenance issue
- restaurant rush issue
- lost/found or guest issue
- checklist round
```

## Pilot metrics

```txt
- Observations submitted/day
- Signals created vs aggregated
- no_signal_created rate
- Actions created
- Actions completed/validated
- time from Observation to Action
- checklist completion rate
- user adoption by role
- manager corrections of domains
- notification usefulness
- realtime update reliability
```

## Pilot protocol must define

```txt
- users involved
- roles involved
- scenarios
- duration
- success metrics
- feedback questions
- incident support path
- rollback/support plan
```

---

# 30. Non-negotiables

```txt
No raw Observation in product API.
No raw Observation in realtime.
No raw Observation in notifications.
No frontend-side RBAC authority.
No Signal direct manual creation MVP.
No Action without Signal.
No shared user accounts.
No photo-only Observation.
No long-lived unrotated refresh token.
No direct provider AI call from frontend.
No business workflow in React.
No business workflow in Celery task body.
No business workflow in Channels consumer.
No server state in Zustand.
No websocket payload as business truth.
No generic PATCH status endpoint for business transitions.
No OpenAPI/client generation command invented by the AI.
```

---

# 32. Out of MVP

```txt
- billing
- SSO
- MFA
- native mobile
- advanced analytics dashboard
- advanced AI review UI
- recommended assignees
- presence / typing / read receipts
- full admin product console
- direct-to-S3 upload
- offline mutation queue
- durable offline storage of sensitive business data
```

---

## 30. Risk — AI-generated overengineering

```
Risk:
The AI creates generic abstractions, premature utilities, unnecessary layers, or broad refactors.

Mitigation:
Tickets must be small.
Out of scope must be explicit.
No new top-level folder without justification.
No generic core utility without demonstrated repeated need.
Prefer local explicit code over abstraction.

No premature abstraction.
Prefer explicit domain services, selectors, hooks, and components until duplication is proven.
```

# 32. Final recommendation

Le Build Plan v0.2 est prêt à remplacer le v0.1.

La décision structurante :

```txt
Le backend possède les règles métier.
Le frontend possède l’expérience utilisateur.
OpenAPI relie les deux.
Celery exécute l’async.
Channels invalide/refetch seulement.
Redis ne stocke aucune vérité métier.
```

L’ordre final à respecter :

```txt
0. Full-stack foundation
1. Identity / Memberships / RBAC
2. Runtime config / Onboarding minimal
3. Observation / Media / Transcription
4. AI Pipeline / Signal Feed
5. Actions / Execution Feed
6. Notifications
7. Realtime invalidation
8. Checklists
9. Hardening / Pilot readiness
```