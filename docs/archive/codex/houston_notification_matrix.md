# Houston — Notification Matrix

**Version:** v0.1  
**Date:** 2026-05-23  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — notifications in-app, push, recipients, channels, priorities  
**Source d’arbitrage:** réponses utilisateur du fichier `Texte collé(14).txt`

**Documents liés :**
- `Houston_event_catalog.md`
- `Houston_rbac_permissions_domain.md`
- `Houston_signal_domain.md`
- `Houston_action_domain.md`
- `Houston_checklist_domain.md`
- `Houston_observation_domain.md`
- `Houston_ai_overview.md`
- `Houston_ai_observation_pipeline_contract.md`
- `Houston_ai_transcription_contract.md`
- `Houston_ai_onboarding_contract.md`

---

# 1. Objectif du document

Ce document formalise la **Notification Matrix** de Houston pour le MVP.

Il définit :
- ce qu’est une notification ;
- la différence Event / Notification ;
- les canaux MVP ;
- les règles de destinataires ;
- les règles de priorité ;
- les règles de payload ;
- les règles RBAC / visibilité ;
- la déduplication ;
- les statuts ;
- les deliveries par canal ;
- les règles par event ;
- le modèle de données ;
- les services backend recommandés ;
- les tests fonctionnels attendus.

Ce document s’appuie sur le principe validé dans l’Event Catalog :

```txt
Event = fait système.
Notification = message utilisateur décidé par Notification Matrix.
```

---

# 2. Principe central

```txt
Notify only when attention or action is required.
Realtime/feed handles visibility.
```

En français :

```txt
Notifier uniquement quand l’attention ou l’action de l’utilisateur est requise.
Le feed et le realtime gèrent la visibilité.
```

Conséquence : tout ce qui change dans l’application ne mérite pas une notification.

---

# 3. Définition d’une notification

## 3.1 Définition

Une notification est un message utilisateur généré à partir d’un event selon une matrice de règles.

```txt
Notification = message utilisateur généré à partir d’un event selon une matrice de règles.
```

## 3.2 Event → Notification

Un event peut déclencher :

```txt
0 notification
1 notification
N notifications
```

selon Notification Matrix.

## 3.3 Flow standard

```txt
Event
        ↓
NotificationDispatcher
        ↓
NotificationMatrix
        ↓
RecipientResolver
        ↓
Notification created
        ↓
NotificationDelivery per channel
```

---

# 4. Canaux de notification

## 4.1 Canaux MVP

```txt
MVP:
├── in_app
├── email
└── push
```

## 4.3 Email MVP limité

Email MVP uniquement pour :

```txt
invitation utilisateur
activation compte
cas système critiques si nécessaire
```

## 4.4 Pourquoi limiter l’email

L’email est utile pour l’accès et les cas critiques, mais mauvais pour le pilotage opérationnel temps réel :
- bruit ;
- lenteur ;
- risque spam ;
- coût ;
- faible pertinence terrain.

---

# 5. Notification object vs Delivery

## 5.1 Notification métier

La notification est un objet métier.

```txt
Notification = objet métier.
```

Elle est persistée pour l’in-app / Notification Center.

## 5.2 NotificationDelivery

```txt
NotificationDelivery = tentative par canal.
```

Une notification peut avoir plusieurs deliveries :
- in_app ;
- push ;
- email si applicable.

## 5.3 Pourquoi séparer

Séparer notification et delivery permet :
- d’avoir une inbox stable ;
- de tracer les push failed ;
- de retenter un canal sans recréer la notification ;
- de différencier statut utilisateur et statut provider.

---

# 6. Persistance et Notification Center

## 6.1 In-app persisté

```txt
Notifications in-app persistées.
```

## 6.2 Notification Center MVP

```txt
MVP: Notification Center simple.
```

Fonctions MVP :
- voir les notifications ;
- distinguer unread/read ;
- archiver ;
- cliquer vers le subject autorisé.

## 6.3 Pas de hard delete utilisateur

```txt
User can mark read/archive.
No hard delete MVP.
```

---

# 7. Statuts

## 7.1 Notification statuses

```txt
Notification statuses:
├── unread
├── read
└── archived
```

## 7.2 Pas de dismissed MVP

```txt
Pas de dismissed MVP.
Utiliser archived si l’utilisateur veut masquer.
```

## 7.3 Delivery statuses

```txt
Delivery statuses:
├── queued
├── sent
├── delivered
├── failed
└── skipped
```

---

# 8. RBAC / visibilité

## 8.1 Vérification obligatoire

Avant notification, le backend vérifie visibilité/RBAC du recipient.

```txt
Before notification, backend checks recipient visibility/RBAC.
```

## 8.2 Notification ≠ permission

```txt
Notification ≠ permission.
La notification ne donne jamais accès.
```

## 8.3 Mentions

```txt
@mention → notification ciblée.
@mention ne donne pas de permission.
```

Si l’utilisateur mentionné n’a pas accès au subject, la notification ne doit pas lui donner l’accès.

---

# 9. Payload notification

## 9.1 Payload minimal

```txt
Payload minimal:
├── notification_id
├── event_type
├── subject_type
├── subject_id
├── title court
├── body court non sensible
├── channel
└── created_at
```

## 9.2 Données interdites

Ne jamais inclure :
- `Observation.raw_text` ;
- audio ;
- photos ;
- secrets ;
- emails inutiles ;
- données sensibles ;
- contenu complet de commentaire.

## 9.3 Observation raw text

```txt
Jamais d’Observation.raw_text dans notification.
```

## 9.4 Commentaires

Notification commentaire :

```txt
Notification commentaire:
├── comment_id
├── subject_id
└── body générique ou extrait court non sensible
```

---

# 10. Scope

## 10.1 Establishment scoped

```txt
Notification belongs_to establishment + recipient.
```

## 10.2 Pourquoi

Houston est un runtime établissement.  
Une notification appartient donc :
- à un établissement ;
- à un recipient ;
- à un event source ;
- à un subject.

---

# 11. Préférences utilisateur

## 11.1 Préférences MVP

```txt
MVP preferences:
├── push_enabled
├── email_enabled
└── quiet_hours optional post-MVP
```

## 11.2 Quiet hours

```txt
Quiet hours post-MVP.
```

## 11.3 Presence-aware notifications

```txt
MVP simple: pas de presence-aware notifications.
Post-MVP: suppress push if user active on subject.
```

---

# 12. Déduplication et grouping

## 12.1 Dedup minimal

```txt
same recipient + same event_type + same subject_id within short window → skip/merge.
```

## 12.2 Window

```txt
dedup_window = 5 minutes
```

## 12.3 Grouping

```txt
MVP: dedup simple.
Post-MVP: grouping.
```

## 12.4 Pourquoi

Évite :
- avalanche de push ;
- doublons liés aux retries ;
- sur-notification sur aggregation ;
- bruit terrain.

---

# 13. Priorités

## 13.1 Priorités validées

```txt
Notification priority:
├── info
├── action_required
├── urgent
└── system
```

## 13.2 Urgent

```txt
urgent notification only if human-controlled Signal.urgency = high or critical operational rule.
```

L’IA ne décide jamais l’urgence.

## 13.3 Mapping priorité → canaux

```txt
info → in_app
action_required → in_app + push
urgent → in_app + push
system → in_app/email selon type
```

## 13.4 Actor self-notification

```txt
Do not notify actor for own action by default.
Exception: async failures.
```

---

# 14. Owner / Director

## 14.1 Principe

```txt
Owner/Director:
├── voient tout dans app
├── reçoivent notifications ciblées seulement
└── high/configuration/supervision events prioritaires
```

## 14.2 Pourquoi

Owner/Director ont une visibilité globale, mais ne doivent pas recevoir toutes les notifications.

Règle produit :
- la visibilité globale est gérée par les feeds ;
- la notification doit rester ciblée.

---

# 15. Staff

## 15.1 SignalCreated

```txt
Staff ne reçoit pas SignalCreated par défaut.
```

## 15.2 Exceptions

Staff reçoit une notification Signal si :
- mention ;
- Action assignée ;
- Checklist assignée ;
- Signal pinned.

---

# 16. Rules — Signal events

## 16.1 SignalCreated

Recipients :

```txt
SignalCreated recipients:
├── Owner/Director
└── Managers dont operational_domains intersect Signal.detected_domains
```

Nuance :

```txt
Owner/Director peuvent recevoir seulement high importance.
```

Canal recommandé :
- `info → in_app` par défaut ;
- `urgent → in_app + push` si Signal high.

## 16.2 SignalAggregated

```txt
SignalAggregated:
├── notify managers concernés si Signal high ou pinned/in_progress
└── sinon in-app only / feed update
```

## 16.3 SignalUrgencyChanged

```txt
SignalUrgencyChanged → notify Managers domain-compatible
```

Canal :
- in_app + push si high ;
- in_app si retour normal.

## 16.4 SignalDomainAdded

```txt
SignalDomainAdded → notify managers of added domain.
```

## 16.5 SignalResolved / SignalCanceled

```txt
SignalResolved/Canceled:
├── creator of linked Actions
├── assignees of linked Actions
├── managers domain-compatible
└── in-app mostly, push only if high/assigned user affected
```

## 16.6 SignalPinned / SignalUnpinned

```txt
SignalPinned/Unpinned → realtime/feed update only.
No notification persisted MVP.
```

## 16.7 SignalCommentAdded

```txt
SignalCommentAdded:
├── mentioned users
└── optional participants/followers post-MVP
```

MVP :
- mentions only.

---

# 17. Rules — Action events

## 17.1 ActionAssigned

```txt
ActionAssigned:
├── assignee: in_app + push
└── creator: in_app optional
```

Priority :
- assignee = action_required ;
- creator optional = info.

## 17.2 ActionReassigned

```txt
ActionReassigned:
├── old_assignee
├── new_assignee
└── action creator
```

Canal :
- new_assignee in_app + push ;
- old_assignee in_app ;
- creator in_app.

## 17.3 ActionAccepted

```txt
ActionAccepted → creator/assigner in_app.
```

Priority :
- info.

## 17.4 ActionPendingValidation

```txt
ActionPendingValidation:
├── Manager validator domain-compatible
└── creator if authorized validator
```

Canaux :

```txt
in_app + push
```

Priority :
- action_required.

## 17.5 ActionValidated

```txt
ActionValidated:
├── assignee
└── creator
```

Canal :
- in_app ;
- push optional post-MVP.

## 17.6 ActionReopened

```txt
ActionReopened:
├── assignee: in_app + push
└── creator/validator: in_app
```

Priority :
- assignee = action_required.

## 17.7 ActionCanceled

```txt
ActionCanceled:
├── assignee
├── creator
```

Canal :
- in_app.

## 17.8 ActionOverdue

```txt
ActionOverdue:
├── assignee
└── creator/manager domain-compatible
```

Canal MVP :

```txt
in-app
push si retard critique post-MVP
```

## 17.9 ActionNoAcceptanceDetected

```txt
ActionNoAcceptanceDetected → creator/assigner.
```

## 17.10 ActionCommentAdded

```txt
ActionCommentAdded:
├── mentioned users
├── assignee
└── creator
```

---

# 18. Rules — Checklist events

## 18.1 ChecklistExecutionAssigned

```txt
ChecklistExecutionAssigned:
└── assignee in_app + push
```

Priority :
- action_required.

## 18.2 ChecklistExecutionCompleted

```txt
ChecklistExecutionCompleted:
└── assigned_by
```

Canal :
- in_app.

## 18.3 ChecklistTaskObservationCreated

```txt
ChecklistTaskObservationCreated:
├── no push direct
├── assigned_by in_app optional
└── SignalCreated notification après pipeline
```

## 18.4 ChecklistExecutionCanceled

```txt
ChecklistExecutionCanceled:
├── assignee
└── assigned_by
```

## 18.5 Personal Checklist

```txt
Personal Checklist notifications post-MVP.
MVP: visible dans Execution Feed.
```

---

# 19. Rules — Observation / AI / Transcription events

## 19.1 ObservationProcessingFailed

```txt
ObservationProcessingFailed:
├── admin/support technical
└── author simplified in_app
```

## 19.2 TranscriptionFailed

```txt
TranscriptionFailed → UX inline, no persisted notification MVP.
AIUsageLog + event suffisent.
```

## 19.3 OnboardingAIInterpretationFailed

```txt
OnboardingAIInterpretationFailed:
├── onboarding actor
└── admin/support
```

---

# 20. Rules — Onboarding / Membership

## 20.1 EstablishmentActivated

```txt
EstablishmentActivated → Owner/Director + initial managers.
```

## 20.2 UserInvited / InitialUserInvited

```txt
UserInvited:
├── email invitation
└── in_app if existing user
```

## 20.3 Membership changes

```txt
Membership changes:
├── affected user
└── audit/admin visibility
```

Events concernés :
- `MembershipRoleChanged`
- `MembershipDomainsChanged`
- `MembershipActivated`
- `MembershipDeactivated`

---

# 21. Notification model

## 21.1 notifications

```txt
notifications
├── id
├── establishment_id
├── recipient_id
├── source_event_id
├── subject_type
├── subject_id
├── priority
├── title
├── body
├── status
├── read_at
├── archived_at
├── created_at
```

## 21.2 notification_deliveries

```txt
notification_deliveries
├── id
├── notification_id
├── channel
├── status
├── provider
├── attempts
├── last_error
├── delivered_at
├── created_at
```

## 21.3 Note provider_message_id

Le fichier d’arbitrage mentionne `provider_message_id` dans la structure logique des deliveries.

Recommandation technique : l’ajouter au modèle DB.

```txt
provider_message_id nullable
```

---

# 22. Rétention

## 22.1 Notifications

```txt
Notification retention MVP = 90 jours.
```

## 22.2 Delivery logs

```txt
Delivery logs = 30 jours.
```

---

# 23. Services backend

## 23.1 Services validés

```txt
Notifications::DispatchFromEvent
Notifications::Matrix
Notifications::RecipientResolver
Notifications::Create
Notifications::Deliveries::Push
Notifications::Deliveries::Email
Notifications::MarkAsRead
```

## 23.2 DispatchFromEvent

Responsabilités :
- recevoir un event ;
- appeler la Matrix ;
- résoudre recipients ;
- vérifier RBAC ;
- créer notifications ;
- créer deliveries.

## 23.3 Matrix

Responsabilités :
- event_type → règles ;
- priority ;
- channels ;
- recipient rules ;
- dedup policy.

## 23.4 RecipientResolver

Responsabilités :
- résoudre roles/domains ;
- appliquer exclusions actor ;
- vérifier membership status ;
- vérifier RBAC/visibility ;
- dédupliquer recipients.

## 23.5 Deliveries::Push

Responsabilités :
- envoyer push ;
- gérer provider ;
- créer/mettre à jour delivery ;
- mapper erreurs.

## 23.6 Deliveries::Email

Responsabilités :
- email invitation ;
- activation compte ;
- système critique si applicable.

## 23.7 MarkAsRead

Responsabilités :
- mark read ;
- archive ;
- bulk mark read éventuel post-MVP.

---

# 24. Push provider

## 24.1 MVP provider strategy

Le document Notification Matrix ne fige pas encore le provider.

Recommandation :
- Web Push pour PWA ;
- FCM/APNs plus tard si app mobile native.

À cadrer dans architecture technique ou mobile-readiness.

## 24.2 Payload push

Push payload minimal :
- notification_id ;
- title court ;
- body court non sensible ;
- subject_type ;
- subject_id ;
- establishment_id.

Pas de données sensibles.

---

# 25. Error handling

## 25.1 Delivery failure

Si delivery échoue :
- status `failed` ;
- attempts increment ;
- last_error stocké ;
- retry selon canal.

## 25.2 Notification creation failure

Ne rollback pas l’event source.

Le système doit :
- log error ;
- créer delivery failed si possible ;
- rendre visible admin/support.

## 25.3 Skipped

Delivery `skipped` si :
- channel disabled ;
- recipient no longer has visibility ;
- dedup window active ;
- actor own action excluded ;
- unsupported channel.

---

# 26. Tests fonctionnels MVP

## 26.1 Tests matrix

```txt
Tests matrix:
Given event + roles/domains
Then expected recipients + channels + priority.
```

## 26.2 SignalCreated manager domain-compatible

```txt
Given SignalCreated with detected_domains = ["maintenance"]
And Manager has operational_domain "maintenance"
When NotificationDispatcher runs
Then Manager receives in_app notification
```

## 26.3 Staff not notified SignalCreated by default

```txt
Given SignalCreated
And Staff has matching domain
When NotificationDispatcher runs
Then Staff receives no notification unless mentioned/assigned/pinned
```

## 26.4 ActionAssigned assignee push

```txt
Given ActionAssigned
When NotificationDispatcher runs
Then assignee receives in_app + push
```

## 26.5 RBAC recheck

```txt
Given recipient no longer has visibility on subject
When NotificationDispatcher runs
Then notification is skipped
```

## 26.6 Dedup

```txt
Given same recipient + event_type + subject_id within 5 minutes
When second notification is evaluated
Then second notification is skipped or merged
```

## 26.7 No sensitive payload

```txt
Given ObservationProcessingFailed
When notification is created for author
Then notification payload does not include Observation.raw_text
```

## 26.8 Mention notification no permission grant

```txt
Given user is mentioned
When user has no permission to see subject
Then notification does not grant access
```

## 26.9 TranscriptionFailed inline only

```txt
Given TranscriptionFailed
When NotificationDispatcher runs
Then no persisted notification is created
```

## 26.10 Actor own action excluded

```txt
Given actor triggers ActionAccepted
When NotificationDispatcher evaluates recipients
Then actor is not notified by default
```

---

# 27. Décisions validées — index

| Décision | Statut |
|---|---:|
| Notification = message utilisateur généré depuis event via matrice | Validé |
| Event peut générer 0..N notifications | Validé |
| MVP channels = in_app + push | Validé |
| Email sélectif/post-MVP | Validé |
| Email MVP limité invitation/activation/critique | Validé |
| In-app notifications persistées | Validé |
| Notification objet métier | Validé |
| NotificationDelivery par canal | Validé |
| NotificationDispatcher → Matrix → recipients/channels | Validé |
| RBAC/visibilité revérifiés | Validé |
| Notification ne donne jamais accès | Validé |
| Mentions notifient sans permission | Validé |
| Payload minimal | Validé |
| No Observation.raw_text | Validé |
| Comment body non complet | Validé |
| Notification belongs_to establishment + recipient | Validé |
| Notification Center simple MVP | Validé |
| Status unread/read/archived | Validé |
| Pas de dismissed MVP | Validé |
| Deliveries trackées par canal | Validé |
| Delivery statuses queued/sent/delivered/failed/skipped | Validé |
| Preferences MVP push/email enabled | Validé |
| Quiet hours post-MVP | Validé |
| Dedup minimal | Validé |
| Dedup window 5 min | Validé |
| Grouping post-MVP | Validé |
| SignalCreated recipients validés | Validé |
| Staff pas notifié SignalCreated par défaut | Validé |
| SignalAggregated conditions validées | Validé |
| SignalUrgencyChanged → Managers domain-compatible | Validé |
| SignalDomainAdded → managers added domain | Validé |
| SignalResolved/Canceled recipients validés | Validé |
| Action notification rules validées | Validé |
| Checklist notification rules validées | Validé |
| ObservationProcessingFailed rules validées | Validé |
| TranscriptionFailed inline only | Validé |
| OnboardingAIInterpretationFailed actor + admin/support | Validé |
| EstablishmentActivated Owner/Director + initial managers | Validé |
| UserInvited email + in_app if existing | Validé |
| Membership changes affected user + audit/admin | Validé |
| Owner/Director notifications ciblées | Validé |
| Priorities info/action_required/urgent/system | Validé |
| Urgent lié à Signal.urgency high ou règle critique | Validé |
| Channel mapping par priority | Validé |
| Actor not notified for own action by default | Validé |
| No presence-aware MVP | Validé |
| Personal Checklist notifications post-MVP | Validé |
| SignalPinned/Unpinned realtime/feed only | Validé |
| SignalCommentAdded mentions MVP | Validé |
| ActionCommentAdded mentioned + assignee + creator | Validé |
| Mark read/archive, no hard delete | Validé |
| Retention notifications 90 jours | Validé |
| Delivery logs 30 jours | Validé |
| Data model notifications + deliveries | Validé |
| Services backend validés | Validé |
| Tests matrix par event critique | Validé |
| Principe notify only attention/action | Validé |
| Realtime/feed handles visibility | Validé |

---

# 28. Points à traiter ailleurs

## 28.1 Push / mobile readiness

À cadrer :
- provider push PWA ;
- FCM/APNs ;
- token registration ;
- device subscriptions ;
- browser permission UX.

## 28.2 Security / RGPD

À cadrer :
- notification retention définitive ;
- push payload minimization ;
- email provider ;
- opt-out ;
- logs provider.

## 28.3 Realtime

À cadrer :
- channels websocket ;
- authorization ;
- feed invalidation ;
- refetch strategy.

## 28.4 Admin/support

À cadrer :
- voir failed deliveries ;
- retry push/email ;
- audit notification dispatch ;
- monitoring.

---

# 29. Recommandation finale

La Notification Matrix est suffisamment cadrée pour le MVP.

Décision centrale :

```txt
Notify only when attention or action is required.
Realtime/feed handles visibility.
```

Le build doit maintenant s’appuyer sur :
- `notifications` ;
- `notification_deliveries` ;
- `Notifications::DispatchFromEvent` ;
- `Notifications::Matrix` ;
- `Notifications::RecipientResolver` ;
- RBAC recheck before create ;
- payload minimal ;
- dedup 5 minutes ;
- in_app + push MVP ;
- email limité invitations/activation/critique ;
- tests matrix par event critique.
