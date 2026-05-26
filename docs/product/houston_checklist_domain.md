# Houston — Checklist Domain

**Version:** v0.1  
**Date:** 2026-05-22  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — Mama Shelter Nice  
**Documents liés:**  
- `Houston_mvp_cadrage_p0.md`
- `Houston_rbac_permissions_domain.md`
- `Houston_observation_domain.md`
- `Houston_signal_domain.md`
- `Houston_action_domain.md`
- `Houston_onboarding_domain.md`

---

# 1. Objectif du document

Ce document formalise le domaine **Checklist** de Houston pour le MVP.

Il définit :
- les types de checklists ;
- la distinction Shared / Personal ;
- le modèle Template / Execution ;
- le lifecycle des templates ;
- le lifecycle des executions ;
- le lifecycle des tasks ;
- les règles d’assignation ;
- les règles d’exécution ;
- la relation avec l’Execution Feed ;
- la relation avec Observation / +Signaler ;
- les permissions ;
- les snapshots ;
- les metrics ;
- les events MVP ;
- les edge cases ;
- les tests fonctionnels attendus.

Ce document sert de référence pour Product Owner, Product Designer, Tech Lead, Backend, Frontend et QA.

---

# 2. Définition métier

## 2.1 Définition

Une Checklist est une routine opérationnelle structurée, réutilisable ou personnelle, composée de tâches, servant à guider l’exécution terrain et pouvant produire des Observations contextualisées.

```txt
Checklist
= routine opérationnelle
= liste structurée de tâches
= guide d’exécution terrain
= objet réutilisable ou personnel
= source possible d’Observation contextualisée
```

## 2.2 Ce qu’une Checklist n’est pas

Une Checklist n’est pas :
- une Action ;
- un Signal ;
- une Observation ;
- un commentaire ;
- une conversation ;
- un simple bloc-notes non structuré.

## 2.3 Principe central

```txt
Checklist ≠ Action
```

Mais :

```txt
ChecklistExecution et Action peuvent toutes deux apparaître dans l’Execution Feed.
```

Pourquoi :
- une Action est une responsabilité issue d’un Signal ;
- une ChecklistExecution est une routine à exécuter ;
- les deux représentent du travail opérationnel.

---

# 3. Types de checklists MVP

## 3.1 Types retenus

Le MVP contient :

```txt
Shared Checklists
Personal Checklists
```

## 3.2 Shared Checklist

Une Shared Checklist est une routine établissement, standardisée et assignable.

```txt
Shared Checklist
= routine établissement
= standardisée
= créée par Owner/Director/Manager
= assignable
= visible dans catalogue par Owner/Director/Manager
```

## 3.3 Personal Checklist

Une Personal Checklist est une routine privée, réutilisable uniquement par son créateur, non assignable à autrui.

```txt
Personal Checklist
= routine privée
= created_by scoped
= réutilisable par son créateur
= non assignable à autrui
= visible uniquement par son créateur dans l’UI produit
```

## 3.4 Différence stricte

| Sujet | Shared Checklist | Personal Checklist |
|---|---|---|
| Scope | Establishment | User |
| Création | Owner/Director/Manager | Tous les users |
| Assignable | Oui | Non à autrui |
| Visible par | Owner/Director/Manager catalogue | Créateur uniquement |
| Execution Feed | Si assignée | Pour son créateur |
| Réutilisable | Oui | Oui |
| Peut générer Observation | Oui | Oui |

---

# 4. Modèle conceptuel

## 4.1 Modèles validés

Le modèle MVP utilise quatre objets :

```txt
ChecklistTemplate
ChecklistTaskTemplate
ChecklistExecution
ChecklistTaskExecution
```

## 4.2 Pourquoi séparer Template et Execution

La séparation est obligatoire pour :
- réutiliser les templates ;
- historiser les executions ;
- modifier un template sans casser l’historique ;
- mesurer les completions ;
- gérer les executions assignées ;
- permettre les snapshots.

## 4.3 Shared Checklist

```txt
Shared Checklist = ChecklistTemplate établissement
```

Une fois assignée :

```txt
ChecklistTemplate
        ↓
ChecklistExecution
```

## 4.4 Personal Checklist

Les Personal Checklists utilisent le même modèle Template / Execution.

```txt
Personal Checklist
= ChecklistTemplate scoped created_by
+ ChecklistExecution lancée par le créateur
```

## 4.5 Modèle relationnel simplifié

```txt
ChecklistTemplate
├── ChecklistTaskTemplate[]

ChecklistExecution
├── checklist_template_id
├── assigned_to_id
├── ChecklistTaskExecution[]
```

---

# 5. ChecklistTemplate

## 5.1 Définition

Un ChecklistTemplate est le modèle réutilisable d’une checklist.

## 5.2 Scope

Un ChecklistTemplate peut être :
- shared establishment-scoped ;
- personal user-scoped.

## 5.3 Statuses

```txt
draft
active
archived
```

## 5.4 draft

```txt
draft = template en préparation, non disponible dans le catalogue.
```

## 5.5 active

```txt
active = template publié / disponible dans le catalogue.
```

Pour Shared Checklist :

```txt
ChecklistTemplate.active = disponible dans le catalogue établissement
```

## 5.6 archived

```txt
archived = template retiré du catalogue, non utilisable pour créer de nouvelles executions.
```

## 5.7 Pas de suppression utilisateur standard

Un template ne doit pas être supprimé en usage métier.

```txt
Archive > delete
```

Soft delete admin éventuel hors UI produit.

---

# 6. ChecklistTaskTemplate

## 6.1 Définition

Un ChecklistTaskTemplate est une tâche modèle appartenant à un ChecklistTemplate.

## 6.2 Status

Décision MVP :

```txt
ChecklistTaskTemplate n’a pas de status MVP.
```

Il appartient au template.

## 6.3 Champs recommandés

```txt
ChecklistTaskTemplate
├── id
├── checklist_template_id
├── title
├── instructions
├── position
├── created_at
└── updated_at
```

## 6.4 Required tasks

Décision MVP :

```txt
required tasks = Non MVP
```

Toutes les tasks peuvent être skipped au MVP.

## 6.5 Proof requirements

Décision MVP :

```txt
Task proof = Non MVP
```

Pas de preuve obligatoire par task au MVP.

---

# 7. ChecklistExecution

## 7.1 Définition

Une ChecklistExecution est une instance runtime d’un ChecklistTemplate.

```txt
ChecklistTemplate
        ↓ assignment / start
ChecklistExecution
```

## 7.2 Assignation

Une ChecklistExecution a exactement un assignee.

```txt
1 ChecklistExecution = 1 assignee
```

## 7.3 Plusieurs assignees

Si une même routine doit être exécutée par plusieurs personnes :

```txt
Créer plusieurs ChecklistExecutions depuis le même ChecklistTemplate.
```

Ne pas faire :

```txt
1 ChecklistExecution avec plusieurs assignees
```

## 7.4 Statuses

```txt
assigned
in_progress
completed
canceled
```

## 7.5 assigned

```txt
assigned = execution créée et attribuée, pas encore démarrée.
```

## 7.6 in_progress

```txt
in_progress = execution démarrée par l’utilisateur.
```

Le passage `assigned → in_progress` se fait quand l’utilisateur clique sur “Start”.

## 7.7 completed

```txt
completed = toutes les task executions sont traitées.
```

Une task est considérée traitée si elle est :
- done ;
- skipped ;
- observation_created.

## 7.8 canceled

```txt
canceled = execution annulée.
```

## 7.9 Completion automatique

La completion est automatique.

```txt
Pas de validation manager MVP.
```

Quand toutes les tasks sont traitées :

```txt
ChecklistExecutionCompleted
```

---

# 8. ChecklistTaskExecution

## 8.1 Définition

Une ChecklistTaskExecution est l’instance runtime d’une ChecklistTaskTemplate.

## 8.2 Statuses

```txt
pending
done
skipped
observation_created
```

## 8.3 pending

```txt
pending = task non traitée.
```

## 8.4 done

```txt
done = task réalisée normalement.
```

## 8.5 skipped

```txt
skipped = task ignorée volontairement.
```

## 8.6 observation_created

```txt
observation_created = une Observation contextualisée a été créée depuis cette task.
```

## 8.7 Task qui crée une Observation

Décision :

```txt
Créer une Observation depuis une task passe la task en observation_created.
```

---

# 9. Execution Feed

## 9.1 Principe

L’Execution Feed contient les objets que l’utilisateur doit exécuter.

```txt
Execution Feed
├── Actions
├── Shared Checklist Executions
└── Personal Checklists
```

## 9.2 ChecklistExecution dans Execution Feed

Une ChecklistExecution assignée apparaît dans l’Execution Feed du user concerné.

```txt
ChecklistExecution assigned_to user
→ visible in user's Execution Feed
```

## 9.3 Staff Execution Feed

```txt
Staff Execution Feed
├── Actions assignées
├── Shared Checklist Executions assignées
└── Personal Checklists
```

## 9.4 Manager Execution Feed

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

## 9.5 Owner / Director Execution Feed

```txt
Owner / Director Execution Feed
= Actions établissement
+ Shared Checklist Executions établissement
+ ses Personal Checklists
```

---

# 10. Shared Checklist Catalog

## 10.1 Visibilité catalogue

Le catalogue Shared Checklist est visible par :

```txt
Owner
Director
Manager
```

Staff ne browse pas le catalogue Shared.

## 10.2 Staff

Le Staff voit :
- les Shared Checklist Executions qui lui sont assignées ;
- pas le catalogue complet ;
- pas les templates établissement non assignés.

## 10.3 Pourquoi

Objectif :
- éviter le bruit ;
- garder Staff centré sur ce qu’il doit exécuter ;
- éviter qu’il lance des routines non prévues.

---

# 11. Création et modification Shared Checklist

## 11.1 Qui peut créer

```txt
Owner
Director
Manager
```

peuvent créer un Shared ChecklistTemplate.

## 11.2 Qui peut modifier

```txt
Owner / Director
= peuvent modifier tous les Shared ChecklistTemplates

Manager
= peut modifier les templates de ses domaines ou créés par lui
```

## 11.3 Qui peut archiver

Même règle que modification :

```txt
Owner / Director
= tous

Manager
= ses domaines ou créés par lui
```

## 11.4 Duplication template

Décision MVP :

```txt
Template duplication = Post-MVP
```

---

# 12. Assignation Shared Checklist

## 12.1 Qui peut assigner

Règle recommandée cohérente avec création / management :

```txt
Owner / Director
= peuvent assigner tous les Shared ChecklistTemplates

Manager
= peut assigner les templates de ses domaines
```

## 12.2 À qui assigner

Une Shared ChecklistExecution peut être assignée à un membre actif de l’établissement.

Recommandation UI :
- recommander les users des domains concernés ;
- autoriser assignation flexible si nécessaire.

## 12.3 Plusieurs assignees

Pour plusieurs personnes :

```txt
Créer plusieurs ChecklistExecutions.
```

---

# 13. Personal Checklist

## 13.1 Modèle

Les Personal Checklists utilisent le même modèle Template/Execution.

```txt
PersonalChecklistTemplate privé
        ↓
PersonalChecklistExecution lancée par le créateur
```

## 13.2 Réutilisable

```txt
PersonalChecklistTemplate privé réutilisable par son créateur.
```

## 13.3 Non assignable

```txt
Non assignable à autrui.
```

L’utilisateur peut lancer une execution personnelle pour lui-même.

## 13.4 Visibilité

```txt
Visible uniquement par le créateur dans l’UI produit.
```

Owner/Director ne voient pas les Personal Checklists d’autrui dans l’UI produit.

## 13.5 Execution Feed

Les Personal Checklists du user apparaissent dans son Execution Feed.

## 13.6 Observation depuis Personal Checklist

Une Personal Checklist Task peut créer une Observation contextualisée.

```txt
Personal Checklist Task
        ↓
+Signaler
        ↓
Observation source=checklist
        ↓
Pipeline IA
        ↓
Signal
```

---

# 14. Observation depuis checklist

## 14.1 Principe

Une task ne crée jamais directement un Signal.

```txt
Task
→ +Signaler
→ Observation contextualisée
→ Pipeline IA
→ Signal
```

## 14.2 Données Observation

Une Observation créée depuis checklist porte :

```txt
Observation
├── checklist_execution_id
├── checklist_task_execution_id
├── operational_unit_id optional
└── source = checklist
```

## 14.3 Texte court

Le contexte checklist/task peut permettre un texte court.

```txt
Checklist task context can support shorter observation text.
```

## 14.4 Status task après Observation

Quand une Observation est créée depuis une task :

```txt
ChecklistTaskExecution.status = observation_created
```

---

# 15. Skip task

## 15.1 Skip autorisé

Une task peut être skipped.

## 15.2 skipped_reason

Décision MVP :

```txt
skipped_reason optional
```

Pas de justification obligatoire.

## 15.3 Required tasks

Décision MVP :

```txt
No required tasks MVP.
```

Donc skip possible sans warning obligatoire.

---

# 16. Cancellation ChecklistExecution

## 16.1 Cancel autorisé

Une ChecklistExecution peut être canceled.

```txt
ChecklistExecutionCanceled
```

## 16.2 Qui peut cancel

```txt
Owner / Director
= peuvent cancel toutes les executions

Manager
= peut cancel les executions de ses domaines

Assignee
= ne cancel pas directement ; il commente si problème
```

## 16.3 Catégorie / commentaire

Le besoin de catégorie obligatoire n’a pas été explicitement retenu pour ChecklistExecution.

Recommandation MVP :
- cancellation_category optionnelle ;
- cancellation_comment optionnel ;
- audit actor obligatoire.

---

# 17. Snapshot et modification template

## 17.1 Règle

Les ChecklistExecutions existantes conservent un snapshot des tasks au moment de création.

```txt
Template change
≠ update existing executions
```

## 17.2 Pourquoi

Cette règle protège :
- l’historique ;
- les metrics ;
- les executions en cours ;
- la compréhension de ce qui a réellement été demandé.

## 17.3 Pas de versioning complet MVP

Décision :

```txt
No full versioning MVP.
```

Mais :

```txt
Snapshot task data dans ChecklistExecution / ChecklistTaskExecution.
```

## 17.4 Snapshot recommandé

Chaque ChecklistTaskExecution doit conserver :
- task title au moment de l’execution ;
- instructions au moment de l’execution ;
- position au moment de l’execution.

---

# 18. Récurrence

## 18.1 Décision MVP

```txt
Pas de récurrence MVP.
```

## 18.2 Création d’executions

Les ChecklistExecutions sont créées manuellement au MVP.

## 18.3 Préparation post-MVP

Prévoir un champ nullable :

```txt
recurrence_rule nullable
```

Mais ne pas activer la récurrence au MVP.

---

# 19. Preuves

## 19.1 Task proof

Décision MVP :

```txt
Task proof = Non MVP
```

Pas de photo proof, pas de preuve obligatoire.

## 19.2 Commentaire task

Un commentaire task peut être envisagé comme option simple, mais il n’est pas requis MVP.

## 19.3 Media proof

Photo proof post-MVP.

---

# 20. Metrics checklist MVP

## 20.1 Metrics simples

Metrics MVP :

```txt
executions_completed
completion_rate
skipped_tasks_count
observations_created_from_checklist
```

## 20.2 Détection anomalies récurrentes

Décision MVP :

```txt
Non MVP.
```

Pas de détection intelligente d’anomalies récurrentes depuis checklist au MVP.

## 20.3 Ce qui peut être mesuré sans dashboard avancé

Même sans analytics complet, enregistrer :
- nombre d’executions créées ;
- nombre d’executions terminées ;
- tasks skipped ;
- Observations créées depuis checklist ;
- templates les plus utilisés.

---

# 21. Modèle de données recommandé

## 21.1 checklist_templates

```txt
checklist_templates
├── id UUID
├── establishment_id UUID nullable for personal if preferred
├── created_by_id UUID
├── checklist_type enum
│   ├── shared
│   └── personal
├── title string
├── description text nullable
├── status enum
│   ├── draft
│   ├── active
│   └── archived
├── operational_domains jsonb / array nullable
├── recurrence_rule string nullable post-MVP
├── archived_at datetime nullable
├── created_at
└── updated_at
```

## 21.2 checklist_task_templates

```txt
checklist_task_templates
├── id UUID
├── checklist_template_id UUID
├── title string
├── instructions text nullable
├── position integer
├── created_at
└── updated_at
```

## 21.3 checklist_executions

```txt
checklist_executions
├── id UUID
├── checklist_template_id UUID
├── establishment_id UUID nullable for personal if preferred
├── checklist_type enum
│   ├── shared
│   └── personal
├── assigned_to_id UUID
├── assigned_by_id UUID nullable
├── started_by_id UUID nullable
├── status enum
│   ├── assigned
│   ├── in_progress
│   ├── completed
│   └── canceled
├── operational_domains jsonb / array nullable
├── template_snapshot jsonb
├── started_at datetime nullable
├── completed_at datetime nullable
├── canceled_at datetime nullable
├── canceled_by_id UUID nullable
├── created_at
└── updated_at
```

## 21.4 checklist_task_executions

```txt
checklist_task_executions
├── id UUID
├── checklist_execution_id UUID
├── checklist_task_template_id UUID nullable
├── title_snapshot string
├── instructions_snapshot text nullable
├── position integer
├── status enum
│   ├── pending
│   ├── done
│   ├── skipped
│   └── observation_created
├── completed_by_id UUID nullable
├── completed_at datetime nullable
├── skipped_by_id UUID nullable
├── skipped_at datetime nullable
├── skipped_reason text nullable
├── observation_id UUID nullable
├── created_at
└── updated_at
```

---

# 22. Events Checklist MVP

## 22.1 Events validés

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

## 22.2 Payload minimal recommandé

### ChecklistTemplateCreated

```json
{
  "event_type": "ChecklistTemplateCreated",
  "checklist_template_id": "uuid",
  "establishment_id": "uuid",
  "checklist_type": "shared",
  "created_by_id": "uuid",
  "created_at": "datetime"
}
```

### ChecklistExecutionCreated

```json
{
  "event_type": "ChecklistExecutionCreated",
  "checklist_execution_id": "uuid",
  "checklist_template_id": "uuid",
  "establishment_id": "uuid",
  "assigned_to_id": "uuid",
  "created_at": "datetime"
}
```

### ChecklistExecutionStarted

```json
{
  "event_type": "ChecklistExecutionStarted",
  "checklist_execution_id": "uuid",
  "actor_id": "uuid",
  "from_status": "assigned",
  "to_status": "in_progress",
  "created_at": "datetime"
}
```

### ChecklistTaskCompleted

```json
{
  "event_type": "ChecklistTaskCompleted",
  "checklist_execution_id": "uuid",
  "checklist_task_execution_id": "uuid",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### ChecklistTaskObservationCreated

```json
{
  "event_type": "ChecklistTaskObservationCreated",
  "checklist_execution_id": "uuid",
  "checklist_task_execution_id": "uuid",
  "observation_id": "uuid",
  "actor_id": "uuid",
  "created_at": "datetime"
}
```

### ChecklistExecutionCompleted

```json
{
  "event_type": "ChecklistExecutionCompleted",
  "checklist_execution_id": "uuid",
  "completed_by_id": "uuid",
  "completed_at": "datetime"
}
```

---

# 23. API endpoints MVP

## 23.1 Create Shared ChecklistTemplate

```txt
POST /api/v1/checklist_templates
```

## 23.2 Update ChecklistTemplate

```txt
PATCH /api/v1/checklist_templates/:id
```

## 23.3 Activate ChecklistTemplate

```txt
POST /api/v1/checklist_templates/:id/activate
```

## 23.4 Archive ChecklistTemplate

```txt
POST /api/v1/checklist_templates/:id/archive
```

## 23.5 Assign Shared Checklist

```txt
POST /api/v1/checklist_templates/:id/executions
```

Body:

```json
{
  "assigned_to_id": "uuid"
}
```

## 23.6 Start ChecklistExecution

```txt
POST /api/v1/checklist_executions/:id/start
```

## 23.7 Complete task

```txt
POST /api/v1/checklist_task_executions/:id/complete
```

## 23.8 Skip task

```txt
POST /api/v1/checklist_task_executions/:id/skip
```

Body:

```json
{
  "skipped_reason": "Optionnel"
}
```

## 23.9 Create Observation from task

```txt
POST /api/v1/checklist_task_executions/:id/observations
```

This routes to +Signaler / Observation creation flow.

## 23.10 Cancel ChecklistExecution

```txt
POST /api/v1/checklist_executions/:id/cancel
```

## 23.11 Create Personal ChecklistTemplate

```txt
POST /api/v1/personal_checklist_templates
```

## 23.12 Start Personal ChecklistExecution

```txt
POST /api/v1/personal_checklist_templates/:id/executions
```

---

# 24. Backend services recommandés

## 24.1 ChecklistTemplates::Create

Responsabilités :
- vérifier permission ;
- créer template ;
- créer task templates ;
- émettre event.

## 24.2 ChecklistTemplates::Activate

Responsabilités :
- valider tasks ;
- passer template active ;
- émettre ChecklistTemplateActivated.

## 24.3 ChecklistTemplates::Archive

Responsabilités :
- archiver template ;
- empêcher nouvelles executions ;
- préserver history.

## 24.4 ChecklistExecutions::Create

Responsabilités :
- vérifier template active ;
- vérifier assignee ;
- créer execution ;
- snapshot template/tasks ;
- créer task executions ;
- émettre ChecklistExecutionCreated / Assigned.

## 24.5 ChecklistExecutions::Start

Responsabilités :
- vérifier assignee ;
- passer assigned → in_progress ;
- émettre ChecklistExecutionStarted.

## 24.6 ChecklistTaskExecutions::Complete

Responsabilités :
- passer task à done ;
- vérifier completion globale ;
- émettre events.

## 24.7 ChecklistTaskExecutions::Skip

Responsabilités :
- passer task à skipped ;
- stocker skipped_reason optionnelle ;
- vérifier completion globale.

## 24.8 ChecklistTaskExecutions::CreateObservation

Responsabilités :
- lancer flow +Signaler ;
- créer Observation contextualisée ;
- passer task à observation_created ;
- vérifier completion globale.

## 24.9 ChecklistExecutions::Cancel

Responsabilités :
- vérifier permission ;
- passer execution à canceled ;
- émettre event.

---

# 25. Contraintes backend

## 25.1 Une execution = un assignee

```txt
checklist_execution.assigned_to_id required
```

## 25.2 Template active requis

On ne peut créer une execution que depuis un template active.

```txt
ChecklistTemplate.status = active
```

## 25.3 Snapshot obligatoire

Créer une execution doit créer un snapshot des tasks.

## 25.4 Personal privacy

```txt
Personal Checklist visible only to created_by.
```

## 25.5 Staff catalog access

```txt
Staff cannot browse Shared Checklist catalog.
```

## 25.6 Completion rule

```txt
ChecklistExecution completed
if all tasks are done OR skipped OR observation_created.
```

---

# 26. Edge cases

## 26.1 Template archived while execution in progress

Existing execution continues with snapshot.

```txt
Template archived
≠ cancel existing execution
```

## 26.2 Template modified while execution exists

Existing execution unchanged.

## 26.3 User tries to assign archived template

Reject.

## 26.4 Staff tries to open Shared catalog

Reject / hide UI.

## 26.5 Personal Checklist accessed by another user

Reject.

## 26.6 Task creates Observation

Task becomes observation_created.

## 26.7 All tasks skipped

Execution can complete.

This is allowed MVP.

## 26.8 Assignee has problem with ChecklistExecution

Assignee comments.  
Manager cancels if needed.

## 26.9 Multiple people need same checklist

Create multiple executions.

---

# 27. Tests fonctionnels MVP

## 27.1 Create Shared ChecklistTemplate

```txt
Given Manager
When Manager creates Shared ChecklistTemplate
Then template is created in draft
And ChecklistTemplateCreated is emitted
```

## 27.2 Activate template

```txt
Given draft template with tasks
When authorized user activates
Then status becomes active
And ChecklistTemplateActivated is emitted
```

## 27.3 Staff cannot browse catalog

```txt
Given Staff user
When Staff requests Shared Checklist catalog
Then request is rejected
```

## 27.4 Assign ChecklistExecution

```txt
Given active Shared ChecklistTemplate
When Manager assigns to active user
Then ChecklistExecution is created assigned
And task executions are snapshotted
```

## 27.5 Start execution

```txt
Given assigned ChecklistExecution
When assignee clicks Start
Then execution becomes in_progress
```

## 27.6 Complete task

```txt
Given in_progress execution
When assignee completes task
Then task status becomes done
```

## 27.7 Skip task

```txt
Given in_progress execution
When assignee skips task
Then task status becomes skipped
And skipped_reason may be empty
```

## 27.8 Create Observation from task

```txt
Given checklist task execution
When user creates Observation from task
Then Observation has source checklist
And checklist_task_execution_id is stored
And task status becomes observation_created
```

## 27.9 Complete execution

```txt
Given all task executions are done/skipped/observation_created
When last task is processed
Then ChecklistExecution becomes completed
```

## 27.10 Existing execution unaffected by template update

```txt
Given execution created from template
When template is modified
Then execution task snapshots remain unchanged
```

## 27.11 Personal checklist privacy

```txt
Given Personal Checklist created by user A
When user B requests it
Then request is rejected
```

## 27.12 Personal checklist in execution feed

```txt
Given user created Personal Checklist
When user opens Execution Feed
Then Personal Checklist appears
```

---

# 28. Décisions validées — index

| Décision | Statut |
|---|---:|
| MVP = Shared + Personal Checklists | Validé |
| Shared = routine établissement standardisée assignable | Validé |
| Personal = routine privée réutilisable non assignable | Validé |
| Modèle Template / Execution / TaskTemplate / TaskExecution | Validé |
| Shared Checklist = ChecklistTemplate établissement | Validé |
| Assignée = ChecklistExecution | Validé |
| ChecklistExecution visible Execution Feed user concerné | Validé |
| Checklist ≠ Action | Validé |
| Execution Feed contient Actions + Shared Executions + Personal | Validé |
| 1 ChecklistExecution = 1 assignee | Validé |
| Plusieurs personnes = plusieurs executions | Validé |
| active réservé au template catalogue | Validé |
| Template statuses draft/active/archived | Validé |
| Execution statuses assigned/in_progress/completed/canceled | Validé |
| TaskTemplate sans status MVP | Validé |
| TaskExecution statuses pending/done/skipped/observation_created | Validé |
| Start manuel par clic utilisateur | Validé |
| Completion quand toutes tasks traitées | Validé |
| Task Observation = status observation_created | Validé |
| Task crée Observation via +Signaler uniquement | Validé |
| Texte court accepté via contexte checklist | Validé |
| skipped_reason optionnel | Validé |
| Required tasks non MVP | Validé |
| Proof task non MVP | Validé |
| Completion automatique sans validation manager | Validé |
| ChecklistExecution cancelable | Validé |
| Owner/Director cancel toutes ; Manager cancel domains | Validé |
| Personal même modèle Template/Execution | Validé |
| Personal Template privé réutilisable | Validé |
| Personal Task peut créer Observation | Validé |
| Personal Checklist dans Execution Feed créateur | Validé |
| Personal non assignable à autrui | Validé |
| Personal visible uniquement créateur | Validé |
| Shared catalog visible Owner/Director/Manager | Validé |
| Staff ne browse pas Shared catalog | Validé |
| Owner/Director/Manager créent Shared Templates | Validé |
| Owner/Director modifient tous ; Manager ses domains / créés par lui | Validé |
| Existing executions gardent snapshot | Validé |
| Pas de versioning complet MVP | Validé |
| Pas de récurrence MVP | Validé |
| recurrence_rule nullable post-MVP | Validé |
| Duplication template post-MVP | Validé |
| Metrics simples checklist MVP | Validé |
| Détection anomalies récurrentes non MVP | Validé |
| Events Checklist MVP | Validé |

---

# 29. Points à traiter dans d'autres domaines

## 29.1 AI Pipeline Contract

À cadrer :
- comment le contexte checklist est injecté dans le prompt ;
- comment la task influence le split ;
- comment la task influence detected_domains.

## 29.2 Notification Matrix

À cadrer :
- checklist assigned ;
- checklist started ;
- checklist completed ;
- task observation created ;
- checklist canceled.

## 29.3 Event Catalog

À cadrer :
- persistence events ;
- idempotence ;
- correlation_id ;
- causation_id ;
- event consumers.

## 29.4 Upload / Media Lifecycle

À cadrer si task proof photo post-MVP.

---

# 30. Recommandation finale

Le domaine Checklist est suffisamment cadré pour le MVP.

Décision centrale :

```txt
Checklist = routine d'exécution structurée.
Action = responsabilité issue d'un Signal.
Les deux cohabitent dans l'Execution Feed sans être confondus.
```

Le build doit maintenant s'appuyer sur :
- modèles Template / Execution ;
- separation Shared / Personal ;
- Personal strictement privé ;
- Shared catalogue réservé Owner/Director/Manager ;
- Staff uniquement via executions assignées ;
- Observations contextualisées via +Signaler ;
- no recurrence MVP ;
- snapshots pour préserver l'historique.

La prochaine étape logique est le **AI Pipeline Contract**, car il doit maintenant intégrer Observation, Onboarding context, Signal candidates, Aggregation, Domains et Checklist context.
