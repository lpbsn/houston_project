# Spore Analytics — Document de cadrage fonctionnel et data

**Statut :** cible produit validée  
**Portée :** refonte Dashboard Analytics + navigation desktop scopée + adaptations desktop Observations / Exécution  
**Usage prévu :** document de référence pour l’audit du repo, la création du plan d’implémentation, sa validation, l’implémentation, la review des diffs et l’hygiène finale.

---

## 1. Hiérarchie des sources de vérité

Pour cette évolution, utiliser l’ordre suivant :

1. **Ce document** : vérité fonctionnelle et data.
2. **Captures d’écran de la maquette cible fournies avec le prompt Cursor** : référence visuelle, hiérarchie, densité, composition et intention UI.
3. **Repo `lpbsn/houston_project`** : point de départ technique à auditer, **pas une vérité à préserver**.

En cas de conflit :
- le présent document prime sur la maquette pour le comportement et les données ;
- la maquette prime pour l’intention visuelle lorsqu’elle ne contredit pas ce document ;
- l’existant peut être refactoré, remplacé ou supprimé si nécessaire pour atteindre une cible plus simple, fiable et cohérente.

Ne pas conserver une architecture, un endpoint, un composant, un filtre ou une convention uniquement parce qu’ils existent déjà.

---

## 2. Vocabulaire

- **Observation** : libellé produit affiché à l’utilisateur.
- **Signal** : objet métier / technique correspondant à une observation.
- **Motif** : catégorie métier canonique permettant de regrouper plusieurs Signals relevant du même problème.
- **Récurrence d’un Signal** : mécanique existante de dédoublonnage / agrégation d’un même incident. **Ce n’est pas la récurrence d’un motif définie dans ce document.**
- **Scope** : contexte courant `Cross établissement` ou `Établissement`.
- **Période actuelle** : fenêtre glissante sélectionnée par l’utilisateur.
- **Période précédente** : fenêtre de même durée immédiatement antérieure.

---

## 3. Objectif produit

Le Dashboard Spore Analytics doit permettre à une direction ou à un manager de répondre rapidement à quatre questions :

1. Quels problèmes reviennent ou apparaissent ?
2. L’organisation traite-t-elle correctement les observations et plans d’action ?
3. Où se concentre l’activité opérationnelle ?
4. Qui contribue le plus sur la période ?

Le dashboard doit rester lisible, décisionnel et non trompeur. Une métrique ne doit pas être ajoutée uniquement parce qu’elle est calculable.

---

## 4. Navigation desktop et scopes

### 4.1 Desktop uniquement

La nouvelle sidebar scopée concerne **uniquement le desktop**.

- Desktop : navigation par scope dans la sidebar.
- Mobile : conserver le fonctionnement mobile actuel et le switch établissement.

Le switch établissement actuel ne doit plus être présenté comme mécanisme de navigation dans le shell desktop concerné.

### 4.2 Scope dans l’URL

Le scope courant doit être représenté explicitement dans l’URL.

Un deep-link doit permettre de déterminer sans ambiguïté :
- le scope Cross ;
- ou l’établissement courant.

Ne pas faire dépendre ces pages uniquement d’un `activeEstablishment` global implicite.

La forme exacte des routes est une décision d’implémentation après audit du repo, à condition que le scope reste explicite et deep-linkable.

### 4.3 Sidebar

Ordre :
1. **Cross établissement**
2. établissements accessibles à l’utilisateur, triés alphabétiquement.

Comportement :
- Cross établissement déplié par défaut ;
- établissements repliés par défaut ;
- la section correspondant à la route courante s’ouvre automatiquement ;
- état ouvert / fermé local à la session de navigation ;
- aucune préférence persistée en V1.

Une URL pointant vers un établissement non autorisé doit produire un **refus d’accès explicite**, jamais un fallback silencieux vers un autre établissement.

### 4.4 Contenu du scope Cross établissement

- Dashboard
- Nouvelle observation — **placeholder “Bientôt disponible”**
- Observations — lecture seule
- Exécution — lecture seule
- Chat — **placeholder “Bientôt disponible”**
- Paramètres Analytics — **placeholder “Bientôt disponible”**

Pas de page `Général` Cross en V1.

### 4.5 Contenu d’un scope établissement

- Dashboard
- Nouvelle observation
- Observations
- Exécution
- Chat
- Général
- Paramètres Analytics — **placeholder “Bientôt disponible”**

### 4.6 RBAC

Dashboard Analytics :
- `owner`
- `director`
- `manager`

Un `staff` :
- ne voit pas l’entrée Dashboard ;
- ne peut pas ouvrir la route Dashboard ;
- ne peut pas appeler les endpoints Analytics protégés.

Cross établissement :
- owner / director : accès Cross selon leur organisation ;
- manager : Cross limité aux établissements qu’il est autorisé à gérer ;
- staff : pas de Cross.

Le contrôle doit être garanti **côté backend et côté frontend**. Le masquage UI n’est pas une protection.

Les agrégations Cross ne doivent jamais inclure un établissement que l’utilisateur n’est pas autorisé à consulter dans ce contexte.

---

## 5. Dashboard — structure générale

Titre de page :

> **Dashboard Spore Analytics**

La même structure de dashboard est utilisée :
- en Cross établissement, avec agrégation du scope autorisé ;
- dans un établissement, avec données strictement limitées à cet établissement.

### 5.1 Résumé de la semaine — IA

Fonctionnalité future.

Afficher une carte / section visible avec :
> **Bientôt disponible**

Le futur résumé IA utilisera également la période sélectionnée.

Aucun backend fictif, aucune donnée simulée et aucune génération IA ne doivent être développés en V1.

### 5.2 Export

Afficher le bouton d’export comme fonctionnalité future :
> **Bientôt disponible**

Aucun export réel en V1.

### 5.3 CA vs Observations

Fonctionnalité future.

Afficher uniquement le placeholder :
> **Bientôt disponible**

Aucun calcul ou endpoint dédié en V1.

### 5.4 Personnalisation du dashboard

Le drag & drop des cartes, la sauvegarde de l’ordre et les layouts personnalisés sont **hors scope**.

---

## 6. Période globale

Presets disponibles :

- **3 j**
- **7 j**
- **15 j**
- **30 j**
- **90 j**

Période par défaut :
> **7 jours**

### 6.1 Définition

Une période est une **fenêtre glissante exacte** jusqu’au moment de consultation.

Exemple :
- `7 j` = les 7 × 24 dernières heures.

Un refresh recalcule la fenêtre. Le preset doit être représenté dans l’état de navigation ; il ne faut pas figer accidentellement un ancien `period_end` dans l’URL.

### 6.2 Période précédente

La période précédente a exactement la même durée et précède immédiatement la période actuelle.

Exemple :
- actuel : `J-7 → maintenant`
- précédent : `J-14 → J-7`

### 6.3 Timezone

- scope établissement : timezone métier de l’établissement ;
- scope Cross : timezone métier de l’organisation.

Les timestamps restent timezone-aware dans les calculs et le stockage.

### 6.4 Portée du filtre

La période s’applique à **tout le Dashboard Analytics**, y compris au futur résumé IA.

Seule l’**ancienneté des observations ouvertes** utilise une logique de stock spécifique définie plus bas afin de ne pas masquer les observations anciennes.

---

## 7. Comparaisons et sémantique des évolutions

### 7.1 Formule standard

Pour une valeur comparable :

`(actuel - précédent) / précédent × 100`

Si `précédent = 0` :
- actuel > 0 → afficher **Nouveau** ;
- actuel = 0 → afficher `—` ;
- ne jamais produire `∞` ou un faux `+100 %`.

Pour les proportions / taux, comparer en **points de pourcentage** et non en pourcentage relatif.

Exemple :
- 54 % → 61 % = `+7 pts`

### 7.2 Sens métier des couleurs

Une hausse n’est pas automatiquement positive.

- délai de traitement ↓ : positif ;
- délai de traitement ↑ : négatif ;
- réouvertures ↓ : positif ;
- réouvertures ↑ : négatif ;
- taux de résolution ↑ : positif ;
- part des clôtures résolues ↑ : positif ;
- ancienneté `> 15 j` ↓ : positif ;
- motifs récurrents ↑ : négatif ;
- motifs récurrents ↓ : positif ;
- volume d’observations : neutre ;
- activité par pôle : neutre ;
- nouveaux motifs : neutre ;
- zones les plus signalées : volume et évolution neutres tant qu’aucun indicateur de risque fiable n’existe.

---

## 8. Motifs récurrents

Titre :
> **Motifs récurrents**

### 8.1 Définition

Un motif récurrent est un **motif canonique associé à au moins 2 Signals métier distincts** dans le scope et la période sélectionnés.

La mécanique existante de récurrence / dédoublonnage d’un même Signal ne constitue **pas** une récurrence de motif.

Exemple :
- 5 remontées agrégées dans le même Signal = 1 Signal métier pour le motif ;
- un nouvel incident distinct rattaché au même motif = nouvelle occurrence du motif.

### 8.2 Affichage

Pour chaque motif :
- nom ;
- nombre de **Signals distincts** associés pendant la période ;
- évolution en % par rapport au nombre de Signals distincts du même motif sur la période précédente.

### 8.3 Tri et limite

Afficher les **5 premiers motifs**.

Tri :
1. nombre d’occurrences décroissant ;
2. dernière occurrence la plus récente ;
3. nom alphabétique.

### 8.4 Identité historique

Renommer ou fusionner un motif ne doit pas créer artificiellement un nouveau motif ni casser son historique.

Les calculs utilisent l’identité canonique du motif.

---

## 9. Nouveaux motifs

Titre :
> **Nouveaux motifs**

### 9.1 Définition

Un nouveau motif est un motif dont la **première apparition historique connue dans le scope courant** intervient pendant la période sélectionnée.

- Cross : jamais vu auparavant dans l’organisation.
- Établissement : jamais vu auparavant dans cet établissement, même s’il est déjà connu ailleurs.

La nouveauté est évaluée relativement à l’historique réellement disponible dans Spore.

### 9.2 Affichage

Pour chaque nouveau motif :
- nom ;
- date relative de détection, ex. `Détecté il y a 4 j` ;
- donnée secondaire :
  - établissement : `X observations depuis sa détection` ;
  - Cross : `X observations · Y établissements`.

Ne pas afficher le taux de confiance.

### 9.3 Limite

Afficher **5 nouveaux motifs maximum** par défaut.

Prévoir `Voir tout / Réduire` pour afficher les autres.

---

## 10. Classement des contributeurs

Titre :
> **Classement des contributeurs**

Afficher les **5 premiers contributeurs** selon les points effectivement gagnés pendant la période.

### 10.1 Source du score

Le classement doit être calculé depuis les **événements de points historiés** de la période.

Interdits :
- utiliser le score cumulé courant ;
- calculer `score actuel - ancien score` ;
- dépendre d’un reset de score.

Si l’historique nécessaire n’existe pas, créer une source fiable plutôt que produire une approximation.

Les corrections négatives sont prises en compte : score de période = solde net des événements de points.

### 10.2 Scope

- établissement : uniquement les points rattachés à cet établissement ;
- Cross : somme des événements de points des établissements autorisés, sans double comptage.

Un utilisateur désactivé après avoir gagné ses points reste visible dans le classement historique de la période.

### 10.3 Égalités

1. points ;
2. nombre de contributions ayant généré des points ;
3. nom alphabétique.

### 10.4 Affichage

Même ligne :
- nom + prénom à gauche ;
- score à droite, format `24 pts`.

Sous le nom :
- badge du rôle ;
- pôle(s) associé(s), affichés à la suite ;
- si aucun pôle : `Sans pôle`.

Supprimer toute notion de `Qualité`.

---

## 11. Observations — performance de traitement

La section doit permettre de lire :
1. la vitesse de traitement ;
2. l’efficacité de résolution ;
3. la santé du backlog.

### 11.1 Population statistique des délais

Pour une métrique de délai, un Signal participe à la période lorsque **l’événement terminal mesuré intervient pendant la période**.

Exemple :
- Signal créé il y a 20 jours ;
- résolu hier ;
- il participe à la métrique de résolution des 7 derniers jours.

Un Signal n’ayant jamais atteint l’événement cible est exclu de cette métrique.

### 11.2 Transitions mesurées

**Annulation**
- création du Signal → première transition vers `Annulé`

**Résolution**
- création du Signal → première transition vers `Résolu`

**Transformation en plan**
- création du Signal → création / association du premier plan d’action issu de ce Signal

Ne pas utiliser simplement `in_progress` si la création du plan constitue l’événement métier plus exact.

### 11.3 Statistiques de délai

Pour chacune des trois transitions afficher :

- **Médiane / P50**
- **Moyenne**
- **P90**
- **n**

Micro-descriptions discrètes :

- Médiane : `50 % des observations sont traitées dans ce délai ou moins.`
- Moyenne : `Délai moyen observé.`
- P90 : `90 % des observations sont traitées dans ce délai ou moins.`
- n : `Nombre d’observations mesurées.`

Le P90 est affiché uniquement à partir de **10 observations éligibles**. En dessous :
> `Données insuffisantes`

Moyenne, médiane et P90 sont calculés sur les **durées individuelles**, jamais à partir de moyennes pré-agrégées.

Afficher l’évolution par rapport à la période précédente lorsqu’elle est comparable.

---

## 12. Observations — résolution

### 12.1 Taux de résolution opérationnel

Objectif :
> mesurer la part du travail réellement disponible pendant la période qui est résolue à la fin de cette période.

**Population de travail de la période = union des Signals distincts :**
- non terminaux au début de la période ;
- créés pendant la période ;
- réouverts pendant la période.

**Numérateur :**
- Signals de cette population en état `Résolu` à la fin de la période.

Formule :

`Signals du workload résolus à la fin / Signals distincts du workload`

Une Observation résolue puis réouverte et encore active à la fin de la période **ne compte pas comme résolue**.

Afficher :
- taux actuel ;
- évolution en points de pourcentage vs période précédente.

Hausse = positive.

### 12.2 Part des clôtures résolues

Objectif :
> parmi les Signals effectivement clôturés, mesurer la part ayant abouti à une résolution plutôt qu’à une annulation.

Formule :

`Résolus / (Résolus + Annulés)`

La population est basée sur les transitions terminales intervenues pendant la période.

Afficher :
- taux actuel ;
- évolution en points de pourcentage vs période précédente.

Cette métrique ne remplace pas le taux de résolution opérationnel car elle ne mesure pas le backlog restant.

### 12.3 Réouvertures

Afficher le nombre de **Signals distincts réouverts pendant la période**.

Réouverture :
> transition depuis `Résolu` vers un état actif.

Afficher :
- nombre ;
- évolution vs période précédente.

Hausse = négative.

Pas de taux de réouverture en V1.

---

## 13. Observations — ancienneté des observations ouvertes

Ne pas afficher le terme technique `Aging` dans l’UI.

Titre :
> **Ancienneté des observations ouvertes**

Objectif :
> rendre visible un stock ancien que les métriques calculées uniquement sur les éléments terminés pourraient masquer.

### 13.1 Population

Photographie de **tous les Signals actuellement non terminaux du scope**, indépendamment de leur date de création.

Le preset de période ne filtre donc pas les vieux Signals hors de cette vue.

### 13.2 Tranches V1

- `< 3 j`
- `3–7 j`
- `8–15 j`
- `> 15 j`

Ces seuils sont descriptifs et **ne constituent pas des SLA**.

Ne pas utiliser les termes `bon`, `à risque`, `critique` ou `bloqué` sans règle métier dédiée.

### 13.3 Affichage

Afficher :
- nombre total d’observations ouvertes ;
- distribution nombre + part dans chaque tranche ;
- mise en avant de la part `> 15 j`.

Comparer principalement :

> part des observations ouvertes âgées de plus de 15 jours

entre :
- snapshot actuel ;
- snapshot à la fin de la période précédente, c’est-à-dire au début de la période actuelle.

Évolution en **points de pourcentage**.

Hausse = négative.

---

## 14. Plans d’action — délais de traitement

Les métriques sont calculées **par issue**.

### 14.1 Début d’exécution

Événement métier :
> première transition du plan vers `En cours`.

Une timestamp canonique existante peut être utilisée si elle représente exactement et de façon immuable ce même événement.

### 14.2 Annulation

`Début d’exécution → Annulé`

Le plan participe lorsque sa transition vers `Annulé` intervient dans la période.

### 14.3 Résolution

`Début d’exécution → Résolu`

Le plan participe lorsque sa transition vers `Résolu` intervient dans la période.

### 14.4 Temps de validation

Titre :
> **Temps de validation**

Définition :
> première transition vers `pending_validation` → résolution correspondante.

### 14.5 Statistiques affichées

Pour Annulation, Résolution et Temps de validation :

- **Médiane**
- **Moyenne**
- nombre d’éléments mesurés `n`

Afficher les évolutions par rapport à la période précédente lorsqu’elles sont comparables.

Pas de P90 ni d’ancienneté spécifique des plans en V1 : le respect des échéances couvre déjà la lecture de la longue traîne opérationnelle.

---

## 15. Plans d’action — respect des échéances

Objectif :
> représenter la capacité à respecter les échéances des plans d’action.

### 15.1 Classification

Pour un plan avec échéance :

- **En avance** : résolu avant le jour d’échéance ;
- **À temps** : résolu le jour de l’échéance ;
- **En retard** : résolu après l’échéance.

La comparaison calendaire utilise la timezone de l’établissement.

### 15.2 Plans encore ouverts

- échéance dépassée : compter **En retard** ;
- échéance future : exclure du graphique car le résultat n’est pas encore connu.

### 15.3 Exclusions

Exclure :
- plans annulés ;
- plans sans échéance.

### 15.4 Dénominateur

Population :
> plans résolus avec échéance + plans non terminés dont l’échéance est dépassée.

Afficher la part :
- En avance
- À temps
- En retard

Comparer les proportions à la période précédente en **points de pourcentage**.

---

## 16. Zones les plus signalées

Remplacer la notion de `Carte de chaleur des zones à risque`.

Titre recommandé :
> **Zones les plus signalées**

Le volume brut de Signals ne constitue pas une mesure de risque : certaines zones produisent naturellement plus d’activité que d’autres et Spore ne possède pas nécessairement de dénominateur d’exposition fiable.

### 16.1 Mesure

Nombre de **Signals distincts** associés à chaque zone opérationnelle sur la période actuelle.

Afficher aussi l’évolution par rapport à la même zone sur la période précédente.

Cette évolution reste visuellement **neutre** : plus de Signals peut signifier plus de problèmes ou une meilleure adoption du reporting.

### 16.2 Cross établissement

En Cross, une ligne représente un couple :

> `(établissement, zone)`

Ne pas fusionner des zones uniquement parce qu’elles portent le même nom.

Afficher un badge avec le nom de l’établissement.

### 16.3 Limite

Vue repliée :
- top 7 ;
- ligne `Autres` si nécessaire.

Prévoir :
> `Voir tout / Réduire`

pour afficher toutes les zones.

### 16.4 Couleurs

Les barres représentent uniquement le volume et restent neutres.

Ne pas utiliser rouge / vert ou un score de risque sans modèle métier spécifique.

---

## 17. Activité du pôle

Titre :
> **Activité du pôle**

### 17.1 Définition

Mesurer le nombre de **Signals distincts** par pôle responsable auquel l’observation a été routée.

Ne pas utiliser le pôle du contributeur ayant créé le Signal.

Sans affectation :
> `Sans pôle`

### 17.2 Évolution

Comparer le volume courant au volume de la période précédente.

L’évolution est visuellement **neutre**.

### 17.3 Cross établissement

En Cross, une ligne représente un couple :

> `(établissement, pôle)`

Ne pas fusionner deux pôles uniquement parce qu’ils portent le même libellé.

Afficher un badge établissement.

---

## 18. Observations et Exécution — affichage desktop

Un affichage spécifique desktop est autorisé et souhaité.

Principe :
- domaine métier partagé ;
- queries partagées ;
- mutations partagées ;
- règles d’autorisation partagées ;
- présentation pouvant diverger entre mobile et desktop.

Ne pas créer deux implémentations métier indépendantes.

### 18.1 Profondeur de refonte

Cette évolution ne doit pas déclencher une refonte fonctionnelle complète des feeds Observations / Exécution.

Objectif :
- intégration propre dans le nouveau shell desktop ;
- meilleure utilisation de l’espace desktop ;
- conservation des fonctionnalités métier existantes compatibles.

Une refonte plus profonde nécessite un cadrage dédié.

### 18.2 Cross Observations / Exécution

Cross est **strictement en lecture seule en V1**.

Autorisé :
- consultation ;
- recherche ;
- filtrage ;
- ouverture du détail.

Interdit :
- changement de statut ;
- création / modification de plan ;
- validation ;
- annulation ;
- toute autre mutation métier.

Cette interdiction doit être assurée côté backend, pas uniquement par suppression des boutons.

Chaque élément Cross doit afficher clairement son **établissement d’origine**.

Un filtre établissement est disponible dans les feeds Cross lorsque plusieurs établissements sont visibles.

---

## 19. Fonctionnalités futures / placeholders

En V1 :

| Fonction | Comportement |
|---|---|
| Résumé IA | placeholder |
| Export | placeholder |
| CA vs Observations | placeholder |
| Paramètres Analytics | placeholder |
| Cross Chat | placeholder |
| Cross Nouvelle observation | placeholder |
| Fan-out d’une observation vers tous les établissements | non implémenté |
| Drag & drop dashboard | hors scope |
| Sauvegarde d’un layout personnalisé | hors scope |
| Score de risque des zones | hors scope |

Un placeholder :
- ne déclenche aucun appel backend inutile ;
- n’affiche aucune fake data ;
- ne provoque pas l’implémentation anticipée de la fonctionnalité future.

---

## 20. Intégrité data — règles non négociables

1. Aucune métrique historique ne doit être reconstruite approximativement depuis l’état courant lorsqu’un historique d’événements est nécessaire.
2. Si l’historique nécessaire n’existe pas, le plan doit proposer de le créer ou de le rendre reconstructible de façon fiable.
3. Les calculs sensibles de scope, classement et agrégation Analytics doivent être réalisés côté backend.
4. Le frontend ne doit pas télécharger un périmètre excessif puis recréer les agrégats de sécurité côté client.
5. Les calculs reposent sur les événements métier réels : transitions de statuts, événements de points, création de plan, associations de motifs, etc.
6. `0`, donnée absente et donnée non comparable sont trois états différents.
7. Aucun chiffre fictif pour remplir la maquette.
8. Une modification d’architecture existante est autorisée lorsqu’elle simplifie ou fiabilise la cible.
9. Les métriques Cross ne doivent pas mélanger silencieusement des entités homonymes provenant de plusieurs établissements.
10. Les agrégations doivent être déterministes et couvertes par des tests sur les bornes temporelles, les transitions et les autorisations.

---

## 21. Contraintes de conception du Dashboard

Le dashboard doit privilégier :
- hiérarchie visuelle claire ;
- lecture rapide par direction / management ;
- densité suffisante sans surcharge ;
- distinction entre **flux**, **résultat**, **stock** et **tendance** ;
- micro-descriptions discrètes lorsque le nom de la métrique peut être mal interprété ;
- unités toujours explicites (`pts`, `%`, `j`, `h`, etc.) ;
- tailles d’échantillon visibles pour les statistiques de délai ;
- absence de couleur normative lorsqu’aucune interprétation métier fiable n’existe.

La maquette cible sert de référence visuelle, mais peut être adaptée lorsqu’une définition data validée dans ce document nécessite une présentation différente ou plus complète.

---

## 22. Ce que l’audit Cursor doit vérifier avant de proposer un plan

L’agent doit confronter cette cible au repo réel, notamment :

- modèle actuel de navigation et de sélection d’établissement ;
- RBAC frontend et backend ;
- endpoints Analytics existants et leurs scopes ;
- historique des transitions de Signals ;
- historique des transitions de Plans ;
- relation exacte Signal → premier Plan ;
- capacité à reconstruire un snapshot historique de backlog ;
- modèle de points / ledger / resets ;
- identité canonique et historique des motifs ;
- relation motif ↔ Signals distincts ;
- zones opérationnelles ;
- pôles responsables ;
- timezone organisation / établissement ;
- structures desktop actuelles des feeds Observations et Exécution ;
- contrats OpenAPI et types frontend générés ;
- tests existants et impacts de migration.

L’audit ne doit pas présupposer que l’implémentation actuelle est adaptée.

---

## 23. Attendus du plan d’implémentation

Le plan doit :
- identifier les écarts entre le repo et cette cible ;
- relever les ambiguïtés techniques restantes ;
- proposer les migrations / historisations réellement nécessaires ;
- éviter les approximations data ;
- découper l’évolution en étapes vérifiables ;
- expliciter les changements backend, frontend, routing, RBAC, OpenAPI et tests ;
- conserver l’expérience mobile hors des changements explicitement nécessaires ;
- signaler toute décision du présent document qui serait impossible ou dangereuse avec l’état réel du modèle de données avant de proposer un contournement.

Le plan ne doit pas implémenter.

---

## 24. Critères d’acceptation fonctionnels

La V1 est considérée conforme lorsque :

- le scope desktop est explicite, deep-linkable et sécurisé ;
- le switch établissement n’est plus nécessaire pour naviguer entre les scopes desktop ;
- Dashboard Cross et Dashboard établissement utilisent la même structure mais des données correctement scopées ;
- staff ne peut accéder à Analytics ;
- les presets `3 / 7 / 15 / 30 / 90 j` fonctionnent comme fenêtres glissantes ;
- toutes les comparaisons utilisent la période immédiatement précédente de même durée ;
- les motifs récurrents comptent des Signals métier distincts et non les récurrences d’un même Signal ;
- les nouveaux motifs respectent la première apparition historique du scope ;
- les contributeurs sont classés sur les points historiés de la période ;
- les délais Observations exposent médiane, moyenne, P90 et `n` ;
- le taux de résolution opérationnel, la part des clôtures résolues et les réouvertures suivent les définitions de ce document ;
- l’ancienneté des observations ouvertes reste visible même pour des Signals antérieurs à la période ;
- les délais Plans exposent moyenne et médiane ;
- le temps de validation et le respect des échéances suivent les événements métier définis ;
- les zones affichent du volume, pas un faux score de risque ;
- les vues Cross distinguent explicitement les établissements ;
- Observations et Exécution Cross sont réellement read-only ;
- tous les placeholders restent des placeholders sans backend fictif ;
- aucune donnée sensible ou agrégée n’est accessible hors RBAC ;
- aucun KPI n’est calculé à partir d’une approximation silencieuse.

---

## 25. Hors scope explicite

- génération du résumé IA ;
- export réel ;
- CA vs Observations réel ;
- Paramètres Analytics ;
- Cross Chat ;
- création Cross multi-établissements / fan-out vers les pipelines ;
- score de risque des zones ;
- taux de réouverture cohorté ;
- SLA configurables ;
- personnalisation / réorganisation du dashboard ;
- refonte fonctionnelle complète des feeds mobile ;
- nouvelle logique métier non demandée pour le détail ou la gouvernance des motifs.

