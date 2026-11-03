# Fiche terrain commune — proposition pour Léo

Base étudiée : `staging`, commit `d84533bad2ec878a3c00685bc1ed83a3f049df2d`.
Cette proposition doit rester en Draft jusqu’à validation de la CI et de la recette sur une copie de données. Ne pas déployer automatiquement.

## Pourquoi

Un équipier partage une observation. Le manager travaille ensuite dans la même fiche : responsable, échéance, blocage, participants, tâches, discussion et plans distincts si nécessaire. Il n'a pas à apprendre un parcours de conversion vers un autre objet.

L’interface commune ne fusionne pas les preuves avec les décisions : `Observation` garde le témoignage, `Signal` porte la fiche, `ActionPlanExecution` conserve le travail réel et ses droits. Les projets créés directement ne génèrent pas de faux témoignages.

## Parcours

- Équipier : envoyer une observation, retrouver sa fiche, voir ses tâches dans Ma journée, échanger dans la discussion autorisée, recevoir les nouvelles du traitement.
- Manager : liste ou Kanban À traiter / En cours / À vérifier / Clos. Le blocage est un attribut séparé, avec une raison et éventuellement une personne attendue.
- Responsable possible sans tâche. Clôture directe avec motif : résolu, pris en compte, abandonné.
- Travail : tâches rapides ou plans nommés, chacun conservant ses participants, validation et discussion avec pièces jointes. Les options avancées et récurrences existantes restent accessibles.
- Une action peut être rattachée à plusieurs fiches. L’action demeure unique et garde ses permissions.
- Terminer le travail conduit à « À vérifier » : la résolution du problème exige une décision distincte. L’atteinte d’un objectif KPI reste une troisième vérification, dans Brain.
- Calendrier : fiches avec échéance uniquement, bande de la création à l’échéance, prolongée jusqu’à aujourd’hui si en retard ; arrêt à la clôture effective ; échéance originale conservée.
- Ma journée complète les tâches existantes par les fiches dont on est responsable sans tâche personnelle en cours et les résultats à vérifier dans son périmètre.

## Architecture

`Signal` reçoit des attributs de pilotage et un type (`observation`, `project`, `intake`). La saisie crée un point d’entrée avant classification ; l’IA enrichit les preuves, sans clôturer la fiche ni écraser une décision humaine.

`SignalExecutionLink` porte la relation plusieurs-à-plusieurs. `source_signal` reste la provenance initiale pour les consommateurs existants. `SignalParticipant` gère le suivi, sans accorder de nouveaux droits. `SignalRecordEvent` conserve les décisions ; `SignalAlias` préserve les anciens liens lors d’un rapprochement. Les fusions conservent la source historique.

Les nouveaux endpoints `records/` sont dans le domaine signals : sélecteurs pour lire, services pour écrire, permissions côté serveur, pagination bornée. Les commandes exigent `expected_updated_at` pour ne pas écraser une modification simultanée.

Les tâches ont un préalable facultatif, dans le même groupe de travail : pas de cycle, pas de validation avant le préalable. Cette première version ne crée pas un moteur de dépendances entre établissements, ni une vue de charge.

Brain reçoit les décisions, dates, blocages, liens d’exécution et objectifs rattachés dans son dossier figé. Les projets ne doivent pas devenir des observations dans les métriques. Les anciennes analyses ne sont pas recalculées. La PR #361 est indépendante et n’est pas présumée intégrée.

Les notifications utilisent l’infrastructure existante : événements durables, livraison après commit, clés d’idempotence. Rappels J-1 et premier jour de retard selon le fuseau du site ; pas de rappel quotidien répété. Le worker opérationnel et Celery Beat doivent tourner.

## Installation sans Docker

1. Récupérer la branche de cette PR et vérifier les conflits avec le dernier `staging`. Ne pas cherry-pick uniquement le frontend : le contrat, les migrations et les services forment un ensemble.
2. Faire une sauvegarde de PostgreSQL et des médias. Recetter sur une copie isolée avant production.
3. Installer les dépendances habituelles : `uv sync`, puis `npm ci` dans `apps/web`.
4. Suspendre temporairement les écritures et workers pendant les migrations de reprise, pour éviter de créer une exécution entre sa lecture et son rattachement.
5. Dans `apps/api` : `uv run python manage.py check`, `uv run python manage.py makemigrations --check --dry-run`, puis `uv run python manage.py migrate`.
6. Dans `apps/web` : `npm run api:generate`, `npm run typecheck`, `npm run lint`, `npm test`, `npm run build` ; construire séparément le bundle natif avec la configuration habituelle.
7. Redémarrer API, workers opérationnels / IA et Beat avec la même révision. Vérifier les files et notifications.
8. Faire la recette ci-dessous avant ouverture. Déployer une version native compatible ; les anciens endpoints restent présents, leur comportement de résolution doit être pris en compte dans la recette.

Les tests serveur locaux suivent la procédure du dépôt (`make backend-test`). En environnement CI, le workflow existant fournit PostgreSQL, Redis et RabbitMQ. Aucun secret supplémentaire ni nouvelle dépendance applicative n’est ajouté.

## Migrations et retour arrière

Les migrations ajoutent les champs et relations, puis rattachent les exécutions existantes. Une exécution sans observation reçoit une fiche projet. Une ancienne exécution terminée est reprise comme travail pris en compte, pas comme preuve automatique qu’un problème terrain est résolu. Les échéances existantes sont conservées.

Ne pas supprimer les nouvelles tables après usage : elles portent des décisions et relations nouvelles. En cas d’incident, suspendre le parcours, conserver la base et les médias, corriger en avant. Une restauration de sauvegarde implique de traiter explicitement les écritures intervenues depuis la sauvegarde.

## Recette indispensable

- Témoignage texte/photo/vocal ; regroupement de plusieurs auteurs sans perdre leur date ni leur contenu ; original réservé aux droits existants.
- Responsable sans tâche ; équipier ne pouvant ni réassigner ni clôturer ; aucun accès à un autre établissement.
- Ajout de tâches, modification et réordonnancement sans perdre les dépendances ; refus des cycles ; discussion générale et discussion de plan distinctes.
- Plan partagé entre deux fiches ; validation du travail sans résolution automatique ; clôture et réouverture explicites ; réapparition d’un sujet sans effacer l’épisode précédent.
- Calendrier à cheval sur deux semaines, retard, clôture avant/après échéance, fiche sans date.
- Anciennes notifications et liens après rapprochement ; médias conservés selon les règles de rétention existantes.
- Brain : capture datée, action partagée identifiée par le même ID, projet sans témoignage artificiel, objectifs indépendants de la clôture.
- Rappels dans le fuseau du site, absence de doublons, notifications coupées, modification d’échéance et membre désactivé.

Les résultats exacts de validation et les éventuels points restant à corriger sont indiqués dans la PR ; ce document n’est pas une attestation de réussite des tests.
