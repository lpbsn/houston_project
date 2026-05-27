# Houston — Action Domain

**Version:** v0.1  
**Date:** 2026-05-22  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — Mama Shelter Nice  
**Documents liés:**  
- `Houston_mvp_cadrage_p0.md`
- `Houston_rbac_permissions_domain.md`
- `Houston_observation_domain.md`
- `Houston_signal_domain.md`

---

# 1. Objectif du document

Ce document formalise le domaine **Action** de Houston pour le MVP.

Il définit :
- la définition métier d'une Action ;
- ses règles de création ;
- ses règles d'assignation ;
- son lifecycle ;
- ses statuts ;
- ses règles de validation ;
- ses règles de réassignation ;
- ses règles d'annulation ;
- ses permissions ;
- sa relation avec Signal ;
- son comportement dans l'Execution Feed ;
- ses commentaires ;
- ses events MVP ;
- ses edge cases ;
- les tests fonctionnels attendus.

Ce document sert de référence pour Product Owner, Product Designer, Tech Lead, Backend, Frontend et QA.

---

# 2. Définition métier

## 2.1 Définition

Une Action est une **responsabilité opérationnelle concrète, assignée, exécutable et validable, créée depuis un Signal**.

```txt
Action
= responsabilité opérationnelle
= exécution concrète
= assignée à une personne
= validable
= liée à un Signal
```

## 2.2 Ce qu'une Action n'est pas

Une Action n'est pas :
- un Signal ;
- une Observation ;
- une checklist ;
- une tâche libre personnelle ;
- un commentaire ;
- une conversation ;
- un objet non assigné.

## 2.3 Rôle dans Houston

L'Action transforme une situation supervisée en responsabilité d'exécution.

```txt
Signal
        ↓
Action créée et assignée
        ↓
Assignee accepte
        ↓
Travail en cours
        ↓
Assignee marque terminé
        ↓
Validation manager
        ↓
Action done
```

## 2.4 Principe central

```txt
Signal = situation opérationnelle visible
Action = exécution responsable
Personal Checklist = tâche libre personnelle
```

---

# 3. Relation Action ↔ Signal

## 3.1 Action toujours liée à un Signal

Décision MVP :

```txt
Toute Action doit être liée à un Signal.
```

Il n'y a pas d'Action libre au MVP.

## 3.2 Pas d'Action libre

Les tâches libres relèvent de :

```txt
Personal Checklist
```

Pas de :

```txt
Action without Signal
```

## 3.3 Impact sur Signal

Créer une Action a un effet direct sur le Signal parent.

```txt
ActionCreated
        ↓
Signal passe in_progress
```

Si le Signal était pinned et open :

```txt
ActionCreated on pinned open Signal
        ↓
SignalUnpinned
        ↓
SignalStatusChanged(open → in_progress)
```

## 3.4 Résolution Signal

Les Actions alimentent la résolution du Signal.

```txt
Toutes Actions done/canceled
        ↓
Signal peut passer resolved
```

Si toutes les Actions sont canceled et aucune Action active ne reste :

```txt
Signal revient open
```

---

# 4. Création d'une Action

## 4.1 Qui peut créer

```txt
Owner
Director
Manager
```

Staff ne peut pas créer d'Action.

## 4.2 Règle Manager

Un Manager peut créer une Action seulement si le Signal contient au moins un de ses `operational_domains` dans `detected_domains`.

```txt
manager.operational_domains ∩ signal.detected_domains != empty
```

Si le Signal ne contient pas son domaine :

```txt
Manager doit ajouter un detected_domain pertinent avant d'agir.
```

## 4.3 assigned_to obligatoire

Une Action MVP doit être assignée dès sa création.

```txt
assigned_to_id required
```

Il n'y a pas de brouillon d'Action non assignée au MVP.

## 4.4 Un seul assignee

```txt
1 Action = 1 assignee
```

Pourquoi :
- accountability claire ;
- lifecycle simple ;
- validation simple ;
- feed lisible ;
- pas de dilution de responsabilité.

## 4.5 Pas de watchers

Décision MVP :

```txt
No watchers
```

Les managers du domaine voient les Actions via l'Execution Feed.  
Les mentions déclenchent des notifications, mais ne créent pas de permissions.

---

# 5. Assignation

## 5.1 Qui peut assigner

```txt
Owner / Director
= peuvent assigner toute Action

Manager
= peut assigner les Actions de ses domaines
```

## 5.2 À qui assigner

Une Action peut être assignée à tout membre actif de l'établissement.

```txt
assigned_to
= active EstablishmentMembership user
```

## 5.3 Recommandation UI

L'UI doit recommander en priorité les utilisateurs appartenant aux domaines concernés.

```txt
UI recommended assignees
= users with operational_domains matching action/signal domain
```

Mais l'assignation reste possible à tout membre actif de l'établissement pour garder de la flexibilité terrain.

---

# 6. Réassignation

## 6.1 Réassignation autorisée

Une Action peut être réassignée.

```txt
ActionReassigned
```

## 6.2 Audit obligatoire

Chaque réassignation doit tracer :
- ancien assignee ;
- nouvel assignee ;
- actor_id ;
- timestamp ;
- raison optionnelle.

## 6.3 Qui peut réassigner

```txt
Owner / Director
= peuvent réassigner toute Action

Manager
= peut réassigner les Actions de ses domaines
```

## 6.4 Assignee

L'assignee ne réassigne pas directement au MVP.

S'il y a un problème :
- il commente ;
- le Manager réassigne ;
- ou le Manager annule l'Action.

---

# 7. Statuts Action

## 7.1 Statuts MVP

```txt
open
in_progress
pending_validation
reopened
done
canceled
```

## 7.2 open

```txt
open = Action créée, assignée, en attente d'acceptation de l'assignee.
```

## 7.3 in_progress

```txt
in_progress = Action acceptée, prise en charge, travail en cours.
```

## 7.4 pending_validation

```txt
pending_validation = Action marquée terminée par l'assignee, en attente de validation.
```

## 7.5 reopened

```txt
reopened = Action refusée en validation, à reprendre par l'assignee.
```

## 7.6 done

```txt
done = Action terminée et validée.
```

## 7.7 canceled

```txt
canceled = Action annulée, état final métier.
```

---

# 8. Lifecycle Action

## 8.1 Lifecycle principal

```txt
open
  ↓ assignee accepts
in_progress
  ↓ assignee marks done
pending_validation
  ↓ manager validates
done
```

## 8.2 Lifecycle avec reopen

```txt
pending_validation
  ↓ manager reopens
reopened
  ↓ assignee accepts again
in_progress
  ↓ assignee marks done
pending_validation
```

## 8.3 Lifecycle avec cancel

```txt
open / in_progress / pending_validation / reopened
  ↓ authorized user cancels
canceled
```

## 8.4 Pas de transition directe open → done

Décision :

```txt
Pas de open → done direct.
```

L'Action doit passer par :
- `in_progress` ;
- puis `pending_validation` ;
- puis `done`.

## 8.5 Acceptation explicite

L'assignee doit accepter l'Action pour passer de `open` à `in_progress`.

```txt
ActionAccepted
```

## 8.6 Pas de declined MVP

Il n'y a pas de statut `declined` au MVP.

Si l'assignee a un problème :
- il commente ;
- le manager réassigne ;
- ou le manager annule.

---

# 9. Pending validation et done

## 9.1 Passage à pending_validation

Quand l'assignee marque l'Action comme terminée :

```txt
ActionMarkedDone
        ↓
ActionPendingValidation
```

## 9.2 Qui peut marquer terminé

```txt
Assignee peut marquer done.
Owner/Director/Manager peuvent aussi le faire avec audit si nécessaire.
```

## 9.3 Validation obligatoire

Toutes les Actions passent par validation.

```txt
All Actions require validation.
```

## 9.4 Qui valide

```txt
Owner / Director
= peuvent valider toute Action

Manager
= peut valider les Actions de ses domaines

Staff
= ne valide jamais
```

## 9.5 Manager peut valider sa propre Action

Décision validée :

```txt
Si un Manager s'assigne une Action,
il peut la marquer terminée puis la valider lui-même.
```

Pas de règle spécifique pour ce cas.

---

# 10. Reopen

## 10.1 Depuis quel statut

```txt
pending_validation → reopened
```

Pas de reopen depuis :
- `done` ;
- `canceled`.

## 10.2 Signification

```txt
reopened = validation refusée, travail à reprendre.
```

## 10.3 Après reopened

```txt
reopened
  ↓ assignee accepts
in_progress
```

L'assignee accepte comme pour une Action open.

## 10.4 Nombre de reopen

Reopen illimité au MVP.

```txt
reopen_count
```

## 10.5 Raison de reopen

Décision MVP :

```txt
reopen reason non obligatoire
```

Mais il est recommandé d'encourager un commentaire manager pour expliquer la reprise.

---

# 11. Annulation

## 11.1 Cancel autorisé

Une Action peut être annulée.

```txt
ActionCanceled
```

## 11.2 Depuis quels statuts

Cancelable depuis :

```txt
open
in_progress
pending_validation
reopened
```

Non cancelable depuis :

```txt
done
canceled
```

## 11.3 Qui peut annuler

```txt
Owner / Director
= peuvent annuler toute Action

Manager
= peut annuler les Actions de ses domaines
```

## 11.4 Catégorie obligatoire

Cancel Action nécessite une catégorie obligatoire.

```txt
cancellation_category required
```

Catégories recommandées :

```txt
not_needed
duplicate
wrong_assignment
invalid
other
```

## 11.5 Commentaire optionnel

```txt
cancellation_comment optional
```

## 11.6 Effet sur Signal

Une Action `canceled` compte comme état final pour la résolution du Signal.

```txt
done OR canceled
= final state for Signal resolution calculation
```

---

# 12. Priority et urgence

## 12.1 Décision

L'Action hérite de l'urgence du Signal.

```txt
Action high si Signal high
Action normal si Signal normal
```

## 12.2 Pas de priorité indépendante

Au MVP, il ne faut pas créer une priorité d'Action indépendante du Signal.

```txt
No independent Action priority MVP
```

Pourquoi :
- éviter deux sources de vérité ;
- éviter les contradictions ;
- simplifier le feed ;
- garder Signal comme niveau de supervision.

## 12.3 Implémentation recommandée

Deux options possibles :

### Option A — champ calculé

```txt
action.priority = signal.urgency
```

### Option B — copie au moment de création

```txt
action.priority set from signal.urgency at creation
```

Recommandation MVP :

```txt
Option A : priorité calculée depuis Signal.urgency.
```

Cela évite la désynchronisation.

---

# 13. Due date

## 13.1 due_at optionnel

```txt
due_at optional
```

## 13.2 Qui peut modifier due_at

```txt
Owner / Director
= toute Action

Manager
= Actions de ses domaines
```

## 13.3 Overdue

Si `due_at` est dépassé :

```txt
ActionOverdue
```

MVP :
- visible dans Execution Feed ;
- pas de notification/escalade automatique ;
- pas d'auto-priority change.

---

# 14. SLA et escalade

## 14.1 No acceptance SLA

Décision MVP :

```txt
No acceptance escalation = Non MVP
```

L'objectif est d'abord de prouver l'exécution simple.

## 14.2 Mesure possible

Même si l'escalade est hors MVP, on peut mesurer :

```txt
ActionNoAcceptanceDetected
```

Mais sans notification automatique obligatoire.

## 14.3 Due_at dépassé

Décision MVP :

```txt
due_at dépassé visible dans feed
notification/escalade post-MVP
```

## 14.4 Pas d'auto-priority change

```txt
No automatic priority upgrade MVP.
```

---

# 15. Preuves et commentaires

## 15.1 Preuves MVP

Preuves optionnelles au MVP.

Décision :

```txt
Proof MVP = comment only
```

Pas de photo proof au MVP.

## 15.2 Commentaire done

Commentaire non obligatoire pour marquer terminé.

```txt
done_comment optional
```

## 15.3 Commentaire cancel

Commentaire cancel optionnel.

Mais :

```txt
cancellation_category required
```

## 15.4 Action comments

Les commentaires d'Action restent scoped à l'Action.

```txt
Action comments
= visible dans l'Action
= ne remontent pas automatiquement au Signal
```

## 15.5 Signal comments dans Action

Les commentaires Signal sont visibles dans les Actions liées, idéalement repliables.

```txt
Signal comments visible in linked Actions
Action comments remain scoped to Action
```

---

# 16. Execution Feed

## 16.1 Staff

```txt
Staff Execution Feed
├── Actions assignées à lui
├── Shared Checklist Executions assignées à lui
└── Personal Checklists à lui
```

## 16.2 Manager

```txt
Manager Execution Feed par défaut
├── Actions créées par lui
├── Actions de ses domaines
├── Personal Checklists à lui
├── Shared Checklist Executions attribuées par lui
└── Shared Checklist Executions attribuées à lui
```

Vue générale Manager :

```txt
Actions de ses domaines
+
Shared Checklist Executions de ses domaines
```

## 16.3 Owner / Director

```txt
Owner / Director Execution Feed
= Actions établissement
+ Shared Checklist Executions établissement
+ ses Personal Checklists
```

---

# 17. Permissions Action

## 17.1 Création

| Rôle | Peut créer Action |
|---|---:|
| Owner | Oui |
| Director | Oui |
| Manager | Oui, si domain compatible |
| Staff | Non |

## 17.2 Assignation

| Rôle | Peut assigner |
|---|---:|
| Owner | Toute Action |
| Director | Toute Action |
| Manager | Actions de ses domaines |
| Staff | Non |

## 17.3 Réassignation

| Rôle | Peut réassigner |
|---|---:|
| Owner | Toute Action |
| Director | Toute Action |
| Manager | Actions de ses domaines |
| Staff | Non |

## 17.4 Exécution

| Rôle | Peut exécuter |
|---|---:|
| Assignee | Oui |
| Owner/Director/Manager | Oui si assigné ou intervention avec audit |
| Staff | Oui si assigné |

## 17.5 Validation

| Rôle | Peut valider |
|---|---:|
| Owner | Toute Action |
| Director | Toute Action |
| Manager | Actions de ses domaines |
| Staff | Non |

## 17.6 Annulation

| Rôle | Peut annuler |
|---|---:|
| Owner | Toute Action |
| Director | Toute Action |
| Manager | Actions de ses domaines |
| Staff | Non |

---

# 18. Modèle de données recommandé

## 18.1 actions

```txt
actions
├── id UUID
├── establishment_id UUID
├── signal_id UUID
├── title string
├── description text
├── operational_domain string
├── created_by_id UUID
├── assigned_to_id UUID
├── status enum
│   ├── open
│   ├── in_progress
│   ├── pending_validation
│   ├── reopened
│   ├── done
│   └── canceled
├── due_at datetime nullable
├── accepted_at datetime nullable
├── accepted_by_id UUID nullable
├── marked_done_at datetime nullable
├── marked_done_by_id UUID nullable
├── validated_at datetime nullable
├── validated_by_id UUID nullable
├── canceled_at datetime nullable
├── canceled_by_id UUID nullable
├── cancellation_category string nullable
├── cancellation_comment text nullable
├── reopen_count integer default 0
├── last_reopened_at datetime nullable
├── last_reopened_by_id UUID nullable
├── created_at datetime
└── updated_at datetime
```

## 18.2 action_comments

```txt
action_comments
├── id UUID
├── action_id UUID
├── author_id UUID
├── body text
├── created_at datetime
└── updated_at datetime
```

## 18.3 action_events

Optionnel si event log global existe.

```txt
action_events
├── id UUID
├── action_id UUID
├── event_type string
├── actor_id UUID nullable
├── payload jsonb
├── created_at datetime
└── updated_at datetime
```

---

# 19. Events Action MVP

## 19.1 Liste validée

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
ActionPriorityChanged
ActionDueDateChanged
ActionOverdue
ActionNoAcceptanceDetected
ActionCommentAdded
ActionProofAdded
```

## 19.2 Note sur ActionPriorityChanged

Comme l'Action hérite de `Signal.urgency`, `ActionPriorityChanged` ne doit être émis que si l'Action matérialise une priorité dérivée ou si l'urgence du Signal impacte les Actions liées.

Recommandation MVP :

```txt
SignalUrgencyChanged
→ peut recalculer priorité affichée des Actions
→ ActionPriorityChanged optionnel
```

## 19.3 Payload minimal recommandé

### ActionCreated

```json
{
  "event_type": "ActionCreated",
  "action_id": "uuid",
  "signal_id": "uuid",
  "establishment_id": "uuid",
  "created_by_id": "uuid",
  "assigned_to_id": "uuid",
  "operational_domain": "maintenance",
  "created_at": "datetime"
}
```

### ActionAssigned

```json
{
  "event_type": "ActionAssigned",
  "action_id": "uuid",
  "assigned_to_id": "uuid",
  "assigned_by_id": "uuid",
  "created_at": "datetime"
}
```

### ActionReassigned

```json
{
  "event_type": "ActionReassigned",
  "action_id": "uuid",
  "previous_assignee_id": "uuid",
  "new_assignee_id": "uuid",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### ActionAccepted

```json
{
  "event_type": "ActionAccepted",
  "action_id": "uuid",
  "actor_id": "uuid",
  "from_status": "open",
  "to_status": "in_progress",
  "created_at": "datetime"
}
```

### ActionMarkedDone

```json
{
  "event_type": "ActionMarkedDone",
  "action_id": "uuid",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### ActionPendingValidation

```json
{
  "event_type": "ActionPendingValidation",
  "action_id": "uuid",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### ActionValidated

```json
{
  "event_type": "ActionValidated",
  "action_id": "uuid",
  "validated_by_id": "uuid",
  "from_status": "pending_validation",
  "to_status": "done",
  "created_at": "datetime"
}
```

### ActionReopened

```json
{
  "event_type": "ActionReopened",
  "action_id": "uuid",
  "actor_id": "uuid",
  "reopen_count": 2,
  "created_at": "datetime"
}
```

### ActionCanceled

```json
{
  "event_type": "ActionCanceled",
  "action_id": "uuid",
  "actor_id": "uuid",
  "cancellation_category": "not_needed",
  "cancellation_comment": null,
  "created_at": "datetime"
}
```

### ActionDueDateChanged

```json
{
  "event_type": "ActionDueDateChanged",
  "action_id": "uuid",
  "actor_id": "uuid",
  "previous_due_at": "datetime",
  "new_due_at": "datetime",
  "created_at": "datetime"
}
```

### ActionOverdue

```json
{
  "event_type": "ActionOverdue",
  "action_id": "uuid",
  "due_at": "datetime",
  "created_at": "datetime"
}
```

### ActionNoAcceptanceDetected

```json
{
  "event_type": "ActionNoAcceptanceDetected",
  "action_id": "uuid",
  "assigned_to_id": "uuid",
  "created_at": "datetime"
}
```

### ActionCommentAdded

```json
{
  "event_type": "ActionCommentAdded",
  "action_id": "uuid",
  "comment_id": "uuid",
  "author_id": "uuid",
  "created_at": "datetime"
}
```

### ActionProofAdded

```json
{
  "event_type": "ActionProofAdded",
  "action_id": "uuid",
  "proof_id": "uuid",
  "author_id": "uuid",
  "proof_type": "comment",
  "created_at": "datetime"
}
```

---

# 20. API endpoints MVP

## 20.1 Create Action

```txt
POST /api/v1/signals/:signal_id/actions
```

### Body

```json
{
  "title": "Vérifier la fuite devant la chambre 312",
  "description": "Contrôler l'origine de la fuite et sécuriser la zone.",
  "operational_domain": "maintenance",
  "assigned_to_id": "uuid",
  "due_at": "datetime"
}
```

## 20.2 Accept Action

```txt
POST /api/v1/actions/:id/accept
```

## 20.3 Mark done

```txt
POST /api/v1/actions/:id/mark_done
```

## 20.4 Validate

```txt
POST /api/v1/actions/:id/validate
```

## 20.5 Reopen

```txt
POST /api/v1/actions/:id/reopen
```

## 20.6 Cancel

```txt
POST /api/v1/actions/:id/cancel
```

### Body

```json
{
  "cancellation_category": "not_needed",
  "cancellation_comment": "Déjà traité par l'équipe technique."
}
```

## 20.7 Reassign

```txt
POST /api/v1/actions/:id/reassign
```

### Body

```json
{
  "assigned_to_id": "uuid"
}
```

## 20.8 Update due_at

```txt
PATCH /api/v1/actions/:id/due_at
```

## 20.9 Add comment

```txt
POST /api/v1/actions/:id/comments
```

---

# 21. Backend services recommandés

## 21.1 Create

```txt
Actions::Create
```

Responsabilités :
- vérifier permission ;
- vérifier Signal actif ;
- vérifier domain compatibility ;
- vérifier assigned_to actif dans établissement ;
- créer Action ;
- émettre ActionCreated / ActionAssigned ;
- déclencher Signal transition `open → in_progress` ;
- auto-unpin Signal si nécessaire.

## 21.2 Accept

```txt
Actions::Accept
```

Responsabilités :
- vérifier assignee ;
- transition `open/reopened → in_progress` ;
- émettre ActionAccepted.

## 21.3 Mark done

```txt
Actions::MarkDone
```

Responsabilités :
- vérifier assignee ou manager autorisé ;
- transition `in_progress → pending_validation` ;
- émettre ActionMarkedDone ;
- émettre ActionPendingValidation.

## 21.4 Validate

```txt
Actions::Validate
```

Responsabilités :
- vérifier permission validation ;
- transition `pending_validation → done` ;
- émettre ActionValidated ;
- vérifier résolution Signal.

## 21.5 Reopen

```txt
Actions::Reopen
```

Responsabilités :
- vérifier permission ;
- transition `pending_validation → reopened` ;
- increment `reopen_count` ;
- émettre ActionReopened.

## 21.6 Cancel

```txt
Actions::Cancel
```

Responsabilités :
- vérifier permission ;
- vérifier status cancelable ;
- exiger cancellation_category ;
- transition vers `canceled` ;
- émettre ActionCanceled ;
- recalculer status Signal.

## 21.7 Reassign

```txt
Actions::Reassign
```

Responsabilités :
- vérifier permission ;
- vérifier new assignee actif ;
- changer assigned_to ;
- éventuellement remettre status à `open` si déjà accepté ;
- émettre ActionReassigned.

## 21.8 UpdateDueAt

```txt
Actions::UpdateDueAt
```

Responsabilités :
- vérifier permission ;
- modifier due_at ;
- émettre ActionDueDateChanged.

---

# 22. Contraintes backend

## 22.1 Signal obligatoire

```txt
signal_id required
```

## 22.2 assigned_to obligatoire

```txt
assigned_to_id required
```

## 22.3 One assignee

```txt
No many-to-many assignees MVP.
```

## 22.4 Status transitions strictes

Transitions autorisées :

```txt
open → in_progress
in_progress → pending_validation
pending_validation → done
pending_validation → reopened
reopened → in_progress
open/in_progress/pending_validation/reopened → canceled
```

Transitions interdites :

```txt
open → done
done → reopened
done → canceled
canceled → reopened
canceled → done
```

## 22.5 Manager domain permission

```txt
manager.operational_domains includes action.operational_domain
```

## 22.6 Cancellation category required

```txt
if status changes to canceled:
    cancellation_category required
```

---

# 23. Edge cases

## 23.1 Manager creates Action on pinned Signal

```txt
Signal open + pinned
Action created
        ↓
Signal unpinned
Signal in_progress
```

## 23.2 Assignee does not accept

MVP :
- visible as open ;
- `ActionNoAcceptanceDetected` can be measured ;
- no automatic escalation.

## 23.3 Assignee cannot do it

MVP :
- assignee comments ;
- manager reassigns or cancels.

## 23.4 Reassign in_progress Action

Decision to implement carefully.

Recommended MVP behavior :

```txt
If in_progress Action is reassigned:
    status returns to open
    new assignee must accept
```

## 23.5 Cancel last active Action

If all Actions become canceled :

```txt
Signal returns to open
```

If all Actions are final done/canceled and business rule resolves :

```txt
Signal can become resolved
```

Signal Domain owns final status recalculation.

## 23.6 Overdue

```txt
due_at < now
status not in done/canceled
        ↓
display overdue in Execution Feed
```

## 23.7 Action priority after Signal urgency changes

Because Action priority is derived :

```txt
Signal urgency high
→ linked Actions displayed high
```

If Signal returns normal :

```txt
linked Actions displayed normal
```

No independent Action priority edit.

---

# 24. Tests fonctionnels MVP

## 24.1 Create Action

```txt
Given Manager with matching domain
And active Signal with that detected_domain
When Manager creates Action with assignee
Then Action is created open
And ActionCreated is emitted
And Signal becomes in_progress
```

## 24.2 Staff cannot create Action

```txt
Given Staff user
When Staff tries to create Action
Then request is rejected
```

## 24.3 Action requires assignee

```txt
Given authorized Manager
When Action is created without assigned_to
Then request is rejected
```

## 24.4 Assignee accepts

```txt
Given open Action assigned to user
When assignee accepts
Then Action becomes in_progress
And ActionAccepted is emitted
```

## 24.5 No direct open to done

```txt
Given open Action
When user tries to mark done without in_progress
Then request is rejected
```

## 24.6 Mark done

```txt
Given in_progress Action
When assignee marks done
Then Action becomes pending_validation
And ActionMarkedDone / ActionPendingValidation are emitted
```

## 24.7 Staff cannot validate

```txt
Given pending_validation Action
When Staff tries to validate
Then request is rejected
```

## 24.8 Manager validates domain Action

```txt
Given pending_validation Action in Manager domain
When Manager validates
Then Action becomes done
And ActionValidated is emitted
```

## 24.9 Manager validates own Action

```txt
Given Manager is assignee and domain manager
When Manager marks done and validates
Then Action becomes done
```

## 24.10 Reopen

```txt
Given pending_validation Action
When Manager reopens
Then Action becomes reopened
And reopen_count increments
And ActionReopened is emitted
```

## 24.11 Reopened accept

```txt
Given reopened Action
When assignee accepts
Then Action becomes in_progress
```

## 24.12 Cancel with category

```txt
Given active Action
When authorized user cancels with category
Then Action becomes canceled
And ActionCanceled is emitted
```

## 24.13 Cancel without category rejected

```txt
Given active Action
When user cancels without category
Then request is rejected
```

## 24.14 Canceled counts final

```txt
Given Signal with Actions
When one Action is canceled
Then it counts as final for Signal status calculation
```

## 24.15 Reassign

```txt
Given Action in Manager domain
When Manager reassigns
Then assigned_to changes
And ActionReassigned is emitted
```

---

# 25. Décisions validées — index

| Décision | Statut |
|---|---:|
| Action = responsabilité opérationnelle concrète | Validé |
| Action créée depuis Signal | Validé |
| Action toujours liée à Signal | Validé |
| Pas d'Action libre MVP | Validé |
| Tâches libres = Personal Checklist | Validé |
| assigned_to obligatoire | Validé |
| 1 Action = 1 assignee | Validé |
| Pas de watchers MVP | Validé |
| Owner/Director/Manager créent | Validé |
| Staff ne crée pas | Validé |
| Manager crée seulement sur Signal de ses domains | Validé |
| Assignation à tout membre actif | Validé |
| UI recommande users des domains concernés | Validé |
| Réassignation avec audit | Validé |
| Owner/Director réassignent toute Action | Validé |
| Manager réassigne Actions de ses domains | Validé |
| Status open/in_progress/pending_validation/reopened/done/canceled | Validé |
| open = créée/assignée/en attente acceptation | Validé |
| Acceptation explicite | Validé |
| Pas de declined MVP | Validé |
| Pas de open→done direct | Validé |
| pending_validation quand assignee marque terminé | Validé |
| Validation obligatoire | Validé |
| Owner/Director valident toute Action | Validé |
| Manager valide Actions de ses domains | Validé |
| Staff ne valide jamais | Validé |
| Manager peut valider sa propre Action | Validé |
| done = terminée et validée | Validé |
| Reopen depuis pending_validation | Validé |
| Reopen illimité avec reopen_count | Validé |
| Reopen reason non obligatoire | Validé |
| Cancel possible | Validé |
| Cancel category obligatoire | Validé |
| Cancel comment optionnel | Validé |
| Cancelable depuis open/in_progress/pending_validation/reopened | Validé |
| Pas de cancel depuis done | Validé |
| canceled final pour Signal | Validé |
| Pas de suppression utilisateur | Validé |
| Action priority dérivée de Signal urgency | Validé |
| due_at optionnel | Validé |
| Overdue visible dans feed | Validé |
| Pas d'escalade automatique MVP | Validé |
| Preuve optionnelle = commentaire | Validé |
| Done comment non obligatoire | Validé |
| Action comments scoped Action | Validé |
| Signal comments visibles dans Actions liées | Validé |
| Events Action MVP | Validé |

---

# 26. Points à traiter dans d'autres domaines

## 26.1 Notification Matrix

À cadrer :
- notification Action assigned ;
- notification Action pending validation ;
- notification Action overdue ;
- notification comment ;
- notification reassign ;
- payload minimal.

## 26.2 Event Catalog

À cadrer :
- event persistence ;
- idempotence ;
- correlation_id ;
- causation_id ;
- retries ;
- consumers.

## 26.3 Checklist Domain

À cadrer :
- lifecycle ChecklistExecution ;
- relation avec Execution Feed ;
- completion ;
- skip ;
- assignment ;
- recurrence ou non.

## 26.4 Media Lifecycle

À cadrer :
- preuve photo post-MVP ;
- stockage ;
- rétention ;
- signed URLs.

---

# 27. Recommandation finale

Le domaine Action est suffisamment cadré pour le MVP.

Décision centrale :

```txt
Action = responsabilité d'exécution liée à un Signal.
```

Le build doit maintenant s'appuyer sur :
- Action toujours liée à Signal ;
- assignee obligatoire ;
- 1 assignee ;
- lifecycle strict ;
- validation obligatoire ;
- manager autorisé sur Actions de ses domaines ;
- cancel catégorisé ;
- priorité dérivée du Signal ;
- due_at optionnel ;
- escalade post-MVP ;
- Action comments scoped Action.

La prochaine étape logique est le **Checklist Domain**, car les checklists partagent l'Execution Feed avec les Actions et peuvent créer des Observations contextualisées.
