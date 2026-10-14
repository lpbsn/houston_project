# SPORE Brain V1 — Cadrage fonctionnel consolidé
Version du 8 octobre 2026 — révision 2, après contrôle des hypothèses et cas limites

## 1. Statut et mission confiée à Cursor

Ce document consolide le cadrage initial, sa revue critique et les arbitrages validés le 8 octobre 2026. Il devient la référence fonctionnelle pour préparer le plan du moteur Brain. En cas de divergence, il prévaut sur le cadrage initial et sur le prototype.

**Travail demandé maintenant : analyser le dépôt et le patch, puis proposer un plan d’implémentation. Ne pas implémenter avant validation de ce plan.**

Dépôt : `lpbsn/houston_project`. Partir de `staging`, jamais directement de `main`. Relire les instructions du dépôt et son code actuel. La revue précédente portait sur `e1a3d37bfe35109c91e5d12ebc1273a3d531c412` ; cette référence n’est pas une affirmation sur la tête actuelle.

Le patch `Spore-Brain-Integration-2026-10-05.patch` constitue une source de composants et d’idées, pas une architecture à préserver. La revue détaillée du même jour fournit des constats de code, à revérifier si nécessaire.

Les exigences ci-dessous fixent les comportements et garanties. Les noms conceptuels ne prescrivent ni une table par concept, ni un framework d’orchestration. Cursor choisit la solution technique la plus simple qui respecte ces exigences et justifie ses choix.

### Liberté de conception et ordre de priorité

| Nature | Traitement attendu |
|---|---|
| Décisions produit validées | Respecter formats, exclusions, partage, dossier figé, décisions humaines, règles de réanalyse et conservation |
| Contraintes d’intégration retenues | Rester dans Houston/SPORE, réutiliser les services et contrats existants, isoler l’exécution Brain ; partir de staging |
| Garanties de qualité et de fonctionnement | Proposer un mécanisme vérifiable, sans confondre l’objectif avec une implémentation imposée |
| Solutions techniques et paramètres | Choisir et justifier dans le plan, après lecture du repo et, si nécessaire, une investigation ciblée |

Sont notamment ouverts : schéma de données, stockage des snapshots, isolation/verrouillage SQL, nombre et découpage des tâches et appels IA, extraction native ou conversion, algorithme de recherche, sélection du Knowledge, stratégie de lots et mécanisme de reprise. Aucun ResearchPlan, CandidateUniverse, EvidenceBundle ou AnalysisAttempt ne doit devenir une table ou un appel obligatoire par son seul nom.

Les contraintes d’intégration ne sont pas une interdiction de critiquer l’existant. Si le repo ne permet pas de respecter une garantie, exposer le conflit et proposer l’adaptation minimale ; ne pas dupliquer par défaut ni prétendre que l’existant suffit. Une modification d’une décision produit validée doit être soumise explicitement, jamais dissimulée dans le plan.

## 2. Promesse produit et périmètre

Brain confronte un reporting métier aux informations opérationnelles autorisées d’un établissement pour produire une analyse utile à sa direction : constats, explications étayées ou hypothèses, contradictions, limites, actions ou investigations possibles.

Brain peut conclure qu’il ne sait pas ou qu’aucune intervention n’est justifiée. Il ne garantit pas de découvrir la cause de chaque variation.

**Inclus V1 :** lancement manuel, import documentaire, analyse chiffrée et textuelle, historique pertinent, dossier figé, sources consultables, follow-ups, suggestions de Plans, objectifs KPI indépendants, mécanismes métier candidats soumis à revue humaine, audit du traitement.

**Exclus V1 :** analyses programmées/automatiques, surveillance continue, agent autonome, SQL ou code arbitraire généré et exécuté, vector database, plateforme RAG générique, création automatique de Plans, activation automatique de Knowledge, apprentissage autonome, clustering sophistiqué, OCR et interprétation d’images.

Les commentaires, chats, Observations techniques brutes, transcriptions, photos et pièces jointes terrain sont exclus des sources Brain. Le reporting importé suit ses propres règles ci-dessous.

## 3. Acteurs, accès et partage

L’espace Brain est partagé entre les **owner et director actifs de l’établissement**, quel que soit l’auteur des documents ou analyses.

- Ils consultent les reportings, analyses, conversations et preuves de cet établissement.
- L’auteur de chaque lancement, message et décision reste identifiable.
- Les décisions métier Brain au niveau établissement sont effectuées par un owner/director actuellement autorisé, dans les limites des services Houston ; l’auteur initial ne dispose pas d’un droit exclusif sur l’analyse partagée.
- La perte des droits retire aussi l’accès à l’historique et aux fichiers servis par SPORE. Le plan doit couvrir les liens déjà délivrés et leurs éventuelles limites de révocation : ne pas remplacer silencieusement cette exigence par une simple expiration différée. Toute limite technique incompatible doit être soumise explicitement. Un fichier déjà téléchargé ne peut pas être rappelé.
- Une référence fournie par le modèle ne permet jamais de récupérer une donnée hors de l’établissement ou hors du dossier autorisé.
- L’administration du Knowledge relève du modèle Platform Operator existant. Elle n’accorde pas automatiquement l’accès aux reportings et preuves privées des clients.
- Le plan doit définir les contrôles au lancement, lors des travaux différés, avant les envois au fournisseur et lors des consultations/mutations. Une révocation ne peut pas rappeler un contenu déjà envoyé.

Le mode d’accès autorisé aux preuves privées lors de la revue plateforme des mécanismes doit être explicité avant sa mise en service. À défaut, ne pas exposer ces preuves à l’administration globale.

Ne pas confondre perte d’accès de l’auteur et suppression d’une analyse partagée. Le comportement d’un traitement déjà lancé lorsque son auteur perd ses droits ou que l’établissement devient inactif doit être proposé explicitement : aucune poursuite implicite sous l’identité d’un autre dirigeant. La capacité de consulter et d’agir est toujours contrôlée sur les droits actuels.

## 4. Reporting : formats, préparation et limites

### 4.1 Formats contractuels

**Un fichier importé = un Reporting.** Plusieurs feuilles ou sections restent un seul Reporting.

| Format | Contenu attendu |
|---|---|
| XLSX | Cellules, tableaux et feuilles ; valeurs de formules disponibles, sans exécution de macros |
| CSV | Données tabulaires ; contrôle de l’encodage, séparateur et formats numériques |
| PDF textuel | Texte et tableaux dont la structure est suffisamment exploitable |
| DOCX | Paragraphes et tableaux, avec leur ordre et contexte |

DOC est hors V1. Un fichier DOC est refusé avec une consigne d’export DOCX ou PDF textuel.

Les scans, captures et graphiques en image ne sont pas interprétés. Les images décoratives ne doivent pas provoquer à elles seules un rejet. Lorsqu’un contenu essentiel est identifié comme inaccessible, demander un export exploitable. Ne pas promettre une détection parfaite du sens des images sans les analyser : la limite de prise en charge doit être visible à l’import.

Accepter une extension ne garantit pas l’exploitation de toute mise en page. Un document inexploitable est refusé avec une explication utile, sans présentation trompeuse d’une lecture complète.

### 4.2 Préparation

Conserver le fichier original, son identité, la représentation utilisée et les versions d’extraction pertinentes. L’import ne déclenche pas automatiquement l’analyse principale. La préparation technique peut précéder Analyser ou faire partie de son traitement ; ne pas imposer un second pipeline ni une attente HTTP longue. Les appels IA nécessaires à l’analyse sont couverts par la confirmation Analyser et son budget, sans demander une confirmation pour chaque étape. Un traitement IA avant cette action nécessiterait un parcours explicite proposé dans le plan.

Le plan décrit le passage de fichier reçu à reporting exploitable, les erreurs de préparation et le nettoyage des imports abandonnés, sans imposer ici de modèles ou d’états internes. Un document vide ou sans contenu analysable n’aboutit pas à une analyse réussie vide.

La période métier principale doit être connue et confirmée. Distinguer sous-périodes, budget, N-1 et autres comparatifs. Toute modification matérielle après analyse produit une nouvelle version ou un nouveau Reporting ; elle ne modifie pas le dossier historique.

La confirmation de période peut être associée à Analyser ; si sa détermination échoue pendant le traitement, échouer avec une demande ciblée plutôt qu’inventer une période ou conserver indéfiniment une analyse active. Un reporting ambigu sur l’établissement ou agrégeant plusieurs établissements doit être clarifié ou remplacé par un export du périmètre voulu. La V1 ne réalise pas d’analyse multi-établissements.

Les conversions/parsers doivent être bornés en taille, mémoire et temps. Aucune macro, formule active, lien externe ou instruction embarquée ne doit déclencher une exécution ou un accès arbitraire.

### 4.3 Chiffres et provenance

Pour chaque mesure utilisée dans une conclusion, préserver : libellé, valeur, unité/devise pertinente, période, périmètre, définition disponible et emplacement source.

- Différencier zéro, absence, erreur et valeur non interprétable.
- Détecter les ambiguïtés matérielles : HT/TTC, euros/k€, pourcentage/points, mois/cumul, détail/total.
- Vérifier la comparabilité avant tout rapprochement.
- Vérifier par calcul déterministe les variations et agrégats calculés par Brain et publiés, depuis des opérandes validés ; conserver opération et sources. Réutiliser les mécanismes appropriés du backend sans construire un moteur de formules universel. Une valeur déjà déclarée dans le reporting reste un fait rapporté, identifiable comme tel ; l’absence de ses opérandes ne doit pas forcer un recalcul impossible. Une incohérence détectée est signalée.
- Ne pas moyenner des taux sans les dénominateurs appropriés.
- Ne pas inventer de valeur lorsqu’une formule n’a pas de résultat exploitable.
- Une interprétation IA de libellé ou de tableau reste une donnée dérivée à contrôler.

La provenance utilise les coordonnées disponibles : feuille/cellules, ligne/colonnes, page/fragment ou paragraphe/tableau.

Une ambiguïté qui affecte matériellement les conclusions doit être clarifiée ou bloquer le traitement, pas être comblée par supposition.

## 5. Analyse, Conversation et lancement

Une analyse principale utilise un Reporting et un dossier figé. Une Conversation correspond à cette analyse et à ses follow-ups. Le même Reporting peut faire l’objet de plusieurs analyses explicitement demandées, chacune avec sa Conversation.

Le lancement se fait uniquement par action explicite sur **Analyser**. Il est idempotent pour une même demande utilisateur. Réimporter le même fichier et réessayer une requête réseau ne sont pas la même opération.

**Une seule analyse principale QUEUED ou RUNNING par établissement.** Cette garantie reste vraie avec plusieurs utilisateurs et plusieurs workers. Les établissements restent indépendants. Une seconde demande distincte ne crée ni analyse concurrente ni nouvelle analyse active cachée : informer qu’un traitement existe et donner accès à celui-ci. Une répétition de la même demande retrouve l’analyse créée. La file globale peut contenir des analyses de plusieurs établissements.

Statuts métier : `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELED`. Préparation, capture, analyse, validation et finalisation sont des étapes internes, pas de nouveaux statuts produit.

L’utilisateur peut quitter la page et revenir. L’interface distingue attente et traitement, expose une erreur compréhensible et permet l’annulation tant que l’analyse n’est pas terminale. Aucun résultat intermédiaire ne doit être présenté comme une conclusion finale.

Un retry technique reste la même analyse. Une réanalyse manuelle crée une nouvelle analyse et une nouvelle Conversation. L’état d’un follow-up reste distinct de celui de l’analyse principale.

COMPLETED, FAILED et CANCELED sont terminaux pour l’analyse principale. La réanalyse ne remplace pas l’historique. Les follow-ups analytiques utilisent une analyse COMPLETED disposant encore de son dossier ; une analyse échouée ou annulée affiche son état, pas une conversation prétendant expliquer un résultat inexistant.

## 6. Sources terrain et interprétation temporelle

Le **Signal** est la source terrain canonique. Brain ne remonte pas au contenu de l’Observation brute, même pour compléter un résumé insuffisant.

Sources autorisées : Signals, classifications/motifs existants pertinents, Plans et exécutions, tâches, relations explicites, statuts et événements structurés, dates, pôles, responsabilités professionnelles nécessaires, validations/résolutions structurées, objectifs Brain validés, reportings antérieurs pertinents et contexte établissement.

L’autorisation porte sur les **champs**, pas sur tout le contenu d’un modèle : une validation contenant un commentaire libre ne rend pas ce commentaire autorisé. Charger seulement les personnes utiles ; un droit d’accès ne prouve pas une responsabilité opérationnelle.

La collecte analytique est indépendante des règles d’affichage des feeds : rétention, pins et pagination UX. Elle réutilise les règles d’autorisation, pas la fenêtre du feed.

### Règles temporelles

- Examiner la période complète et les chevauchements ; ne pas filtrer seulement sur la date de création.
- Distinguer date du phénomène, déclaration/enregistrement, transition applicative et capture.
- Ne pas assimiler `updated_at` ou `last_activity_at` à la survenance du phénomène.
- Une date déduite du texte conserve provenance et incertitude.
- Un événement de période déclaré plus tard reste un fait de période connu tardivement.
- Les événements postérieurs servent au suivi, pas à expliquer rétroactivement un résultat.
- Les événements effectivement survenus sont bornés à la capture. Une date planifiée future reste une intention, jamais un événement déjà réalisé.
- Un statut actuel ne prouve pas le statut pendant la période. Utiliser le journal disponible et signaler ses limites.
- Distinguer dates planifiées, démarrage effectif, fin déclarée et validation d’une exécution.
- Employer le fuseau de l’établissement pour interpréter les périodes civiles.

Les remontées agrégées ne sont pas des incidents indépendants. Une durée de traitement n’est pas automatiquement une durée de panne. L’absence de Signal ne prouve pas l’absence de problème ; leur nombre dépend aussi des pratiques de déclaration.

Consommer les motifs/récurrences existants sans créer un moteur concurrent ni charger les preuves d’autres établissements par leurs relations organisationnelles.

## 7. Dossier figé, historique et recherche

Le dossier conserve matériellement les contenus réellement utilisés et les données candidates nécessaires aux recherches complémentaires/audit. Une liste d’identifiants d’objets vivants ne suffit pas.

Il distingue au minimum : reporting, sources candidates, éléments sélectionnés, contexte établissement, objectifs, mémoire historique, Knowledge et configuration effective. Ces catégories peuvent partager une représentation physique.

### Frontière de capture

Le plan choisit l’ordre de préparation, collecte et interprétation initiale. La règle obligatoire est la suivante : les données Houston présentées comme appartenant au même dossier proviennent d’une vue cohérente, et leur contenu exact est conservé. Une lecture préparatoire éventuelle de Houston doit appartenir à cette même vue si elle sert de preuve ou influence la sélection ; elle ne peut introduire discrètement un état différent.

Le plan définit un point de fermeture vérifiable. Après fermeture, aucun enrichissement depuis les objets vivants ; toute recherche complémentaire porte sur les copies. Ne pas imposer un appel IA de planification préalable, un unique SELECT, une transaction particulière ou une copie intégrale de l’établissement. Si plusieurs étapes de collecte sont choisies, démontrer qu’elles respectent la cohérence, sans maintenir de transaction pendant un appel IA.

Cursor doit démontrer la cohérence des lectures concurrentes. Ne pas maintenir une transaction de capture pendant parsing, appel IA ou autre opération réseau longue. Les timestamps documentent la capture ; ils ne remplacent pas la conservation des contenus.

Avant qu’un dossier complet soit durable, une reprise de capture peut recommencer avec un nouvel instant de capture tracé. Après fermeture, aucune reprise ne mélange ce dossier avec des données actuelles.

Figer l’état connu à la capture ne reconstitue pas tout l’état historique : les conclusions doivent respecter les limites des journaux Houston.

### Sélection et historique

Une compréhension IA bornée peut identifier KPI, sujets et recherches souhaitées dans un contrat contrôlé. Houston valide les paramètres et choisit les lectures ; le modèle ne fournit pas de SQL ou de noms de modèles Django à exécuter, et tout identifiant proposé est vérifié.

La collecte de base ne dépend pas d’une seule hypothèse. Rechercher aussi contradictions, explications alternatives et relations transversales. Le pôle priorise, il n’exclut pas les autres pôles de l’établissement.

Historique ciblé : période comparable précédente, N-1 pertinent, relations directes, récurrence existante, Plans et objectifs liés. Ni fenêtre universelle arbitraire, ni chargement intégral systématique de l’historique.

Les anciens reportings fournissent les mesures originales disponibles. Les anciennes analyses aident à retrouver hypothèses et décisions ; leur répétition ne transforme pas une hypothèse en fait et ne réintroduit pas une source interdite.

Une recherche complémentaire pendant le raisonnement reste bornée et limitée au dossier. Si le besoin exige des données nouvelles, annoncer la limite et proposer une nouvelle analyse.

Dédupliquer les sources techniques sans fusionner les Signals. Conserver les raisons de sélection/exclusion. Un élément non examiné n’est pas déclaré non pertinent. Les sources interdites ne sont pas copiées dans l’inventaire.

L’inventaire porte sur les candidats effectivement collectés, pas sur chaque ligne de la base. Conserver également le périmètre et les critères des recherches exécutées, y compris celles sans résultat : une absence de résultat doit être distinguable d’une recherche non exécutée. Les limites d’historique disponible ou de classification existante sont explicites ; ne pas attendre indéfiniment qu’un autre pipeline complète le terrain.

## 8. Couverture, raisonnement et résultat

Trois dimensions sont suivies, éventuellement dans un même journal :

| Dimension | Garantie attendue |
|---|---|
| Reporting | Traitement ou exclusion explicite des sections/mesures identifiées |
| Recherche | Exécution des recherches requises pour les sujets |
| Traitement | Traitement et validation des éléments/lots prévus |

Ne pas confondre ces garanties avec la certitude que le modèle a tout compris. Un booléen IA de couverture ou le retour des identifiants de lots ne suffit pas à prouver l’exhaustivité sémantique.

Le plan précise comment sont établis les sujets et travaux requis, quelles recherches minimales ne dépendent pas d’une seule hypothèse IA, et comment est contrôlée la correspondance entre contenu d’entrée et résultat. « Matériel » désigne ce qui peut modifier un constat principal, sa comparaison ou une décision proposée. Les règles doivent être explicables, testées sur le corpus et stables pendant un traitement ; pas de seuil universel de vérité ni de promesse de rappel parfait.

La profondeur peut varier selon l’importance métier. Aucun sujet important ne peut être rétrogradé après un échec pour obtenir COMPLETED. La restitution peut regrouper les mesures secondaires sans les supprimer silencieusement du traitement.

| Situation | Issue attendue |
|---|---|
| Recherche correcte sans preuve terrain pertinente | COMPLETED possible ; absence d’explication explicite |
| Comparatif absent/non comparable, autres constats exploitables | COMPLETED possible avec limite |
| Cause indéterminable malgré le traitement attendu | Hypothèse, investigation ou abstention |
| Contenu matériel illisible/ambigu | Clarification avant analyse ou FAILED avec motif |
| Recherche/lot requis non terminé | FAILED ; INSUFFICIENT_COVERAGE si applicable |
| Résultat invalide après correction autorisée | FAILED |

Pas de statut PARTIALLY_COMPLETED. COMPLETED peut comporter des limites, mais ne masque pas un traitement requis inachevé.

Chaque conclusion importante distingue constat, éléments terrain, interprétation, contradictions et informations manquantes. Une source rapportant un fait ne valide pas toute son interprétation causale.

Une référence doit appartenir au dossier et être consultable selon les droits. Une source citée doit soutenir l’affirmation ; sa seule existence ne suffit pas. Le code contrôle références, calculs et invariants vérifiables ; l’évaluation métier contrôle aussi la pertinence du raisonnement.

Un Signal, son Plan et sa résolution ne sont pas automatiquement trois preuves indépendantes. Ne pas inventer d’impact chiffré ou de probabilité causale. Une action peut être utile sans causalité entièrement démontrée si son intérêt et ses limites sont explicités.

Les résultats possibles sont **ACTION**, **INVESTIGATION**, **NO_ACTION**. Ne pas imposer une action ou un objectif pour remplir la restitution.

Ces orientations s’appliquent par sujet, pas comme un choix unique pour toute l’analyse. Le résultat IA respecte un contrat structuré et versionné choisi par Cursor, validé par le backend. Refus fournisseur, réponse tronquée, référence inconnue ou invariant invalide ne sont jamais transformés silencieusement en résultat réussi. Le modèle ne contrôle ni autorisation, ni publication, ni mutation.

## 9. Follow-ups et décisions opérationnelles

**Décision validée : les follow-ups restent sur le dossier figé.**

| Demande | Comportement |
|---|---|
| Expliquer une conclusion, détailler une preuve/comparaison disponible | Même Conversation |
| Explorer un scénario hypothétique | Même Conversation ; hypothèse explicitement étiquetée |
| Intégrer un nouveau document, actualiser le terrain ou corriger un fait matériel | Nouvelle analyse explicitement confirmée |
| Modifier une suggestion ou décider d’un KPI | Décision humaine indépendante ; pas de réanalyse obligatoire |

Les messages peuvent compléter la discussion mais ne deviennent pas silencieusement des preuves. Brain ne recapture ni contexte établissement ni mémoire terrain actuelle pour répondre.

Lorsqu’une réanalyse est nécessaire, expliquer pourquoi, préremplir ce qui peut l’être et lier l’analyse précédente. Ne jamais démarrer automatiquement un traitement payant.

Une correction matérielle déclarée dans un message est conservée comme déclaration, jamais appliquée au dossier courant ni réputée vraie par défaut. Pour la nouvelle analyse, proposer un reporting corrigé lorsque le fichier source change. L’intégration d’une correction déclarative comme entrée additionnelle versionnée est une option de parcours à soumettre explicitement dans le plan, pas un éditeur de données ou un système d’overrides imposé par ce cadrage. Si la même preuve montre une erreur d’interprétation de Brain, le follow-up peut la reconnaître et l’expliquer ; le résultat principal historique n’est pas réécrit en silence.

Un follow-up a un budget et un état propres ; son échec ne modifie pas le statut COMPLETED de l’analyse principale. Les échanges simultanés doivent être ordonnés de manière cohérente.

Le plan définit l’idempotence d’une question, l’ordre/contexte de réponses concurrentes et la gestion des longues conversations. Ne pas tronquer silencieusement les preuves requises ; une mémoire de conversation résumée reste dérivée. La configuration des follow-ups est traçable et ne change pas silencieusement le Knowledge utilisé par l’analyse. Si une ancienne configuration n’est plus utilisable, signaler la limite et proposer une réanalyse.

Ne pas faire d’un follow-up une voie parallèle de publication de nouvelles évaluations KPI, de nouveaux mécanismes globaux ou de doublons de suggestions. S’il doit proposer de nouveaux objets décisionnels à partir du même dossier, leur cycle, leur provenance et leur déduplication doivent être proposés explicitement dans le plan ; aucune mutation automatique n’est permise.

L’interface peut afficher l’état actuel d’une conversion ou vérifier les droits/assignés pour agir. Cela ne permet pas de réinjecter les données actuelles dans le raisonnement historique.

## 10. Suggestions, objectifs et Knowledge

### Plans et investigations

Une ActionSuggestion est modifiable avant confirmation : titre, description, tâches, pôle, assignés et dates. La confirmation appelle le service métier Houston, avec contrôle des droits et idempotence.

Présenter les Plans pertinents existants pour éviter les doublons sans les modifier automatiquement. Une suggestion déjà convertie ne crée pas un deuxième Plan. Ne pas déduire un responsable d’un simple droit d’accès ; à défaut de responsabilité explicite, demander une désignation.

Cette garantie de conversion vise la même suggestion/demande, pas une détection parfaite de doublons sémantiques entre analyses. Un Plan supprimé après conversion n’autorise pas une recréation silencieuse. Les modifications concurrentes de deux dirigeants ne doivent pas écraser une décision plus récente ; le plan choisit comment détecter et présenter le conflit. Un nouveau Plan existant depuis la capture peut être signalé à la confirmation, sans réécrire le raisonnement historique ni exiger une nouvelle analyse pour toute mutation.

Une investigation peut rester une vérification ou un brouillon de message ; aucun message n’est envoyé automatiquement et aucun Plan n’est obligatoire.

### Objectifs KPI

Créer un Plan et valider/modifier/refuser un KPI sont deux décisions indépendantes. Un Plan n’exige pas un KPI artificiel ; un objectif peut exister sans Plan créé.

Un objectif évaluable précise indicateur, unité, périmètre, référence, cible/condition, échéance et méthode/source de mesure. Ne pas inventer une cible sans justification. Préserver les révisions et décisions humaines.

Une nouvelle analyse sélectionne les objectifs pertinents et comparables. L’évaluation conserve la version de l’objectif, la période mesurée, les mesures et leurs sources. NON_EVALUABLE signifie que les données ou la comparabilité nécessaires manquent ; il n’impose pas que toute interprétation métier soit automatisable par un calcul. Les comparaisons numériques vérifiables relèvent du code ; toute appréciation qualitative reste explicitement identifiée. Plan terminé ≠ objectif atteint ; objectif atteint ≠ impact du Plan démontré.

Le plan définit les conflits de révision d’objectif et les évaluations successives : une analyse d’une ancienne période exécutée plus tard ne doit pas écraser silencieusement un bilan plus récent. Le résultat figé peut conserver l’évaluation de la version capturée ; sa publication comme état courant d’un objectif modifié depuis doit être contrôlée et présentée comme telle.

### Knowledge et mécanismes

Séparer règles du moteur, Knowledge métier validé/versionné et données client non autoritaires. Un fichier ou message ne peut changer les permissions, le Knowledge ou les outils disponibles.

Un mécanisme connu oriente l’interprétation sans prouver sa réalisation. Conserver version et sélection utilisées. Une hypothèse doit préciser pourquoi elle est plausible et ce qui permettrait de la vérifier.

Un MechanismCandidate conserve formulation, conditions, limites, incertitude, origine et preuves privées. Workflow : candidature → revue humaine/modification → approbation ou rejet → nouvelle version → activation explicite séparée.

La formulation globale ne doit contenir aucune donnée identifiante du client. Retirer uniquement les références n’est pas une anonymisation suffisante. Pas de fusion, promotion ou activation autonome.

Le plan définit la configuration initiale requise, le comportement en l’absence de Knowledge/prompt actif et la validation avant activation. Ne pas inventer de référentiel privé manquant ou activer un contenu de démonstration en production. Le contenu métier privé doit être fourni pour valider les analyses réelles, sans empêcher le travail technique sur des fixtures explicites.

## 11. Résilience et budgets

Brain reste dans le monolithe avec une file dédiée `brain_analysis` et des ressources d’exécution isolées des workflows terrain. Réutiliser les mécanismes Houston appropriés : publication confirmée, état durable, recovery, permissions et journal d’usage.

Exigences :

- État durable avant publication ; récupération automatique des tâches non publiées ou abandonnées.
- Ownership des tentatives ; rejet des exécutions obsolètes et tolérance aux redeliveries.
- Finalisation atomique du résultat et des objets dérivés.
- Conservation du dossier et des résultats de lots coûteux validés nécessaires à la reprise, sans framework générique de checkpoints.
- Annulation committée avant finalisation : aucun résultat ni suggestion/objectif/mécanisme tardif publié.
- Finalisation déjà committée : indiquer « terminé », sans prétendre annuler rétroactivement.
- Coût éventuel d’un appel déjà engagé conservé dans l’audit.

Politique V1 : au plus une reprise automatique de l’analyse pour erreur réellement transitoire. Pas de retry pour correction utilisateur, permission, fichier invalide, budget fonctionnel ou couverture insuffisante. Les compteurs sont durables ; les redeliveries/republications ne réinitialisent pas le budget.

Une passe de correction du résultat principal est autorisée, sans nouvelle analyse ni suppression d’un sujet pour contourner une erreur. Le plan propose les règles des sorties intermédiaires et follow-ups, sans hériter automatiquement d’un retry supplémentaire à chaque étage. Tous les appels et corrections consomment le budget global concerné ; une reprise ne le remet pas à zéro. Désactiver ou maîtriser les retries fournisseur concurrents.

Garantir une seule publication métier, sans promettre un seul appel facturé en cas de crash à la frontière fournisseur/persistance.

Le moteur choisit automatiquement comment traiter le dossier dans ses limites. Privilégier un chemin simple quand il suffit ; proposer sélection contrôlée, lecture directe ou traitement par lots selon le volume et la qualité mesurée. « Tient dans la fenêtre du modèle » ne suffit pas à prouver qu’un unique appel est préférable. Aucun mode manuel ni nombre fixe d’appels n’est imposé. Préserver en-têtes, unités et relations lors d’une découpe. Les synthèses intermédiaires ne sont jamais de nouvelles preuves ; chaque conclusion remonte aux sources figées.

Les garde-fous configurables couvrent fichier décompressé, lignes/objets, mémoire, temps de collecte, tokens, nombre d’appels, cycles, coût et sortie finale. Un plafond technique est permis avec refus explicite ; aucune troncature silencieuse ni top-K global présenté comme exhaustif.

## 12. Performance, maintenabilité et montée en charge

Brain est une fonction centrale de commercialisation. Sa capacité doit être **mesurée**, pas déclarée sur la base d’un choix d’architecture. Aucun volume commercial, délai garanti ou coût cible n’a encore été fixé.

Le plan doit protéger :

- **Le terrain** : ressources de calcul séparées, connexions/requêtes DB bornées, aucun appel IA dans une longue transaction.
- **Les autres établissements** : admissions et concurrence maîtrisées ; un gros dossier ne monopolise pas toute la capacité.
- **La reprise** : étapes coûteuses conservées, publication idempotente.
- **L’évolution** : plusieurs workers/replicas possibles sans verrou métier local ni dépendance à un worker global unique.
- **La maintenance** : responsabilités lisibles, contrats versionnés, absence de clients API, règles RBAC ou moteurs métier concurrents.

Une file d’attente absorbe un pic temporaire, pas une saturation permanente. Définir capacité d’attente, refus explicites quand nécessaire, âge de file observable et prise en compte des limites fournisseur. Une limite par établissement ne remplace pas une limite globale. L’équité impose une politique d’admission/exécution bornée, pas nécessairement un ordonnanceur sophistiqué ou la préemption des lots dès V1. Le plan distingue le mécanisme minimal déployé des conditions mesurées qui justifieraient son évolution.

Chaque lecture croissant avec l’historique possède une stratégie bornée et justifiée. Éviter N+1, chargement intégral systématique et duplication de documents entre les représentations. Les optimisations de cache ne contournent ni droits, ni isolation, ni versions/snapshots.

Les follow-ups ne relancent pas toute la collecte. Leur orchestration doit éviter qu’ils contournent les budgets ou monopolisent le moteur, sans imposer d’avance une deuxième infrastructure.

**Mesures minimales :** attente, extraction/conversion, capture, IA, validation et durée totale ; distributions de latence dont p95 ; coût/appels/tokens ; mémoire maximale ; requêtes/temps DB ; backlog et âge ; échecs/reprises ; impact sur les fonctions terrain.

Tester dossiers petits et volumineux, historique dense, pics multi-établissements, dossier disproportionné, pannes fournisseur/broker/worker. Le plan propose des paliers de test et seuils d’acceptation justifiés, explicitement distincts d’une prévision commerciale. La capacité et la marge d’exploitation ne seront annoncées qu’après mesure.

## 13. Audit, conservation et confidentialité

Conserver les versions réellement utilisées : extraction, schémas, moteur pertinent, prompt, Knowledge, contexte établissement, modèle/configuration, ainsi que le dossier et le résultat. La reproductibilité signifie pouvoir retrouver les entrées et le traitement ; pas garantir une réponse IA identique bit à bit.

Les versions/contenus effectifs restent cohérents au cours d’une analyse, même si une configuration globale est activée pendant son exécution. Aucun catalogue de versions universel n’est exigé : Cursor choisit les identités/copies nécessaires à l’audit.

Tracer chaque appel et son usage disponible, y compris correction, échec et annulation. Différencier coût mesuré, estimé et inconnu. Un timeout sans métriques ne vaut pas zéro coût. Ne pas journaliser inutilement de contenu client ; intégrer le journal Houston existant.

**Décision validée : tant qu’une analyse reste proposée comme consultable, son dossier de preuves est conservé.** Ne pas purger automatiquement ses sources tout en promettant la même consultation et les mêmes follow-ups.

Le fichier original peut suivre une durée différente. Après sa suppression, ne plus promettre une réextraction ou un aperçu original ; conserver la représentation utilisée et les sources suffisantes à l’audit annoncé.

La suppression volontaire/applicable reste possible. Prévoir la purge cohérente des copies, preuves privées, contenus dérivés et fichiers selon la politique retenue. Si elle impose la disparition de sources nécessaires, retirer ou limiter explicitement les fonctions dépendantes ; ne pas substituer des objets vivants. La politique des sauvegardes, suppressions et droits correspondants doit être arrêtée avant production.

La disparition d’un objet terrain courant et une demande de purge de ses copies Brain sont des événements distincts : aucune cascade implicite ne doit décider de la politique. Le plan doit identifier ces dépendances, ainsi que celles entre reportings réutilisés, analyses, objectifs et Plans créés. Supprimer une analyse ne doit pas supprimer silencieusement un Plan Houston existant. Une vue résiduelle après purge éventuelle doit être signalée comme indisponible/incomplète, sans promettre l’audit et les follow-ups normaux.

Les durées chiffrées restent ouvertes ; aucune valeur de 30/90 jours ou autre ne doit être inventée comme décision produit. Les principes de dépendance et de suppression doivent être conçus maintenant.

SPORE conserve sa mémoire durable. Le choix d’API/configuration doit prendre en compte la rétention effective du fournisseur ; « stateless » n’est pas une promesse de zéro rétention. L’information utilisateur et le cadre applicable aux données envoyées doivent être validés avant usage client. Le développement peut avancer sur données fictives.

## 14. Restitution et intégration

Utiliser DRF, OpenAPI/types générés, client HTTP partagé, TanStack Query, navigation et composants SPORE existants. Pas de framework frontend parallèle.

La restitution doit rendre lisibles : reporting/période/capture, constats, interprétations, preuves, contradictions, limites, propositions et décisions. Ne pas exposer prompts privés, Knowledge interne ou métriques de lots comme justification métier.

Afficher les sources figées distinctement d’un éventuel lien vers l’objet actuel. Les noms, titres et périodes doivent être compréhensibles sans identifiants techniques.

Brain V1 est disponible sur ordinateur seulement. L’arbre partagé ne propose ni entrée ni interface Brain sur mobile web ou natif. Une URL Brain ouverte sur mobile affiche que la fonctionnalité est disponible sur ordinateur. Le polling desktop est acceptable ; aucune obligation de streaming ou de temps réel pour V1.

## 15. Recette obligatoire

Chaque scénario vérifie un comportement observable et la couche qui le garantit. Les tests techniques et l’évaluation métier IA sont distincts ; un juge IA seul ne valide pas la qualité.

| Cas | Résultat attendu |
|---|---|
| CSV/XLSX/DOCX/PDF textuel représentatifs | Mesures et locateurs corrects, aucune perte matérielle silencieuse |
| DOC | Refus avec consigne d’export DOCX ou PDF textuel |
| Scan ou chiffres uniquement en image | Limite signalée ; export exploitable demandé, pas d’OCR implicite |
| Formule sans valeur, colonne ambiguë, taux mal défini | Pas de chiffre inventé ; clarification/échec adapté |
| Mois contre cumul, HT contre TTC, ratios | Comparaison invalide refusée ; calculs vérifiés |
| Incident Maintenance pertinent pour Restauration | Recherche transverse et preuve retenue si pertinente |
| Signal pertinent sorti du feed | Présence dans la collecte analytique |
| Remontées agrégées et Plan lié | Pas de faux incidents ni preuves indépendantes artificielles |
| Déclaration tardive, résolution après période | Temporalité correctement distinguée |
| Aucun fait terrain ou N-1 absent | Limite explicite sans causalité inventée ni échec injustifié |
| Contradiction et instructions hostiles dans le fichier | Contradiction conservée ; instructions sans autorité |
| Lot requis échoué/budget dépassé | Pas de faux COMPLETED |
| Double lancement, broker indisponible, worker interrompu | État durable, reprise bornée, pas de double publication |
| Import abandonné, document vide ou échec de préparation | Aucun faux succès ni travail actif bloqué indéfiniment ; nettoyage défini |
| Annulation/finalisation concurrentes | Résultat conforme à l’ordre des commits |
| Ancien worker termine après reprise | Publication rejetée |
| Follow-up explicatif/hypothétique | Même dossier, hypothèses étiquetées |
| Nouveau fait/document dans le follow-up | Réanalyse proposée, jamais lancée automatiquement |
| Questions simultanées ou répétées, longue conversation | Ordre et contexte explicites ; pas de réponse dupliquée ni perte silencieuse de preuve requise |
| Double conversion, responsable devenu inactif | Aucun doublon ; règles actuelles vérifiées |
| Plan terminé, KPI non atteint/non mesurable | Décisions et évaluations indépendantes |
| Deux dirigeants modifient une suggestion/un objectif ; ancien bilan exécuté tardivement | Conflit détecté ; aucune décision récente écrasée silencieusement |
| Approbation d’un mécanisme | Aucune activation automatique ni fuite client |
| Révocation d’accès/cross-établissement | Refus effectif, y compris sources historiques |
| Auteur révoqué, établissement inactif ou configuration changée pendant traitement | Politique explicite, pas de changement silencieux d’acteur ou de dossier |
| Suppression original/dossier | Capacités et conservation conformes aux dépendances |
| Pics multi-établissements et gros dossiers | Limites, équité et impact terrain mesurés |
| Navigation mobile ou native, y compris grand écran | Aucune entrée Brain |
| URL Brain ouverte sur mobile | Message de disponibilité sur ordinateur ; pas d’interface d’analyse |

Constituer avant recette commerciale un corpus de documents réels anonymisés ou représentatifs, avec mesures attendues, preuves importantes, conclusions interdites et actions acceptables. Aucun fichier représentatif n’a été fourni à ce stade ; la fiabilité documentaire n’est donc pas encore validée.

## 16. Paramètres ouverts et sortie attendue de Cursor

Ne pas inventer comme décisions validées :

- modèle exact et paramètres ;
- bibliothèques d’extraction/conversion et conditions précises des formats ;
- budgets, concurrence, timeouts et objectifs de latence/coût ;
- durées de conservation et politique détaillée de suppression/sauvegarde ;
- cadre d’information/traitement fournisseur ;
- accès plateforme aux preuves privées.

Cursor doit proposer les choix techniques nécessaires au plan, distinguer hypothèses et décisions produit, et classer les points ouverts selon leur effet réel. Pas d’infrastructure spéculative, de promesse de capacité sans benchmark ou de réduction silencieuse du périmètre.

| Point encore ouvert | Attendu avant la phase concernée |
|---|---|
| Correction déclarative, nouveaux objets décisionnels en follow-up, traitement en cours après révocation | Proposition fonctionnelle explicite dans le plan ; arbitrage avant implémentation du parcours concerné |
| Accès plateforme aux preuves privées | Décision d’accès avant implémentation d’une revue qui en dépend ; aucune autorisation implicite |
| Suppression/rétention détaillée | Dépendances et comportement proposés dans le plan ; rôles, durées et purge arrêtés avant mise en production |
| Modèle, parsing, budgets, concurrence, stockage | Choix techniques proposés et validés selon le repo, le corpus et les mesures ; pas de question produit artificielle pour chaque détail |
| Documents représentatifs et Knowledge métier privé | Nécessaires à la recette métier et aux engagements commerciaux ; fixtures explicites pour avancer avant leur disponibilité |

Ces points ne doivent pas être résolus silencieusement par une hypothèse. Ils n’empêchent pas de produire le plan, mais le plan doit exposer leurs conséquences et dépendances. Ne pas inventer d’écran d’édition universel, de moteur de correction ou d’autorisation pour remplir un blanc.

**Le plan attendu comprend :**

1. État réel du repo et matrice du patch : réutiliser, adapter, retirer, manquant.
2. Architecture proposée et justification des frontières de collecte, capture, tentatives et finalisation.
3. Contrats de lecture documentaire, données analytiques, API et sorties IA.
4. Lots ordonnés et vérifiables ; pour chacun : objectif, code réel concerné, backend/frontend, migrations nécessaires, tests, risques et validation.
5. Scénarios de charge, instruments de mesure, seuils proposés et protection du terrain.
6. Correspondance entre exigences du présent document et validations prévues.
7. Questions humaines restantes uniquement lorsque le repo et le présent cadrage ne permettent pas de décider.

Pour chaque choix structurant non imposé, donner la solution retenue, le besoin qu’elle couvre, ses limites et une alternative seulement si elle constitue un vrai arbitrage. Le plan doit aussi indiquer ce qu’il n’est pas nécessaire de construire en V1. Une recommandation de la revue antérieure ne devient pas une obligation technique en l’absence de cette justification.

Le plan doit notamment corriger les écarts identifiés dans le prototype : collecte via feeds, sources interdites, multi-fichiers par Conversation, actualisation des follow-ups, couplage Plan/KPI, activation immédiate du Knowledge, autorisation Brain parallèle, absence de la résilience et de l’audit cibles.

**Ne pas commencer l’implémentation à la livraison du plan.**

