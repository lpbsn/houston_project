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
- la création d’une architecture analytique, d’un cache ou d’un système d’agrégation sans besoin démontré.

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
6. Délais et taux de résolution des plans d’action
7. Plans d’action en retard
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

Présenter la répartition des observations selon les destinations réellement disponibles :

- résolue directement, sans plan d’action ;
- transformée en plan d’action ;
- épinglée ;
- intéressante ;
- annulée ;
- toute autre destination réellement existante et pertinente dans les données.

Pour chaque destination, afficher sa part et son évolution par rapport à la période précédente. Ne créer aucune catégorie artificielle.

### 9.5. Délai avant chaque destination

Afficher le délai moyen nécessaire pour qu’une observation atteigne chaque destination :

- nom de la destination ;
- barre horizontale proportionnelle ;
- durée moyenne ;
- unité de temps cohérente avec la valeur affichée.

La comparaison entre destinations doit être lisible immédiatement.

### 9.6. Délais et taux de résolution des plans d’action

Afficher la répartition des plans d’action terminés selon les catégories suivantes :

- terminé en avance ;
- terminé à temps ;
- terminé en retard.

La carte présente une barre de répartition, la part de chaque catégorie et son évolution par rapport à la période précédente.

Les règles permettant de distinguer ces trois catégories doivent être constatées dans le fonctionnement métier existant. Toute règle absente ou ambiguë doit être signalée dans le plan.

### 9.7. Plans d’action en retard

Cette carte concerne uniquement les plans actuellement en retard. Elle les répartit selon leur taux de dépassement.

Le taux de dépassement compare le temps de retard à la durée initialement prévue du plan :

`Taux de dépassement = (temps de retard / durée prévue du plan) × 100`

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

> Le taux de dépassement compare le temps de retard à la durée initialement prévue du plan. Plus le pourcentage est élevé, plus le retard est important par rapport au délai prévu. Exemple : 2 jours de retard sur un plan de 30 jours représentent 6,7 %, tandis que 2 jours de retard sur un plan de 2 jours représentent 100 %.

### 9.8. Qualité des résolutions de plans d’action

Afficher la répartition des évaluations de résolution, de cinq étoiles à une étoile.

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

La liste est repliée à cinq lieux par défaut. Le lien « Voir tout » permet d’afficher les lieux supplémentaires lorsqu’ils existent.

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
- mécanisme de glisser-déposer ou de personnalisation des cartes.

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
- les calculs, catégories, périodes et comparaisons sont cohérents ;
- les états de chargement, d’absence de données et d’erreur sont traités ;
- l’affichage reste utilisable sur desktop et sur écran plus étroit ;
- les tests couvrent le périmètre établissement, les principaux calculs et les risques de régression ;
- le code obsolète lié à l’ancien Dashboard cross est retiré ;
- les optimisations retenues sont justifiées et n’ajoutent pas de complexité inutile.

À l’issue de la première phase, produire uniquement le plan et attendre sa validation explicite avant toute implémentation.
