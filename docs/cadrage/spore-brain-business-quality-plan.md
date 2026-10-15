# Spore Brain — audit métier et plan de renforcement

Statut : proposition à revoir par Léo. Cette PR ne modifie aucun comportement applicatif.

Base inspectée le 15 octobre 2026 : `staging`, commit `a28ee9499675f42c501f92a43e1989ddba6e85f6` (PR #303 intégrée, correctif tokens #314 inclus).
`main` observée : `3adb518875406fc269b7542bb07681e03da04d43`, sans le module Brain. Cela ne permet pas de déterminer la version déployée.

## But et limites de l'audit

Faire de Brain un outil de décision : expliquer les évolutions chiffrées avec des faits terrain vérifiables, proposer une intervention adaptée et mesurer ensuite son résultat.

Les constats ci-dessous proviennent de la lecture de l'implémentation et des tests associés. Aucune analyse réelle ni suite de tests n'a été exécutée pour cette PR documentaire. La configuration de production, le modèle effectivement utilisé et le contenu du Knowledge en base ne sont pas vérifiés.

Conserver le moteur actuel : capture figée, isolation des établissements, sources citées, calculs vérifiés, budgets de tokens, lecture par lots, contrôle des réponses, propositions soumises à validation et historique des décisions. Ne pas réintroduire le prototype local comme moteur parallèle.

## 1. Méthode d'analyse métier explicite

### Constat vérifié

[`openai_provider.py`](../../apps/api/houston/brain/openai_provider.py), `system_prompt()` et `OpenAIBrainProvider.complete`, envoient un prompt système constant centré sur le contrat, la provenance et les calculs. Le dossier et le Knowledge sont transmis dans le message utilisateur. `HOUSTON_BRAIN_PROMPT_VERSION` est un identifiant de version ; ce n'est pas un contenu de prompt métier chargé depuis les paramètres.

[`contract.py`](../../apps/api/houston/brain/contract.py) prévoit déjà `statement`, `interpretation`, `contradictions`, `gaps`, `orientation`, `calculations` et `reported_facts`. La présence de ces champs ne garantit pas un bon raisonnement.

### Pourquoi

Une réponse au bon format peut expliquer trop vite une baisse par le premier incident trouvé. Il faut d'abord identifier ce qui varie, puis chercher les éléments qui soutiennent ou contredisent les explications possibles.

### Modification proposée

Ajouter une méthode métier courte et versionnée au propriétaire actuel du prompt, sans nouvel éditeur de prompt dans cette première étape :

1. Identifier les mesures comparables : établissement, pôle, période, unité, HT/TTC, détail ou total, réel/budget/historique.
2. Relever les évolutions pertinentes et signaler explicitement les comparaisons impossibles. Un niveau isolé n'est pas une baisse.
3. Décomposer quand les données le permettent : CA = volume × panier, puis effet prix, composition des ventes, remises ou suppléments. Ne pas inventer de ventilation absente.
4. Chercher les faits terrain compatibles avec cette évolution et leur chronologie, puis les faits contradictoires et les autres explications plausibles.
5. Distinguer constat, hypothèse et explication étayée. Une action terminée ne prouve pas un effet sur les ventes.
6. Choisir ACTION, INVESTIGATION ou NO_ACTION. Vérifier les plans existants avant de suggérer un nouveau plan. Ne pas fabriquer une action pour chaque ligne stable du reporting.
7. Écrire une restitution brève : constat, éclairage terrain, décision proposée et mesure à suivre. Garder les identifiants techniques dans les citations structurées, pas dans le texte métier.

Ne pas copier tel quel l'ancien prompt local : ses noms de champs et ses outils ne correspondent pas nécessairement à `brain_analysis_v1`. Maintenir la séparation entre instructions fiables et contenus importés non fiables.

### Validation

- Un changement de prompt modifie effectivement la requête envoyée et son comptage de tokens.
- Le schéma strict et les limites de correction restent respectés.
- Une baisse de panier n'entraîne pas automatiquement une recommandation de hausse des prix.
- Aucun lien causal affirmé si seules une proximité temporelle ou une corrélation sont disponibles.

## 2. Accès ciblé aux observations sources

### Constat vérifié

[`collection.py`](../../apps/api/houston/brain/collection.py), `_signal_item`, fournit les synthèses des signaux, leur périmètre, leurs statuts et événements. `source_observation_link_counts` fournit des nombres de liens. La collecte inspectée ne constitue pas un dossier des observations originales avec leur texte, auteur et date individuels.

### Pourquoi

« Attente au déjeuner » décrit un problème. « Trois tables refusent le dessert faute de temps » apporte un élément directement utile pour expliquer le panier moyen. Le résumé du signal peut perdre cette précision, même si certaines synthèses la conservent.

### Modification proposée

- Compléter les signaux retenus par leurs observations sources utiles, selon les liens métier existants et les droits du dossier.
- Préserver identifiant, contenu disponible, date du fait si connue, date de saisie, auteur autorisé et rattachement au signal/pôle.
- Figer les sources avant les appels IA ; aucun accès improvisé à la base par le modèle.
- Faire évoluer ensemble collecte, localisateurs de citations, budget, regroupement des lots et résolution des liens UI.
- Borner les requêtes et les volumes. Si le dossier ne peut pas être couvert, annoncer cette limite ; ne pas présenter une sélection partielle comme exhaustive.
- Ne pas ajouter les commentaires dans ce lot : leur exclusion fait partie du périmètre demandé.

### Validation

- Observation liée accessible dans le bon dossier ; aucune fuite inter-établissement ni inclusion d'une source devenue non autorisée selon les règles existantes.
- Un détail absent du résumé mais présent dans l'observation peut être cité et ouvert.
- Distinguer date de saisie et période du phénomène ; un correctif postérieur ne justifie pas une hausse antérieure.
- Budgets, gros dossiers, citations et regroupements par lots restent cohérents.

## 3. Référentiel cumulatif, sélectionné selon le sujet

### Constat vérifié

[`configuration.py`](../../apps/api/houston/brain/configuration.py), `selected_knowledge`, charge une `BrainKnowledgeVersion` active avec formulation, conditions, limites et incertitude. [`knowledge.py`](../../apps/api/houston/brain/knowledge.py) crée une version à partir d'un candidat approuvé ; l'activation désactive les autres versions actives.

Le circuit de validation des candidats existe donc déjà. En revanche, il ne constitue pas encore la sélection de plusieurs mécanismes dans une bibliothèque cumulative telle qu'envisagée dans le JSON. Une formulation peut contenir beaucoup de texte en base ; ce contenu n'a pas été inspecté.

### Pourquoi

Ajouter une nouvelle connaissance ne doit pas faire disparaître les précédentes. Le système doit aussi pouvoir n'en utiliser aucune lorsque les conditions ne sont pas remplies.

### Modification proposée

- Distinguer l'identité d'un mécanisme et ses révisions. L'activation d'une révision remplace celle du même mécanisme, pas toute la bibliothèque.
- Conserver la validation humaine, les conditions d'application, contre-exemples, limites, niveau d'incertitude et statut synthétique/terrain validé.
- Sélectionner les mécanismes pertinents d'après le sujet, le secteur, le KPI et les conditions disponibles. Commencer par une sélection explicable et bornée ; pas d'infrastructure vectorielle imposée.
- Figer les révisions sélectionnées et la raison de sélection dans la configuration de l'analyse.
- Autoriser une sélection vide et une déduction nouvelle, clairement présentée comme hypothèse. Un mécanisme n'est jamais une preuve concernant cet établissement.
- Examiner les versions déjà stockées avant migration. Ne pas activer automatiquement tous les anciens candidats approuvés : certains peuvent être obsolètes ou avoir été remplacés.
- Adapter les écrans/API d'administration existants et les tests d'activation. Ne pas introduire un second référentiel concurrent via un fichier JSON chargé hors de ce circuit.

### Validation

- Deux mécanismes distincts restent disponibles après activation du second ; une nouvelle révision remplace seulement l'ancienne du même mécanisme.
- Aucun candidat non validé n'est injecté comme connaissance approuvée.
- Un cas sans mécanisme applicable est analysable sans rapprochement forcé.
- Une analyse passée conserve les versions utilisées.

## 4. Calculs comparables et suivi des objectifs

### Constat vérifié

[`contract.py`](../../apps/api/houston/brain/contract.py), `evaluate_calculation`, revérifie les opérandes cités, les ambiguïtés, les unités et le résultat. Il ne réalise pas un inventaire systématique de tous les leviers métier en amont du raisonnement.

[`objectives.py`](../../apps/api/houston/brain/objectives.py), `_matching_measures`, rapproche l'indicateur et le libellé par égalité normalisée. `_reading` contrôle ensuite notamment l'unicité et l'unité. Le périmètre `scope` de l'objectif n'intervient pas dans cette sélection de la mesure. La collecte applique des règles de période au dossier ; cela ne remplace pas une vérification de la période propre à chaque mesure.

Les objectifs et leurs révisions existent. Les propositions IA, elles, contiennent suggestions et mécanismes, pas d'objectif KPI. Le test `test_a_proposal_cannot_invent_a_kpi_target` exprime une protection volontaire à préserver.

### Pourquoi

Deux lignes « CA » peuvent concerner deux pôles, deux périodes ou réel/budget. Une comparaison arithmétiquement juste peut rester incorrecte sur le plan métier. Un plan exécuté peut aussi ne pas avoir produit le résultat attendu.

### Modification proposée

- Donner aux mesures un contexte comparable : indicateur, unité, pôle/périmètre, période et nature de comparaison, avec provenance et ambiguïtés explicites.
- Utiliser ce contexte pour les calculs et les bilans d'objectifs. Si une dimension déterminante manque, résultat non évaluable plutôt que conclusion forcée.
- Conserver objectifs validés, échéances, historique des révisions et protection contre un ancien bilan écrasant le plus récent.
- Relier clairement sujet analysé, suggestion de plan et objectif saisi/validé par l'humain. Faire ce lien dans les services métier, avec intégrité et contrôle de droits.
- Une cible suggérée par l'IA nécessiterait une évolution explicite du contrat : ne pas la glisser dans le prompt pour contourner l'interdiction actuelle. Pour ce plan, garder la cible sous décision humaine.
- Au bilan, séparer résultat numérique vérifié et explication terrain hypothétique ou étayée. Ne jamais déduire « objectif atteint » du seul statut du plan.

### Validation

- Même libellé pour deux pôles, deux périodes, budget/réel : pas de correspondance silencieusement incorrecte.
- Cible refusée, unité différente, mesure absente ou ambiguë : pas de succès affiché.
- Ancienne analyse terminant plus tard : aucun écrasement du bilan plus récent.
- Objectif lié à un plan terminé mais KPI dégradé : résultat non atteint.

## 5. Qualité métier mesurée avant élargissement

Les tests de contrat et de cycle de vie restent indispensables. Ils ne suffisent pas à démontrer que les recommandations sont utiles. Aucun benchmark C01/C02 n'a été retrouvé dans les tests Brain inspectés.

Construire un petit jeu versionné de dossiers synthétiques, distinct des données clients et des mécanismes donnés au modèle :

| Cas | Réponse attendue / erreur à éviter |
| --- | --- |
| C01 : attente et desserts refusés | Examiner l'organisation du service et la comparaison avant/après ; ne pas promettre un gain garanti. |
| C02 : formule moins chère, couverts stables | Examiner fréquentation, occupation et composition des ventes ; deux avis favorables ne valident pas une stratégie. |
| Aucun fait terrain explicatif | Dire ce qui manque et proposer une vérification ciblée. |
| Terrain contradictoire | Montrer les deux ensembles de faits et ne pas forcer une cause unique. |
| Plan existant ou déjà terminé | Suivre/évaluer avant de créer un doublon. |
| Mesures homonymes sur deux pôles | Ne pas comparer des périmètres différents. |
| JSON sans mécanique pertinente | Produire un raisonnement prudent sans usage artificiel du référentiel. |
| Gros dossier en plusieurs lots | Garder les faits contradictoires et les liens nécessaires dans la synthèse. |

Les cas C01/C02 sont des références de développement, pas des preuves commerciales. Reconstruire et faire valider leurs entrées complètes avant une notation ; les résumés ci-dessus ne constituent pas un dataset suffisant.

Mesurer séparément : exactitude des chiffres, précision des citations, pertinence causale, traitement des contradictions, utilité de la décision, absence de doublons, suivi des objectifs, coût et latence. Comparer le moteur actuel et chaque modification avec le même dossier et la même configuration de modèle. Conserver des cas non utilisés pour rédiger les mécanismes ou le prompt.

## Ordre d'intégration proposé à Léo

1. **Baseline d'évaluation** : figer quelques dossiers et les résultats actuels ; valider les réponses attendues avec Maxime.
2. **Méthode métier dans le prompt existant** : petit changement, aucune migration ; vérifier les budgets et comparer les réponses.
3. **Preuves terrain ciblées** : collecte + citations + lots + liens UI ensemble ; tester les droits et volumes.
4. **Comparabilité KPI et objectifs** : contexte des mesures, rapprochement fiable et liens métier ; tests déterministes avant essais IA.
5. **Knowledge cumulatif** : migration examinée, sélection bornée, activation et administration cohérentes ; réévaluation sans et avec référentiel.
6. **Recette complète** : importer, analyser, discuter, confirmer un plan, saisir/valider un objectif, importer la période suivante et vérifier le bilan.

Livrer en petites PR cohérentes basées sur la dernière `staging`. Respecter les commandes canoniques du dépôt (`make backend-test ARGS=...` pour les tests ciblés) et les consignes API/Web applicables. Mettre à jour les contrats et clients générés lorsqu'un schéma public évolue. Aucune dépendance à un installateur local Docker pour Léo.

Critère de sortie : aucune régression de droits, provenance, calcul ou cycle de vie ; amélioration métier vérifiée sur les dossiers de référence et les cas réservés. La fusion de cette PR documentaire n'implémente aucune de ces corrections.
