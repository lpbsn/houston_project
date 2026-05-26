# Houston — MVP Build Plan

**Version:** v0.1  
**Date:** 2026-05-26  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — ordre de construction, phases, jalons, tickets, dépendances, critères d’acceptation, risques, pilote Mama Shelter Nice

**Documents liés :**

- `houston_technical_architecture_erd_final.md`
- `houston_api_contract_mvp.md`
- `houston_feed_query_sorting_contract.md`
- `houston_realtime_architecture.md`
- `houston_authentication_identity_domain.md`
- `houston_rbac_permissions_domain.md`
- `houston_onboarding_domain.md`
- `houston_observation_domain.md`
- `houston_signal_domain.md`
- `houston_action_domain.md`
- `houston_checklist_domain.md`
- `houston_ai_overview.md`
- `houston_event_catalog.md`
- `houston_notification_matrix.md`
- `houston_upload_media_lifecycle.md`
- `houston_security_rgpd_baseline.md`

---

# 1. Objectif du document

Ce document transforme le cadrage produit/tech Houston en plan de build MVP.

Il définit :
- l’objectif MVP ;
- le périmètre pilote ;
- les phases de construction ;
- les jalons ;
- les vertical slices ;
- les dépendances ;
- les tickets types ;
- les critères d’acceptation ;
- les risques ;
- les exclusions MVP ;
- le protocole pilote Mama Shelter Nice.

---

# 2. Principe central

```txt
Build the smallest complete operational loop.
Harden it for pilot.
Then expand.
```

En français :

```txt
Construire la plus petite boucle opérationnelle complète.
La durcir pour le pilote.
Étendre ensuite.
```

---

# 3. Rôle du MVP Build Plan

```txt
MVP Build Plan = ordre de construction + jalons + tickets + critères d’acceptation + risques.
```

Ce document n’est pas :
- un planning commercial ;
- un chiffrage définitif ;
- une roadmap long terme ;
- un backlog exhaustif de tous les tickets techniques.

Il sert à :
- éviter le scope creep ;
- guider Cursor/Codex/Claude Code ;
- sécuriser l’ordre de développement ;
- valider chaque phase par preuve fonctionnelle ;
- préparer le pilote terrain.

---

# 4. Objectif MVP

```txt
MVP objective = permettre à une équipe terrain de signaler, structurer, assigner, exécuter, valider et suivre des situations opérationnelles en conditions réelles.
```

## 4.1 P0 absolu

```txt
P0 = complete operational loop:
Observation → Signal → Action → Execution → Validation → Feed update.
```

## 4.2 Critère d’acceptation principal

```txt
Acceptance #1:
A user can submit an Observation.
System creates/aggregates Signal.
Manager creates Action.
Staff executes Action.
Manager validates.
Feeds update.
```

---

# 5. Périmètre pilote

## 5.1 Pilote initial

```txt
Pilot MVP = Mama Shelter Nice.
```

## 5.2 Nancy

```txt
Nancy pilot = post-Mama Shelter stabilization.
Not part of initial MVP build acceptance.
```

## 5.3 Implication

Le build MVP doit optimiser pour :
- un établissement hôtel/restauration réel ;
- des utilisateurs terrain ;
- des managers opérationnels ;
- des flux mobile-first ;
- une validation rapide en conditions réelles.

---

# 6. Stratégie de construction

## 6.1 Vertical slices

```txt
Build by vertical slices.
Chaque slice doit produire un flux utilisable de bout en bout.
```

## 6.2 Pourquoi

Construire par vertical slices évite :
- backend complet inutilisable ;
- frontend déconnecté de l’API ;
- modèle DB surdimensionné ;
- feedback terrain trop tardif.

Chaque phase doit produire une preuve fonctionnelle.

---

# 7. UI Kit MVP

## 7.1 Décision

```txt
Build minimal mobile-first UI kit:
buttons, forms, cards, badges, feed items, modals, toasts.
```

## 7.2 Objectif

Avoir un socle UI suffisant pour :
- formulaires auth/onboarding ;
- cartes feed ;
- badges domains/status/urgency ;
- actions principales ;
- états loading/error/empty ;
- UX mobile terrain.

## 7.3 Hors MVP

Pas de design system complet.

---

# 8. Stratégie IA

## 8.1 Fake provider d’abord

```txt
Start with fake/deterministic AI provider.
Then plug real provider behind same interface.
```

## 8.2 Pourquoi

Réduit :
- instabilité IA ;
- coûts ;
- lenteur tests ;
- dépendance provider ;
- bugs non déterministes.

## 8.3 Acceptation IA

```txt
AI acceptance:
- valid JSON schema
- backend validates domains
- max 5 candidates
- create/aggregate/no_signal_created outcomes work
```

---

# 9. OpenAPI / frontend contract

## 9.1 OpenAPI dès le début

```txt
OpenAPI generated from day 1.
OpenAPI documents JSON APIs and future mobile/API consumers.
HTMX product screens use server-rendered templates and partials.
Generated TypeScript client is optional for targeted JSON API consumers.
```

## 9.2 Frontend start

```txt
Frontend starts with Django Templates from Phase 0/1.
HTMX partials start once authenticated workflows exist.
OpenAPI remains generated continuously for JSON endpoints.
Generated TypeScript client is only used where a TypeScript module consumes JSON APIs.
```

## 9.3 Mocks

```txt
Frontend mocks should be avoided for server-rendered flows.
If JSON API mocking is needed, mocks must follow OpenAPI schemas.
```

## 9.4 Acceptance

```txt
OpenAPI acceptance:
- JSON product APIs are documented.
- schema generation passes in CI.
- TypeScript client can be generated when needed.
- HTMX product screens do not depend on a generated client.
```

---

# 10. Tests

## 10.1 Test priority

```txt
Test priority:
1. domain services
2. permissions
3. API integration
4. feed queries
5. AI contracts
6. realtime authorization
```

## 10.2 Pourquoi

Les plus gros risques sont :
- règles métier ;
- droits d’accès ;
- feeds ;
- IA ;
- realtime.

Les tests UI complets ne doivent pas masquer des bugs backend.

---

# 11. Definition of Done

## 11.1 Ticket done

```txt
Ticket done =
- code implemented
- tests pass
- API documented if endpoint
- permissions checked
- no raw sensitive data leaked
- basic error handling
```

## 11.2 Taille ticket

```txt
Ticket size target:
small enough to review diff safely.
```

## 11.3 Format backlog

```txt
Backlog format:
Epic
→ Slice
→ Ticket
→ Acceptance criteria
→ Dependencies
→ Tests
```

---

# 12. Phases MVP

## 12.1 Vue globale

```txt
MVP Build Plan phases:
0. Foundations
1. Runtime config + onboarding minimal
2. Observation + upload + transcription
3. AI pipeline + Signal Feed
4. Actions + Execution Feed
5. Checklists + Notifications + Realtime
6. Hardening + pilot readiness
```

## 12.2 Ordre

```txt
Strict phase order.
Flexible ticket order inside phase if dependencies met.
```

## 12.3 Migrations

```txt
Migrations generated per domain slice.
Review schema after each phase.
```

---

# 13. Phase 0 — Foundations

## 13.1 Objectif

Construire le socle technique et les fondations métier nécessaires à tout le reste.

## 13.2 Scope

```txt
Phase 0:
- project setup
- auth
- user identities email/username
- organizations/establishments
- memberships
- operational domains
- permission services
- OpenAPI base
```

## 13.3 Milestone 0.1

```txt
Milestone 0.1:
- repo structure
- Docker Compose
- Django project
- PostgreSQL
- Redis
- pytest
- Ruff
- OpenAPI setup
```

## 13.4 CI MVP

```txt
CI MVP:
- lint
- tests
- migrations check
- OpenAPI schema generation check
```

## 13.5 Critical dependency

```txt
Critical dependency #1 = Auth + EstablishmentMembership + permissions.
```

## 13.6 Acceptance Phase 0

- API project démarre localement via Docker Compose.
- Tests s’exécutent.
- OpenAPI schema générable.
- User email identity et username identity possibles.
- Organization + Establishment créables.
- Membership active/deactivated fonctionne.
- Permission service minimal testé.
- No secrets in repo.

---

# 14. Phase 1 — Runtime config + onboarding minimal

## 14.1 Scope

```txt
Phase 1:
- create organization/establishment
- submit establishment description
- validate modules/domains/units
- invite initial users
- activate establishment
```

## 14.2 Mama Shelter seed

```txt
Create Mama Shelter Nice seed dataset after Phase 1.
```

## 14.3 Acceptance Phase 1

- Un établissement peut être initialisé.
- Modules/domains/units validés.
- Owner/Director/Manager/Staff peuvent être invités.
- Staff sans email peut être créé via username identity.
- Establishment peut passer `active`.
- Mama Shelter Nice seed disponible.

---

# 15. Phase 2 — Observation + upload + transcription

## 15.1 Scope

```txt
Phase 2:
- submit text Observation
- temporary uploads
- optional photos
- transcription audio
- ObservationProcessing queued
```

## 15.2 Photos

```txt
Photos = P0 optional.
Photo-only Observation forbidden.
```

## 15.3 Audio

```txt
Audio transcription = P0, but never blocks text submit.
```

## 15.4 Offline

```txt
Offline MVP:
local Observation draft only.
Submit requires online.
```

## 15.5 Media acceptance

```txt
Media acceptance:
- max 3 photos
- no photo-only Observation
- audio deleted after transcription
- signed URLs authorized
- cleanup jobs work
```

## 15.6 Acceptance Phase 2

- Un user peut soumettre une Observation texte.
- Une Observation sans texte valide est refusée.
- Photos optionnelles uploadées temporairement puis liées.
- Photo-only refusé.
- Audio transcrit en texte éditable.
- Audio supprimé après transcription ou échec final.
- ObservationProcessing créé en `queued`.
- Aucun raw Observation exposé hors flux autorisé.

---

# 16. Phase 3 — AI pipeline + Signal Feed

## 16.1 Scope

```txt
Phase 3:
- AI pipeline contract
- fake provider
- Signal creation
- Signal aggregation
- Signal Feed
- Signal detail
```

## 16.2 Feed dependency

```txt
Feeds require:
- operational domains
- membership domains
- signal detected domains
- last_activity_at
```

## 16.3 Acceptance Phase 3

- Fake AI provider retourne candidates déterministes.
- Backend valide domains.
- Max 5 candidates par Observation.
- Signal créé si candidate distincte.
- Signal agrégé si candidate similaire.
- no_signal_created fonctionne.
- Signal Feed personnel/général fonctionne.
- Signal detail sans Observation brute.
- Signal.last_activity_at mis à jour.
- Signal Feed respecte RBAC.

---

# 17. Phase 4 — Actions + Execution Feed

## 17.1 Scope

```txt
Phase 4:
- create Action from Signal
- assign
- accept
- mark done
- validate
- reopen
- cancel
- Execution Feed Actions
```

## 17.2 Dependencies

```txt
Actions depend on:
Signal Domain
Accounts/Memberships
RBAC
```

## 17.3 Acceptance Phase 4

- Manager crée une Action depuis un Signal autorisé.
- Action assignée à un user actif.
- Assignee accepte Action.
- Assignee marque done/pending validation.
- Manager/Director/Owner valide selon permissions.
- Reopen fonctionne.
- Cancel fonctionne.
- Signal passe in_progress/resolved selon règles.
- Execution Feed affiche Actions pertinentes.
- Permissions Action testées.

---

# 18. Phase 5 — Checklists + Notifications + Realtime

## 18.1 Scope

```txt
Phase 5:
- Shared Checklists
- Personal Checklists
- Notification Matrix MVP
- Realtime invalidation
```

## 18.2 Checklists

```txt
Checklists = P0 MVP, build after Action lifecycle.
```

## 18.3 Checklist dependencies

```txt
Checklists depend on:
Users
Operational domains
Execution Feed
Observation submit for task-generated Observations
```

## 18.4 Notifications

```txt
P0 = in-app notifications.
Push = optional P0.5 / P1 depending pilot need.
```

## 18.5 Notifications dependencies

```txt
Notifications depend on:
ApplicationEvents
Notification Matrix
Recipients/users
```

## 18.6 Realtime

```txt
Realtime = P0 minimal invalidation/refetch.
Presence/typing/read receipts = NO.
```

## 18.7 Notification acceptance

```txt
Notification acceptance:
P0 in-app notifications appear for ActionAssigned, pending validation, mentions, important Signal events.
```

## 18.8 Realtime acceptance

```txt
Realtime acceptance:
visible feed/detail updates after relevant event without manual refresh.
```

## 18.9 Acceptance Phase 5

- Shared ChecklistTemplate créé/activé.
- Shared ChecklistExecution assignée.
- Personal Checklist créée et exécutée par son créateur.
- Checklist task peut créer une Observation contextualisée.
- Notification in-app créée pour triggers P0.
- Notification Center fonctionne.
- Realtime invalide/refetch Signal Feed, Execution Feed, Notification Center, details.
- Unauthorized websocket user ne reçoit pas d’event non autorisé.

---

# 19. Phase 6 — Hardening + pilot readiness

## 19.1 Scope

```txt
Phase 6:
- security baseline checks
- cleanup jobs
- backup/restore smoke test
- pilot dataset
- mobile QA
- performance smoke tests
```

## 19.2 Security acceptance

```txt
Security acceptance:
- no secrets in repo
- token auth works
- RBAC tested
- no raw Observation in product API/realtime/notifications
```

## 19.3 Mobile acceptance

```txt
Mobile acceptance:
Core flows usable on smartphone viewport.
```

## 19.4 Acceptance Phase 6

- Cleanup jobs testés.
- Temporary uploads expirent correctement.
- AI structured outputs retention 14 jours.
- Logs ne contiennent pas de raw Observation/comment/audio/photo.
- Backup/restore smoke test documenté.
- Dataset Mama Shelter prêt.
- Scénarios pilote scriptés.
- Performance feed acceptable pour volume pilote.
- Déploiement pilote prêt.

---

# 20. P0 / P1

## 20.1 P0

```txt
P0 = complete operational loop:
Observation → Signal → Action → Execution → Validation → Feed update.
```

P0 includes:
- Auth/memberships/RBAC.
- Runtime config minimal.
- Observation text.
- Optional photos.
- Audio transcription.
- AI pipeline fake then real.
- Signal Feed.
- Action lifecycle.
- Execution Feed.
- Shared Checklists.
- Personal Checklists.
- In-app notifications.
- Minimal realtime.
- Security baseline.

## 20.2 P1

```txt
P1:
- analytics dashboard
- recommended assignees
- AI quality review UI
- billing
- mobile native
```

## 20.3 Out of MVP

```txt
Out of MVP:
- billing
- SSO
- MFA
- native mobile
- analytics dashboard avancé
- advanced AI review UI
- recommended assignees
- presence/typing/read receipts
- full admin product console
- direct-to-S3 upload
```

## 20.4 Billing

```txt
Billing excluded MVP.
Keep architecture compatible with establishment-level billing later.
```

---

# 21. Acceptance criteria globaux

## 21.1 Operational loop

```txt
A user can submit an Observation.
System creates/aggregates Signal.
Manager creates Action.
Staff executes Action.
Manager validates.
Feeds update.
```

## 21.2 AI

```txt
AI acceptance:
- valid JSON schema
- backend validates domains
- max 5 candidates
- create/aggregate/no_signal_created outcomes work
```

## 21.3 RBAC

```txt
RBAC acceptance:
API and realtime never expose data outside authorized scope.
```

## 21.4 Mobile

```txt
Mobile acceptance:
Core flows usable on smartphone viewport.
```

## 21.5 Offline

```txt
Offline MVP:
local Observation draft only.
Submit requires online.
```

## 21.6 Realtime

```txt
Realtime acceptance:
visible feed/detail updates after relevant event without manual refresh.
```

## 21.7 Notifications

```txt
Notification acceptance:
P0 in-app notifications appear for ActionAssigned, pending validation, mentions, important Signal events.
```

## 21.8 Media

```txt
Media acceptance:
- max 3 photos
- no photo-only Observation
- audio deleted after transcription
- signed URLs authorized
- cleanup jobs work
```

## 21.9 Security

```txt
Security acceptance:
- no secrets in repo
- token auth works
- RBAC tested
- no raw Observation in product API/realtime/notifications
```

## 21.10 OpenAPI

```txt
OpenAPI acceptance:
JSON APIs are OpenAPI-documented; generated TypeScript client is optional for targeted consumers.
```

---

# 22. Backlog structure

## 22.1 Format

```txt
Epic
→ Slice
→ Ticket
→ Acceptance criteria
→ Dependencies
→ Tests
```

## 22.2 Ticket size

```txt
Ticket size target:
small enough to review diff safely.
```

## 22.3 Ticket template

```txt
Ticket title:
Context:
Scope:
Out of scope:
Dependencies:
Implementation notes:
Acceptance criteria:
Tests:
Security/RBAC checks:
OpenAPI impact:
```

---

# 23. Suggested epics and slices

## Epic 0 — Foundations

Slices:
- Project bootstrap.
- Base models and settings.
- Auth identities.
- Organizations/Establishments.
- Memberships/RBAC.
- OpenAPI base.

## Epic 1 — Runtime config / Onboarding

Slices:
- Organization/Establishment creation.
- Runtime modules/domains/units.
- Knowledge items.
- Onboarding session.
- Initial user invitation.
- Establishment activation.

## Epic 2 — Observation / Upload / Transcription

Slices:
- Observation submit text.
- Temporary uploads.
- Photo lifecycle.
- Audio transcription.
- ObservationProcessing queue.
- Cleanup jobs.

## Epic 3 — AI Pipeline / Signals

Slices:
- AI schemas.
- Fake provider.
- Pipeline task.
- Signal create.
- Signal aggregate.
- Signal Feed.
- Signal detail.

## Epic 4 — Actions / Execution Feed

Slices:
- Action create from Signal.
- Assignment.
- Accept / mark done.
- Validation / reopen.
- Cancel.
- Execution Feed Actions.

## Epic 5 — Checklists

Slices:
- Shared Checklist templates.
- Shared Checklist executions.
- Personal Checklists.
- Task execution.
- Task → Observation.

## Epic 6 — Notifications / Realtime

Slices:
- ApplicationEvents consumers.
- Notification Matrix MVP.
- Notification Center.
- Django Channels setup.
- Feed invalidation.
- Detail invalidation.

## Epic 7 — Hardening / Pilot

Slices:
- Security baseline.
- Retention/cleanup.
- Logs/monitoring.
- Mobile QA.
- Pilot seed.
- Pilot protocol.

---

# 24. Critical dependencies

## 24.1 Dependency #1

```txt
Critical dependency #1 = Auth + EstablishmentMembership + permissions.
```

## 24.2 Feeds

```txt
Feeds require:
- operational domains
- membership domains
- signal detected domains
- last_activity_at
```

## 24.3 Actions

```txt
Actions depend on:
Signal Domain
Accounts/Memberships
RBAC
```

## 24.4 Checklists

```txt
Checklists depend on:
Users
Operational domains
Execution Feed
Observation submit for task-generated Observations
```

## 24.5 Notifications

```txt
Notifications depend on:
ApplicationEvents
Notification Matrix
Recipients/users
```

---

# 25. Risk register

## 25.1 Risk — MVP too wide

```txt
Main risk = MVP too wide.
Mitigation = strict P0 loop and phase gates.
```

## 25.2 Risk — data visibility bugs

```txt
Risk = data visibility bugs.
Mitigation = permission tests + feed tests + realtime authorization tests.
```

## 25.3 Risk — AI instability

```txt
Risk = AI output instability.
Mitigation = strict Pydantic schemas + fake provider + backend validation.
```

## 25.4 Risk — field UX friction

```txt
Risk = field UX friction.
Mitigation = mobile-first flows + reduce clicks + pilot scripts.
```

---

# 26. Pilot validation — Mama Shelter Nice

## 26.1 Scripted scenarios

```txt
Pilot validation uses scripted scenarios:
- room issue
- maintenance issue
- restaurant rush issue
- lost/found or guest issue
- checklist round
```

## 26.2 Pilot metrics

```txt
Pilot metrics:
- Observations submitted/day
- Signals created vs aggregated
- no_signal_created rate
- Actions created
- Actions completed/validated
- time from Observation to Action
- checklist completion rate
- user adoption by role
- manager corrections of domains
```

## 26.3 Pilot protocol

```txt
Create pilot protocol:
- users involved
- scenarios
- duration
- success metrics
- feedback questions
- incident support path
```

---

# 27. Phase gates

## 27.1 Gate Phase 0

Can move to Phase 1 only if:
- auth works ;
- memberships work ;
- permissions tested ;
- OpenAPI base generated ;
- CI passes.

## 27.2 Gate Phase 1

Can move to Phase 2 only if:
- Mama Shelter runtime seed exists ;
- operational domains assigned ;
- initial users invited/activated ;
- establishment active.

## 27.3 Gate Phase 2

Can move to Phase 3 only if:
- Observation submit works ;
- upload lifecycle works ;
- transcription works/fallback text works ;
- no raw Observation leaked ;
- ObservationProcessing queued.

## 27.4 Gate Phase 3

Can move to Phase 4 only if:
- fake AI pipeline creates/aggregates Signals ;
- Signal Feed works ;
- Signal detail works ;
- RBAC feed tests pass.

## 27.5 Gate Phase 4

Can move to Phase 5 only if:
- Action lifecycle complete ;
- Execution Feed Actions works ;
- validations/reopen/cancel tested ;
- Signal status transitions work.

## 27.6 Gate Phase 5

Can move to Phase 6 only if:
- Shared and Personal Checklists work ;
- Notification Center works ;
- realtime invalidation works ;
- unauthorized realtime tests pass.

## 27.7 Gate Phase 6

Pilot-ready only if:
- mobile QA passes ;
- cleanup jobs pass ;
- backup/restore smoke test complete ;
- logs/security checks pass ;
- pilot protocol ready.

---

# 28. Non-negotiables

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
```

---

# 29. Decisions index

| Décision | Statut |
|---|---:|
| Build Plan defines order/milestones/tickets/acceptance/risks | Validé |
| MVP objective complete field workflow | Validé |
| Pilot MVP Mama Shelter Nice | Validé |
| Build by vertical slices | Validé |
| Slice 0 Foundations | Validé |
| Minimal mobile-first UI kit | Validé |
| Fake deterministic AI provider first | Validé |
| Real provider behind same interface | Validé |
| OpenAPI from day 1 | Validé |
| Frontend uses Django Templates + HTMX for MVP | Validé |
| Test priority services/permissions/API/feeds/AI/realtime | Validé |
| Ticket done definition | Validé |
| 7 phases 0–6 | Validé |
| Phase 0 Foundations | Validé |
| Phase 1 Runtime config/onboarding | Validé |
| Phase 2 Observation/upload/transcription | Validé |
| Phase 3 AI pipeline/Signal Feed | Validé |
| Phase 4 Actions/Execution Feed | Validé |
| Phase 5 Checklists/Notifications/Realtime | Validé |
| Phase 6 Hardening/pilot readiness | Validé |
| P0 operational loop | Validé |
| P1 list | Validé |
| Checklists P0 after Actions | Validé |
| Photos P0 optional | Validé |
| Photo-only forbidden | Validé |
| Audio transcription P0, fallback text | Validé |
| Realtime P0 minimal invalidation/refetch | Validé |
| Presence/typing/read receipts excluded | Validé |
| In-app notifications P0 | Validé |
| Push optional P0.5/P1 | Validé |
| Milestone 0.1 | Validé |
| CI MVP | Validé |
| Mama Shelter seed after Phase 1 | Validé |
| TypeScript used only for targeted frontend modules | Validé |
| OpenAPI generated from day 1 for JSON APIs | Validé |
| Generated TypeScript client optional for targeted consumers | Validé |
| Frontend starts with server-rendered screens from Phase 0/1 | Validé |
| JSON API mocks only from OpenAPI schemas if needed | Validé |
| Critical dependency Auth + Membership + permissions | Validé |
| Feed dependencies validées | Validé |
| Action dependencies validées | Validé |
| Checklist dependencies validées | Validé |
| Notification dependencies validées | Validé |
| Out of MVP list validée | Validé |
| Nancy post-stabilization | Validé |
| Billing excluded MVP | Validé |
| Acceptance #1 operational loop | Validé |
| AI acceptance criteria | Validé |
| RBAC acceptance criteria | Validé |
| Mobile acceptance criteria | Validé |
| Offline local draft only | Validé |
| Realtime acceptance criteria | Validé |
| Notification acceptance criteria | Validé |
| Media acceptance criteria | Validé |
| Security acceptance criteria | Validé |
| OpenAPI acceptance criteria | Validé |
| Backlog format | Validé |
| Ticket size reviewable | Validé |
| Strict phase order, flexible inside phase | Validé |
| Migrations per domain slice | Validé |
| Main risks and mitigations | Validé |
| Pilot scenarios | Validé |
| Pilot metrics | Validé |
| Pilot protocol | Validé |
| Final principle | Validé |

---

# 30. Recommandation finale

Le MVP Build Plan est validé pour démarrer le build.

Décision centrale :

```txt
Build the smallest complete operational loop.
Harden it for pilot.
Then expand.
```

Ordre à respecter :

```txt
0. Foundations
1. Runtime config + onboarding minimal
2. Observation + upload + transcription
3. AI pipeline + Signal Feed
4. Actions + Execution Feed
5. Checklists + Notifications + Realtime
6. Hardening + pilot readiness
```

Le premier objectif opérationnel n’est pas de tout construire.

Le premier objectif est :

```txt
A user submits an Observation.
A Signal appears.
A Manager creates an Action.
A Staff member executes it.
A Manager validates it.
Feeds update correctly.
```
