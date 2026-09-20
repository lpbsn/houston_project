# Cadrage UX/UI — Spore Platform V1

**Statut :** validé pour planification  
**Périmètre :** frontend desktop Web de `/platform`  
**Nature :** cadrage produit et ergonomique, sans prescription d’architecture React

## 1. Contexte

Spore Platform est le control plane interne utilisé par les opérateurs Spore pour rechercher et inspecter les organisations, établissements et utilisateurs, ainsi que pour réaliser entièrement les onboardings clients.

La V1 fonctionnelle existe. Son interface reste cependant proche d'un prototype administratif : hiérarchie visuelle faible, listes peu structurées, statuts difficiles à parcourir et formulaires permanents qui concurrencent le contenu principal.

Cette évolution modernise l'expérience Platform sans modifier ses capacités métier.

## 2. Objectif

Faire de Platform un outil opérateur :

- immédiatement identifiable comme un contexte distinct du produit tenant ;
- rapide à parcourir et efficace sur des volumes croissants ;
- compact sans devenir austère ;
- cohérent entre listes, détails et wizard ;
- accessible et utilisable au clavier ;
- extensible visuellement sans créer dès maintenant un design system générique.

La modernité recherchée vient de la hiérarchie, de la densité, de la lisibilité et du feedback. Elle ne repose pas sur des effets décoratifs.

## 3. Utilisateur et tâches prioritaires

L'utilisateur principal est un opérateur Spore sur desktop Web.

L'interface doit lui permettre, dans cet ordre, de :

1. comprendre immédiatement qu'il se trouve dans Platform ;
2. trouver une organisation, un établissement, un utilisateur ou un onboarding ;
3. identifier rapidement l'état d'une ressource ;
4. ouvrir son détail ou reprendre son onboarding ;
5. effectuer une mutation autorisée avec un feedback clair.

## 4. Principes directeurs

### 4.1 Identité distincte, même famille Spore

Platform possède son propre shell et sa propre palette. Elle conserve la typographie, la qualité de finition et les fondamentaux d'interaction du produit Spore.

Elle ne reprend ni le shell Terrain ni la présentation crème du wizard historique.

### 4.2 Densité compacte et lisible

Les collections privilégient le scan : colonnes stables, lignes resserrées, statuts alignés et actions explicites.

La densité ne doit pas réduire la taille des zones interactives, masquer la hiérarchie ou rendre les libellés ambigus.

### 4.3 Couleur fonctionnelle

La couleur sert à distinguer le contexte Platform, les actions principales et les états. Elle ne remplace jamais un libellé.

### 4.4 Peu de surfaces, peu d'ombres

Les bordures et espacements structurent les pages. Les ombres sont réservées aux éléments superposés tels que modales, menus et popovers.

Éviter l'accumulation de cartes autour de chaque information.

### 4.5 Pas d'abstraction prématurée

Le cadrage définit des patterns visuels, pas une liste obligatoire de composants ou de fichiers. L'analyse du repo détermine ce qui doit être réutilisé, adapté ou extrait.

## 5. Périmètre

La modernisation couvre :

- le shell et la navigation Platform ;
- la liste des onboardings ;
- la création d'un onboarding ;
- le wizard opérateur ;
- les listes et détails Organisations ;
- les listes et détails Établissements ;
- les listes et détails Utilisateurs ;
- les relations et memberships affichés dans les détails ;
- les confirmations de suppression ;
- les états de chargement, vide, sans résultat et erreur.

La modernisation doit être cohérente sur l'ensemble de cette surface. Une refonte limitée à la page Onboardings n'est pas acceptable.

## 6. Direction visuelle

### 6.1 Palette de référence

| Usage | Valeur de référence |
|---|---|
| Navigation | `#0B1F33` |
| Fond principal | `#F7F8FC` |
| Surface | `#FFFFFF` |
| Accent primaire | indigo Spore existant |
| Texte principal | `#172033` |
| Texte secondaire | `#64748B` |
| Bordure | `#E2E8F0` |
| Danger | rouge sémantique existant |

Ces valeurs doivent être exprimées par des tokens sémantiques locaux au contexte Platform et ajustées si nécessaire pour respecter les contrastes. Elles ne doivent pas être répétées arbitrairement dans chaque écran.

### 6.2 Style général

- fond principal opaque pour isoler Platform du fond marketing global ;
- surfaces blanches, bordures fines et rayons modérés ;
- titres sobres, sans typographie marketing ;
- pas de gradient, glassmorphism ou ombre lourde ;
- icônes uniquement lorsqu'elles améliorent le repérage ou clarifient une action.

## 7. Shell et navigation

La navigation latérale est fixe, d'une largeur proche de `240px`, sur fond bleu nuit.

Elle contient :

- la marque « Spore Platform » ;
- Onboardings ;
- Organisations ;
- Établissements ;
- Utilisateurs ;
- la zone compte et les actions de session déjà prévues par le produit.

L'entrée active utilise un fond indigo atténué, un texte plus lumineux et éventuellement un indicateur latéral fin. L'accent indigo plein reste réservé aux actions principales.

La navigation utilise de vrais liens : ouverture dans un nouvel onglet, focus clavier et comportement navigateur doivent rester possibles.

Le shell doit pouvoir accueillir plus tard de nouvelles sections, sans introduire aujourd'hui de navigation imbriquée ou repliable.

## 8. Structure des pages

Chaque page suit une hiérarchie stable :

1. éventuel fil d'Ariane ;
2. titre et description ;
3. action principale à droite ;
4. recherche ou actions de collection ;
5. contenu principal ;
6. navigation de pagination si nécessaire.

Le header n'est pas enfermé dans une carte.

Les largeurs dépendent du contenu :

- wizard et formulaires : environ `720–800px` ;
- pages détail : environ `960–1100px` ;
- collections : largeur disponible, avec une limite confortable autour de `1440px`.

## 9. Collections

Les collections sont présentées comme des tables HTML sémantiques légères :

- en-têtes explicites ;
- lignes d'environ `56–64px` ;
- séparateurs fins ;
- hover discret ;
- colonnes stables ;
- lien explicite sur la ressource principale ;
- action ou chevron accessible à droite.

La ligne entière ne doit pas devenir une zone de navigation implicite. Ce pattern resterait fragile lors de l'ajout futur d'actions ou de sélections.

Les listes affichent uniquement les informations utiles au scan, pas tous les champs disponibles dans l'API.

### 9.1 Colonnes attendues

| Collection | Colonnes principales |
|---|---|
| Onboardings | Organisation, Établissement, État fonctionnel, Action |
| Organisations | Nom, Statut, Action |
| Établissements | Nom, Organisation, Statut, Action |
| Utilisateurs | Identité, E-mail, Statut, Action |

Les identifiants techniques, dates détaillées, `has_been_operational`, `current_step`, erreurs et métadonnées complètes appartiennent aux fiches détail, sauf besoin opérateur démontré pendant l'implémentation.

La recherche existante est conservée avec une largeur maîtrisée et un bouton d'effacement accessible. Aucun nouveau filtre n'est introduit dans cette refonte. Le filtre `functional_status` ne doit notamment pas réapparaître.

La pagination cursor est visible. Lorsqu'un `next_cursor` existe, l'interface propose « Charger plus » et ne s'arrête jamais silencieusement à la première page.

Le retour depuis un détail doit préserver la recherche en cours.

## 10. Statuts

Les statuts utilisent des badges compacts : fond très clair, texte foncé de la même famille et libellé explicite.

| État fonctionnel | Sémantique |
|---|---|
| `activated` | succès, vert |
| `in_progress` | information, bleu |
| `waiting_acceptance` | attention, ambre |
| `ready_to_complete` | action disponible, violet |
| `error` | problème, rouge |

Les statuts métier des autres ressources suivent les mêmes familles sémantiques. Les couleurs saturées en fond plein sont évitées.

## 11. Création d'un onboarding

Le formulaire permanent est retiré de la liste.

Le header de la page contient l'action « Nouvel onboarding ». Elle ouvre une modale courte comprenant :

- le nom de l'organisation, obligatoire ;
- le nom de l'établissement, facultatif ;
- Annuler ;
- Démarrer.

Après création, le comportement existant est conservé : navigation vers le wizard créé.

La modale doit gérer le focus, le clavier, la validation, la soumission en cours, les erreurs API et la restitution du focus à sa fermeture. Une soumission en cours ne doit pas pouvoir être interrompue accidentellement.

## 12. Wizard opérateur

Le parcours, les étapes, les règles d'activation, l'autosave et les appels existants ne changent pas.

La modernisation concerne uniquement la présentation :

- contenu centré et largeur maîtrisée ;
- retour clair vers les onboardings ;
- progression lisible ;
- surface principale sobre ;
- titres, aides, champs et actions mieux hiérarchisés ;
- action principale stable ;
- erreurs en français et rattachées au bon niveau.

Le wizard doit appartenir visuellement à Platform et non au produit tenant.

## 13. Pages détail

Les pages détail privilégient la lecture :

- fil d'Ariane ;
- titre et badge d'état ;
- résumé sous forme de paires clé/valeur ;
- relations dans des listes ou tables secondaires ;
- actions contextuelles proches du titre ;
- zone destructive clairement séparée en bas.

Éviter les grilles de petites cartes et les métriques décoratives.

Les identifiants techniques sont affichés sur la fiche lorsqu'ils sont utiles, dans un format lisible avec une action Copier accessible. Ne pas utiliser l'attribut HTML `title` comme seul moyen d'accès à une valeur complète.

Les règles, justifications et messages de blocage des suppressions restent inchangés.

## 14. États d'interface

Chaque collection et chaque détail gère explicitement :

- le chargement ;
- l'absence initiale de données ;
- l'absence de résultat après recherche ;
- l'erreur avec possibilité de réessayer ;
- la mutation en cours ;
- le succès ou l'échec d'une mutation.

Les tables utilisent des lignes skeleton qui conservent leur structure. Les spinners sont réservés aux actions ponctuelles, notamment les boutons en cours de soumission.

Les états vides restent sobres et contextualisés. Ils ne doivent pas ressembler à un écran marketing.

## 15. Accessibilité et ergonomie

- contraste au minimum WCAG AA ;
- focus visible sur chaque élément interactif ;
- navigation clavier complète ;
- ordre des titres HTML cohérent ;
- liens et boutons distingués selon leur comportement ;
- modales accessibles ;
- actions iconiques avec nom accessible ;
- aucune information transmise par la couleur seule ;
- respect de la réduction des animations ;
- pas d'éléments interactifs HTML imbriqués de manière invalide.

## 16. Comportement desktop

Platform reste réservée au desktop Web. Aucun écran mobile ou natif n'est ajouté.

L'interface doit néanmoins rester utilisable :

- dans une fenêtre desktop réduite ;
- avec le zoom navigateur ;
- entre environ `1024px` et un écran ultrawide ;
- lorsque les tables nécessitent un débordement horizontal contrôlé.

## 17. Contraintes d'implémentation

- aucun changement backend, OpenAPI, permission ou règle métier ;
- aucune nouvelle dépendance UI sans blocage démontré ;
- réutiliser les primitives, icônes et conventions déjà présentes ;
- ne pas modifier les composants globaux pour satisfaire uniquement Platform ;
- garder les styles et éventuelles abstractions spécifiques sous la feature Platform ;
- n'extraire un composant commun qu'après constat d'une duplication réelle ;
- utiliser les mécanismes TanStack Query déjà présents pour la pagination et le cache plutôt qu'un état artisanal concurrent ;
- ne pas éditer manuellement le client OpenAPI généré ;
- préserver les parcours, URLs et paramètres de recherche existants.

Ce document ne prescrit ni les noms de composants ni leur découpage en fichiers. Le plan d'implémentation doit les déterminer après inventaire du repo.

## 18. Validation attendue

La refonte est acceptée si :

- toutes les pages Platform utilisent une identité et des patterns cohérents ;
- Platform reste clairement distincte du tenant ;
- la liste Onboardings ne contient plus le formulaire permanent ;
- les statuts sont immédiatement identifiables ;
- les collections restent efficaces avec un volume croissant ;
- les états chargement, vide, sans résultat et erreur sont traités ;
- le clavier et les focus fonctionnent sur navigation, tables et modales ;
- aucun contrat backend ou comportement métier n'est modifié ;
- aucune dépendance UI injustifiée n'est introduite ;
- tests frontend, typecheck et builds Web/native restent verts.

Une vérification visuelle réelle est requise pour le shell, les quatre listes, les fiches détail, la modale et le wizard aux largeurs desktop représentatives `1024px`, `1440px` et ultrawide. Les tests comportementaux seuls ne valident pas une refonte visuelle.

## 19. Hors périmètre

- dashboard et métriques Platform ;
- recherche globale ;
- nouveaux filtres ;
- tri non supporté ;
- nouvelles données API ;
- modification du modèle d'autorisation ;
- modification du workflow d'onboarding ;
- dark mode et personnalisation de thème ;
- gestion UI des opérateurs ;
- mobile et natif ;
- refonte du produit tenant ;
- design system générique ;
- effets visuels décoratifs sans valeur ergonomique.

## 20. Références de principes

Ces références servent à comprendre les patterns, pas à reproduire leur identité :

- Shopify Polaris : collections administratives orientées action ;
- GitHub Primer : densité et labels d'état compacts ;
- Atlassian Design System : navigation, tables et statuts sémantiques.

## 21. Décisions closes

- identité distincte mais appartenant à la famille Spore ;
- navigation bleu nuit, contenu clair et accent indigo ;
- densité compacte et lisible ;
- création d'onboarding en modale ;
- tables sémantiques pour les collections ;
- navigation par liens explicites, pas par ligne entièrement cliquable ;
- cinq couleurs sémantiques pour les états fonctionnels ;
- aucun filtre `functional_status` ni nouveau filtre dans cette refonte ;
- aucun changement backend ou métier ;
- aucune question produit restante avant le plan d'implémentation.
