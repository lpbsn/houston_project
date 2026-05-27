# Houston — RBAC & Permissions Domain

**Version:** v0.1  
**Date:** 2026-05-22  
**Statut:** Décisions MVP validées  
**Périmètre:** Houston MVP — Mama Shelter Nice  
**Document parent:** `Houston_mvp_cadrage_p0.md`

---

# 1. Objectif du document

Ce document formalise le domaine **RBAC / Permissions** de Houston pour le MVP.

Il définit :
- les rôles ;
- leur scope ;
- les règles de visibilité ;
- les droits par rôle ;
- les règles des feeds ;
- les règles liées aux Signals ;
- les règles liées aux Actions ;
- les règles liées aux Checklists ;
- les règles de mentions ;
- les principes backend de résolution des permissions ;
- les implications techniques pour le build.

Ce document sert de référence pour :
- Product Owner ;
- Product Designer ;
- Tech Lead ;
- Backend ;
- Frontend ;
- QA / tests fonctionnels.

---

# 2. Principes structurants

## 2.1 Principe central

Houston ne repose pas sur une privatisation forte de l'information opérationnelle.

Le produit privilégie :
- la visibilité opérationnelle ;
- la coordination ;
- la réduction du bruit ;
- la capacité à filtrer et personnaliser les vues.

Le modèle retenu est donc :

```txt
Information opérationnelle largement visible
+
Actions de pilotage contrôlées par rôle et domaine
```

## 2.2 Principe clé

```txt
Voir ≠ agir
```

Un utilisateur peut voir une information sans pouvoir :
- créer une Action ;
- assigner une Action ;
- valider une Action ;
- annuler un Signal ;
- modifier une checklist ;
- administrer un utilisateur.

## 2.3 Backend authority

Les permissions et la visibilité sont toujours résolues côté backend.

Le frontend :
- n'est jamais source d'autorité ;
- ne décide pas seul des permissions ;
- ne doit pas exposer d'actions interdites ;
- ne doit pas recevoir de données non autorisées selon le contexte backend.

Le websocket :
- ne bypass jamais les règles backend ;
- doit recevoir des événements déjà filtrés ou explicitement autorisés ;
- ne doit jamais diffuser un événement brut à tout le monde sans résolution de visibilité.

## 2.4 Permissions MVP

Les permissions sont **codées en dur** au MVP.

```txt
MVP
= permissions fixes
= non configurables par client
= pas de permission builder
= pas de matrice administrable
```

Les permissions configurables sont hors MVP.

---

# 3. Modèle d'identité et scope des rôles

## 3.1 Décision validée

Le rôle ne vit pas directement dans `User`.

Le rôle vit dans `EstablishmentMembership`.

```txt
User
↔ EstablishmentMembership
↔ Establishment
```

## 3.2 Modèle logique

```txt
User
├── id
├── first_name
├── last_name
├── email
├── authentication data
└── timestamps

EstablishmentMembership
├── id
├── user_id
├── establishment_id
├── role
├── operational_domains[]
├── status
└── timestamps

Establishment
├── id
├── organization_id
├── name
└── runtime context
```

## 3.3 Pourquoi

Un même utilisateur peut potentiellement avoir :
- un rôle différent selon l'établissement ;
- des domaines différents selon l'établissement ;
- un statut différent selon l'établissement.

Exemple :

```txt
User A
├── Manager à Mama Shelter Nice
└── Staff au Centre Commercial Nancy
```

Même si 95% des utilisateurs appartiennent à un seul établissement, ce modèle évite une dette future.

## 3.4 Règle UX

```txt
Si l'utilisateur a une seule membership :
    ne pas afficher de switch établissement

Si l'utilisateur a plusieurs memberships :
    afficher un switch établissement
```

---

# 4. Rôles MVP

## 4.1 Rôles disponibles

Les rôles MVP sont :

```txt
OWNER
DIRECTOR
MANAGER
STAFF
```

## 4.2 Hiérarchie fonctionnelle

```txt
OWNER
    ↓
DIRECTOR
    ↓
MANAGER
    ↓
STAFF
```

## 4.3 Définition des rôles

| Rôle | Définition MVP |
|---|---|
| Owner | Gouvernance globale, accès complet, gestion business et structurante |
| Director | Supervision complète de l'établissement |
| Manager | Coordination opérationnelle sur ses domaines |
| Staff | Utilisateur terrain : remonte, consulte, exécute |

## 4.4 Scope

Tous les rôles sont **establishment-scoped** via `EstablishmentMembership`.

```txt
role = membership.role
domains = membership.operational_domains
status = membership.status
```

---

# 5. Concepts de visibilité

## 5.1 Vue personnelle

La vue personnelle est la vue par défaut.

Elle sert à réduire le bruit en affichant en priorité ce qui concerne l'utilisateur.

## 5.2 Vue générale

La vue générale permet d'accéder à une vision plus large.

Elle n'est pas forcément équivalente selon les feeds :
- Signal Feed : vue générale large ;
- Execution Feed : vue générale limitée aux responsabilités opérationnelles.

## 5.3 Filtres domaines

Les filtres par domaine existent en parallèle des vues.

Ils permettent de filtrer les feeds par :
- Maintenance ;
- Housekeeping ;
- Security ;
- Food Service ;
- Guest Experience ;
- Pricing ;
- autres domains de l'établissement.

## 5.4 Important

Les filtres ne sont pas des permissions.

```txt
Filtre domaine = navigation / réduction du bruit
Permission = règle backend
```

---

# 6. Signal Feed

## 6.1 Principe

Le Signal Feed sert à la supervision opérationnelle.

Il affiche des Signals.

Un Signal représente une situation opérationnelle vivante.

## 6.2 Règle domain

Les Signals portent :

```txt
detected_domains[]
```

Ces domaines servent à :
- alimenter la vue personnelle ;
- router les Signals vers les bons managers ;
- notifier les bons utilisateurs ;
- filtrer le feed ;
- mesurer la qualité IA ;
- autoriser l'action des managers de ces domaines.

## 6.3 Owner — Signal Feed

```txt
Owner Signal Feed
├── vue par défaut : tous les Signals de l'établissement
├── vue générale : tous les Signals de l'établissement
└── filtres domaines : disponibles
```

## 6.4 Director — Signal Feed

```txt
Director Signal Feed
├── vue par défaut : tous les Signals de l'établissement
├── vue générale : tous les Signals de l'établissement
└── filtres domaines : disponibles
```

## 6.5 Manager — Signal Feed

Décision validée :

```txt
Manager Signal Feed
├── vue par défaut : Signals de ses domaines
├── vue générale : tous les Signals de l'établissement
└── filtres domaines : disponibles
```

### Règle personnelle Manager

```txt
Signal visible dans la vue personnelle Manager
si signal.detected_domains intersecte manager.operational_domains
```

### Règle générale Manager

```txt
Vue générale Manager
= tous les Signals de l'établissement
```

## 6.6 Staff — Signal Feed

Décision validée :

```txt
Staff Signal Feed
├── vue par défaut : Signals de ses domaines
├── vue générale : tous les Signals de l'établissement
└── filtres domaines : disponibles
```

### Règle personnelle Staff

```txt
Signal visible dans la vue personnelle Staff
si signal.detected_domains intersecte staff.operational_domains
```

### Règle générale Staff

```txt
Vue générale Staff
= tous les Signals de l'établissement
```

## 6.7 Pourquoi le Staff voit aussi des Signals

Houston n'a pas de règle de privatisation forte de l'information opérationnelle.

Le Staff peut donc consulter les Signals, mais ses capacités d'action restent limitées.

```txt
Staff peut voir
Staff ne peut pas piloter
```

---

# 7. Execution Feed

## 7.1 Principe

Le Execution Feed sert à afficher ce que l'utilisateur doit exécuter, suivre ou superviser.

Il contient :
- Actions ;
- Shared Checklist Executions ;
- Personal Checklists.

## 7.2 Distinction avec Signal Feed

```txt
Signal Feed
= supervision des situations

Execution Feed
= exécution des responsabilités
```

---

# 8. Execution Feed — Staff

## 8.1 Décision validée

```txt
Staff Execution Feed
├── Actions assignées à lui
├── Shared Checklist Executions assignées à lui
└── Personal Checklists créées par lui
```

## 8.2 Vue par défaut Staff

```txt
Staff Execution Feed par défaut
=
ses Actions assignées
+
ses Shared Checklist Executions assignées
+
ses Personal Checklists
```

## 8.3 Vue générale Staff

Aucune vue générale d'exécution n'est prévue au MVP pour Staff.

Raison :
- le Staff exécute ce qui lui est attribué ;
- il ne supervise pas l'exécution des autres ;
- il ne pilote pas les responsabilités opérationnelles.

## 8.4 Permissions Staff dans Execution Feed

| Action | Autorisé |
|---|---:|
| Voir ses Actions assignées | Oui |
| Voir les Actions non assignées à lui | Non |
| Accepter Action assignée | Oui |
| Marquer Action done | Oui |
| Valider Action | Non |
| Reopen Action | Non |
| Annuler Action | Non |
| Voir ses Shared Checklist Executions assignées | Oui |
| Exécuter Shared Checklist assignée | Oui |
| Créer Personal Checklist | Oui |
| Voir Personal Checklists d'un autre user | Non |

---

# 9. Execution Feed — Manager

## 9.1 Décision validée

Le Manager Execution Feed inclut :
- les Actions qu'il a créées ;
- les Actions de ses domaines ;
- ses Personal Checklists ;
- les Shared Checklist Executions qu'il a attribuées ;
- les Shared Checklist Executions qui lui sont attribuées ;
- en vue générale, les Actions et Shared Checklist Executions de ses domaines.

## 9.2 Vue par défaut Manager

```txt
Manager Execution Feed par défaut
=
Actions créées par lui
+
Actions de ses domaines
+
Personal Checklists à lui
+
Shared Checklist Executions attribuées par lui
+
Shared Checklist Executions attribuées à lui
```

## 9.3 Vue générale Manager

Décision validée :

```txt
Manager Execution Feed général
=
Actions de ses domaines
+
Shared Checklist Executions de ses domaines
```

## 9.4 Règles Actions Manager

```txt
Manager voit une Action si :
- action.created_by_id = manager.id
OR
- action.operational_domain ∈ manager.operational_domains
```

## 9.5 Règles Shared Checklist Executions Manager

```txt
Manager voit une Shared Checklist Execution dans sa vue par défaut si :
- checklist_execution.assigned_by_id = manager.id
OR
- checklist_execution.assigned_to_id = manager.id
```

```txt
Manager voit une Shared Checklist Execution dans sa vue générale si :
- checklist_execution.operational_domains intersecte manager.operational_domains
```

## 9.6 Personal Checklist Manager

```txt
Manager voit uniquement ses propres Personal Checklists.
```

Les Personal Checklists restent privées.

---

# 10. Execution Feed — Director

## 10.1 Principe

Le Director supervise tout l'établissement.

## 10.2 Vue par défaut Director

```txt
Director Execution Feed par défaut
=
Actions de l'établissement
+
Shared Checklist Executions de l'établissement
+
ses Personal Checklists
```

## 10.3 Vue générale Director

```txt
Director Execution Feed général
=
Actions de l'établissement
+
Shared Checklist Executions de l'établissement
```

## 10.4 Personal Checklists

Le Director ne voit pas les Personal Checklists des autres utilisateurs par défaut.

```txt
Personal Checklist = privée
```

---

# 11. Execution Feed — Owner

## 11.1 Principe

L'Owner possède une capacité de supervision complète.

## 11.2 Vue par défaut Owner

```txt
Owner Execution Feed par défaut
=
Actions de l'établissement
+
Shared Checklist Executions de l'établissement
+
ses Personal Checklists
```

## 11.3 Vue générale Owner

```txt
Owner Execution Feed général
=
Actions de l'établissement
+
Shared Checklist Executions de l'établissement
```

## 11.4 Personal Checklists

L'Owner ne voit pas les Personal Checklists des autres utilisateurs par défaut.

```txt
Personal Checklist = privée
```

---

# 12. Permissions — Observations

## 12.1 Principe

Tout rôle peut créer une Observation.

## 12.2 Matrice

| Action Observation | Owner | Director | Manager | Staff |
|---|---:|---:|---:|---:|
| Créer Observation texte | Oui | Oui | Oui | Oui |
| Créer Observation audio | Oui | Oui | Oui | Oui |
| Ajouter photos optionnelles | Oui | Oui | Oui | Oui |
| Créer Observation depuis checklist task | Oui | Oui | Oui | Oui si checklist assignée |
| Voir ses Observations | Oui | Oui | Oui | Oui |
| Voir toutes les Observations brutes | Oui | Oui | À cadrer | À cadrer |
| Supprimer Observation | À cadrer | À cadrer | À cadrer | À cadrer |

## 12.3 P0 restant

La visibilité de l'Observation brute reste à cadrer dans le domaine Observation.

Ce document RBAC fixe seulement que tous les rôles peuvent créer des Observations.

---

# 13. Permissions — Signals

## 13.1 Signal Feed

| Action Signal | Owner | Director | Manager | Staff |
|---|---:|---:|---:|---:|
| Voir Signal Feed personnel | Oui | Oui | Oui | Oui |
| Voir Signal Feed général | Oui | Oui | Oui | Oui |
| Filtrer par domaine | Oui | Oui | Oui | Oui |
| Voir détail Signal | Oui | Oui | Oui | Oui |
| Créer Signal manuellement | À cadrer | À cadrer | À cadrer | Non |
| Créer Action depuis Signal | Oui | Oui | Oui | Non |
| Commenter Signal | Oui | Oui | Oui | Oui à cadrer selon contexte |
| Pin Signal | Oui | Oui | Oui | Non |
| Modifier urgence Signal | Oui | Oui | Oui | Non |
| Résoudre Signal | Oui | Oui | Oui | Non |
| Annuler Signal | Oui | Oui | Oui | Non |
| Archiver Signal | Oui | Oui | À cadrer | Non |

## 13.2 Manager et Signals hors domaine

Le Manager peut voir les Signals hors domaine via la vue générale.

Mais il n'est pas forcément autorisé à piloter tous les Signals hors domaine.

Règle MVP recommandée :

```txt
Manager peut agir sur un Signal
si signal.detected_domains intersecte manager.operational_domains
```

Exception possible à cadrer :
- Manager peut créer une Action hors domaine depuis la vue générale ?
- Manager peut transférer ou ajouter un domaine ?
- Manager peut seulement commenter ?

Décision non finalisée.

## 13.3 Staff et Signals

Le Staff peut consulter les Signals.

Mais il ne peut pas :
- créer une Action ;
- assigner une Action ;
- valider une Action ;
- résoudre un Signal ;
- annuler un Signal ;
- pin un Signal ;
- modifier l'urgence.

---

# 14. Permissions — Actions

## 14.1 Création

| Action | Owner | Director | Manager | Staff |
|---|---:|---:|---:|---:|
| Créer Action | Oui | Oui | Oui | Non |
| Créer Action depuis Signal | Oui | Oui | Oui | Non |
| Créer Action libre sans Signal | À cadrer | À cadrer | À cadrer | Non |

## 14.2 Assignation

| Action | Owner | Director | Manager | Staff |
|---|---:|---:|---:|---:|
| Assigner Action | Oui | Oui | Oui | Non |
| Réassigner Action | Oui | Oui | Oui | Non |
| S'assigner Action | Oui | Oui | Oui | Non |

## 14.3 Exécution

| Action | Owner | Director | Manager | Staff |
|---|---:|---:|---:|---:|
| Accepter Action assignée | Oui | Oui | Oui | Oui |
| Marquer Action in_progress | Oui | Oui | Oui | Oui si assignée |
| Marquer Action done | Oui | Oui | Oui si assignée | Oui si assignée |
| Ajouter commentaire Action | Oui | Oui | Oui | Oui si assignée |
| Ajouter preuve | Oui | Oui | Oui si assignée | Oui si assignée |

## 14.4 Validation

Décision validée :

```txt
Si un Manager s'assigne une Action,
il peut la valider lui-même.
Aucune règle spécifique n'est ajoutée pour ce cas.
```

| Action | Owner | Director | Manager | Staff |
|---|---:|---:|---:|---:|
| Valider Action | Oui | Oui | Oui | Non |
| Valider sa propre Action | Oui | Oui | Oui | Non |
| Reopen Action | Oui | Oui | Oui | Non |
| Annuler Action | Oui | Oui | Oui | Non |

## 14.5 Règle Manager

Le Manager peut valider les Actions de ses domaines.

```txt
Manager can validate action if:
action.operational_domain ∈ manager.operational_domains
```

Si le Manager est lui-même assigné à cette Action, il peut quand même la valider.

---

# 15. Permissions — Shared Checklists

## 15.1 Templates

| Action Shared Checklist Template | Owner | Director | Manager | Staff |
|---|---:|---:|---:|---:|
| Voir catalogue Shared Checklists | Oui | Oui | Oui | Non à confirmer |
| Créer template | Oui | Oui | Oui | Non |
| Modifier template | Oui | Oui | Oui si domaine compatible / créateur | Non |
| Archiver template | Oui | Oui | Oui si domaine compatible / créateur | Non |
| Supprimer template | À cadrer | À cadrer | À cadrer | Non |

## 15.2 Executions

| Action Shared Checklist Execution | Owner | Director | Manager | Staff |
|---|---:|---:|---:|---:|
| Créer execution | Oui | Oui | Oui | Non |
| Assigner execution | Oui | Oui | Oui | Non |
| Exécuter si assignée | Oui | Oui | Oui | Oui |
| Voir execution assignée à soi | Oui | Oui | Oui | Oui |
| Voir executions de ses domaines | Oui | Oui | Oui | Non |
| Valider completion | À cadrer | À cadrer | À cadrer | Non |

## 15.3 Staff

Décision maintenue :

```txt
Staff ne browse pas le catalogue Shared Checklists.
Staff voit les Shared Checklist Executions qui lui sont assignées.
```

## 15.4 Manager

Le Manager :
- crée des Shared Checklist Templates ;
- assigne des Shared Checklist Executions ;
- voit celles qu'il a attribuées ;
- voit celles qui lui sont attribuées ;
- voit en vue générale celles de ses domaines.

---

# 16. Permissions — Personal Checklists

## 16.1 Principe

Une Personal Checklist est privée.

```txt
Personal Checklist
= visible uniquement par son créateur
= réutilisable par son créateur
= non partageable
= non assignable
```

## 16.2 Matrice

| Action Personal Checklist | Owner | Director | Manager | Staff |
|---|---:|---:|---:|---:|
| Créer Personal Checklist | Oui | Oui | Oui | Oui |
| Voir ses Personal Checklists | Oui | Oui | Oui | Oui |
| Voir Personal Checklist d'un autre user | Non | Non | Non | Non |
| Modifier sa Personal Checklist | Oui | Oui | Oui | Oui |
| Supprimer / archiver sa Personal Checklist | Oui | Oui | Oui | Oui |
| Assigner Personal Checklist | Non | Non | Non | Non |
| Partager Personal Checklist | Non MVP | Non MVP | Non MVP | Non MVP |

---

# 17. Mentions

## 17.1 Décision validée

```txt
Mention = notification
Mention ≠ permission
```

## 17.2 Règles

Une mention :
- déclenche une notification ;
- ne donne pas automatiquement accès à un objet ;
- ne modifie pas les rôles ;
- ne modifie pas les domains ;
- ne modifie pas les memberships ;
- ne bypass pas le backend.

## 17.3 Exemple

```txt
Manager mentionne Staff dans un Signal.

Résultat :
- Staff reçoit une notification
- Staff ne reçoit pas de permission spéciale
- si une intervention est nécessaire, une Action doit être créée et assignée
```

---

# 18. Notifications et permissions

## 18.1 Principe

Une notification ne doit jamais exposer plus d'information que ce que l'utilisateur peut consulter dans l'app.

## 18.2 Règle

```txt
Notification payload
= minimal
= compatible avec permissions backend
= pas de contenu sensible inutile
```

## 18.3 P0 restant

La matrice de notifications reste à cadrer dans un document dédié.

---

# 19. Résolution backend recommandée

## 19.1 Service de permission

Créer un service backend explicite.

Exemples conceptuels :

```txt
PermissionService
AuthorizationPolicy
```

## 19.2 Exemples de méthodes

```txt
can_view_signal?(user:, signal:, establishment:)
can_create_action?(user:, signal:)
can_assign_action?(user:, action:)
can_validate_action?(user:, action:)
can_view_execution_feed?(user:, establishment:)
can_view_shared_checklist_execution?(user:, checklist_execution:)
can_create_shared_checklist_template?(user:, establishment:)
can_execute_checklist?(user:, checklist_execution:)
```

## 19.3 Recommandation backend

Utiliser des policies explicites.

Exemple conceptuel :

```txt
SignalPolicy.show?
  same_establishment? && member_active?

SignalPolicy.create_action?
  owner_or_director? || manager_with_matching_domain?

SignalPolicy.resolve?
  owner_or_director? || manager_with_matching_domain?
```

## 19.4 Règle critique

Toutes les queries doivent être establishment-scoped.

```txt
Signal.where(establishment_id: current_establishment.id)
```

Jamais :

```txt
Signal.all
```

---

# 20. Queries backend recommandées

## 20.1 Signal Feed Manager — vue personnelle

```rb
Signal
  .where(establishment_id: current_establishment.id)
  .where("detected_domains && ARRAY[?]::varchar[]", current_membership.operational_domains)
```

## 20.2 Signal Feed Manager — vue générale

```rb
Signal
  .where(establishment_id: current_establishment.id)
```

## 20.3 Staff Signal Feed — vue personnelle

```rb
Signal
  .where(establishment_id: current_establishment.id)
  .where("detected_domains && ARRAY[?]::varchar[]", current_membership.operational_domains)
```

## 20.4 Staff Signal Feed — vue générale

```rb
Signal
  .where(establishment_id: current_establishment.id)
```

## 20.5 Manager Execution Feed — vue par défaut

```rb
Action
  .where(establishment_id: current_establishment.id)
  .where(
    "created_by_id = :user_id OR operational_domain = ANY(:domains)",
    user_id: current_user.id,
    domains: current_membership.operational_domains
  )
```

## 20.6 Manager Execution Feed — Shared Checklists par défaut

```rb
ChecklistExecution
  .where(establishment_id: current_establishment.id)
  .where(
    "assigned_by_id = :user_id OR assigned_to_id = :user_id",
    user_id: current_user.id
  )
```

## 20.7 Manager Execution Feed — vue générale

```rb
Action
  .where(establishment_id: current_establishment.id)
  .where(operational_domain: current_membership.operational_domains)
```

```rb
ChecklistExecution
  .where(establishment_id: current_establishment.id)
  .where("operational_domains && ARRAY[?]::varchar[]", current_membership.operational_domains)
```

## 20.8 Staff Execution Feed

```rb
Action
  .where(establishment_id: current_establishment.id)
  .where(assigned_to_id: current_user.id)
```

```rb
ChecklistExecution
  .where(establishment_id: current_establishment.id)
  .where(assigned_to_id: current_user.id)
```

```rb
PersonalChecklist
  .where(created_by_id: current_user.id)
```

---

# 21. Frontend UX rules

## 21.1 Signal Feed

Tous les rôles peuvent avoir :
- une vue personnelle ;
- une vue générale ;
- des filtres domain.

## 21.2 Execution Feed

Le contenu dépend du rôle.

| Rôle | Default Execution Feed | General Execution Feed |
|---|---|---|
| Owner | Actions + Shared Checklists établissement + ses Personal | Actions + Shared Checklists établissement |
| Director | Actions + Shared Checklists établissement + ses Personal | Actions + Shared Checklists établissement |
| Manager | Actions créées + Actions domaines + Shared assignées par/à lui + ses Personal | Actions domaines + Shared domaines |
| Staff | Actions assignées + Shared assignées + ses Personal | Non MVP |

## 21.3 Actions UI

Le frontend doit masquer les actions interdites.

Exemple :
- Staff ne voit pas bouton “Créer Action” ;
- Staff ne voit pas bouton “Valider Action” ;
- Manager ne voit pas bouton “Modifier rôle user” ;
- Staff ne voit pas bouton “Créer Shared Checklist”.

Mais le backend doit quand même refuser toute action interdite.

---

# 22. Matrice globale synthétique

| Capability | Owner | Director | Manager | Staff |
|---|---:|---:|---:|---:|
| Créer Observation | Oui | Oui | Oui | Oui |
| Signal Feed personnel | Oui | Oui | Oui | Oui |
| Signal Feed général | Oui | Oui | Oui | Oui |
| Filtrer Signals par domaine | Oui | Oui | Oui | Oui |
| Créer Action | Oui | Oui | Oui | Non |
| Assigner Action | Oui | Oui | Oui | Non |
| Exécuter Action assignée | Oui | Oui | Oui | Oui |
| Valider Action | Oui | Oui | Oui | Non |
| Valider sa propre Action | Oui | Oui | Oui | Non |
| Pin Signal | Oui | Oui | Oui | Non |
| Modifier urgence Signal | Oui | Oui | Oui | Non |
| Résoudre Signal | Oui | Oui | Oui | Non |
| Annuler Signal | Oui | Oui | Oui | Non |
| Créer Shared Checklist Template | Oui | Oui | Oui | Non |
| Voir catalogue Shared Checklist | Oui | Oui | Oui | Non |
| Assigner Shared Checklist Execution | Oui | Oui | Oui | Non |
| Exécuter Shared Checklist assignée | Oui | Oui | Oui | Oui |
| Créer Personal Checklist | Oui | Oui | Oui | Oui |
| Voir Personal Checklist d'autrui | Non | Non | Non | Non |
| Inviter user | Oui | Oui | Non MVP | Non |
| Modifier rôle user | Oui | Oui sauf Owner | Non | Non |
| Modifier domains user | Oui | Oui | Non | Non |
| Désactiver user | Oui | Oui sauf Owner | Non | Non |

---

# 23. Points explicitement non couverts / à cadrer plus tard

## 23.1 Observation

- suppression Observation ;
- modification Observation ;
- visibilité Observation brute ;
- Observation inexploitable ;
- Observation sans Signal ;
- Observation multi-Signal.

## 23.2 Signal

- création manuelle de Signal ;
- droit Manager sur Signal hors domaine ;
- fusion / split de Signal ;
- reopen Signal ;
- archivage ;
- résolution sans Action.

## 23.3 Action

- statut initial ;
- acceptation obligatoire ou non ;
- refus ;
- preuve obligatoire ;
- commentaire obligatoire ;
- escalade ;
- SLA.

## 23.4 Checklist

- versioning template ;
- récurrence ;
- validation completion ;
- skip reason obligatoire ou non ;
- preuve obligatoire sur task ;
- visibilité catalogue Staff à confirmer.

## 23.5 Notification

- matrice complète des notifications ;
- canaux ;
- payload ;
- priorités ;
- fréquence ;
- anti-spam.

---

# 24. Décisions validées — index

| Décision | Statut |
|---|---:|
| Rôles dans EstablishmentMembership | Validé |
| Permissions codées en dur au MVP | Validé |
| Pas de privatisation forte de l'information | Validé |
| Vue personnelle + vue générale | Validé |
| Filtres domain en parallèle | Validé |
| Manager Signal Feed par défaut = ses domains | Validé |
| Manager Signal Feed général = tous Signals | Validé |
| Staff Signal Feed par défaut = ses domains | Validé |
| Staff Signal Feed général = tous Signals | Validé |
| Staff Execution Feed = ses Actions + Shared assignées + Personal | Validé |
| Manager Execution Feed défaut = Actions créées + Actions domains + Checklists assignées/par lui/à lui + Personal | Validé |
| Manager Execution Feed général = Actions + Shared Checklists de ses domains | Validé |
| Mention = notification, pas permission | Validé |
| Manager peut valider sa propre Action | Validé |
| Personal Checklist privée | Validé |
| Shared Checklist administrée par Owner/Director/Manager | Validé |
| Staff ne crée pas Action | Validé |
| Staff ne valide pas Action | Validé |

---

# 25. Recommandation finale

Le domaine RBAC / Permissions est suffisamment cadré pour le MVP.

Il peut servir de base à :
- modèles backend ;
- policies backend ;
- écrans frontend ;
- tests fonctionnels ;
- tests d'autorisation ;
- documentation produit.

La prochaine étape logique est de transformer ce document en :
1. policies backend ;
2. matrice de tests QA ;
3. stories MVP par rôle ;
4. règles de navigation frontend.
