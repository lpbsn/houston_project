# Ma journée et retour aux auteurs d'observations

Proposition pour Léo, basée sur main `7dc06f04c924d5a5db33739ce686d85698358f63`.
Périmètre : améliorer la boucle quotidienne sans ajouter un outil de projet parallèle.

## Pourquoi

La captation dépend de l'utilité pour les équipes. Spore doit rester un outil terrain
simple : utile aux établissements sans outil dédié et à ceux dont les conversations
ou les outils de projet deviennent trop difficiles à suivre. Ce positionnement est
une hypothèse à valider chez les clients, pas une supériorité démontrée sur Asana.

Deux raisons de revenir : retrouver son travail ; voir la suite de ses observations.

## Comportement livré

- « Ma journée » : barre latérale web, raccourci dans Exécution et dans Général
  (application native comprise). Routes /my-day et /e/:id/my-day.
- Tâches en attente des plans en cours et déjà visibles, triées en retard,
  aujourd'hui, à venir, sans échéance.
- Attribution nominative prioritaire. Les tâches sans personne sont affichées
  comme partagées uniquement dans le pôle concerné, pour un plan auquel on est
  assigné ou un pôle contributeur. Voir tous les plans en tant que directeur
  ne transforme pas toutes leurs tâches en travail personnel.
- Échéance de tâche, sinon échéance du plan ; fuseau de l'établissement.
  Une échéance de plan « journée entière » ne devient pas en retard à minuit
  au début de la journée.
- Ouvrir le plan / Discuter ouvrent les écrans existants. Pas de nouveau statut,
  de nouvelle discussion, ni de logique de validation côté client.
- « Tous mes plans » garde l'accès aux plans sans tâches, en validation, etc.
- Dernières notifications réelles, marquage lu et liens existants. Ce panneau
  contient toutes les notifications personnelles, pas seulement les observations.
- Les auteurs de toutes les observations sources (créées, agrégées, fusionnées)
  rejoignent les destinataires du cycle signal : épinglage, résolution, annulation.
- À la disponibilité d'un plan créé depuis un signal, notification informative
  aux auteurs non déjà destinataires de l'assignation. Elle ouvre le signal :
  elle n'accorde aucun nouveau droit sur le plan.
- Le service existant conserve les contrôles de visibilité, déduplication,
  exclusion de l'acteur et livraison après commit. Le push reste conditionné
  à la configuration et aux préférences existantes.
- Aucun envoi rétroactif sur les événements antérieurs à l'installation.

## Limites explicites

Il ne s'agit pas de promettre une notification pour toute transformation technique
du pipeline : une observation sans signal exploitable, une fusion sans événement
de cycle ultérieur ou un objet auquel l'auteur n'a plus accès ne sont pas couverts
par une nouvelle notification dans ce périmètre. Aucun droit n'est élargi pour
forcer une notification. Les données supprimées/inaccessibles restent protégées.

Les plans planifiés n'entrent dans Ma journée qu'à leur démarrage opérationnel.
Les tâches partagées restent partagées, pas automatiquement assignées.
Les sections sont paginées (30 tâches) ; aucun total partiel n'est présenté comme
un total global. La pagination offset peut évoluer pendant des modifications
simultanées ; l'actualisation remet la liste à jour.

Pas de consignes, blocages ou passation de service ajoutés ici : ces éléments de
la maquette n'ont pas été retenus pour cette PR.

## Architecture / installation

- Selecteur propriétaire : action_plans/day_selectors.py.
- GET /api/v1/establishments/:id/my-day/ : lecture bornée, autorisation
  via le mécanisme d'établissement existant. Pas de requête par plan côté client.
- Contrat OpenAPI et types TypeScript générés avec les commandes habituelles.
- TanStack Query, invalidation opérationnelle existante + rafraîchissement
  toutes les 60 secondes pour les échéances, reprise réseau et retour sur la page.
- Notifications : extension des destinataires et événement existant
  action_plan.execution.created_from_signal, avec sujet signal pour le reporter.
- Aucune migration, variable d'environnement ou dépendance supplémentaire.
- Déployer l'API avant le frontend ; conserver workers et push habituels.
  Pas de changement nécessaire au mode de déploiement de Léo.

## Recette

1. Créer un plan avec tâches personnelles et partagées ; vérifier les deux profils.
2. Tester une tâche pour quelqu'un d'autre : elle ne devient pas « ma tâche ».
3. Vérifier échéances datées, journée entière, sans date et fuseau de l'établissement.
4. Ouvrir une tâche puis sa discussion ; terminer depuis le plan et revenir.
5. Avec un second utilisateur hors du pôle, envoyer une observation. Créer le plan,
   résoudre le signal : vérifier notification, lien et absence de double envoi.
6. Ajouter plusieurs observations du même auteur et d'un autre auteur au signal.
7. Vérifier utilisateur désactivé, autre établissement, objet inaccessible et
   préférences push désactivées.
8. Vérifier téléphone et ordinateur, erreurs réseau et pagination.

## Validation

- Contrôle Django, Ruff, génération des contrats, TypeScript et build web vérifiés.
- Tests ciblés frontend : 114 réussis au premier contrôle final.
- Tests serveur ajoutés pour les droits, destinataires, déduplication, échéances,
  pagination et isolation. L'environnement de cet auteur n'a pas Docker/.env local :
  leur exécution est à vérifier dans la CI avant fusion.
- La PR reste draft : revue et validation finale par Léo, aucun déploiement live.
