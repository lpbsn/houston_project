# Spore — Vue calendaire du feed Plans d’action

## 1. Contexte

Le feed **Plans d’action / Exécutions** est aujourd’hui consulté principalement sous forme de **liste opérationnelle**. Les exécutions à venir existent déjà (aperçu « Planifiées », page **À venir**), mais elles ne sont pas lues dans une grille temporelle.

L’évolution ajoute une **vue calendaire** de ce feed. Ce n’est pas seulement un autre habillage de la liste du jour : c’est une **surface de planning**. Elle doit permettre de voir **dans le temps** les exécutions déjà commencées **et** celles **à venir**, sans affaiblir les permissions ni les règles de visibilité existantes.

La vue calendrier s’inspire de l’expérience **Apple Calendar sur iPhone / Mac** pour la lisibilité, la hiérarchie visuelle et la navigation temporelle, sans reproduire l’ensemble des fonctionnalités Apple.

Les maquettes jointes au thread Cursor constituent la **référence visuelle cible** et priment en cas d’ambiguïté visuelle. Elles ne priment pas sur les décisions produit de ce document (périmètre, planning, timezone, Toute la journée).

---

## 2. Objectif

Permettre à l’utilisateur, dans le feed **Plans d’action / Exécutions** (établissement actif), de basculer entre :

- **Vue Liste** : comportement existant conservé (y compris la séparation actuelle entre le backlog opérationnel et l’entrée **À venir**) ;
- **Vue Calendrier** :
  - **Jour**
  - **Semaine**
  - **Mois**

Le calendrier représente le **même périmètre autorisé** que les surfaces d’exécution déjà accessibles à l’utilisateur (liste, **À venir**, détail), filtré à la **période affichée**. Les règles de visibilité, de scope, de RBAC et de navigation vers le détail restent applicables. Le calendrier **n’élargit pas** ce qu’un utilisateur a le droit de voir ; il **n’omet pas** non plus les exécutions à venir qu’il a déjà le droit de consulter.

---

## 3. Périmètre fonctionnel

### Inclus

- Feed **Plans d’action / Exécutions** du hub établissement
- Switch **Liste / Calendrier**
- Sous-switch **Jour / Semaine / Mois**, visible uniquement en vue calendrier
- Navigation temporelle
- Affichage des exécutions **en cours / terminées / annulées** **et** des exécutions **à venir** sur la période visible
- Notion métier **Toute la journée** / libellé UI **Journée entière**
- Prise en charge de cette notion à la **création**, au **détail** et à la **modification** d’un plan / d’une exécution
- Vue responsive mobile et desktop
- Consultation des exécutions depuis le calendrier (détail existant)
- Conservation des modes **Personnel / Général** (Ma vue / Vue globale)
- Conservation des filtres existants applicables au feed (aujourd’hui : essentiellement ce mode de vue)
- Respect des scopes et permissions existants

### Hors périmètre V1

La **grille calendrier** est **consultative uniquement**.

Sont explicitement hors périmètre :

- création depuis la grille calendrier ;
- drag & drop ;
- déplacement d’un événement ;
- resize ;
- modification directe des dates depuis la grille ;
- édition inline dans la grille ;
- vue **Année** (présente sur certaines maquettes, non livrée) ;
- chrome type application Calendrier macOS (search, inbox, boutons fenêtre, panneau latéral de détail dédié) — le détail reste la **page d’exécution existante** ;
- calendrier sur le feed **cross-établissement** (la surface cross actuelle reste en liste, sans nouveau contrôle inventé).

La création / modification **hors grille** (formulaires de planning déjà existants) **fait partie du périmètre** pour la notion **Toute la journée**.

---

## 4. Références visuelles

Les maquettes jointes au thread Cursor doivent être utilisées comme référence pour :

- la structure Jour / Semaine / Mois ;
- la hiérarchie du header ;
- les jours sticky ;
- la zone **Toute la journée** sticky ;
- la grille horaire ;
- la représentation des événements ;
- la navigation précédent / aujourd’hui / suivant ;
- le comportement compact du mois ;
- l’adaptation mobile / desktop.

La mention « Apple Calendar » décrit la **direction UX**, mais les maquettes jointes priment en cas d’ambiguïté visuelle.

Il ne s’agit pas d’un objectif de reproduction pixel-perfect d’Apple Calendar, ni d’un objectif de reproduction du chrome Mac.

---

## 5. Navigation et états de vue

### Switch principal

Le feed permet de basculer entre :

- **Liste**
- **Calendrier**

La vue Liste actuelle doit rester fonctionnellement inchangée, hors l’ajout du switch de représentation.

### Granularité calendrier

Lorsque la vue Calendrier est active, afficher :

- **Jour**
- **Semaine**
- **Mois**

Le sélecteur n’est pas visible en vue Liste.

### Navigation temporelle

La vue calendrier doit permettre de :

- revenir à la période précédente ;
- revenir à **Aujourd’hui** ;
- avancer à la période suivante.

L’ancre temporelle doit évoluer de manière cohérente lorsque l’utilisateur change de granularité.

Un aller-retour vers le **détail d’une exécution** doit ramener l’utilisateur au calendrier dans le même état de vue (Liste/Calendrier, granularité, période, Ma vue / Vue globale), sans réinitialisation arbitraire.

### Personnel / Général

Les modes existants **Personnel / Général** (libellés actuels **Ma vue** / **Vue globale**) sont conservés.

Le choix actif doit être préservé lorsque l’utilisateur bascule entre **Liste** et **Calendrier**.

---

## 6. Règles temporelles des Plans d’action / Exécutions

La représentation temporelle s’appuie sur les informations de planning **métier**, pas sur une interprétation d’horaires sentinelles.

### 6.1 Plage avec horaire

Lorsqu’un début et une fin **horaires** sont définis, le plan est une **plage datée**.

Il est représenté sur sa durée réelle dans la **grille horaire**.

Un plan **multi-jours avec horaires** conserve cette sémantique de plage. Il **ne** doit **pas** être transformé en événement **Toute la journée**.

### 6.2 Toute la journée (notion métier)

**Toute la journée** est une notion métier **explicite** des plans d’action / exécutions.

Elle s’applique dès qu’une **date** (ou une plage de dates) est renseignée **sans horaire métier**. Dans ce cas, le plan est **Toute la journée par défaut**.

Elle doit pouvoir être posée, conservée et modifiée :

- à la **création** (plan ponctuel, chronologie partagée ou individuelle, y compris récurrence) ;
- à la **modification** du planning / de l’exécution ;
- à la lecture du **détail**.

Dans l’UI de détail (informations de planning de l’exécution — y compris toute colonne / encart latéral de planning existant sur la fiche), afficher le libellé **« Journée entière »**. Ne pas afficher une fausse plage horaire du type 00:00–23:59.

La vue calendrier utilise **cette information explicite** pour placer l’événement dans la zone **Toute la journée**.

Il est **interdit** d’inférer Toute la journée à partir d’horaires du type 00:00–23:59. Les exécutions existantes qui n’ont pas cette notion restent des **plages horaires** ; elles ne sont **pas** reclassées automatiquement.

Un plan **Toute la journée** multi-jours occupe la zone **Toute la journée** sur les jours concernés. Il ne doit pas être dessiné comme un bloc de grille horaire.

Si l’utilisateur renseigne ensuite un horaire, le plan redevient une plage horodatée (plus Toute la journée).

### 6.3 Aucune date connue

Un plan sans aucune date de planification est **Non planifié**.

Il doit rester visible depuis la vue calendrier, mais **ne doit pas** être représenté comme une durée couvrant la période visible.

Objectifs UX :

- ne pas perdre ces éléments ;
- les identifier explicitement comme **Non planifiés** ;
- ne pas leur inventer de durée ;
- ne pas les mélanger avec **Toute la journée** ;
- éviter de saturer la grille Jour / Semaine / Mois.

Traitement attendu : une zone dédiée, distincte de **Toute la journée**, repliable ou équivalente, intégrée au shell existant.

### 6.4 Bornes partielles (plages horodatées uniquement)

Le modèle autorise une date/heure de **début** sans **fin** ; il n’autorise pas une fin sans début.

L’implémentation ne doit pas inventer silencieusement une durée métier. Un début sans fin reste un événement horodaté **ouvert**, distinct de **Toute la journée** et de **Non planifié**.

---

## 7. Vues calendaires

### 7.1 Jour

- une seule colonne temporelle ;
- grille horaire verticale ;
- scroll vertical ;
- zone **Toute la journée** en haut ;
- date courante clairement identifiable ;
- événements horodatés positionnés selon leur horaire réel ;
- événements **Toute la journée** uniquement dans la zone dédiée.

### 7.2 Semaine

#### Desktop

- 7 colonnes ;
- largeur complète disponible dans le shell Terrain ;
- axe horaire partagé ;
- jours sticky ;
- zone **Toute la journée** sticky.

#### Mobile

L’objectif reste une lecture hebdomadaire.

Priorité :

1. afficher 7 colonnes compactes si la lisibilité et les interactions restent satisfaisantes ;
2. sinon préférer un défilement horizontal conservant une largeur minimale exploitable par jour plutôt que de compresser la grille jusqu’à la rendre illisible.

### 7.3 Mois

- grille mensuelle compacte ;
- semaines et jours clairement identifiables ;
- date courante mise en évidence ;
- quelques événements visibles directement dans chaque cellule (Toute la journée et horodatés) ;
- au-delà du seuil affichable : **`+N de plus`** ;
- action sur `+N de plus` ouvrant une vue de détail ou une sheet adaptée au device ;
- navigation possible vers le détail d’une exécution.

Le nombre exact d’événements affichés par cellule peut être adapté à l’espace réellement disponible.

---

## 8. Sticky headers et scroll

Dans les vues Jour et Semaine :

- les jours restent **sticky en haut** ;
- la zone **Toute la journée** reste également **sticky** ;
- la grille horaire défile verticalement sous ces éléments.

Éviter les doubles scrollbars ou conflits de scroll avec le shell existant.

Sur mobile, le comportement sticky doit rester compatible avec les safe areas et le shell Capacitor.

---

## 9. Filtres, scopes et permissions

Le calendrier ne définit pas un nouveau rôle ni un nouveau périmètre d’établissement.

Il applique :

- le mode **Personnel / Général** du feed établissement ;
- l’établissement actif ;
- les scopes et le RBAC existants ;
- les permission hints existants pour ouvrir le détail ;
- les **règles de visibilité déjà en vigueur** sur les surfaces d’exécution (y compris la mise à disposition différée lorsqu’elle masque une exécution à un utilisateur donné).

Conséquence pour les **à-venir** : une exécution planifiée future apparaît dans le calendrier **si et seulement si** l’utilisateur pourrait déjà la consulter sur les surfaces équivalentes (**À venir** / détail), pour le même mode de vue. Le calendrier ne contourne pas `visible_from` ni le RBAC « Ma vue ».

Changer de représentation ne doit jamais permettre de voir une exécution inaccessible par ailleurs.

Le feed **cross-établissement** n’est pas une cible V1 de cette vue (voir hors périmètre). Son comportement liste actuel est préservé.

---

## 10. Interaction avec les événements

La V1 de la **grille** est uniquement consultative.

### Tap / clic sur un événement

Ouvrir le **détail existant de l’exécution**.

### Surcharge d’une date

En vue Mois, ou lorsque la densité rend l’affichage direct insuffisant :

- afficher un indicateur `+N de plus` ;
- ouvrir une sheet, popover ou vue équivalente adaptée au device ;
- permettre ensuite l’ouverture du détail existant.

---

## 11. Chargement des données

La vue calendrier doit être **exhaustive pour toute la période affichée**, y compris les exécutions **à venir** de cette période.

Il est interdit de considérer comme complet un calendrier construit uniquement à partir des premières pages du feed Liste, ou à partir du seul aperçu « Planifiées » (plafond actuel).

La récupération doit garantir cette exhaustivité pour la fenêtre visible. Une évolution d’API est attendue si les endpoints liste / à-venir paginés ne suffisent pas.

### Fenêtre temporelle

La récupération est alignée sur la période effectivement affichée :

- Jour : journée visible ;
- Semaine : semaine visible ;
- Mois : grille mensuelle réellement rendue, y compris les jours adjacents affichés.

Le changement de période déclenche une récupération cohérente avec cette nouvelle fenêtre, sans recharger inutilement l’historique hors fenêtre.

### Événements intersectant la période

Une exécution **planifiée** (horodatée ou Toute la journée) est incluse si sa plage **intersecte** la fenêtre visible, y compris lorsqu’elle :

- commence avant la période et se termine pendant ;
- commence pendant la période et se termine après ;
- couvre entièrement la période.

Les **non planifiés** ne participent pas à cette intersection : ils sont listés à part, indépendamment du jour affiché.

---

## 12. Fuseau horaire et locale

Pour la V1, **tous les établissements partagent le même fuseau horaire métier**.

Le calendrier, la création, la modification et le détail affichent les dates et heures dans **ce** fuseau. Ils ne doivent jamais exposer des timestamps UTC bruts à l’utilisateur.

Il n’est pas requis, en V1, de gérer un fuseau distinct par établissement, un fuseau utilisateur, ou un calendrier multi-fuseaux.

Attendus de présentation :

- locale française ;
- semaine commençant le lundi ;
- gestion correcte des changements d’heure dans ce fuseau métier unique ;
- cohérence entre les dates du calendrier, le détail (« Journée entière » vs horaires) et les données de planning.

---

## 13. Responsive

La fonctionnalité cible :

- Web desktop ;
- Web mobile ;
- app native Capacitor iOS / Android.

Les comportements sont adaptés au device plutôt que reproduits à l’identique.

### Principes

- préserver la lisibilité des horaires, des libellés **Journée entière** et des titres ;
- préserver une zone tactile suffisante ;
- éviter les colonnes trop étroites ;
- préserver les sticky headers ;
- respecter les safe areas natives ;
- ne pas dégrader la vue Liste existante.

---

## 14. États particuliers à prendre en compte

Le plan d’implémentation doit vérifier le comportement pour :

- période sans aucune exécution ;
- événements simultanés ;
- plusieurs événements Toute la journée ;
- Toute la journée sur un jour vs plusieurs jours ;
- événements multi-jours horodatés ;
- événement démarrant avant la période visible ;
- événement finissant après la période visible ;
- exécution à venir (pas encore commencée) ;
- plan non planifié ;
- début horodaté sans fin ;
- chronologie partagée vs individuelle ;
- récurrence Toute la journée vs récurrence horodatée ;
- changement Personnel / Général ;
- changement d’établissement ;
- changement Liste / Calendrier ;
- changement Jour / Semaine / Mois ;
- chargement, erreur et retry ;
- navigation vers détail puis retour au calendrier.

---

## 15. Exigences de qualité

### Performance

- ne charger que ce qui sert la période visible (et les non planifiés, sans les rattacher à chaque jour) ;
- rester fluide lors des navigations successives (jour / semaine / mois précédent-suivant) ;
- limiter les rerenders coûteux de la grille ;
- préserver la fluidité du scroll sur mobile ;
- éviter une dépendance lourde sans bénéfice démontré ;
- rester raisonnable si la période contient beaucoup d’exécutions (indicateur de saturation plutôt qu’une grille figée ou un chargement non borné).

### Accessibilité

- événements accessibles au clavier sur Web ;
- focus visible ;
- libellés accessibles pour les contrôles de navigation et pour **Journée entière** ;
- ne pas dépendre uniquement de la couleur pour transmettre un état.

### Régression

La vue Liste existante reste fonctionnellement inchangée hors l’ajout du switch de représentation.

Les règles de permission, de visibilité et de cycle de vie des exécutions ne sont pas assouplies.

---

## 16. Architecture — décisions volontairement ouvertes

Le besoin produit ne prescrit pas :

- une bibliothèque calendrier précise ;
- une implémentation custom ;
- un nouvel endpoint précis ;
- une structure de composants précise ;
- un mécanisme précis de persistance UI.

Le plan technique doit comparer les options à partir de l’existant Houston.

La mutualisation reste proportionnée au besoin réel. Il n’est pas nécessaire de concevoir une abstraction destinée à plusieurs domaines métier dans cette V1.

---

## 17. Critères de réussite

La fonctionnalité est considérée conforme lorsque :

1. l’utilisateur peut basculer **Liste / Calendrier** dans le feed Plans d’action établissement ;
2. **Jour / Semaine / Mois** sont disponibles uniquement en calendrier ;
3. le calendrier affiche les exécutions de la période, **y compris les à-venir** autorisés ;
4. **Toute la journée** est une information métier explicite, posée par défaut si date sans heure, visible comme **Journée entière** au détail, et utilisée telle quelle par le calendrier ;
5. aucune inférence 00:00–23:59 n’est utilisée pour classer un événement en Toute la journée ;
6. les objets non planifiés sont visibles sans fausse durée et distincts de Toute la journée ;
7. Personnel / Général restent cohérents lors des changements de vue ;
8. aucune donnée hors scope ou permission n’est exposée ;
9. toute période visible est chargée de manière exhaustive ;
10. les jours et la zone Toute la journée restent sticky ;
11. le calendrier est utilisable sur mobile et desktop ;
12. les événements ouvrent les détails existants ;
13. aucun événement n’est modifiable depuis la grille ;
14. la vue Liste existante n’est pas régressée.

---

## 18. Livrable attendu avant implémentation

Le plan d’implémentation doit rester aligné sur ce cadrage et préciser notamment :

- comment exposer les à-venir sans casser visibilité / permissions ;
- comment porter **Toute la journée** sur les modes de planning existants (ponctuel, récurrent, chronologie partagée / individuelle) ;
- la règle de timezone V1 (fuseau métier unique) ;
- la stratégie d’exhaustivité par fenêtre (y compris récurrences futures) ;
- la gestion des non planifiés ;
- les risques de volume, de navigation successive et de cache ;
- les surfaces volontairement non traitées (cross, Année, édition depuis la grille).

Aucune implémentation ne doit être lancée avant validation de ce plan.
