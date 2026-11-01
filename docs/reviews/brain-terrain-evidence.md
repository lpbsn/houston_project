# Brain — préserver les remontées et comprendre l'exécution

## Base et objectif

Base : `staging` au commit `031582135115c878ca97fc01f9766175e75db7f6`.
Les PR #358, #359 et #360 ciblent `main` ; elles ne sont pas incluses dans ce diff.
Ne pas fusionner Brain vers main indépendamment du circuit de promotion habituel.

Le moteur consultait surtout le résumé initial d'un Signal et les descriptions
et journaux des plans. Une remontée agrégée pouvait conserver une conséquence
métier dans CandidateSignal sans que le moteur la lise. La correction rend ces
sources accessibles, sans réécrire la synthèse du Signal ni créer une seconde
vérité opérationnelle.

## Parcours

1. L'admission existante contrôle les droits et fige la configuration.
2. `corpus.assemble_investigation_corpus` capture les sources existantes et appelle
   `terrain_evidence.collect_terrain_evidence` dans la même transaction REPEATABLE READ.
3. Les sources supplémentaires deviennent des BrainDossierItem `terrain_evidence`.
   Chaque source a un identifiant, une version de contenu, ses dates, sa provenance
   et une qualification métier. Aucune migration de modèle n'est nécessaire.
4. `search_evidence` recherche dans ces copies figées, par type, parent, texte ou
   période de déclaration. Les résultats sont paginés et soumis au budget commun.
5. Le moteur cite les fiches réellement consultées ; l'interface conserve leur
   identité et propose un lien vers le Signal ou l'exécution actuelle.
6. Les objectifs, évaluations de KPI et validations Knowledge suivent leurs
   services existants ; aucune activation automatique n'est ajoutée.

## Sources et limites exactes

- **Remontées** : résumés individuels des CandidateSignal créés/agrégés avec leur
  observation et leur Signal. Les candidats rejetés/en attente sont exclus.
  Deux candidats d'une observation partagent un event_key : leur nombre n'est pas
  un nombre de témoignages indépendants. Les observations liées sans résumé
  exploitable rendent cette famille explicitement incomplète.
- **Tâches** : titre, description, pôle, assigné, position, échéance, état à la
  capture, date de réalisation/abandon et motif d'abandon.
- **Discussions** : uniquement les commentaires rattachés à une exécution du site,
  avec auteur, date, fil et clôture. Un commentaire est un propos rapporté,
  jamais une décision validée par simple épinglage ou clôture.
- **Évaluations** : note, commentaire, auteur, date et activité à la capture.
  Une bonne note de réalisation ne prouve pas un effet sur les KPI.
- **Assignations** : responsables et dates de l'état capturé, pas un historique
  rétroactif inventé. Les journaux existants des plans (y compris les reports
  d'échéance) sont maintenant visibles dans search_actions.

Le texte brut des observations n'est pas envoyé à Brain. Le prompt de structuration
préserve désormais explicitement quantités, conséquences, renoncements,
comparaisons et causes rapportées. Il ne répare pas automatiquement les anciens
résumés qui auraient déjà perdu ces détails. Pas d'OCR ni d'interprétation nouvelle
des photos/PDF joints aux discussions ; la politique de rétention reste inchangée.

## Branchements des trois PR

- **#358** : les tâches, assignations et événements sous-jacents sont exploités.
  Les notifications de Ma journée ne sont pas de nouvelles preuves.
- **#359** : deux adaptateurs bornés prennent en compte ses modèles lorsqu'ils
  sont installés : provenance ChatObservationSource (auteur initial, date et ID,
  jamais le contenu du chat privé), et lien Comment.created_task/pinned_at.
  Les champs ne sont pas réintroduits ici : cela évite des migrations concurrentes.
  Le code fonctionne avant et après l'intégration de #359. Déployer ses migrations
  avant de redémarrer l'API/worker qui charge ses modèles.
- **#360** : les créations/modifications et états des plans alimentent les mêmes
  tables. Pas de dépendance à l'écran Kanban. Les reports conservent le journal.
  La duplication de #360 ne persiste pas de lien d'origine : cette PR n'invente
  donc pas de filiation. Les plans restent des exécutions distinctes. Ajouter une
  filiation explicite sera un changement séparé du contrat de création.

## Coût et couverture

Chaque famille utilise le plafond existant max_candidates_per_category et des
requêtes en lots, pas une requête par ligne. Les liens #359 sont au plus un par
source sélectionnée. Les textes restent dans le dossier, pas tous dans le prompt.
Le nombre d'appels d'outils passe de 8 à 12 pour permettre les consultations de
détails ; les plafonds de tokens et de 40 copies distinctes restent en place.
Cela autorise jusqu'à quatre consultations de plus, sans promettre une analyse
exhaustive d'un dossier arbitrairement grand. Un dépassement ou une ancienne
capture sans ces familles est déclaré indisponible/incomplet, jamais « aucun fait ».
Les nouvelles familles peuvent augmenter le volume stocké ; mesurer en staging
sur un établissement actif avant promotion (temps de capture, taille du dossier,
tokens, couverture et qualité des conclusions).

## Installation pour Léo

1. Appliquer cette branche sur staging contenant le moteur Brain actuel.
2. Exécuter les tests indiqués ci-dessous ; pas de nouvelle dépendance ni migration.
3. Déployer l'API et le worker Brain depuis le même commit, avec le prompt embarqué.
4. Créer une **nouvelle analyse**. Les dossiers historiques restent inchangés.
5. Après intégration de #359, réexécuter aussi les cas d'intégration conditionnels.
6. Promouvoir vers main selon le circuit habituel. Aucun changement live ici.

## Vérifications

Commande canonique serveur :

```sh
make backend-test ARGS='houston/brain/tests/test_terrain_evidence.py houston/brain/tests/test_engine.py houston/ai/tests/test_observation_pipeline_prompt.py'
```

Tests : conséquence nouvelle dans une remontée agrégée, absence de texte brut,
provenance et dédoublement, isolement inter-établissements, état abandonné,
évaluation distincte d'un résultat, capture immuable, pagination/couverture,
consultation sans requête live, requêtes bornées sans N+1, citation vers son parent.
Le scénario de lien commentaire→tâche est conditionnel à #359.

Validation locale : Ruff et compilation Python ; typecheck web et 8 tests UI
ciblés réussis. Les tests Django ne peuvent pas être exécutés dans l'environnement
Codex sans le .env de test et Docker ; ne pas les contourner avec pytest sur l'hôte.
La CI de la PR doit confirmer les tests serveur avant fusion. Aucun appel réel à
un fournisseur IA, aucune mesure de qualité sur données clients n'a été effectué.
