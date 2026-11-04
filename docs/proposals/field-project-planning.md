# Fiches terrain : projets, planification et documents

Proposition complémentaire à #377, pour revue de Léo. Base :
`codex/unified-field-record`, commit `24b8d8ca0948bab38d94d0e690870b1964dfb32d`.
Aucune fusion ou mise en production automatique.

## Pourquoi

La fiche commune simplifie la remontée et le traitement d'un sujet. Les travaux plus longs
(ouverture d'un site, implantation saisonnière, rénovation) nécessitent aussi un regroupement,
des étapes datées et des documents faciles à retrouver. Ces usages deviennent optionnels :
une observation reste une fiche simple, sans création obligatoire de projet ni tâche.

## Parcours proposé

1. Créer une fiche simple, un projet ou un jalon depuis le même formulaire. Un projet est créé
   explicitement ; on peut lui rattacher des fiches issues d'observations sans transformer leurs
   témoignages en projets artificiels.
2. Ouvrir un projet : retrouver ses fiches, sous-projets et jalons, leurs responsables et étapes.
   Trois niveaux maximum (projet → sous-projet → fiche) et 200 enfants directs par projet.
   Le compteur indique les **fiches accessibles closes**, jamais une mesure d'impact métier.
3. Planifier : saisir un début prévu et une échéance, ou déplacer/étirer une barre dans le Gantt
   ordinateur. Le bouton « Planifier » propose le même parcours au clavier et sur mobile.
4. Définir éventuellement un préalable (une autre fiche du même établissement).
   La relation est fin → début au plus tôt le lendemain, en jours calendaires sans heures.
   Un préalable de planification n'est pas une autorisation automatique d'exécution.
5. Toute modification passe par un aperçu : fiches concernées, anciennes et nouvelles dates.
   Si la fin du préalable dépasse le début suivant, ce dernier est repoussé en gardant sa durée.
   Une avance ne tire pas automatiquement les successeurs vers l'avant. Confirmation explicite.
6. Retrouver les photos et PDF des plans dans **Documents**, rechercher un nom, ouvrir l'aperçu
   ou revenir au message d'origine. Pour partager un fichier, utiliser la discussion du plan dans
   **Travail**. Dans un projet, l'index comprend aussi ses descendants accessibles (2 niveaux).
   Les photos de l'observation restent accessibles dans la fiche.

## UI/UX

- Header compact : titre, pôle, responsable, échéance, état ; début prévu si renseigné.
- Actions principales : Ajouter du travail/une fiche, Planifier, Suivre.
- Réglages secondaires dans « Plus d'options » : participants, responsable/blocage, rattachement,
  préalable, pôle/sujet, alertes. La création courante reste courte.
- Onglets séparés : fiches du projet, travail, documents, observations, discussion, historique,
  impact KPI (selon droits). Boutons sélectionnés et texte foncé sur fond clair.
- Gantt : en-tête et intitulés fixes, calendrier continu, jalons, liens des préalables visibles,
  défilement interne et action au clavier. La vue mobile garde la liste et les fiches.
- Le calendrier conserve le contrat #377 (création → fin effective). Le Gantt utilise le début
  planifié s'il existe, en conservant l'historique de création. Les filtres et la pagination restent
  partagés. Une vue partielle l'indique explicitement.

## Architecture et limites volontaires

`Signal` reste la fiche unique. Migration additive `signals.0024` : `is_project`, `is_milestone`,
`parent_project`, `planned_start_on`, `planning_predecessor`. Les anciennes fiches ne sont pas
reclassées automatiquement. Les anciennes dates, observations, plans et liens sont conservés.

Écritures dans `project_services.py` / `planning_services.py`, lectures dans
`record_selectors.py` / `record_documents.py`. API typée et contrats OpenAPI régénérés.
Les nouveaux endpoints sont sous `/api/v1/establishments/{id}/records/{record_id}/` :
`organization/`, `predecessor/`, `planning/`, `documents/`.

- Permissions serveur : établissement, périmètre de fiche et droits de modification ; aucun droit
  accordé par simple appartenance à un projet. Un titre de parent/préalable inaccessible est masqué.
- Aperçu et confirmation recalculent les impacts ; les versions de toutes les fiches liées sont
  vérifiées. Transactions, verrou de l'établissement pour les mutations du graphe, puis verrou des
  fiches. Aucun changement partiel en cas de conflit. Chaîne limitée à 200 fiches.
- Les cycles, quatre niveaux, dates inversées, modification d'un successeur clos ou inaccessible
  sont refusés. Une édition ordinaire de date ne contourne pas la vérification des dépendances.
- Clore un projet exige d'abord de clore ses enfants. Cela ne valide pas les KPI. La clôture des
  enfants ne clôture pas automatiquement le projet.
- Les dates de tâches et plans conservent leurs règles existantes. Déplacer une fiche ne réécrit pas
  leurs dates. Déplacer un projet ne déplace pas implicitement tous ses enfants : la propagation
  suit uniquement les liens de préalable prévisualisés.
- Un regroupement automatique de signaux ne fusionne pas silencieusement un graphe planifié : les
  fiches avec projet/dépendance/planification sont protégées du merge de contenu.
- Documents = index des pièces existantes, sans copie, stockage parallèle ni prolongation de
  rétention. Accès au plan et téléchargement restent contrôlés par les services existants.
  Photos et PDF seulement : cette PR n'ajoute ni versions de documents ni annotation/approbation.
- Brain reçoit les nouveaux identifiants et dates dans son contexte figé. Le lien projet est une
  information d'organisation, pas une preuve de résultat ou de causalité.

## Installation sans Docker

Cette PR cible la branche #377 pour isoler son diff. Revoir puis intégrer #377, rebaser/recibler
celle-ci sur `staging` et revérifier la CI. Ne pas cherry-pick uniquement l'interface : le backend,
la migration et les types sont un contrat commun.

Avec la base de validation habituelle de Léo et les variables déjà utilisées par le projet :

```sh
uv sync --frozen
uv run python apps/api/manage.py migrate
uv run python apps/api/manage.py check
```

Dans `apps/web` :

```sh
npm ci
npm run api:generate
npm run typecheck
npm run build:bundle
```

Redémarrer API et workers via le gestionnaire habituel, publier le bundle web. Pour une livraison
native, utiliser le pipeline natif existant et ses véritables origines. Pas de dépendance ajoutée,
pas de clé, de nouveau stockage ni de configuration fournisseur.

Avant intégration : sauvegarde et migration sur une copie des données, recette ci-dessous.
Un retour au code précédent peut conserver les colonnes additives et les données saisies ; ne pas
supprimer cette migration après usage sans décider du traitement des nouvelles relations.

## Recette

- Observation ordinaire : envoyer, suivre, ajouter travail/discussion, clore sans projet.
- Projet avec sous-projet, fiche et jalon : navigation, compteurs, refus de niveau/cycle invalide.
- Gantt mois et trimestre, barre traversant un mois, fiche en retard et fiche close ; glisser,
  redimensionner puis annuler ; recommencer au clavier et confirmer.
- Chaîne de 3 fiches : aperçu, confirmation, dates créées conservées, tâches inchangées.
- Modifier le successeur entre aperçu et confirmation : conflit, aucune date modifiée.
- Rôles directeur, manager d'un pôle et staff : pas de fuite de titres, compteurs ou documents.
- Photos/PDF de plusieurs plans dont un restreint et un expiré : source correcte, filtrage et
  téléchargement, recherche, pagination, pièces d'un sous-projet.
- Clôture d'un projet avec enfant ouvert refusée ; clore ensuite sans déclarer un KPI atteint.
- Brain : conserver historique/relations/dates, sans gonfler le nombre d'observations.

Tests serveur ajoutés dans `test_project_planning.py` ; tests UI dans `planning-dialog.test.tsx`.
La CI du dépôt est le contrôle serveur reproductible (PostgreSQL/Redis/RabbitMQ). Dans l'environnement
Codex utilisé, Docker n'est pas disponible ; aucun pytest serveur n'est lancé hors de la procédure
requise par AGENTS. Contrôles locaux : lint, check Django, cohérence migrations/schéma, tests UI,
typecheck et builds. Résultat final de CI indiqué dans la description de PR.
