# SPORE — Cadrage produit & UX
## Formulaires + Bibliothèque mobile

**Statut : validé pour cadrage**  
**Périmètre : mobile web + Capacitor iOS/Android**  
**Desktop : ne pas dégrader l’existant ; référence fonctionnelle lorsque pertinent**  
**Hors scope : Feed/Pagination, Navigation/Transitions, calendrier Exécution**

---

## 1. Objectif

Refondre et consolider les parcours mobiles liés à la Bibliothèque et aux formulaires de création, d’utilisation, de planification et d’édition afin de rendre l’expérience :

- moderne ;
- rapide à comprendre sur le terrain ;
- sûre lors de la saisie ;
- cohérente entre mobile web et Capacitor ;
- maintenable et scalable côté frontend ;
- compatible avec les contrats backend existants.

Le chantier doit être pensé comme un parcours produit complet :

**Bibliothèque → modèle → utiliser → lancer / planifier → exécution**

et non comme une simple refonte graphique de champs de formulaire.

---

## 2. Principes validés

### 2.1 Même produit mobile

Mobile web et Capacitor iOS/Android doivent partager la même UI et les mêmes parcours.

Une divergence spécifique à iOS ou Android n’est acceptable que si elle répond à un comportement réellement natif et nécessaire.

### 2.2 Desktop

Le desktop existant sert de référence fonctionnelle lorsque pertinent mais ne contraint pas le layout mobile.

Le chantier ne doit pas dégrader :

- les parcours desktop ;
- les permissions ;
- les contrats API ;
- les comportements existants validés.

### 2.3 Pas de sur-abstraction

Ne pas créer :

- de design system générique ;
- de framework de formulaire ;
- de composant `Field` générique par principe ;
- d’abstraction destinée à des usages hypothétiques.

Factoriser uniquement la duplication réelle observée dans le repo.

### 2.4 Hiérarchie mobile

Ordre d’importance cible :

**contenu → tâches → organisation → planification → options**

La structure de l’interface ne doit pas simplement refléter l’ordre des propriétés du modèle de données.

### 2.5 Progressive disclosure

Les informations secondaires ou avancées ne doivent pas être visibles en permanence.

En particulier :

- configuration détaillée d’une tâche ;
- récurrence ;
- chronologie par assigné ;
- paramètres avancés ;
- métadonnées du modèle.

---

## 3. État actuel du repo

Le cœur du chantier se trouve principalement dans :

`apps/web/src/features/action-plans/`

avec des entrées produit depuis :

`apps/web/src/features/execution/`

et :

`apps/web/src/features/signals/`

Les briques existantes importantes comprennent notamment :

- `ActionPlanCreatePage`
- `ActionPlanExecutionEditPage`
- `ActionPlanTemplateDetailPage`
- `ActionPlanUseSheet`
- `ActionPlanTaskDraftEditor`
- `ActionPlanEventPlanningForm`
- les composants de planning date / heure / options
- les sheets d’assignation
- les helpers de validation
- les helpers de permissions
- les hooks de soumission
- le mapping des erreurs API
- la logique d’idempotence des soumissions de planning.

Le chantier doit préserver cette base métier lorsque son comportement est correct.

---

## 4. Architecture produit cible

Le produit doit distinguer clairement deux intentions.

### 4.1 Modèle

Un modèle décrit :

> ce qui devra être fait lorsque ce plan sera utilisé.

Il contient principalement :

- titre ;
- description ;
- pôle pilote ;
- tâches ;
- règles du modèle ;
- validation éventuelle.

Il ne représente pas encore une occurrence terrain.

### 4.2 Exécution

Une exécution répond à :

> quoi faire, qui le fait et quand.

Elle contient :

- contenu opérationnel ;
- assignation ;
- chronologie ;
- éventuelle récurrence ;
- état de réalisation ;
- validation.

Cette distinction doit être visible dans l’UX même lorsque le code sous-jacent reste partagé.

---

# 5. Parcours cible — Bibliothèque

## 5.1 Bibliothèque

La Bibliothèque reste une surface canonique dédiée.

Structure mobile cible :

- titre ;
- recherche ;
- filtres utiles ;
- liste une colonne ;
- cartes modèles ;
- CTA de création pour les utilisateurs autorisés.

Interactions :

- tap sur carte → détail du modèle ;
- utilisation possible depuis une action explicitement identifiable ;
- pas de duplication de catalogue dans Exécution.

La Bibliothèque actuelle doit être consolidée, pas reconstruite sans besoin.

---

# 6. Parcours cible — Détail modèle

Le détail doit répondre rapidement à :

1. qu’est-ce que ce modèle ?
2. que contient-il ?
3. quelle action puis-je réaliser ?

Hiérarchie cible :

```text
← Bibliothèque

Titre du modèle
Pôle pilote · Validation requise

Description

Tâches
  ...
  ...
  ...

Informations secondaires
  Créateur
  Dernière modification
  État

──────────────
[ Utiliser ce modèle ]
```

## Arbitrage validé

Un seul CTA principal :

**Utiliser ce modèle**

Les actions administratives comme Modifier, Activer, Désactiver ou Supprimer ne doivent pas concurrencer l’action métier principale.

Elles doivent être secondaires ou regroupées dans un menu contextuel lorsque cela est pertinent.

---

# 7. Parcours cible — Utiliser un modèle

L’utilisation d’un modèle devient une vraie surface mobile de lancement.

Le futur parcours ne doit pas reposer sur une grosse bottom sheet contenant tout le planning.

La bottom sheet reste adaptée aux choix courts et contextuels mais pas à un formulaire complet comprenant :

- assignés ;
- dates ;
- heures ;
- récurrence ;
- chronologie avancée.

Structure cible :

```text
← Modèle

Nom du modèle
3 tâches · Maintenance

QUI
Assignés
> Équipe maintenance

QUAND
● Maintenant
○ Planifier

[si Planifier]
Date / période
Heure
Répéter

OPTIONS
Validation requise
Options avancées >

──────────────
[ Lancer le plan ]
```

Le contenu du modèle n’a pas vocation à être entièrement réédité lors de ce parcours.

L’intention utilisateur est de lancer du travail à partir d’un modèle existant.

---

# 8. Maintenant vs Planifier

Le choix temporel doit être explicite et progressif.

État initial :

```text
Quand

[ Maintenant ] [ Planifier ]
```

Si `Planifier` :

```text
Début
Fin / durée

Répéter >
```

Si `Répéter` :

```text
Fréquence / jours
Fin de récurrence
```

Les options rares comme la chronologie par assigné doivent être placées derrière un niveau avancé.

## Arbitrage validé

Ne pas présenter simultanément au même niveau :

- Répéter ;
- Journée entière ;
- Chronologie par assigné ;
- Début ;
- Fin ;
- jours de récurrence.

La capacité métier reste disponible mais sa complexité initiale disparaît.

---

# 9. Parcours cible — Création depuis Exécution

Le menu de création reste basé sur deux intentions :

```text
Créer

Créer un plan
Utiliser la bibliothèque
```

### Créer un plan

Ouvre le formulaire de création directe.

### Utiliser la bibliothèque

Ouvre la Bibliothèque canonique puis le parcours :

**Bibliothèque → modèle → utiliser → lancer**

Aucun second catalogue ou picker métier ne doit être maintenu en parallèle.

---

# 10. Parcours cible — Création directe

Le formulaire doit construire le plan progressivement.

## 10.1 Informations

```text
Nouveau plan

Titre
[ ................ ]

Description
[ ................ ]
```

Les labels doivent toujours rester visibles.

Les placeholders ne doivent jamais remplacer les labels.

## 10.2 Tâches

Structure cible compacte :

```text
Tâches                         +

Contrôler les extincteurs       >
  Maintenance

Nettoyer la zone                >
  Restauration
```

`ActionPlanTaskDraftEditor` possède déjà un mode compact proche de cette cible.

Les informations avancées d’une tâche restent derrière un disclosure :

- description ;
- deadline ;
- assigné ;
- pôle spécifique.

## 10.3 Organisation

```text
Organisation

Pôle pilote
Maintenance                     >

Assignés
Jean + 2                        >

Validation requise              ●
```

La présence réelle des lignes dépend des rôles et des permissions existantes.

## 10.4 Planification

Le formulaire principal affiche un résumé du choix :

```text
Planification

Quand
Maintenant                      >
```

ou :

```text
Quand
1 oct. · 09:00 → 12:00          >

Répétition
Chaque lundi                    >
```

Le détail est édité via une interaction secondaire dédiée.

## 10.5 Options

```text
Options

Enregistrer aussi comme modèle
Options avancées                >
```

Les options secondaires ne doivent pas rivaliser avec la création du plan.

---

# 11. Parcours cible — Création depuis Signal

Le parcours réutilise le même socle que la création directe.

Il ne doit pas devenir un formulaire distinct.

La différence est le contexte source.

Exemple :

```text
← Signal

Plan lié au signal

┌────────────────────────────┐
│ Climatisation défaillante  │
│ Chambre 402                │
└────────────────────────────┘

Titre
...

Description
...
```

Le contexte Signal est :

- visible ;
- compact ;
- non éditable.

Les règles existantes doivent être préservées :

- permission spécifique ;
- pôle responsable éventuellement verrouillé ;
- fallback vers le pôle pertinent ;
- création liée au Signal ;
- gestion du `issueFocus` lorsqu’il est requis.

Lorsqu’il est requis, `issueFocus` doit être placé près du contexte Signal et non enfoui dans une zone générique d’options.

---

# 12. Parcours cible — Création d’un modèle

La création d’un modèle doit être explicitement distincte d’une création d’exécution.

Structure cible :

```text
Nouveau modèle

INFORMATIONS
Titre
Description

TÂCHES
...

ORGANISATION
Pôle pilote
Validation requise

──────────────
[ Enregistrer le modèle ]
```

Le modèle ne doit pas exposer de configuration d’exécution inutile :

- date ;
- heure ;
- assignation d’une occurrence ;
- récurrence d’une occurrence.

---

# 13. Parcours cible — Modification d’un modèle

Même grammaire que la création d’un modèle :

```text
Modifier le modèle

Informations
Tâches
Organisation

──────────────
[ Enregistrer ]
```

Le mode `template-edit` actuel peut rester une base technique commune.

---

# 14. Parcours cible — Modification d’une exécution

Une exécution existante peut avoir déjà commencé à vivre.

Le formulaire doit donc distinguer :

- contenu encore modifiable ;
- tâches déjà traitées ;
- tâches restantes ;
- planning éditable selon les règles métier.

Structure cible :

```text
Modifier le plan

INFORMATIONS
Titre
Description

TÂCHES
Tâches restantes
...

Tâches déjà traitées          3 >
(read-only)

ORGANISATION
...

PLANIFICATION
...

──────────────
[ Enregistrer ]
```

Une tâche traitée ne doit jamais donner l’impression qu’elle peut être réécrite.

Les règles existantes de modification d’exécution doivent rester en place.

---

# 15. Tâches

Le composant existant `ActionPlanTaskDraftEditor` constitue une bonne base.

Il possède déjà :

- un mode compact ;
- une ligne principale ;
- un disclosure pour les détails ;
- des champs avancés ;
- les relations pôle / assigné ;
- les erreurs associées.

Le chantier doit donc privilégier :

- polish visuel ;
- cohérence des labels ;
- réduction de densité ;
- meilleure hiérarchie ;
- interactions plus lisibles.

Ne pas réécrire ce composant sans justification mesurée.

---

# 16. Assignés et pôles

Le pôle pilote et les assignés doivent être considérés comme des éléments d’organisation.

Ils ne doivent pas avoir le même poids visuel que :

- le titre ;
- la description ;
- les tâches.

La logique existante autour :

- des rôles ;
- des scopes ;
- des pôles visibles ;
- des tâches cross-pôle ;
- des assignés ;

doit rester fondée sur les helpers et contrats existants.

---

# 17. Validation et erreurs

Le repo possède déjà une base robuste à conserver.

À préserver :

- validation frontend ;
- revalidation après première tentative ;
- mapping des erreurs API sur les champs ;
- message global ;
- guidage vers la première erreur ;
- expansion automatique d’une tâche si l’erreur se trouve dans sa partie avancée ;
- gestion des conflits sur édition ;
- gestion des permissions ;
- idempotence de soumission du planning.

La refonte mobile ne doit pas remplacer cette plomberie si elle reste fonctionnellement correcte.

---

# 18. États de soumission

Tous les parcours doivent avoir un comportement explicite pour :

- loading initial ;
- soumission ;
- succès ;
- erreur frontend ;
- erreur serveur ;
- conflit ;
- double submit.

## Règles

Pendant une mutation :

- l’action principale est désactivée ;
- aucune seconde soumission identique ne doit pouvoir être déclenchée ;
- l’état reste compréhensible ;
- le formulaire ne doit pas disparaître avant confirmation du succès.

---

# 19. Perte de saisie

Contrat produit validé :

> Une saisie modifiée ne doit pas être perdue silencieusement.

Cependant, la logique générale d’interception de navigation appartient au chantier Navigation/Transitions.

Ce chantier doit donc :

- identifier correctement l’état dirty des formulaires ;
- exposer ou consommer le futur mécanisme partagé ;
- ne pas créer un système parallèle de navigation ;
- ne pas ajouter une solution locale incompatible avec le chantier Navigation.

Un formulaire intact peut quitter immédiatement la page.

Un formulaire modifié doit être protégé lorsque l’architecture Navigation stabilisée est disponible.

---

# 20. Clavier, scroll et safe areas

Le comportement mobile doit être traité comme un invariant du chantier.

Les écrans doivent :

- fonctionner avec clavier ouvert ;
- maintenir le champ actif visible ;
- éviter que le CTA sticky masque le contenu ;
- respecter les safe areas Capacitor ;
- éviter les scrolls imbriqués inutiles ;
- éviter les chaînes excessives page → sheet → picker → clavier ;
- conserver des zones tactiles adaptées au mobile.

---

# 21. CTA

Les grands formulaires utilisent un CTA principal unique et sticky lorsque pertinent.

Exemples :

- `Créer le plan`
- `Lancer le plan`
- `Enregistrer le modèle`
- `Enregistrer`

Le CTA doit :

- rester accessible ;
- respecter le clavier ;
- respecter la safe area ;
- refléter précisément le résultat produit.

Ne pas ajouter plusieurs actions principales concurrentes dans un même footer.

---

# 22. Résultat après succès

## Modèle

Création ou modification réussie :

**→ détail du modèle**

## Exécution directe unique

Lorsque la création produit une seule exécution identifiable :

**→ détail de l’exécution**

Cette destination est préférable au simple retour vers le feed car elle permet de vérifier immédiatement le résultat.

## Multi-exécution ou récurrence

Lorsque plusieurs occurrences sont créées ou planifiées :

**→ feed Exécution**

Il n’existe alors pas une destination unique pertinente.

Les retours doivent continuer à respecter l’architecture Navigation/Transitions lorsqu’elle sera stabilisée.

---

# 23. Annulation

L’annulation ou le retour doit respecter le contrat anti-perte de saisie.

Le chantier ne doit pas ajouter un comportement de navigation spécifique incompatible avec l’architecture dédiée.

---

# 24. Permissions

Les permissions doivent continuer à provenir des contrats et helpers existants.

Ne pas reconstruire les règles de permission à partir du rôle seul si des `permission_hints` existent.

Vérifier notamment :

- création depuis Bibliothèque ;
- modification d’un modèle ;
- utilisation d’un modèle ;
- création depuis Signal ;
- création directe ;
- édition d’une exécution ;
- planification ;
- tâches cross-pôle ;
- assignation.

L’UI masquée ou désactivée doit rester cohérente avec l’autorisation serveur.

---

# 25. Frontières du chantier

## Dans le scope

- Bibliothèque mobile ;
- détail modèle mobile ;
- utilisation d’un modèle ;
- création directe ;
- création liée à un Signal ;
- édition d’un modèle ;
- édition d’une exécution ;
- hiérarchie de formulaire ;
- tâches ;
- assignation ;
- pôles ;
- planning ;
- récurrence ;
- CTA ;
- validation ;
- erreurs ;
- loading / submitting ;
- clavier / scroll / safe areas ;
- continuité des parcours.

## Hors scope

- feed contracts ;
- pagination ;
- refonte générale Navigation / Transitions ;
- refonte du calendrier Exécution ;
- évolution backend non nécessaire ;
- nouveau design system ;
- abstraction générique de formulaires ;
- refonte desktop sans besoin lié au partage de composants.

---

# 26. Invariants techniques

La refonte doit respecter :

- React / TypeScript existant ;
- UI mobile commune mobile web / Capacitor ;
- réutilisation des composants pertinents ;
- maintien des contrats backend sauf besoin produit explicitement validé ;
- validation et erreurs existantes ;
- permissions existantes ;
- performances ;
- accessibilité ;
- maintenabilité ;
- scalabilité ;
- absence de duplication métier inutile.

Le desktop ne doit pas être dégradé par une évolution d’un composant partagé.

---

# 27. Arbitrages validés

1. Conserver un seul socle métier de formulaire sans framework `Field` générique.
2. Séparer clairement dans l’UX les intentions Modèle et Exécution.
3. `Utiliser ce modèle` devient l’entrée unique du lancement.
4. Le lancement complexe ne doit plus être porté par une grosse bottom sheet.
5. Hiérarchie mobile : contenu → tâches → organisation → planning → options.
6. Planning progressif : Maintenant / Planifier → dates → récurrence → avancé.
7. Pôles, assignés et validation appartiennent au bloc Organisation.
8. Les tâches restent compactes par défaut avec détails à la demande.
9. Conserver la plomberie actuelle de validation, erreurs API, permissions, idempotence et conflits.
10. Définir un contrat anti-perte de saisie sans recréer le système Navigation.
11. Mobile web et Capacitor partagent exactement la même UI.
12. Ne pas chercher artificiellement à tout implémenter dans une seule PR.
13. Un seul CTA principal sur le détail modèle : `Utiliser ce modèle`.
14. Le lancement d’un modèle devient une vraie surface mobile.
15. Une création directe produisant une seule exécution ouvre son détail.
16. Une création multi-occurrences / récurrente retourne vers Exécution.
17. Le formulaire principal résume le planning au lieu d’exposer tous les contrôles.
18. Création modèle et création exécution restent deux intentions UX distinctes même si elles partagent des briques techniques.

---

# 28. Critère de réussite

Le chantier est réussi si un utilisateur terrain peut :

1. trouver ou créer un modèle ;
2. comprendre immédiatement ce qu’il contient ;
3. le lancer sans se confronter à une configuration inutile ;
4. créer rapidement un plan ponctuel ;
5. planifier ou rendre récurrent uniquement lorsqu’il en a besoin ;
6. comprendre qui fait quoi et quand ;
7. corriger facilement une erreur de saisie ;
8. revenir sans perdre silencieusement son travail ;
9. utiliser la même expérience sur mobile web, iOS et Android ;
10. retrouver immédiatement le résultat créé dans Exécution.

L’amélioration doit rester compatible avec une architecture frontend sobre, factorisée uniquement lorsque nécessaire, et capable d’évoluer à mesure que SPORE grossit.
