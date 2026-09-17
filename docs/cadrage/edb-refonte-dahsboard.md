# Refonte du Dashboard établissement — Expression de besoin

## 1. Objet

Refondre le Dashboard Analytics de Spore afin d’en faire un tableau de bord strictement mono-établissement, fidèle aux maquettes jointes et adapté à la montée en charge.

La refonte concerne l’interface et, uniquement lorsque l’analyse du projet le justifie, les données, les traitements et les échanges nécessaires au Dashboard.

Ce chantier doit également permettre de supprimer la complexité devenue inutile, notamment tout ce qui rattache le Dashboard actuel à une vue cross-établissements.

## 2. Objectifs

- présenter les indicateurs d’un seul établissement à la fois ;
- reproduire fidèlement la structure, la hiérarchie visuelle, la densité et les graphiques des maquettes ;
- rendre les indicateurs immédiatement compréhensibles et comparables ;
- simplifier le fonctionnement existant et supprimer les éléments obsolètes ou redondants ;
- améliorer les performances et la scalabilité lorsque des limites concrètes sont constatées ;
- préserver la fiabilité des données et éviter toute valeur fictive.

## 3. Méthode de travail

La réalisation se déroule en deux phases :

1. analyse du projet et production d’un plan d’implémentation ;
2. implémentation après validation explicite du plan.

Pour la première phase :

- ne modifier aucun fichier ;
- ne produire aucun code ;
- examiner le fonctionnement réel du Dashboard dans le projet ;
- identifier les écarts entre l’existant et le besoin ;
- proposer un plan concret, vérifiable et justifié par le code observé.

Aucune décision d’architecture ne doit être inventée à l’avance. Le nombre d’API, l’organisation des composants, le mode de calcul, le cache ou toute autre solution technique doivent découler de l’analyse du projet et être justifiés dans le plan.

## 4. Sources de vérité

Les sources doivent être utilisées dans l’ordre suivant :

1. les règles fonctionnelles et contraintes du présent document ;
2. les maquettes jointes pour le rendu visuel ;
3. le projet existant pour constater les données, comportements et contraintes réels.

Les valeurs visibles dans les maquettes sont illustratives et ne doivent jamais être utilisées comme données réelles.

En cas d’ambiguïté ou de donnée manquante, le plan doit exposer le point à valider sans formuler d’hypothèse. Les règles écrites dans ce document priment sur les éléments contradictoires des maquettes, notamment concernant l’absence de glisser-déposer.

## 5. Périmètre

### Inclus

- le Dashboard d’un établissement ;
- son intégration dans le contexte de navigation d’un établissement ;
- les indicateurs, filtres, états et interactions décrits ci-dessous ;
- le nettoyage des références à l’ancien Dashboard cross-établissements ;
- les adaptations de données ou de traitements nécessaires aux indicateurs ;
- les tests concernés par la refonte ;
- l’analyse et l’optimisation des traitements réellement coûteux ou inutilement complexes.

### Hors périmètre

- la conception du futur Dashboard cross-établissements ;
- la refonte générale de la navigation ou de la sidebar ;
- la modification des autres pages de Spore, hors ajustements indispensables à l’accès au Dashboard ;
- l’ajout d’indicateurs ou de fonctionnalités absents de ce document et des maquettes ;
- la création d’une architecture analytique, d’un cache ou d’un système d’agrégation sans besoin démontré ;
- la suppression de l’archivage des observations, traitée dans un chantier distinct.

Le Dashboard ne doit ni afficher une destination « Archivée », ni calculer un délai associé, ni prévoir de compatibilité ou de comportement hérités pour l’archivage.

## 6. Périmètre établissement et navigation

Le Dashboard doit toujours représenter un établissement précis. Il ne doit plus proposer ni afficher de vue agrégée sur plusieurs établissements.

Le nom de l’établissement actif doit être visible dans l’en-tête. Toutes les données, comparaisons, périodes et exports éventuels doivent respecter ce périmètre.

Le Dashboard actuel doit être retiré de l’espace cross-établissements. Les éléments devenus inutiles pour gérer une vue cross doivent être identifiés puis supprimés proprement, sans conserver de double logique inutile.

Dans la navigation cross-établissements, une entrée distincte « Dashboard Cross » doit rester visible sous forme de placeholder. Elle ne doit ni afficher ni réutiliser le Dashboard établissement. Son contenu fonctionnel sera cadré ultérieurement.

## 7. Structure générale du Dashboard

Les cartes sont affichées dans une seule colonne et dans l’ordre fixe suivant :

1. Sujets récurrents
2. Nouveaux sujets
3. Nombre d’observations
4. Destination des observations
5. Délai avant chaque destination
6. Respect des échéances des plans d’action
7. Plans d’action actuellement en retard
8. Qualité des résolutions de plans d’action
9. Classement des contributeurs
10. Lieux les plus cités

Il ne doit exister aucun glisser-déposer, aucune poignée de déplacement, aucun réglage d’ordre et aucune mémorisation personnalisée de l’ordre des cartes.

## 8. En-tête et filtres

L’en-tête comprend :

- le titre « Dashboard » ;
- le nom de l’établissement actif ;
- la période sélectionnée ;
- un sélecteur de période : `3 j`, `7 j`, `15 j`, `30 j`, `90 j` ;
- un bouton « Exporter » ;
- les filtres « Pôle d’activité », « Sujet » et « Responsable ».

Les filtres « Pôle d’activité », « Sujet » et « Responsable » ne sont pas encore cadrés fonctionnellement. Ils doivent apparaître comme placeholders et ne doivent pas simuler un filtrage inexistant.

Le comportement du bouton « Exporter » doit être constaté dans le projet :

- s’il existe et fonctionne, il est conservé en respectant le périmètre mono-établissement ;
- s’il n’existe pas ou n’est pas opérationnel, le bouton reste un placeholder en attendant son cadrage.

## 9. Contenu des cartes

Pour les cartes « Sujets récurrents », « Nouveaux sujets » et « Lieux les plus cités » :

- afficher les cinq premiers éléments par défaut ;
- afficher « Voir tout » lorsqu’il existe plus de cinq éléments ;
- permettre l’accès à tous les résultats ;
- ne pas appliquer de limite métier arbitraire aux données disponibles.

La manière de charger les résultats supplémentaires n’est pas imposée.

### 9.1. Sujets récurrents

Afficher, pour chaque sujet :

- son nom ;
- sa dernière détection ou la période correspondante ;
- le nombre d’occurrences ;
- son évolution par rapport à la période précédente.

La zone « Impact futur potentiel · IA » doit être présente mais afficher uniquement « Bientôt disponible ». Aucun contenu d’analyse ne doit être généré dans ce chantier.

### 9.2. Nouveaux sujets

Afficher, pour chaque sujet :

- son nom ;
- sa date ou son ancienneté de première détection.

La zone « Impact futur potentiel · IA » suit la même règle que celle des sujets récurrents : placeholder « Bientôt disponible » uniquement.

### 9.3. Nombre d’observations

La carte comprend un sélecteur local à deux états :

- « Pôle concerné », actif par défaut ;
- « Pôle responsable ».

Ce sélecteur agit uniquement sur cette carte.

Le graphique présente cinq périodes :

- il y a 4 périodes ;
- il y a 3 périodes ;
- il y a 2 périodes ;
- période précédente ;
- période en cours.

Pour chaque période :

- la hauteur de la barre représente le nombre total d’observations ;
- la barre est segmentée par pôle d’activité ;
- chaque segment affiche le nombre d’observations et sa part en pourcentage ;
- une couleur stable permet d’identifier chaque pôle ;
- le total et le libellé de la période sont visibles ;
- la période en cours est visuellement distinguée.

Une légende associe chaque couleur à son pôle. Sous le graphique, afficher uniquement le total de la période en cours et son évolution par rapport à la période précédente.

### 9.4. Destination des observations

Présenter la répartition exclusive des observations selon les sept catégories suivantes :

1. En attente
2. Intéressante
3. Plan d’action en cours
4. Résolue directement
5. Résolue via un plan d’action
6. Résolue après demande de résolution
7. Annulée

Règles :

- chaque observation n’apparaît que dans une seule catégorie ;
- la répartition totalise 100 % ;
- la catégorie correspond à la situation de l’observation à la fin de la période analysée ;
- les catégories sont calculées à partir de la situation réellement applicable à cette période, sans réinterpréter une période ancienne avec l’état actuel de l’observation ;
- « En attente » correspond aux observations encore ouvertes et entre dans le dénominateur ;
- « Résolue directement » correspond à une résolution déclenchée directement par un utilisateur depuis le bouton « Résolue » ;
- une observation peut être « Résolue directement » même si un ou plusieurs plans lui ont été associés auparavant puis annulés ;
- « Résolue via un plan d’action » correspond uniquement aux observations dont la résolution a été déclenchée par l’aboutissement d’un plan d’action ;
- « Résolue après demande de résolution » reste distincte des deux catégories précédentes ;
- « Plan d’action en cours » correspond à une observation actuellement prise en charge par un plan, mais pas encore résolue.

Cette carte n’inclut ni « Épinglée » ni « Archivée ».

Pour chaque destination, afficher sa part et son évolution par rapport à la période précédente.

### 9.5. Délai avant chaque destination

Afficher le délai moyen entre la création de l’observation et l’atteinte de sa destination.

Afficher uniquement :

- Intéressante ;
- Plan d’action en cours ;
- Résolue directement ;
- Résolue via un plan d’action ;
- Résolue après demande de résolution ;
- Annulée.

Ne pas afficher :

- En attente, car il s’agit de l’état initial de l’observation ;
- Archivée ;
- Épinglée.

Pour chaque destination affichée :

- nom de la destination ;
- barre horizontale proportionnelle ;
- durée moyenne ;
- unité de temps cohérente avec la valeur affichée.

La comparaison entre destinations doit être lisible immédiatement.

Lorsqu’une date d’atteinte ne peut pas être déterminée de manière fiable, ne pas inventer de délai.

### 9.6. Respect des échéances des plans d’action

Cette carte mesure la capacité des équipes à terminer leur travail dans le délai planifié. Elle ne mesure pas le délai de validation du manager.

Afficher la répartition des plans concernés selon les catégories suivantes :

- terminé en avance ;
- terminé à temps ;
- terminé en retard.

La carte présente une barre de répartition, la part de chaque catégorie et son évolution par rapport à la période précédente.

La fin du travail de l’équipe correspond :

- à l’envoi du plan en validation lorsque celle-ci est requise ;
- à la fin directe du plan lorsqu’aucune validation n’est requise ;
- à la dernière nouvelle soumission lorsqu’un plan a été rejeté puis retravaillé.

Le temps passé à attendre une validation du manager ne doit jamais influencer le classement.

Les calculs utilisent le jour et l’heure complets, sans arrondi au jour.

```text
Durée planifiée = échéance − début planifié
Fenêtre « À temps » = 10 % de la durée planifiée
Seuil « À temps » = échéance − fenêtre « À temps »
```

Classement :

- **Terminé en avance** : fin du travail avant le seuil « À temps » ;
- **Terminé à temps** : fin du travail comprise entre le seuil « À temps » et l’échéance, incluses ;
- **Terminé en retard** : fin du travail postérieure à l’échéance.

Tout dépassement de l’échéance, même d’une minute, doit être considéré comme un retard.

Les plans dont les dates nécessaires sont absentes, incohérentes ou non fiables ne doivent pas être classés artificiellement.

### 9.7. Plans d’action actuellement en retard

Cette carte concerne uniquement les plans dont le travail de l’équipe n’est pas terminé et dont l’échéance est dépassée. Elle les répartit selon leur taux de dépassement.

Inclure :

- les plans planifiés mais non commencés dont l’échéance est dépassée ;
- les plans en cours dont l’échéance est dépassée.

Exclure :

- les plans en attente de validation ;
- les plans terminés ;
- les plans annulés ;
- tout plan pour lequel l’équipe a déjà terminé son travail.

Le taux de dépassement est :

```text
Durée planifiée = échéance actuelle − début planifié actuel
Temps de retard = heure actuelle − échéance actuelle
Taux de dépassement = temps de retard / durée planifiée × 100
```

Employer partout le terme « durée planifiée ».

Exemples :

- 2 jours de retard sur un plan prévu sur 30 jours : `6,7 %` ;
- 2 heures de retard sur un plan prévu sur 8 heures : `25 %` ;
- 4 heures de retard sur un plan prévu sur 3 heures : `133 %`.

Le calcul doit conserver une précision suffisante pour traiter correctement les plans courts et ne doit pas arrondir prématurément les durées.

Les tranches sont :

- moins de `10 %` ;
- de `10 %` à moins de `25 %` ;
- de `25 %` à moins de `50 %` ;
- de `50 %` à moins de `100 %` ;
- `100 %` ou plus.

Chaque tranche affiche :

- le nombre de plans concernés ;
- leur part parmi l’ensemble des plans en retard.

Un pictogramme d’information placé près du titre affiche le tooltip suivant :

> Le taux de dépassement compare le temps de retard à la durée planifiée du plan. Plus le pourcentage est élevé, plus le retard est important par rapport au délai prévu. Exemple : 2 jours de retard sur un plan de 30 jours représentent 6,7 %, tandis que 2 jours de retard sur un plan de 2 jours représentent 100 %.

### 9.8. Qualité des résolutions de plans d’action

Afficher la répartition des évaluations de résolution selon six niveaux :

- 5 étoiles ;
- 4 étoiles ;
- 3 étoiles ;
- 2 étoiles ;
- 1 étoile ;
- 0 étoile.

La période correspond à la date de l’évaluation. Les évaluations à 0 étoile entrent dans le dénominateur comme les autres.

Chaque niveau affiche :

- les étoiles correspondantes ;
- une barre proportionnelle ;
- le pourcentage associé.

### 9.9. Classement des contributeurs

Afficher uniquement :

- le rang ;
- l’avatar ou, à défaut, les initiales ;
- le nom du contributeur ;
- son ou ses pôles ;
- son score suivi de « pts ».

### 9.10. Lieux les plus cités

Afficher les lieux par nombre décroissant de mentions dans les observations.

Chaque ligne comprend :

- le nom du lieu ;
- le nombre d’observations ;
- une barre représentant sa proportion par rapport au lieu le plus cité.

## 10. Exigences visuelles et responsive

- reproduire fidèlement les maquettes dans leur structure, leurs espacements, leur hiérarchie et leur densité ;
- conserver une interface sobre, lisible et principalement neutre, avec le vert comme accent et le rouge réservé aux alertes, erreurs et retards ;
- éviter les effets décoratifs absents des maquettes ;
- conserver la cohérence avec les composants et règles visuelles déjà utilisés dans Spore lorsqu’ils permettent d’atteindre le rendu cible ;
- utiliser les maquettes comme référence desktop et prévoir un comportement lisible sur les écrans plus étroits ;
- ne pas refondre les éléments globaux de l’application au-delà des changements de navigation explicitement demandés.

Les poignées de déplacement et le texte relatif au glisser-déposer visibles dans certaines maquettes ne doivent pas être reproduits.

## 11. Contraintes transversales

- toutes les données du Dashboard doivent être limitées à l’établissement actif ;
- aucune donnée métier ne doit être codée en dur à partir des exemples des maquettes ;
- aucune donnée fictive ne doit être ajoutée ;
- les états de chargement, d’absence de données et d’erreur doivent être prévus ;
- le changement de période doit produire des comparaisons cohérentes pour l’ensemble des cartes concernées ;
- les indicateurs d’une période fermée doivent rester fidèles à la situation applicable à cette période, sans substitution par l’état actuel ;
- l’ordre des cartes est défini par le produit et reste fixe ;
- le futur Dashboard Cross doit rester indépendant du Dashboard établissement ;
- le nettoyage doit supprimer le code devenu inutile, sans créer d’abstraction de remplacement non justifiée ;
- les optimisations doivent répondre à des problèmes constatés : requêtes répétées, chargements trop larges, calculs redondants, volumes inutiles ou autres coûts mesurables ;
- la solution doit rester simple à maintenir et adaptée à l’augmentation du nombre d’observations, de plans d’action et de contributeurs ;
- toute évolution des données ou des traitements doit préserver les autres usages existants identifiés lors de l’analyse.

## 12. Éléments à ne pas ajouter

- résumé IA général en haut du Dashboard ;
- carte « Analyse IA CA vs Observations » ;
- chiffre d’affaires sans donnée réelle ;
- avis Google ou fonctionnalité associée ;
- nouveau filtre non cadré ;
- nouvelle navigation en dehors de l’entrée « Dashboard Cross » demandée ;
- nouvelle logique métier sans validation ;
- mécanisme de glisser-déposer ou de personnalisation des cartes ;
- destination « Épinglée » ;
- destination « Archivée », délai associé, ou comportement hérités d’archivage.

## 13. Attendus du plan d’implémentation

Le plan doit présenter :

1. l’état actuel constaté du Dashboard, de son périmètre et de ses données ;
2. les écarts précis avec ce besoin et les maquettes ;
3. les éléments liés au fonctionnement cross-établissements à retirer ;
4. les fichiers réellement concernés et la raison de leur modification ;
5. la correspondance entre chaque indicateur demandé et les données réellement disponibles ;
6. les données manquantes ou règles métier à valider ;
7. les étapes ordonnées d’implémentation, avec un résultat vérifiable pour chacune ;
8. les simplifications et optimisations proposées, accompagnées de leur justification concrète ;
9. les tests à créer, adapter ou supprimer ;
10. les risques de régression et les moyens de les limiter.

Le plan ne doit pas présenter comme acquise une solution technique qui n’a pas été confirmée par l’analyse du projet.

## 14. Critères d’acceptation

La refonte sera considérée conforme lorsque :

- le Dashboard affiche exclusivement les données de l’établissement actif ;
- aucune vue agrégée cross-établissements ne subsiste dans ce Dashboard ;
- l’entrée « Dashboard Cross » existe comme placeholder indépendant ;
- la structure et le rendu correspondent aux maquettes, sous réserve des règles écrites dans ce document ;
- toutes les cartes sont présentes dans l’ordre défini ;
- aucun mécanisme de glisser-déposer ou de personnalisation de l’ordre n’est présent ;
- les filtres non cadrés et les analyses IA sont clairement présentés comme indisponibles ;
- les graphiques utilisent les données réelles et respectent les proportions affichées ;
- la carte « Destination des observations » présente exactement les sept catégories exclusives, totalise 100 %, et inclut les observations en attente dans le dénominateur ;
- les catégories « Épinglée » et « Archivée » sont absentes du Dashboard, y compris des délais ;
- les trois mécanismes de résolution restent distincts : résolue directement, résolue via un plan d’action, résolue après demande de résolution ;
- les catégories et origines de résolution d’une période correspondent à la situation applicable à cette période, sans réinterprétation par l’état actuel ;
- la carte des délais n’affiche pas En attente ;
- les échéances des plans d’action sont calculées avec le jour et l’heure complets, sans arrondi au jour ;
- la fenêtre « À temps » correspond à 10 % de la durée planifiée ;
- le temps d’attente de validation du manager n’influence pas le classement des échéances ;
- la carte des retards actuels exclut les plans en attente de validation et tout plan dont le travail d’équipe est déjà terminé ;
- la qualité des résolutions affiche les évaluations de 0 à 5 étoiles, 0 étoile compris dans le dénominateur ;
- les cartes Sujets récurrents, Nouveaux sujets et Lieux les plus cités affichent cinq éléments par défaut, proposent « Voir tout » au-delà, et donnent accès à tous les résultats, sans limite métier fixée à cinq ;
- les états de chargement, d’absence de données et d’erreur sont traités ;
- l’affichage reste utilisable sur desktop et sur écran plus étroit ;
- les tests couvrent le périmètre établissement, les principaux calculs et les risques de régression ;
- le code obsolète lié à l’ancien Dashboard cross est retiré ;
- les optimisations retenues sont justifiées et n’ajoutent pas de complexité inutile.

À l’issue de la première phase, produire uniquement le plan et attendre sa validation explicite avant toute implémentation.
