# PR3-A — Refonte du Feed Exécution mobile

## 1. Objet du document

Ce document cadre la refonte du **Feed Exécution en mode Liste** sur mobile web et sur les applications Capacitor iOS/Android.

L’objectif est de transformer le feed actuel en une surface plus moderne, plus lisible et plus orientée terrain, sans modifier la logique métier sous-jacente.

Le feed Exécution doit répondre en priorité à la question :

> **Qu’est-ce qui requiert mon attention maintenant, et où en suis-je ?**

Il ne doit pas devenir une copie du Feed Observations ni un gestionnaire de tâches générique.

---

## 2. Périmètre

### Inclus dans ce chantier

- Refonte du **mode Liste** du Feed Exécution.
- Nouvelle hiérarchie du feed.
- Refonte des cartes mobiles Exécution.
- Variantes visuelles selon le statut.
- Nouveau traitement de la temporalité.
- Affichage des assignés.
- Affichage du créateur.
- Affichage du pôle pilote et du contexte multi-pôles.
- Nouveau traitement des plans planifiés.
- Suppression de la rupture vers l’écran dédié « À venir », si l’audit confirme qu’il peut être remplacé proprement.
- Pin direct depuis la carte.
- Skeletons de chargement.
- Harmonisation du libellé de pagination en `Afficher plus`.
- Conservation de la mémoire de lecture / état des sections.

### Hors périmètre

- Refonte du calendrier.
- Modification de l’UI calendrier mobile.
- Modification de l’UI calendrier desktop.
- Refonte du détail Exécution.
- Refonte des commentaires.
- Refonte du catalogue de plans d’action.
- Refonte des écrans de création / planification.
- Ajout de nouvelles actions métier depuis les cartes.
- Ajout de validation directe depuis le feed.
- Filtres du feed : ils feront l’objet d’un **commit séparé dans la même PR**.
- Refonte desktop du feed, sauf adaptation strictement nécessaire pour ne pas casser l’existant.

---

## 3. Plateformes concernées

La cible de cette refonte est :

- mobile web ;
- iOS Capacitor ;
- Android Capacitor.

Ces trois surfaces doivent partager la même UI, les mêmes composants et les mêmes comportements fonctionnels.

Les adaptations natives éventuelles restent limitées aux contraintes de plateforme : safe areas, clavier, navigation système, etc.

Le desktop conserve son comportement actuel tant qu’aucune adaptation n’est explicitement nécessaire.

---

## 4. Principe produit

Le Feed Observations répond principalement à :

> **Qu’est-ce qui se passe ?**

Le Feed Exécution répond à :

> **Qu’est-ce que je dois traiter maintenant ?**

La hiérarchie de lecture d’une carte Exécution doit donc privilégier :

1. l’état ;
2. le plan ;
3. la temporalité ;
4. les personnes ;
5. le contexte organisationnel.

Les tâches individuelles contenues dans le plan sont secondaires dans ce feed.

Elles ne doivent pas apparaître sur les cartes du Feed Exécution.

---

## 5. Structure générale de l’écran

Sur **mobile web et Capacitor uniquement**, l’ordre des contrôles en haut du feed est figé ainsi :

```text
Exécution

[ Liste | Calendrier ]                         [+]

[ Ma vue | Vue globale ]
```

Le switch **Liste / Calendrier** est affiché au-dessus de **Ma vue / Vue globale**.

Le contrôle de création `+` existant est conservé avec ses permissions, sa destination et son comportement actuels. Ce chantier ne refond pas le flux de création.

### Important

Le contrôle `Calendrier` reste disponible, mais **le calendrier lui-même n’est pas refondu dans ce chantier**.

Aucune modification visuelle ou fonctionnelle de la vue Calendrier ne doit être introduite dans cette PR au titre du présent cadrage.

Le desktop conserve l’ordre, la structure et les interactions actuellement en production. Si un composant partagé doit évoluer pour la cible mobile, l’implémentation doit préserver explicitement le rendu desktop existant.

---

## 6. Structure du feed Liste

La structure cible est :

```text
ÉPINGLÉS

À VALIDER

EN RETARD

EN COURS

PLANIFIÉES                              18  ›
Prochaine : demain · 09:00

TERMINÉS

ANNULÉS
```

### Ordre des sections

Ordre validé :

1. Épinglés
2. À valider
3. En retard
4. En cours
5. Planifiées
6. Terminés
7. Annulés

### Principe de priorité

Le haut du feed doit représenter **ce qui mérite l’attention maintenant**.

Les contenus futurs ou archivés ne doivent pas dominer visuellement la page.

### État initial des sections

Lorsqu’aucun état de lecture n’a encore été mémorisé :

- À valider : ouverte ;
- En retard : ouverte ;
- En cours : ouverte ;
- Planifiées : repliée ;
- Terminés : repliée ;
- Annulés : repliée.

La section Épinglés n’est affichée que lorsqu’au moins une exécution est épinglée.

Une section métier vide n’est pas rendue. Ne pas afficher un titre de section vide uniquement pour conserver la structure théorique.

L’état ouvert / fermé doit continuer à être mémorisé par le mécanisme de reading memory existant.

Si l’utilisateur ouvre ou ferme une section, quitte l’écran puis revient dans le même contexte de lecture, son choix doit être restauré selon le comportement déjà établi dans l’application.

### Affectation d’une exécution à une section

L’affectation visuelle suit cette priorité, afin d’éviter toute duplication :

1. si l’exécution est épinglée, elle est affichée dans **Épinglés** et n’est pas dupliquée dans sa section de statut ;
2. sinon `pending_validation` → **À valider** ;
3. sinon `in_progress` avec retard réel → **En retard** ;
4. sinon `in_progress` → **En cours** ;
5. sinon `scheduled` → **Planifiées** ;
6. sinon `done` → **Terminés** ;
7. sinon `canceled` → **Annulés**.

Un statut non reconnu ne doit pas être réinterprété silencieusement. L’audit doit vérifier les statuts réellement possibles et préserver le comportement métier existant.

À l’intérieur d’une section, conserver l’ordre canonique fourni par l’API, sauf pour la liste Planifiées détaillée qui doit être chronologique par date de début croissante. Ne pas introduire de tri client arbitraire sur les autres sections.

---

## 7. Section Épinglés

L’épinglage est considéré comme un mécanisme **personnel de priorisation**.

Il permet de conserver en haut de page une exécution qui intéresse particulièrement l’utilisateur.

### Comportement

- Les exécutions épinglées restent affichées en haut.
- Pas de carousel.
- Pas de swipe horizontal.
- Pas de carte dédiée spécifique aux épinglés.
- Une carte épinglée conserve la même anatomie que son statut réel.
- Le pin est un attribut de la carte, pas un type de carte.

### Pin direct

Le pin doit être accessible directement depuis la carte :

- icône discrète ;
- état actif visible ;
- cible tactile minimale de 48 px ;
- pas de menu `…` uniquement pour cette action.

Le comportement doit respecter `can_pin`.

Si le contexte est read-only, notamment Cross lorsque le métier l’impose, l’action ne doit pas être proposée.

### Performance attendue

Le pin / unpin doit être **optimiste** :

- mise à jour immédiate du feed ;
- déplacement immédiat vers / depuis la section Épinglés ;
- réconciliation serveur en arrière-plan ;
- rollback propre si l’appel échoue.

La mise en œuvre doit réutiliser les mécanismes de cache existants lorsqu’ils sont adaptés.

---

## 8. Carte mobile standard — En cours

`En cours` constitue la carte de référence.

### Exemple cible

```text
[En cours] [Restauration] [+2 pôles]          📌

Réorganiser le stock petit-déjeuner
avant le prochain service

Début   26 sept. · 08:00
Fin     26 sept. · 12:00               Retard 1 h

━━━━━━━━━━━━●━━━━━━━━━━
        progression temporelle

[LB] [CD] Leonard, Céline +1
Créé par Antoine Martin
```

### Informations obligatoires

La carte standard affiche :

- badge de statut ;
- badge du pôle pilote ;
- information multi-pôles si applicable ;
- titre du plan ;
- début ;
- fin ;
- retard éventuel ;
- progression temporelle ;
- assignés ;
- créateur ;
- pin si disponible.

### Informations explicitement exclues

Ne pas afficher :

- nombre de tâches ;
- progression des tâches ;
- texte `Tâche X/Y` ;
- détails de tâches ;
- classification détaillée de type observation ;
- pôle concerné sous forme d’une longue ligne secondaire ;
- âge relatif / `last_activity_at` dans le header de la carte ;
- toute information qui appartient au détail Exécution.

### Titre

- élément visuel dominant ;
- maximum deux lignes ;
- doit rester facilement lisible en scan rapide.

---

## 9. Pôle pilote et plans multi-pôles

Le badge principal représente le **pôle pilote**.

Exemple :

```text
[Restauration]
```

Lorsqu’un plan concerne plusieurs pôles :

```text
[Restauration] [+2 pôles]
```

Le pôle pilote reste toujours identifiable comme le badge principal.

L’information sur les autres pôles doit rester secondaire et compacte.

Le compteur `+N pôles` compte uniquement les **autres pôles**, hors pôle pilote.

Les noms des autres pôles doivent être accessibles directement dans la carte lorsque les données du feed le permettent, sans empiler plusieurs badges de même importance :

```text
Avec Hôtel · Petit-déjeuner
```

Règle de densité :

- jusqu’à 2 autres pôles : afficher leurs noms ;
- au-delà : afficher les 2 premiers puis `+N`.

Exemple :

```text
Avec Hôtel · Petit-déjeuner +2
```

Ne pas afficher cette ligne lorsqu’il n’existe aucun autre pôle.

### Point technique à vérifier

Le feed doit réellement exposer l’information nécessaire pour identifier les autres pôles.

Ne pas déclencher une requête de détail par carte simplement pour alimenter cette information.

Si les données ne sont pas disponibles dans le feed, Cursor doit le signaler avant implémentation plutôt que d’inventer une donnée.

---

## 10. Assignés

Les assignés représentent :

> **Qui doit agir ?**

Ils sont donc plus importants que le créateur.

### Affichage cible

- petits avatars ;
- afficher au maximum **2 assignés nommément** sur la carte ;
- `+N` pour les assignés supplémentaires.

Exemple :

```text
[LB] [CD] Leonard, Céline +1
```

S’il n’existe aucun assigné, afficher une information secondaire explicite `Non assigné` plutôt qu’un espace vide : l’absence de responsable est une information opérationnelle.

Le feed ne doit pas afficher une longue chaîne de noms qui rend la carte difficile à scanner.

---

## 11. Créateur

Le créateur représente l’origine du plan, pas l’action à effectuer.

Il reste donc une information secondaire.

Libellé :

```text
Créé par Antoine Martin
```

L’avatar du créateur n’est pas obligatoire.

Les avatars doivent être prioritairement réservés aux assignés pour éviter la surcharge visuelle.

Si le feed ne fournit pas de créateur exploitable, masquer la ligne plutôt que d’afficher `Inconnu`.

---

## 12. Temporalité — principe général

La temporalité devient une information centrale des cartes Exécution.

Le feed doit rendre immédiatement lisibles :

- le début ;
- la fin ;
- le retard éventuel ;
- la position temporelle de l’exécution dans sa fenêtre.

La barre n’est **jamais** une progression du travail ni une progression des tâches.

Elle représente uniquement la temporalité.

### Données partielles

Le rendu doit rester honnête lorsque toutes les dates ne sont pas présentes :

- début + fin valides : afficher les deux et la barre lorsque le statut le prévoit ;
- début uniquement : afficher le début, sans barre ;
- fin uniquement : afficher la fin, sans barre ;
- aucune date exploitable : masquer le bloc temporel plutôt que fabriquer une valeur ;
- `all_day` : afficher l’information de journée entière / date pertinente, sans progression horaire artificielle.

Le statut de retard doit s’appuyer sur la logique métier / donnée autoritative existante (`is_overdue` ou équivalent). Ne pas créer dans l’UI une nouvelle définition concurrente du retard. La durée `Retard X` peut être dérivée de l’échéance uniquement lorsque cette échéance est valide.

Ce chantier ne change pas la sémantique de fuseau horaire de l’application. Réutiliser les formatters et conventions temporelles existants ; en Cross, ne pas afficher une heure de résumé si elle ne peut pas être présentée sans ambiguïté.

---

## 13. Barre temporelle — En cours

Lorsque `start_at` et `end_at` sont connus et valides, la barre représente la position actuelle entre le début et la fin.

La progression temporelle est calculée sur l’intervalle `start_at → end_at`, bornée entre 0 % et 100 %. Elle ne doit jamais dépasser visuellement la barre.

Exemple :

```text
Début 08:00                         Fin 12:00
━━━━━━━━━━━━●━━━━━━━━━━━━━━━━
              maintenant
```

### Cas attendus

#### Avant l’échéance

La barre progresse entre le début et la fin.

#### Après la fin

- barre pleine ;
- retard explicitement affiché.

Exemple :

```text
Retard 2 h
```

ou :

```text
Retard 1 j
```

#### Journée entière

Ne pas inventer une fausse progression précise si la donnée ne le permet pas.

Un rendu compact `Journée entière` peut remplacer la barre.

#### Date manquante, invalide ou intervalle incohérent

Ne pas afficher de progression artificielle.

Si `start_at >= end_at`, ne pas afficher la barre et conserver uniquement les informations temporelles que l’on peut présenter sans ambiguïté.

---

## 14. Section En retard

Les exécutions réellement en retard doivent être distinguées des autres exécutions en cours.

Ordre :

```text
À VALIDER
EN RETARD
EN COURS
```

### Règle métier

Une exécution `in_progress` en retard doit apparaître dans `EN RETARD` plutôt que dans `EN COURS`.

`EN RETARD` est une **section de priorité**, pas un nouveau statut métier. La carte conserve son badge de statut `En cours` et l’UI de la carte standard, avec un `Retard X` visible.

### Point technique impératif

Le regroupement en section `EN RETARD` doit être compatible avec :

- l’ordre renvoyé par l’API ;
- la pagination serveur ;
- le comportement de `is_overdue`.

Il ne faut pas fabriquer côté client une section qui donnerait une représentation trompeuse parce que certains éléments en retard n’ont pas encore été chargés.

Si l’architecture backend actuelle ne garantit pas ce comportement proprement, Cursor doit le remonter avant implémentation.

---

## 15. Variante À valider

`À valider` est une variation visuelle de la carte standard.

Elle ne doit pas devenir un composant radicalement différent.

### Exemple cible

```text
[À valider] [Restauration] [+2 pôles]          📌

Réorganiser le stock petit-déjeuner
avant le prochain service

Fin prévue     26 sept. · 12:00

[LB] [CD] Leonard, Céline +1
Créé par Antoine Martin
```

### Règles

- badge `À valider` en premier ;
- tonalité amber discrète ;
- petite icône de notification / cloche dans le header ;
- surface très légèrement chaude pour différencier l’état, sans border épaisse ni grosse zone colorée ;
- pas de grosse sidebar orange ;
- pas de barre temporelle ;
- pas de progression de tâches ;
- pas de `Retard X` ;
- `Fin prévue` uniquement si une échéance fiable existe ; sinon omettre cette ligne ;
- assignés visibles ;
- créateur visible ;
- pin disponible selon permissions ;
- toute la carte ouvre le détail.

### Validation

Ne pas ajouter de bouton `Valider` directement depuis le feed dans ce chantier.

La validation reste dans le détail Exécution.

---

## 16. Variante Planifiée

La carte Planifiée reprend l’anatomie de la carte standard.

### Exemple cible

```text
[Planifiée] [Maintenance] [+1 pôle]            📌

Contrôle préventif de la climatisation

Début   29 sept. · 09:00
Fin     29 sept. · 11:00
Début dans 3 j

━━━━━━━━━━━━━━●━━━━━━━━
       progression vers le début

[AM] Alice Martin
Créé par Leonard Boisson
```

### Principe de barre

Pour une carte Planifiée, la barre représente la progression **vers le début du plan**.

Elle ne représente pas l’avancement du plan.

### Point technique impératif

Le système doit disposer d’une borne de départ fiable pour calculer cette progression vers `start_at`.

Cette borne peut être, selon ce que le modèle métier expose réellement :

- `visible_from` ;
- une autre date de début de visibilité métier ;
- un équivalent existant dans les données.

Ne pas utiliser arbitrairement `created_at` si ce n’est pas la bonne sémantique produit.

Lorsque cette borne fiable existe, la progression est calculée sur l’intervalle `borne_de_visibilité → start_at`, bornée entre 0 % et 100 %.

Ne pas inventer un pourcentage si aucune origine temporelle fiable n’existe, si la borne est postérieure ou égale à `start_at`, ou si les dates sont invalides.

Dans ces cas :

- afficher `Début dans X` lorsque `start_at` est exploitable ;
- ne pas afficher la barre.

---

## 17. Variante Terminé

Les exécutions terminées doivent être visuellement plus compactes.

Elles ne doivent pas rivaliser avec le travail actif.

### Exemple cible

```text
[Terminé] [Restauration]

Réorganiser le stock petit-déjeuner

Terminé le 26 sept. · 11:42
[LB] [CD]
```

### Simplifications

Ne pas afficher :

- barre temporelle ;
- début détaillé ;
- fin détaillée ;
- retard ;
- créateur ;
- information multi-pôles développée ;
- progression des tâches.

Conserver uniquement les informations utiles à la lecture historique rapide.

Le libellé `Terminé le …` ne doit être affiché que si le feed expose un timestamp de fin métier fiable. Ne pas utiliser `last_activity_at` comme substitut à une date de terminaison.

Si aucune date de fin fiable n’est disponible dans le feed, omettre la ligne de date plutôt que d’inventer une information.

Si le métier distingue `Terminé` et `Validé` via les données existantes, conserver cette distinction dans le badge ou le langage déjà prévu par le produit.

---

## 18. Variante Annulé

L’état Annulé doit être encore plus sobre.

### Exemple cible

```text
[Annulé] [Maintenance]

Contrôle préventif de la climatisation

Annulé le 26 sept.
[AM]
```

### Règles

- surface neutre ;
- badge muted ;
- pas de rouge agressif ;
- pas de barre ;
- pas de countdown ;
- pas de créateur ;
- pas de surcharge d’informations.

Le libellé `Annulé le …` ne doit être affiché que si un timestamp d’annulation métier fiable est disponible. Ne pas utiliser `last_activity_at` comme proxy.

Annulé est un état terminal, pas une alerte active.

---

## 19. Section Planifiées — remplacement de l’écran « À venir »

Sur **mobile web et Capacitor**, la navigation vers l’écran dédié actuel « À venir » est remplacée par une expérience inline dans le feed.

Le desktop étant hors périmètre, son accès actuel à « À venir » doit continuer à fonctionner dans ce chantier. Ne pas supprimer globalement une route, une page ou un composant encore utilisé par le desktop.

### État replié — cible figée

```text
PLANIFIÉES                                18   ›
Prochaine : demain · 09:00
```

### Règles

- section repliée par défaut ;
- compteur à droite si le total est fiable ;
- ce compteur représente les planifications **non déjà affichées dans Épinglés**, afin que le nombre corresponde au contenu réellement ouvrable dans la section ;
- chevron pour indiquer l’ouverture ;
- seconde ligne discrète ;
- `Prochaine :` affiché seulement si une prochaine exécution **non épinglée** est identifiable de manière fiable ;
- format attendu : `Prochaine : aujourd’hui · 16:30`, `Prochaine : demain · 09:00` ou `Prochaine : lun. 28 sept. · 09:00` ;
- pour une exécution all-day, remplacer l’heure par `Journée entière`.

Si aucune prochaine exécution ne peut être calculée :

```text
PLANIFIÉES                                18   ›
```

### Objectif

L’utilisateur garde une visibilité sur ce qui arrive ensuite, sans polluer le principe :

> **ce qui m’intéresse maintenant d’abord.**

---

## 20. Section Planifiées — état développé

Quand l’utilisateur ouvre la section :

- affichage inline dans le feed ;
- aucune navigation vers un écran secondaire sur mobile ;
- chargement lazy des prochaines exécutions ;
- afficher **jusqu’à 3 prochaines exécutions** dans le premier lot ;
- affichage des cartes Planifiées définies plus haut ;
- regroupement chronologique léger ;
- pagination inline via `Afficher plus`.

### Regroupement chronologique cible

Chaque groupe correspond à **une date de début**, sans catégories temporelles qui se chevauchent :

```text
Aujourd’hui
Demain
Lun. 28 sept.
Mar. 29 sept.
```

Utiliser `Aujourd’hui` et `Demain` uniquement pour ces deux dates ; au-delà, afficher la date locale formatée.

Les exécutions sont ordonnées par `start_at` croissant dans cette section.

Ne pas créer :

- mini-calendrier ;
- grille ;
- colonnes de jours ;
- nouvelle surface calendrier.

Il s’agit uniquement d’une timeline verticale lisible.

---

## 21. Chargement des Planifiées

Le comportement est lazy :

- le feed initial ne doit pas charger inutilement toute la liste future ;
- la requête upcoming peut être activée lorsque la section est développée ;
- les premières informations nécessaires au résumé replié doivent utiliser les données disponibles sans déclencher une charge excessive ;
- une erreur de chargement de la section Planifiées doit être affichée **dans cette section** avec possibilité de réessayer, sans faire échouer ni masquer le reste du feed.

L’implémentation doit réutiliser autant que possible l’endpoint / query upcoming existant.

Il ne doit exister **qu’une seule section Planifiées** dans le rendu mobile : aucun plan `scheduled` ne doit être dupliqué entre les éléments du feed principal et la liste upcoming.

L’audit doit déterminer la source canonique permettant d’obtenir une liste future exhaustive et paginée. Si l’endpoint upcoming couvre bien ce besoin, il devient la source de contenu de la section développée ; les `scheduled` éventuellement présents dans les pages du feed principal ne doivent alors pas être rendus une seconde fois.

### Cross

La cible produit reste la même en Cross : une seule section Planifiées, repliée par défaut, sans liste future partielle présentée comme exhaustive.

Si l’API Cross actuelle ne permet pas de charger exhaustivement les planifications futures, ne pas bricoler un filtrage sur les seules pages déjà chargées. L’audit doit remonter le besoin d’un support API adapté avant implémentation de cette partie.

### Écran / route « À venir »

Pour la cible mobile, aucune navigation vers un écran secondaire « À venir » ne doit rester dans le parcours Liste. La ligne / CTA mobile `À venir N ›` actuelle disparaît du feed mobile et est remplacée par la section Planifiées repliable.

Les éléments actuels de type :

- `ExecutionUpcomingPage`
- `ExecutionUpcomingNavRow`
- route associée

doivent être audités.

**Ne pas les supprimer globalement dans ce chantier s’ils servent encore au desktop.** Le résultat attendu est l’absence de rupture de navigation sur mobile, pas la suppression forcée d’une route partagée.

---

## 22. Pagination

Dans les sections paginées :

libellé cible :

```text
Afficher plus
```

et non :

```text
Charger plus
```

Le bouton doit rester explicite.

Deux paginations peuvent coexister sans ambiguïté :

- pagination du feed principal : `Afficher plus` à la fin du contenu principal ;
- pagination de la section Planifiées développée : `Afficher plus` **à l’intérieur** de cette section.

L’audit doit toutefois vérifier que la pagination du feed principal ne peut pas charger des pages composées majoritairement de `scheduled` désormais masqués au profit de la section Planifiées. Si c’est le cas, une adaptation de la source/API doit être proposée plutôt qu’un bouton `Afficher plus` qui semble ne rien charger.

Pas d’infinite scroll automatique dans ce chantier.

---

## 23. Compteurs de sections

Ne pas présenter comme total global un nombre qui correspond seulement aux éléments déjà chargés dans la pagination.

### Planifiées

Le feed expose déjà un `scheduled_count`.

Il peut être utilisé si sa sémantique correspond bien au total attendu.

### Autres sections

Si l’API ne fournit pas de total fiable :

- ne pas afficher de faux total ;
- ne pas utiliser `group.items.length` comme si c’était le nombre global.

Cursor doit vérifier la sémantique exacte avant implémentation.

---

## 24. Chargement initial

Le spinner centré actuel doit être remplacé par des skeletons cohérents avec les cartes.

Au chargement initial du feed, afficher un petit lot stable de skeletons de cartes (3 par défaut convient à la cible visuelle). Lors de l’ouverture lazy de Planifiées, utiliser des skeletons locaux à cette section et ne pas bloquer le reste du feed.

Objectifs :

- limiter le saut de layout ;
- donner immédiatement la structure du feed ;
- rester cohérent avec la refonte récente du Feed Observations.

---

## 25. États vides

Conserver un état vide clair et compact.

Le texte doit rester contextualisé selon :

- Ma vue ;
- Vue globale ;
- rôle utilisateur ;
- établissement / Cross.

Ne pas introduire de CTA ou d’action métier non cadrés.

---

## 26. Cross

Le comportement Cross doit être préservé.

Le chantier ne doit pas casser :

- isolation des établissements ;
- source Cross ;
- navigation vers le détail ;
- permissions ;
- read-only si applicable ;
- mémoire de lecture séparée.

Les actions interdites en Cross ne doivent pas devenir accessibles via la refonte visuelle.

La refonte ne doit pas élargir les capacités Cross : si le pin est actuellement indisponible dans ce contexte, il reste indisponible.

---

## 27. Mémoire de lecture

Conserver le comportement existant de reading memory par contexte.

À préserver :

- scroll ;
- état ouvert / fermé des sections ;
- isolation entre établissements ;
- isolation entre établissement et Cross ;
- isolation entre Ma vue / Vue globale si le comportement actuel le prévoit.

La refonte ne doit pas recréer un comportement de fuite A → B → A déjà corrigé ailleurs dans l’application.

---

## 28. Filtres — hors de ce commit

Les filtres feront l’objet d’un **deuxième commit de PR3-A**.

Ne pas ajouter de faux filtres uniquement côté client sur un feed paginé serveur.

Avant le commit filtres, il faudra auditer :

- paramètres acceptés par l’API ;
- compatibilité avec la pagination ;
- besoins réels : statut, pôle, assigné, échéance, épinglés, etc.

Le présent cadrage ne demande aucune implémentation de ces filtres.

---

## 29. Accessibilité et interactions

Toutes les interactions mobiles doivent respecter les standards déjà utilisés dans Spore.

À conserver ou garantir :

- cible tactile minimale 48 px pour les actions créées ou modifiées dans ce chantier, notamment le pin ;
- focus visible sur web ;
- navigation clavier lorsque le composant est rendu sur web ;
- carte entière sélectionnable ;
- pin ne doit pas déclencher l’ouverture de la carte ;
- texte tronqué proprement sans casser les informations essentielles ;
- contraste suffisant ;
- `prefers-reduced-motion` respecté si une animation est ajoutée.

---

## 30. Principes visuels

La direction visuelle doit rester cohérente avec le nouveau langage mobile Spore issu de PR0 / PR1 / PR2.

### À rechercher

- cartes compactes ;
- hiérarchie typographique forte ;
- surfaces sobres ;
- badges courts ;
- couleurs utilisées comme signal, pas comme décoration ;
- peu d’ombres ;
- radius cohérent ;
- respiration suffisante ;
- densité adaptée au terrain ;
- lecture rapide à une main.

### À éviter

- grosses sidebars colorées ;
- cartes complètement teintées selon le statut ;
- répétition de la même information ;
- accumulation de badges ;
- surcharge de métadonnées ;
- effets décoratifs sans valeur fonctionnelle ;
- imitation d’un gestionnaire de tâches générique.

---

## 31. Comportements métier à préserver

La refonte est une refonte de présentation du feed.

Elle ne doit pas modifier sans décision produit explicite :

- statut réel des exécutions ;
- règles de transition de statut ;
- logique de validation ;
- permissions ;
- logique d’assignation ;
- création des plans ;
- planification ;
- sémantique des dates ;
- métier des tâches ;
- règles de visibilité ;
- isolation multi-tenant ;
- Cross ;
- navigation vers le détail.

---

## 32. Contraintes techniques à auditer avant implémentation

Cursor doit vérifier avant de coder :

### Retard

- comment `is_overdue` est déterminé ;
- ordre API ;
- compatibilité avec pagination ;
- possibilité de créer une vraie section `En retard`.

### Barre Planifiée

- existence d’une borne de départ métier fiable ;
- rôle éventuel de `visible_from` ;
- comportement lorsque la borne n’existe pas.

### Multi-pôles

- données réellement exposées par le feed ;
- possibilité d’afficher `+N pôles` sans requête détail.

### Planifiées

- sémantique exacte de `scheduled_count` et inclusion éventuelle des exécutions épinglées ;
- capacité à produire un compteur Planifiées cohérent avec le contenu non épinglé de la section ;
- relation entre les `scheduled` déjà présents dans le feed et l’endpoint upcoming ;
- absence de doublons ;
- possibilité de lazy-load ;
- usages réels de la route / page « À venir ».

### Compteurs

- distinguer total serveur et taille du tableau chargé.

### Pin

- mécanisme de cache existant ;
- possibilité d’optimistic update ;
- rollback ;
- maintien des permissions.

### Évolutions API éventuellement nécessaires

Le cadrage fixe le résultat produit, pas l’architecture technique.

Si l’audit démontre qu’une évolution API minimale est nécessaire pour garantir correctement :

- la section En retard avec pagination ;
- la liste Planifiées exhaustive ;
- Cross ;
- les compteurs fiables ;
- le contexte multi-pôles ;

Cursor doit **s’arrêter au plan**, documenter précisément le manque et proposer l’évolution minimale. Ne pas compenser par un filtrage client incomplet, des totaux approximatifs ou des requêtes détail par carte.

Aucune évolution API ne doit modifier les règles métier de statut, permissions, visibilité ou isolation multi-tenant.

---

## 33. Tests attendus

Le plan d’implémentation doit couvrir au minimum :

### Structure

- Liste / Calendrier au-dessus de Ma vue / Vue globale ;
- calendrier fonctionnel inchangé ;
- ordre des sections ;
- sections par défaut ouvertes / fermées ;
- sections vides non rendues ;
- exécution épinglée non dupliquée dans sa section de statut ;
- contrôle `+` de création inchangé ;
- desktop inchangé.

### Carte En cours

- début / fin ;
- retard ;
- barre temporelle ;
- assignés ;
- créateur ;
- pôle pilote ;
- multi-pôles ;
- absence des tâches ;
- absence de `last_activity_at` / âge relatif ;
- cas dates partielles et all-day.

### À valider

- variation spécifique ;
- pas de barre ;
- pas de retard ;
- pas de bouton validation ;
- badge amber + cloche + surface chaude discrète.

### Planifiée

- début / fin ;
- `Début dans X` ;
- barre vers le début uniquement si calculable ;
- absence de fausse progression.

### Terminée / Annulée

- variantes compactes ;
- absence de temporalité active.

### Épinglage

- pin direct ;
- permissions ;
- optimistic update + rollback ;
- déplacement dans la section Épinglés ;
- Cross ;
- pin sur états terminaux si permis.

### Planifiées inline

- replié par défaut ;
- résumé `Prochaine : …` ;
- ouverture inline ;
- premier lot limité à 3 éléments ;
- lazy loading ;
- pagination locale `Afficher plus` ;
- regroupement chronologique par date sans chevauchement ;
- absence de doublon avec les `scheduled` du feed principal ;
- erreur locale sans casser le feed ;
- aucune navigation vers l’écran dédié sur mobile ;
- comportement desktop actuel préservé.

### Reading memory

- scroll ;
- sections ;
- A → B → A ;
- Ma vue / Vue globale ;
- établissement / Cross.

### États

- loading skeleton ;
- erreur ;
- empty ;
- pagination.

---

## 34. Validation manuelle attendue

Avant merge, vérifier sur :

- mobile web étroit ;
- iOS Capacitor ;
- Android Capacitor.

Scénarios :

1. Feed avec plusieurs exécutions En cours.
2. Feed avec retard.
3. Feed avec plusieurs épinglés.
4. Feed avec une exécution À valider.
5. Feed avec plusieurs plans Planifiés.
6. Ouverture / fermeture de Planifiées.
7. Retour après navigation détail.
8. Changement Ma vue / Vue globale.
9. Changement d’établissement.
10. Cross.
11. Pin / unpin.
12. Plan multi-pôles.
13. Assignés nombreux.
14. Titres longs.
15. Dates invalides ou partielles.
16. Journée entière.
17. Pagination.
18. Calendrier toujours fonctionnel et visuellement inchangé.
19. Aucune duplication d’une exécution épinglée.
20. Aucune duplication d’une exécution Planifiée.
21. Planifiées : erreur réseau locale puis retry.
22. Absence d’assigné (`Non assigné`).
23. Créateur absent : ligne masquée.
24. Desktop : feed et écran « À venir » existants non régressés.

---

## 35. Critères d’acceptation produit

Le chantier est considéré conforme si :

- le feed permet de comprendre immédiatement ce qui demande une attention actuelle ;
- les plans futurs n’occupent pas visuellement le haut de la page ;
- sur mobile, Planifiées est accessible sans quitter le feed ;
- aucune exécution n’est dupliquée entre Épinglés et les sections de statut, ni entre le feed principal et Planifiées ;
- les cartes En cours sont centrées sur plan + temps + personnes ;
- `En retard` reste une priorité d’affichage sans créer de nouveau statut métier ;
- aucune information de tâche n’apparaît dans les cartes du feed ;
- la temporalité n’est jamais présentée comme une progression du travail ;
- le pôle pilote reste identifiable ;
- les plans multi-pôles sont signalés sans surcharge ;
- assignés et créateur sont clairement distingués ;
- À valider possède une identité visuelle spécifique mais cohérente ;
- Terminés et Annulés sont plus compacts ;
- le pin est direct et personnel ;
- Cross et les permissions ne régressent pas ;
- le calendrier reste hors scope et inchangé ;
- le desktop reste visuellement et fonctionnellement inchangé dans ce chantier ;
- aucune fausse donnée n’est introduite pour les compteurs ou barres temporelles.

---

## 36. Découpage recommandé de PR3-A

### Commit 1 — Feed Exécution mobile

Ce cadrage.

Inclut :

- structure ;
- cartes ;
- statuts ;
- temporalité ;
- multi-pôles ;
- assignés ;
- créateur ;
- pin ;
- planifiées inline ;
- skeletons ;
- pagination ;
- reading memory associée.

### Commit 2 — Filtres Feed Exécution

Cadrage séparé après audit API.

---

## 37. Doctrine finale

Le Feed Exécution ne doit pas être une liste exhaustive de données métier.

Il doit être une surface opérationnelle permettant de :

> **voir ce qui compte maintenant, comprendre le timing, identifier qui agit, puis ouvrir le détail lorsque nécessaire.**

La densité et la priorité visuelle doivent toujours favoriser le travail actif avant le futur ou l’historique.
