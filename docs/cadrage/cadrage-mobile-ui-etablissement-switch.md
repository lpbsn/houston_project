# Mobile Establishment Switcher — UI cadrage

## Objectif

Refondre l’écran mobile de sélection d’établissement pour en faire une expérience simple, rapide, moderne et cohérente avec le reste de Spore.

Ce document traite uniquement de l’expérience UI/UX de cette page.

Le comportement de sélection, le routing, la session active, les deep links et la logique de changement de contexte ne font pas partie de ce chantier.

---

## Principe produit

Choisir un établissement est une action de navigation rapide.

L’utilisateur doit pouvoir :

1. comprendre immédiatement quels établissements sont disponibles ;
2. identifier l’établissement actuellement actif lorsqu’il y en a un ;
3. choisir un autre établissement en un seul tap ;
4. comprendre immédiatement que son choix est en cours de traitement.

L’écran doit rester efficace avec seulement deux établissements comme avec une liste plus longue.

---

## Références UX

Le comportement recherché est proche des workspace switchers d’applications comme Notion ou Slack :

* liste facilement scannable ;
* hiérarchie visuelle simple ;
* contexte courant identifiable ;
* sélection directe ;
* très peu d’informations secondaires ;
* feedback immédiat après interaction.

Ces références servent à guider la densité, la hiérarchie et les interactions, pas à reproduire leur identité graphique.

---

## Header

Titre unique :

**Choisir un établissement**

Utiliser ce titre dans tous les cas.

Ne pas changer le wording selon qu’un établissement soit déjà actif ou non.

Éviter un long texte introductif : l’action attendue est suffisamment explicite avec le titre et la liste.

---

## Structure de la page

### Lorsqu’un établissement est actif

Séparer clairement :

**Établissement actuel**

puis :

**Autres établissements**

Exemple conceptuel :

```text id="xa92eu"
Choisir un établissement

ÉTABLISSEMENT ACTUEL

[ LP ]  Le Palais Nancy                 ✓
        Groupe Demo · Directeur


AUTRES ÉTABLISSEMENTS

[ BM ]  Brasserie Metz                  ›
        Groupe Demo · Manager

[ CS ]  Café Strasbourg                 ›
        Groupe Demo · Équipe
```

### Lorsqu’aucun établissement n’est actif

Afficher directement la liste :

```text id="5cmmu2"
Choisir un établissement

[ LP ]  Le Palais Nancy                 ›
        Groupe Demo · Directeur

[ BM ]  Brasserie Metz                  ›
        Groupe Demo · Manager

[ CS ]  Café Strasbourg                 ›
        Groupe Demo · Équipe
```

Ne pas afficher une section « Établissement actuel » vide.

---

## Anatomy d’une row

Chaque établissement est présenté sous forme de row compacte.

### Information principale

Nom de l’établissement.

C’est l’information qui doit attirer l’œil en premier.

### Information secondaire

Une seule ligne :

`Organisation · Rôle`

Elle doit aider à différencier les établissements sans concurrencer leur nom.

### Leading

Utiliser une représentation simple et compacte de l’établissement.

Par exemple :

* monogramme basé sur le nom ;
* avatar neutre adapté au produit.

Éviter de répéter une grosse icône générique `Building` sur chaque ligne si elle n’apporte aucune information.

### Trailing

Selon l’état :

* établissement actif : check discret ;
* établissement sélectionnable : chevron ou affordance légère ;
* établissement en cours de sélection : spinner.

Toute la row doit être interactive.

---

## Densité visuelle

Éviter une succession de grosses cartes indépendantes.

Préférer une liste visuellement cohérente :

* rows regroupées ;
* séparateurs subtils ;
* padding tactile confortable ;
* peu de décorations ;
* faible profondeur visuelle ;
* hiérarchie typographique nette.

L’écran doit ressembler davantage à une surface de navigation mobile qu’à une page de configuration.

---

## Informations à retirer

Ne pas afficher les informations qui ne sont pas nécessaires pour choisir un établissement.

En particulier :

* `Périmètre complet` ;
* nombre de pôles ;
* scope détaillé ;
* accumulation de badges ;
* rôle présenté comme un gros badge ;
* descriptions répétant l’action de la page.

L’utilisateur doit essentiellement voir :

**Établissement**
`Organisation · Rôle`

---

## Établissement actif

L’état actif doit être identifiable immédiatement mais rester discret.

Utiliser une combinaison simple telle que :

* section dédiée `Établissement actuel` ;
* check à droite ;
* légère différence de fond si nécessaire.

Éviter un gros badge `ACTIF`.

L’établissement actif ne doit pas apparaître comme une action primaire à effectuer.

---

## État pending

Lorsqu’un établissement vient d’être sélectionné :

* remplacer son affordance de droite par un spinner ;
* garder le nom et les informations secondaires visibles ;
* désactiver temporairement les autres choix ;
* ne pas provoquer de déplacement du layout.

Le feedback doit être local à l’action effectuée.

Éviter un loader plein écran pour une transition normale.

---

## Erreur

En cas d’échec :

* conserver la liste visible ;
* réactiver les choix ;
* afficher un message d’erreur court à proximité de la liste ;
* éviter une modal supplémentaire.

Le message doit indiquer simplement que l’établissement n’a pas pu être sélectionné.

---

## Navigation retour

Lorsqu’un retour est disponible dans le contexte courant, utiliser le pattern de navigation mobile déjà employé par Spore.

Le retour ne doit pas concurrencer le titre ni apparaître comme une action principale.

Ne pas inventer un nouveau pattern de navigation uniquement pour cet écran.

---

## Mobile first

La composition doit être pensée d’abord pour une largeur de téléphone.

Priorités :

* informations essentielles visibles sans effort ;
* targets tactiles confortables ;
* très peu de chrome ;
* noms longs gérés proprement ;
* scrolling naturel avec de nombreux établissements ;
* aucun élément essentiel dépendant du hover.

Les adaptations responsive éventuelles doivent rester secondaires.

---

## Cohérence Spore

Réutiliser les primitives Terrain pertinentes lorsque leur rendu convient.

La page doit rester reconnaissable comme une surface Spore :

* mêmes principes typographiques ;
* même langage de spacing ;
* mêmes couleurs fonctionnelles ;
* mêmes états de loading et d’erreur ;
* même niveau d’arrondi et de contraste que les surfaces mobiles récentes.

Ne pas conserver un composant existant uniquement parce qu’il existe si son rendu empêche d’atteindre la cible UX.

À l’inverse, éviter de créer un mini design system spécifique à cette page.

---

## Accessibilité

Prévoir :

* row entière tappable ;
* cible tactile confortable ;
* nom de l’établissement dans le nom accessible ;
* état actif exposé autrement que par la couleur ;
* état pending perceptible ;
* contraste suffisant ;
* gestion correcte des noms d’établissement et d’organisation longs ;
* ordre de lecture naturel.

---

## Non-objectifs

Cette refonte ne doit pas modifier :

* les règles d’autorisation ;
* le modèle de membership ;
* la source de vérité de l’établissement actif ;
* le mécanisme backend de switch ;
* les règles de routing ;
* les comportements deep link / app-open ;
* le modèle de navigation desktop.

Ces éléments constituent des contraintes fonctionnelles existantes de la page.

---

## Critères d’acceptation UI

La refonte est réussie si :

* le titre affiché est toujours **« Choisir un établissement »** ;
* la page est immédiatement compréhensible sans longue explication ;
* l’établissement actif est identifiable lorsqu’il existe ;
* les autres établissements sont rapidement scannables ;
* le nom de l’établissement domine visuellement ;
* organisation et rôle restent secondaires ;
* les informations de scope inutiles ont disparu ;
* les rows sont plus compactes que les cartes actuelles ;
* le feedback pending reste local à la row sélectionnée ;
* les noms longs restent propres ;
* la page fonctionne correctement avec une liste importante ;
* l’ensemble reste cohérent avec l’UI mobile actuelle de Spore.
