# Expression de besoin — Plan d’action Houston

## 1. Contexte

Houston doit remplacer les concepts actuels d’Action et de Checklist par un domaine unique : **Plan d’action**.

Le concept de **Checklist** doit disparaître complètement du produit, du code, des routes, des textes UI et de la documentation active.

Houston est en phase de développement. Les données existantes sont obsolètes. Une refonte destructive propre est acceptée. Il n’y a pas de contrainte de compatibilité progressive.

------

## 2. Objectif

Créer un modèle unique permettant de gérer :

- les plans d’action ponctuels ;
- les plans d’action créés depuis un signal ;
- les plans d’action réutilisables via catalogue ;
- les exécutions individuelles ou partagées ;
- les récurrences ;
- les tâches optionnelles ;
- les contributions multi-pôles ;
- les commentaires ;
- la création d’observations depuis une tâche ;
- la validation finale par le pôle pilote, Director ou Owner ;
- l’affichage unifié dans le feed d’exécution.

------

## 3. Vocabulaire produit

### Termes à utiliser

- Plan d’action
- Catalogue de plans d’action
- Exécution de plan
- Tâches du plan
- Pôle d’activité pilote
- Pôles d’activité impliqués
- Contribution

### Termes à supprimer

- Checklist
- Checklist template
- Checklist execution
- Process
- Flash todo
- Action comme concept produit autonome

------

## 4. Modèle cible

### Objets métier

```txt
ActionPlan
Définition du plan : titre, description, classification, réutilisable ou non.

ActionPlanTask
Tâches modèle optionnelles, 0 à 10 tâches maximum.

ActionPlanSchedule
Planification : assignés, récurrence, date de début, date de fin, horaires.

ActionPlanExecution
Instance visible dans le feed : statut, signal nullable, validation, commentaires.

ActionPlanExecutionTeam
Regroupement runtime par pôle d’activité dans une exécution.
Le pôle pilote est explicite.
Les pôles contributeurs émergent des assignés et des tâches.

ActionPlanExecutionTask
Snapshot des tâches sur l’exécution, rattaché à un pôle d’activité.

ActionPlanAssignee
Assignés runtime d’une exécution, rattachés à un pôle d’activité.
```

------

## 5. Création d’un plan d’action

Un plan d’action peut être créé depuis deux endroits.

### Depuis un signal

Le plan garde le lien au signal uniquement au niveau de l’exécution.

```txt
ActionPlanExecution.source_signal_id = signal.id
```

Si le plan est enregistré dans le catalogue, le modèle sauvegardé ne garde pas le lien au signal.

```txt
ActionPlan.source_signal_id = null
```

Le signal est donc un contexte d’exécution, pas une propriété permanente du modèle catalogue.

### Depuis le feed d’exécution

Le plan est créé sans signal.

```txt
source_signal_id = null
```

------

## 6. Catalogue de plans d’action

Un plan peut être réutilisable ou non.

### Champs

```txt
is_reusable: boolean
catalog_status: active | inactive | null
```

### Règles

```txt
is_reusable=false
→ non visible dans le catalogue
→ catalog_status=null
→ au moins une exécution ou planification doit être créée

is_reusable=true
→ visible dans le catalogue si catalog_status=active
→ peut être sauvegardé sans assigné
→ peut être utilisé plus tard depuis le catalogue
```

### Libellé UI

Utiliser :

```txt
Enregistrer dans la bibliothèque
```

Éviter :

```txt
Process
Template
Checklist
```

------

## 7. Statuts d’exécution

Les statuts cible sont :

```txt
in_progress
pending_validation
done
canceled
```

### Workflow

```txt
Création
→ in_progress

Marquer terminé + validation requise
→ pending_validation

Marquer terminé + validation non requise
→ done

Validation finale
→ done

Annulation
→ canceled

Réouverture
→ in_progress
```

Il n’y a plus :

```txt
open
reopened
accept
accepted_by
accepted_at
```

Un plan créé passe directement en cours.

------

## 8. Validation

Champ :

```txt
requires_validation: boolean
```

Règles :

```txt
requires_validation=true
→ mark_done passe l’exécution en pending_validation
→ validation finale requise

requires_validation=false
→ mark_done passe directement l’exécution en done
```

Peuvent valider :

```txt
Manager du pôle d’activité pilote
Director
Owner
```

Les managers contributeurs ne peuvent pas valider le plan final.

------

## 9. Assignation et chronologie

### Sans chronologie commune

Une exécution est créée par utilisateur et par occurrence.

Exemple :

```txt
5 utilisateurs
3 occurrences
= 15 exécutions
```

### Avec chronologie commune

Les utilisateurs partagent la même exécution.

Exemple :

```txt
5 utilisateurs
3 occurrences
= 3 exécutions partagées
```

Chaque exécution partagée possède plusieurs assignés.

------

## 10. Multi-pôle

Un plan d’action a toujours un pôle d’activité pilote.

Les autres pôles ne sont pas ajoutés manuellement comme “pôles impliqués”.

Ils émergent automatiquement des assignés et des tâches.

```txt
Pôle pilote
→ défini explicitement sur le plan

Pôles impliqués
→ déduits des assignés et des tâches rattachés à chaque pôle
```

### Pôle d’activité pilote

Exemple UI :

```txt
Pôle d’activité pilote
Restaurant
```

Le pôle pilote est responsable du plan global.

Le manager du pôle pilote a tous les droits sur le plan d’action, y compris sur les zones contributrices.

Il peut :

```txt
modifier le plan global
modifier la classification
assigner des membres
ajouter des tâches sur tous les pôles (runtime — voir décision 26.7)
modifier ou supprimer les tâches de tous les pôles (runtime — voir décision 26.7)
annuler le plan
marquer le plan comme terminé
valider la completion finale
rouvrir le plan
```

Il n’y a pas d’action dédiée :

```txt
Ajouter un pôle impliqué
```

Un pôle apparaît dans le plan uniquement s’il possède au moins un assigné ou au moins une tâche.

------

## 11. Pôles d’activité impliqués

Un pôle d’activité est affiché comme impliqué s’il possède :

```txt
au moins un assigné
OU
au moins une tâche
```

Exemple UI :

```txt
Pôles d’activité impliqués

Maintenance — En cours
Communication — Terminé
Hôtel
```

Règle importante :

```txt
Un pôle sans tâche n’a pas de statut de contribution.
```

Donc :

```txt
Pôle avec assigné(s) mais sans tâche
→ affiché dans les pôles impliqués
→ aucun statut de contribution affiché

Pôle avec tâche(s)
→ affiché dans les pôles impliqués
→ statut de contribution calculé

Pôle sans assigné et sans tâche
→ non affiché
```

------

## 12. Manager contributeur

Tous les managers peuvent contribuer au plan sur leur propre scope.

Un manager contributeur peut modifier sa contribution au plan.

Il peut :

```txt
ajouter un ou plusieurs membres de son staff
ajouter des tâches sur son pôle (runtime — voir décision 26.7)
modifier les tâches de son pôle
supprimer les tâches de son pôle
```

Il ne peut pas :

```txt
changer le pôle d’activité pilote
valider le plan final
annuler tout le plan
rouvrir tout le plan
modifier les tâches d’un autre pôle
assigner du staff hors de son scope
modifier la classification globale du plan
```

------

## 13. Staff

Un staff voit toutes les tâches du plan pour comprendre le contexte global.

Mais il ne peut agir que sur les tâches de son scope.

Règle exacte :

```txt
user est assigné à l’exécution
ET task.execution_team.business_unit est dans son scope
```

Exemples :

```txt
Staff Restaurant
→ peut cocher les tâches Restaurant

Staff Maintenance
→ peut cocher les tâches Maintenance

Staff Communication
→ peut cocher les tâches Communication
```

Les tâches hors scope sont visibles mais non actionnables.

------

## 14. Tâches

Les tâches sont optionnelles.

Règles :

```txt
0 à 10 tâches maximum
chaque tâche appartient à un pôle d’activité
les tâches sont snapshotées sur l’exécution
la complétion des tâches ne change jamais le statut global de l’exécution
```

Statuts de tâche :

```txt
pending
done
skipped
observation_created
```

Une tâche peut créer une observation.

```txt
ActionPlanExecutionTask → Observation
```

Créer une observation depuis une tâche ne change pas le statut global du plan.

------

## 15. Statut de contribution

Le statut de contribution est uniquement informatif.

Il est calculé uniquement pour les pôles ayant au moins une tâche.

Il n’y a :

```txt
aucun bouton
aucune action utilisateur
aucune transition métier manuelle
aucune validation par équipe
```

### Statuts affichés

```txt
En cours
Terminé
```

### Calcul

Pour chaque pôle ayant au moins une tâche :

```txt
Si toutes les tâches du pôle sont :
- done
- skipped
- observation_created

Alors contribution = Terminé

Sinon contribution = En cours
```

Cas particulier :

```txt
Si le pôle n’a aucune tâche
→ aucun statut de contribution affiché
```

Le statut de contribution ne change jamais le statut global du plan.

------

## 16. Organisation UI des tâches

Dans le détail du plan, les tâches sont organisées par pôle d’activité.

Exemple :

```txt
Restaurant
- T1
- T2
- T4

Maintenance
- T3
- T6

Communication
- T5
- T7
```

Sur une section pôle :

```txt
Maintenance
Contribution : En cours
Assignées : Hugo, Emma
```

Si le pôle a des assignés mais aucune tâche :

```txt
Hôtel
Assignées : Sarah
```

Ne pas afficher :

```txt
Contribution : En cours
Contribution : Terminé
Aucune tâche
```

Pour un staff :

```txt
Toutes les tâches sont visibles.
Seules les tâches de son scope sont actionnables.
```

------

## 17. Commentaires

Les commentaires doivent être disponibles sur les exécutions de plan.

Modèle cible :

```txt
Comment
  signal_id nullable
  action_plan_execution_id nullable
```

Un commentaire doit avoir exactement un parent métier :

```txt
signal_id
OU action_plan_execution_id
```

------

## 18. Feed d’exécution

Le feed ne doit plus retourner deux types `action` et `checklist`.

Cible :

```txt
item_type = action_plan_execution
```

La carte feed affiche :

```txt
titre
description courte
statut
pôle d’activité pilote
pôles impliqués si plusieurs
signal lié si présent
assignés
deadline / heure de fin
maximum 3 tâches visibles
état pending_validation si applicable
```

Les pôles impliqués affichés dans le feed sont déduits des assignés et des tâches.

Si aucune tâche n’existe, la section tâches n’est pas affichée.

------

## 19. UX mobile-first

Le formulaire de création doit être mobile-first.

Sections recommandées :

```txt
Signal lié
Titre
Description
Classification
Pôle d’activité pilote
Tâches
Assignés
Chronologie
Validation requise
Enregistrer dans la bibliothèque
```

Il n’y a pas de section obligatoire :

```txt
Pôles d’activité impliqués
```

Les pôles impliqués apparaissent automatiquement selon les assignés et les tâches créés.

La configuration des assignés et de la chronologie doit utiliser une bottom sheet sur mobile.

Chaque assigné peut avoir sa propre chronologie.

Une option permet d’activer une chronologie commune.

------

## 20. Catalogue de plans d’action

Page :

```txt
Catalogue de plans d’action
```

Contenu :

```txt
header
texte d’aide
recherche par titre
filtre par pôle d’activité pilote
sections dynamiques par pôle pilote
cartes de plans
bouton “Utiliser”
```

La carte catalogue affiche :

```txt
titre
description courte
pôle d’activité pilote
nombre de tâches
nombre de pôles déduits des tâches si > 1
bouton Utiliser
```

Ne pas afficher :

```txt
Tous les jours 08:00
badge ouverture salle
badge Process
badge Checklist
```

------

## 21. API cible

```txt
GET  /action-plans/
POST /action-plans/
GET  /action-plans/{id}/
PATCH /action-plans/{id}/
POST /action-plans/{id}/activate/
POST /action-plans/{id}/deactivate/
POST /action-plans/{id}/use/

GET  /action-plan-executions/{id}/
POST /action-plan-executions/{id}/mark-done/
POST /action-plan-executions/{id}/validate/
POST /action-plan-executions/{id}/reopen/
POST /action-plan-executions/{id}/cancel/

POST /action-plan-execution-tasks/{id}/mark-done/
POST /action-plan-execution-tasks/{id}/skip/
POST /action-plan-execution-tasks/{id}/create-observation/
```

À supprimer :

```txt
/actions/{id}/accept/
/checklist-templates/*
/checklist-executions/*
```

------

## 22. Realtime et notifications

Toute mutation significative doit déclencher une invalidation realtime minimale.

Événements attendus :

```txt
action_plan.created
action_plan.updated
action_plan_execution.created
action_plan_execution.updated
action_plan_execution.canceled
action_plan_execution.done
action_plan_execution.pending_validation
action_plan_execution_task.updated
action_plan_assignee.updated
```

Le payload realtime doit rester minimal.

Le frontend invalide et refetch. Il ne reconstruit pas l’état métier localement.

------

## 23. Règles finales multi-pôles

```txt
Un plan a toujours un pôle d’activité pilote.

Les pôles impliqués ne sont pas ajoutés manuellement.

Un pôle apparaît dans le plan s’il possède au moins un assigné ou au moins une tâche.

Un pôle a un statut de contribution uniquement s’il possède au moins une tâche.

Chaque tâche appartient à un pôle d’activité.

Le manager du pôle pilote a tous les droits sur le plan, y compris sur les zones contributrices.

Un manager contributeur peut modifier uniquement la contribution de son pôle.

Tous les managers peuvent ajouter des assignés de leur propre scope.

Un staff voit toutes les tâches, mais agit uniquement sur les tâches de son scope.

Le statut de contribution est calculé automatiquement depuis les tâches.

Seul le pôle pilote, Director ou Owner peut valider le plan final.
```

------

## 24. Hors périmètre V1

Non inclus dans cette évolution :

```txt
validation par tous les assignés
bouton manuel “contribution terminée”
completion_policy avancée
ajout manuel d’un pôle impliqué
RRULE complexe
preuve photo obligatoire
historique analytique avancé
marketplace de plans
approbation des modèles de catalogue
offline mutation queue
```

------

## 25. Critères d’acceptation

La refonte est validée si :

```txt
1. Le terme Checklist a disparu de l’UI active.
2. Le feed affiche uniquement des exécutions de plan.
3. Un plan peut être créé depuis un signal.
4. Un plan peut être créé depuis le feed.
5. Un plan peut être enregistré dans le catalogue.
6. Un plan enregistré depuis un signal ne garde pas le lien au signal.
7. Une exécution peut être individuelle ou partagée.
8. Un plan a toujours un pôle d’activité pilote.
9. Les pôles impliqués sont déduits des assignés et des tâches.
10. Les tâches sont organisées par pôle d’activité.
11. Les tâches ne changent jamais le statut global de l’exécution.
12. Le statut de contribution est calculé automatiquement uniquement pour les pôles ayant au moins une tâche.
13. Un pôle sans tâche n’a pas de statut de contribution.
14. Une tâche peut créer une observation.
15. Les commentaires fonctionnent sur les exécutions de plan.
16. Le workflow ne contient plus l’étape accepter.
17. Le backend reste source de vérité pour permissions, statuts et visibilité.
18. Les types OpenAPI frontend sont régénérés.
19. Les anciennes routes Checklist sont supprimées.
20. Les tests couvrent RBAC, feed, statuts, récurrence, tâches, observations, multi-pôles, assignés et realtime.
```

------

## 26. Décisions §26 — voir decision log

**Statut Lot -1 :** décisions §26 verrouillées (sign-off 2026-06-28).  
**Arbitrages §26 :** [`decisions_plan_action.md`](decisions_plan_action.md) (`authoritative`)

Les ambiguïtés §26 sont tranchées dans le decision log. Ce tableau est un index — ne pas recopier les règles ici.

| ID | Sujet | Decision log |
|----|-------|--------------|
| 26.1 | Modification globale par un manager contributeur | [decision 26.1](decisions_plan_action.md#decision-26-1) |
| 26.2 | Assignation cross-scope | [decision 26.2](decisions_plan_action.md#decision-26-2) |
| 26.3 | Pôle avec assigné mais sans tâche | [decision 26.3](decisions_plan_action.md#decision-26-3) |
| 26.4 | Completion d'une exécution partagée | [decision 26.4](decisions_plan_action.md#decision-26-4) |
| 26.5 | Signal lié — sync exécutions | [decision 26.5](decisions_plan_action.md#decision-26-5) |
| 26.6 | Plans catalogue multi-pôles | [decision 26.6](decisions_plan_action.md#decision-26-6) |
| 26.7 | Tâches modèle multi-pôles | [decision 26.7](decisions_plan_action.md#decision-26-7) |
| 26.8 | Staff multi-scope | [decision 26.8](decisions_plan_action.md#decision-26-8) |
| 26.9 | Suppression d'un pôle visible | [decision 26.9](decisions_plan_action.md#decision-26-9) |
| 26.10 | Statut contribution et `observation_created` | [decision 26.10](decisions_plan_action.md#decision-26-10) |
| 26.11 | Assigné sans tâche | [decision 26.11](decisions_plan_action.md#decision-26-11) |
| 26.12 | Récurrence et contributeurs | [decision 26.12](decisions_plan_action.md#decision-26-12) |

Arbitrage création vs runtime (§10 / §26.6–26.7) : voir [Arbitrages](decisions_plan_action.md#arbitrages) dans le decision log.  
Récurrence globale vs contributeurs : voir [decision 26.12](decisions_plan_action.md#decision-26-12).