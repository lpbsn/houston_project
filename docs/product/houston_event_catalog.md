# Houston — Event Catalog / Event System

**Version:** v0.1  
**Date:** 2026-05-23  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — Event log, event catalog, consumers, realtime/audit/analytics foundation  
**Source d’arbitrage:** réponses utilisateur du fichier `Texte collé(12).txt`

**Documents liés :**
- `Houston_onboarding_domain.md`
- `Houston_observation_domain.md`
- `Houston_signal_domain.md`
- `Houston_action_domain.md`
- `Houston_checklist_domain.md`
- `Houston_ai_overview.md`
- `Houston_ai_observation_pipeline_contract.md`
- `Houston_ai_transcription_contract.md`
- `Houston_ai_onboarding_contract.md`
- `Houston_rbac_permissions_domain.md`

---

# 1. Objectif du document

Ce document formalise le **Event Catalog / Event System** de Houston pour le MVP.

Il définit :
- la définition d’un event ;
- la différence Event / Notification / Audit Log ;
- la stratégie de persistance ;
- le modèle append-only ;
- le format d’enveloppe standard ;
- les règles de correlation / causation / idempotence ;
- la structure des tables `application_events` et `event_deliveries` ;
- les consumers MVP ;
- les règles realtime ;
- les règles audit ;
- les règles de payload minimal ;
- les listes d’events validées par domaine ;
- les services backend recommandés ;
- les tests fonctionnels attendus.

Ce document est transverse. Il sert de base pour :
- Notification Matrix ;
- Realtime Broadcaster ;
- Audit ;
- Analytics ;
- AI Metrics ;
- debugging des workflows asynchrones.

---

# 2. Définition

## 2.1 Définition d’un event

Un event est une trace immuable d’un fait significatif du système.

```txt
Event = trace immuable d’un fait significatif du système.
```

Un event décrit quelque chose qui s’est produit.

Exemples :
- `SignalCreated`
- `ActionValidated`
- `ChecklistExecutionCompleted`
- `AIRequestFailed`
- `MembershipDomainsChanged`

## 2.2 Ce qu’un event n’est pas

Un event n’est pas :
- une notification utilisateur ;
- un log technique brut ;
- une commande ;
- une mutation directe ;
- une source of truth unique ;
- un websocket message complet.

---

# 3. Event ≠ Notification

## 3.1 Décision

```txt
Event ≠ Notification.
```

```txt
Event = fait système.
Notification = message utilisateur décidé par Notification Matrix.
```

## 3.2 Principe

Un event peut déclencher une notification, mais tous les events ne notifient pas.

```txt
Event emitted
        ↓
NotificationDispatcher evaluates Notification Matrix
        ↓
Notification created or not
```

## 3.3 Pourquoi

Séparer Event et Notification évite :
- de notifier trop souvent ;
- de coupler les services métier aux messages utilisateurs ;
- de rendre les règles de notification impossibles à maintenir ;
- de mélanger fait système et décision UX.

---

# 4. Event ≠ Audit Log

## 4.1 Décision

Event et Audit Log ne sont pas la même chose.

```txt
Certains events métier alimentent l’audit.
Audit Log peut être une projection des events importants.
```

## 4.2 Principe

L’Event Log enregistre les faits.  
L’Audit Log expose ou projette les faits sensibles.

Exemples d’events auditables :
- `MembershipRoleChanged`
- `MembershipDomainsChanged`
- `SignalDomainAdded`
- `SignalResolved`
- `ActionValidated`
- `ActionCanceled`
- `EstablishmentActivated`

---

# 5. Source of truth

## 5.1 Décision

```txt
Tables métier = source of truth.
Events = trace, triggers, analytics, audit.
```

## 5.2 Pas d’Event Sourcing complet MVP

Le MVP n’utilise pas d’Event Sourcing complet.

```txt
MVP = Event Log append-only.
Pas d’Event Sourcing complet.
```

## 5.3 Implication

Les états métier sont lus depuis les tables métier :
- `signals`
- `actions`
- `checklist_executions`
- `observations`
- `memberships`
- etc.

Les events servent à :
- tracer ;
- déclencher des consumers ;
- alimenter analytics ;
- alimenter audit ;
- alimenter realtime ;
- faciliter debug.

---

# 6. Persistance des events

## 6.1 Décision

Persister les events métier et techniques importants.

```txt
Persist important business and technical events.
```

## 6.2 Events append-only

```txt
Events append-only.
Pas d’update métier.
Pas de delete utilisateur.
```

## 6.3 Suppression

Pas de suppression utilisateur.

Une purge technique peut exister selon règles de rétention.

---

# 7. Catégories d’events

## 7.1 Catégories validées

```txt
Event categories:
├── business
├── technical
├── ai
├── audit
└── system
```

## 7.2 Usage

| Category | Usage |
|---|---|
| `business` | changement métier produit |
| `technical` | état technique significatif |
| `ai` | appel IA / retry / failure |
| `audit` | décision sensible / gouvernance |
| `system` | action automatique système |

Un event peut avoir une catégorie principale.  
Les projections audit peuvent sélectionner certains events `business` ou `system`.

---

# 8. Naming convention

## 8.1 Format

```txt
EventType = PascalCase
Format = Subject + PastAction
```

Exemples :

```txt
SignalCreated
ActionValidated
ChecklistExecutionCompleted
```

## 8.2 Pas de préfixe domaine dans event_type

Décision :

```txt
event_type = SignalCreated
subject_type = Signal
category = business
```

Ne pas faire :

```txt
Signal.SignalCreated
signal.created
```

## 8.3 Pourquoi

Le type reste lisible et stable.  
Le domaine est porté par :
- `subject_type`
- `category`
- éventuellement le payload.

---

# 9. Event envelope standard

## 9.1 Envelope validée

```txt
Event envelope standard:
├── id
├── event_type
├── category
├── organization_id
├── establishment_id
├── actor_id
├── subject_type
├── subject_id
├── correlation_id
├── causation_id
├── idempotency_key
├── payload
└── occurred_at
```

## 9.2 Champs d’acteur

```txt
actor_id nullable
actor_type = user/system/ai optional
```

Pourquoi nullable :
- jobs automatiques ;
- système ;
- IA ;
- cleanup ;
- scheduler.

## 9.3 Champs tenant

```txt
establishment_id required when event belongs to an establishment.
Nullable only for global/pre-establishment events.
```

```txt
organization_id required when available.
```

## 9.4 Subject

```txt
subject_type et subject_id obligatoires.
```

Pour global events :

```txt
subject = Organization ou OnboardingSession
```

---

# 10. Correlation, causation, idempotence

## 10.1 correlation_id

Décision :

```txt
correlation_id obligatoire pour tous les events.
```

Exemple :

```txt
ObservationCreated
→ AIRequestStarted
→ SignalCreated
→ NotificationQueued
```

Tous ces events partagent un même `correlation_id`.

## 10.2 causation_id

Décision :

```txt
causation_id nullable mais supporté MVP.
```

`causation_id` permet de savoir quel event a causé l’event courant.

Exemple :

```txt
AIRequestSucceeded.causation_id = AIRequestStarted.id
SignalCreated.causation_id = ObservationProcessingSucceeded.id
```

## 10.3 idempotency_key

Décision :

```txt
idempotency_key obligatoire pour events émis par jobs/services critiques.
```

Objectif :
- éviter doublons sur retry ;
- éviter double notification ;
- éviter double broadcast ;
- éviter double projection analytics/audit.

---

# 11. Rétention

## 11.1 Rétention MVP

```txt
Retention MVP:
├── business/audit events: 24 mois
├── technical/AI events: 6 mois
├── transient delivery logs: 30 jours
```

## 11.2 À challenger

Ces durées sont à challenger plus tard avec :
- RGPD ;
- politique client ;
- exigences légales ;
- coûts de stockage ;
- support/debug réel.

---

# 12. Payload rules

## 12.1 Payload minimal

Décision :

```txt
Payload minimal.
Pas de photos, audio, texte Observation brut, secrets, emails si inutile.
```

## 12.2 No Observation.raw_text

Décision :

```txt
No Observation.raw_text in event payload.
Use observation_id only.
```

## 12.3 No comment body

Décision :

```txt
Comment events contain comment_id, not full body.
Frontend refetches if authorized.
```

## 12.4 before/after

`before/after` dans payload uniquement pour modifications structurantes.

Cas validés :
- domain added/removed ;
- role/membership changes ;
- status changes ;
- assignment/reassignment ;
- due_at changes.

Exemple :

```json
{
  "before": {
    "status": "open"
  },
  "after": {
    "status": "in_progress"
  }
}
```

---

# 13. Event versioning

## 13.1 Décision

```txt
event_version integer, default 1.
```

## 13.2 Pourquoi

Les payloads vont évoluer.  
`event_version` permet :
- migrations progressives ;
- consumers compatibles ;
- debug ;
- stabilité API interne.

---

# 14. Realtime

## 14.1 Principe

Les services métier ne broadcastent pas directement.

```txt
Event emitted
        ↓
RealtimeBroadcaster decides websocket broadcasts
```

## 14.2 Websocket payload minimal

```txt
Websocket payload minimal:
├── event_type
├── subject_type
├── subject_id
├── feed_target
├── timestamp
└── optional summary
```

## 14.3 Refetch frontend

Décision :

```txt
Realtime event indique qu’un changement existe.
Frontend refetch si besoin.
```

Le websocket ne transporte pas toutes les données métier.

## 14.4 Pourquoi

Cela évite :
- fuite de données ;
- payloads trop lourds ;
- divergence frontend/backend ;
- contournement des permissions ;
- complexité d’autorisation côté websocket.

---

# 15. Consumers MVP

## 15.1 Consumers validés

```txt
Event consumers MVP:
├── NotificationDispatcher
├── RealtimeBroadcaster
├── AuditProjector
├── AnalyticsProjector
└── AIMetricsProjector
```

## 15.2 NotificationDispatcher

Évalue la Notification Matrix.

## 15.3 RealtimeBroadcaster

Décide les broadcasts websocket.

## 15.4 AuditProjector

Projette certains events sensibles dans l’audit.

## 15.5 AnalyticsProjector

Alimente les métriques produit.

## 15.6 AIMetricsProjector

Alimente les métriques IA.

---

# 16. Delivery model

## 16.1 Décision

```txt
Persist event during business transaction.
Process consumers async after commit.
```

## 16.2 Consumer failure

Un échec consumer ne rollback pas l’action métier.

```txt
Business transaction persists event.
Consumers async failures do not rollback business action.
```

## 16.3 Failure handling

```txt
Consumer failure:
├── retry limited
├── status failed
├── last_error stored
└── admin/support visible
```

---

# 17. Architecture MVP

## 17.1 Pas Kafka MVP

Décision :

```txt
MVP : application_events table + background jobs.
Pas Kafka MVP.
```

## 17.2 Table unique

```txt
application_events unique table.
```

## 17.3 Event deliveries

`application_events` est l’event log.  
`event_deliveries` suit le processing des consumers.

```txt
application_events = event log.
event_deliveries = tracking consumer processing.
```

---

# 18. Data model recommandé

## 18.1 application_events

```txt
application_events
├── id UUID
├── event_type string
├── event_version integer default 1
├── category string
├── organization_id UUID nullable
├── establishment_id UUID nullable
├── actor_id UUID nullable
├── actor_type string nullable
├── subject_type string
├── subject_id UUID
├── correlation_id UUID
├── causation_id UUID nullable
├── idempotency_key string nullable
├── payload jsonb
├── occurred_at datetime
├── created_at datetime
└── processed_at datetime nullable
```

## 18.2 Note sur processed_at

`processed_at` dans `application_events` est nullable.

Alerte technique :
- un event peut avoir plusieurs consumers ;
- un seul `processed_at` global est ambigu ;
- le suivi réel du processing doit passer par `event_deliveries`.

Recommandation :

```txt
application_events.processed_at = optional legacy/global marker.
event_deliveries = source of truth for consumer processing.
```

## 18.3 event_deliveries

```txt
event_deliveries
├── id UUID
├── application_event_id UUID
├── consumer_name string
├── status string
├── attempts integer
├── last_error text nullable
├── processed_at datetime nullable
└── created_at datetime
```

## 18.4 Indexes recommandés

```txt
index application_events on event_type
index application_events on category
index application_events on establishment_id
index application_events on organization_id
index application_events on subject_type, subject_id
index application_events on correlation_id
index application_events on causation_id
unique index application_events on idempotency_key where idempotency_key is not null
index event_deliveries on application_event_id
index event_deliveries on consumer_name, status
```

---

# 19. Event Registry code

## 19.1 Décision

```txt
Events::Types constants
Events::Schemas optional lightweight validation
```

## 19.2 Pourquoi

Évite :
- typos ;
- payloads incohérents ;
- event types divergents ;
- consumers fragiles.

## 19.3 Services recommandés

```txt
Events::Publish
Events::DispatchJob
Events::Consumers::NotificationDispatcher
Events::Consumers::RealtimeBroadcaster
Events::Consumers::AuditProjector
Events::Consumers::AnalyticsProjector
```

---

# 20. Events Onboarding

## 20.1 Liste validée

```txt
OrganizationCreated
EstablishmentCreated
OnboardingStarted
EstablishmentDescriptionSubmitted
OnboardingAIInterpretationStarted
OnboardingAIInterpretationSucceeded
OnboardingAIInterpretationFailed
OperationalModulesProposed
OperationalDomainsProposed
OperationalUnitsProposed
RuntimeVocabularyProposed
RuntimeTagsProposed
RoutingHintsProposed
OnboardingProposalValidated
OperationalModuleActivated
OperationalDomainActivated
OperationalUnitActivated
RuntimeVocabularyActivated
EstablishmentActivated
InitialUserInvited
MembershipActivated
```

---

# 21. Events Observation

```txt
ObservationCreated
ObservationMediaLinked
ObservationQueuedForAI
ObservationProcessingStarted
ObservationProcessingSucceeded
ObservationProcessingFailed
ObservationLinkedToSignal
ObservationMarkedNotActionable
```

---

# 22. Events Signal

```txt
SignalCreated
SignalAggregated
SignalStatusChanged
SignalDomainAdded
SignalDomainRemoved
SignalUrgencyChanged
SignalPinned
SignalUnpinned
SignalResolved
SignalCanceled
SignalArchived
SignalCommentAdded
```

---

# 23. Events Action

## 23.1 Liste validée MVP

```txt
ActionCreated
ActionAssigned
ActionReassigned
ActionAccepted
ActionMarkedDone
ActionPendingValidation
ActionValidated
ActionReopened
ActionCanceled
ActionDueDateChanged
ActionOverdue
ActionNoAcceptanceDetected
ActionCommentAdded
```

## 23.2 Events exclus MVP

`ActionPriorityChanged` est exclu du MVP car la priorité Action est dérivée de `Signal.urgency`.

`ActionProofAdded` n’est pas retenu dans la liste finale MVP Event Catalog.

---

# 24. Events Checklist

```txt
ChecklistTemplateCreated
ChecklistTemplateActivated
ChecklistTemplateArchived
ChecklistExecutionCreated
ChecklistExecutionAssigned
ChecklistExecutionStarted
ChecklistTaskCompleted
ChecklistTaskSkipped
ChecklistTaskObservationCreated
ChecklistExecutionCompleted
ChecklistExecutionCanceled
PersonalChecklistTemplateCreated
PersonalChecklistExecutionStarted
PersonalChecklistExecutionCompleted
```

---

# 25. Events AI / Transcription

```txt
AIRequestStarted
AIRequestSucceeded
AIRequestFailed
AIRequestRetried
TranscriptionStarted
TranscriptionSucceeded
TranscriptionFailed
TranscriptionAudioDeleted
```

---

# 26. Events RBAC / Membership

```txt
UserInvited
MembershipCreated
MembershipActivated
MembershipDeactivated
MembershipRoleChanged
MembershipDomainsChanged
```

---

# 27. Events Media / Upload placeholders

## 27.1 Liste validée

```txt
MediaUploaded
MediaLinkedToObservation
MediaDeleted
TemporaryAudioUploaded
TemporaryAudioDeleted
OrphanMediaCleaned
```

## 27.2 Attention

À aligner avec le futur document :

```txt
Houston_upload_media_lifecycle.md
```

---

# 28. Events Notification placeholders

```txt
NotificationQueued
NotificationSent
NotificationFailed
```

## 28.1 Note

`NotificationRead` n’est pas retenu dans la liste finale MVP fournie.

Les détails seront cadrés dans :

```txt
Houston_notification_matrix.md
```

---

# 29. Realtime-triggering events

## 29.1 Principe

Realtime uniquement pour events qui changent la vue utilisateur.

```txt
Realtime-triggering events limited to view-changing events.
```

## 29.2 Liste MVP

```txt
SignalCreated
SignalAggregated
SignalStatusChanged
SignalDomainAdded
SignalDomainRemoved
SignalUrgencyChanged
SignalPinned
SignalUnpinned
ActionCreated
ActionAssigned
ActionReassigned
ActionAccepted
ActionPendingValidation
ActionValidated
ActionReopened
ActionCanceled
ChecklistExecutionAssigned
ChecklistExecutionStarted
ChecklistExecutionCompleted
ChecklistExecutionCanceled
```

---

# 30. Strong audit events

## 30.1 Liste validée

```txt
MembershipRoleChanged
MembershipDomainsChanged
SignalDomainAdded
SignalDomainRemoved
SignalUrgencyChanged
SignalResolved
SignalCanceled
ActionReassigned
ActionValidated
ActionCanceled
ChecklistExecutionCanceled
EstablishmentActivated
```

## 30.2 Pourquoi

Ces events représentent :
- changements de permissions ;
- changements de périmètre de visibilité/action ;
- décisions opérationnelles sensibles ;
- validation ou annulation ;
- activation établissement.

---

# 31. Comments and mentions

## 31.1 Comments added = events

Décision :

```txt
Comments added = events.
```

Events :
- `SignalCommentAdded`
- `ActionCommentAdded`

## 31.2 Mentions

Les mentions seront traitées par Notification Matrix.

```txt
Mentions seront traitées par Notification Matrix.
```

## 31.3 Payload comments

Ne pas mettre le corps du commentaire dans l’event.

```txt
Comment events contain comment_id, not full body.
Frontend refetches if authorized.
```

---

# 32. Security / privacy rules

## 32.1 Payload minimal

```txt
Payload minimal.
Pas de photos, audio, texte Observation brut, secrets, emails si inutile.
```

## 32.2 Observation raw text

```txt
No Observation.raw_text in event payload.
Use observation_id only.
```

## 32.3 Comments

```txt
No comment body in event payload.
Use comment_id only.
```

## 32.4 Frontend access

Frontend reçoit un payload minimal et refetch les données autorisées.

---

# 33. Tests fonctionnels MVP

## 33.1 Chaque service métier critique teste les events

```txt
Chaque service métier critique teste:
- DB state
- event emitted
- event payload minimal
```

## 33.2 Exemple SignalCreated

```txt
Given valid Observation processing output
When backend creates a Signal
Then Signal exists in DB
And SignalCreated event exists
And event payload contains signal_id, establishment_id, correlation_id
And event payload does not contain Observation.raw_text
```

## 33.3 Exemple ActionValidated

```txt
Given pending_validation Action
When Manager validates Action
Then Action status becomes done
And ActionValidated event exists
And payload includes actor_id, action_id, before/after status
```

## 33.4 Exemple consumer failure

```txt
Given event created
And NotificationDispatcher fails
When delivery is processed
Then business object remains persisted
And event_delivery status becomes failed
And last_error is stored
```

## 33.5 Exemple idempotency

```txt
Given same idempotency_key
When critical job retries event publish
Then duplicate application_event is not created
```

---

# 34. Décisions validées — index

| Décision | Statut |
|---|---:|
| Event = trace immuable d’un fait significatif | Validé |
| Event ≠ Notification | Validé |
| Event ≠ Audit Log | Validé |
| Certains events alimentent audit | Validé |
| Persister events métier/techniques importants | Validé |
| Event Log append-only | Validé |
| Pas d’Event Sourcing complet MVP | Validé |
| Tables métier = source of truth | Validé |
| Categories business/technical/ai/audit/system | Validé |
| Naming PascalCase SubjectPastAction | Validé |
| Pas de préfixe domaine dans event_type | Validé |
| Event envelope standard | Validé |
| actor_id nullable | Validé |
| actor_type optional | Validé |
| establishment_id requis sauf global/pre-establishment | Validé |
| organization_id requis si disponible | Validé |
| correlation_id obligatoire | Validé |
| causation_id nullable supporté | Validé |
| idempotency_key requis pour jobs/services critiques | Validé |
| Events append-only | Validé |
| Pas de delete utilisateur | Validé |
| Rétention configurable par catégorie | Validé |
| Retention MVP business/audit 24 mois | Validé |
| Retention technical/AI 6 mois | Validé |
| Retention delivery logs 30 jours | Validé |
| before/after seulement modifications structurantes | Validé |
| AI events séparés | Validé |
| Events → NotificationDispatcher | Validé |
| Events → RealtimeBroadcaster | Validé |
| Websocket payload minimal | Validé |
| Frontend refetch détails | Validé |
| Consumers MVP validés | Validé |
| Persist event in transaction | Validé |
| Consumers async after commit | Validé |
| application_events + jobs, pas Kafka MVP | Validé |
| Table unique application_events | Validé |
| event_deliveries pour consumer processing | Validé |
| subject_type/subject_id obligatoires | Validé |
| Subject columns + indexes | Validé |
| Event lists par domaine validées | Validé |
| ActionPriorityChanged exclu MVP | Validé |
| NotificationRead exclu liste finale MVP | Validé |
| Realtime events limités aux changements de vue | Validé |
| Strong audit events validés | Validé |
| Comments added = events | Validé |
| Mentions traitées par Notification Matrix | Validé |
| Payload minimal sans données sensibles | Validé |
| No Observation.raw_text in payload | Validé |
| No comment body in payload | Validé |
| event_version default 1 | Validé |
| Events::Types constants | Validé |
| Events::Schemas optional | Validé |
| Services backend Events validés | Validé |
| Consumer failure ne rollback pas métier | Validé |
| Retry limited + failed visible admin/support | Validé |
| Tests DB state + event emitted + minimal payload | Validé |

---

# 35. Points à traiter dans d’autres documents

## 35.1 Notification Matrix

À cadrer :
- quels events déclenchent notification ;
- qui reçoit quoi ;
- canal push/email/in-app ;
- anti-spam ;
- mentions ;
- NotificationQueued/Sent/Failed payloads.

## 35.2 Upload / Media Lifecycle

À cadrer :
- media upload ;
- temporary upload ;
- cleanup ;
- retention ;
- signed URLs ;
- image/audio deletion events.

## 35.3 Security / RGPD

À cadrer :
- rétention event définitive ;
- payload minimization ;
- audit access ;
- export/suppression ;
- privacy by design.

## 35.4 Technical Architecture

À cadrer :
- choix jobs ;
- queues ;
- transaction after_commit ;
- retries ;
- monitoring ;
- admin support screens.

---

# 36. Recommandation finale

Le Event Catalog est suffisamment cadré pour le MVP.

Décision centrale :

```txt
Tables métier = source of truth.
Events = append-only traces, triggers, audit and analytics foundation.
```

Le build doit maintenant s’appuyer sur :
- `application_events` table ;
- `event_deliveries` table ;
- `Events::Publish` ;
- consumers async after commit ;
- payload minimal ;
- correlation_id obligatoire ;
- idempotency for critical jobs ;
- event registry constants ;
- tests d’émission event sur services critiques.

La prochaine étape logique est :

```txt
Houston_notification_matrix.md
```

car les notifications doivent maintenant s’appuyer sur les events validés.
