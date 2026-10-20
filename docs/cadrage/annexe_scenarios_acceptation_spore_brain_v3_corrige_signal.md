# SPORE Brain — Annexe de recette fonctionnelle (V3 candidate)

**Statut :** candidate à validation métier et technique conjointe, construite après D1/D2 validés et réponses de Maxime du 16 octobre 2026.  
**Référence fonctionnelle candidate :** `cadrage_fonctionnel_spore_brain_cible_v3_corrige_signal.md`.  
**Sources de travail :** annexe V2, audit d'alignement, recette MAMA SHELTER, `Prompt 6_10.docx` et `Spore-Referentiel.json`.  
**Portée :** comportement métier et résultats vérifiables, sans prescrire de technique de recherche, architecture, volume de contexte, modèle ou nombre d'appels.

## 1. Verdict critique sur l'annexe V1

L'annexe V1 identifie correctement les cinq risques principaux, mais **ne suffit pas pour prononcer une acceptation produit** : ses données sont encore trop peu spécifiées, ses formules (« suffisamment pertinent », « conclusion étayée », « au besoin ») risquent de permettre à deux évaluateurs de juger différemment le même résultat ; les scénarios n'éprouvent pas réellement la récupération d'une preuve inattendue ; et la notion de publication partielle permet potentiellement de requalifier n'importe quel échec de recherche en succès. Elle couvre mal la qualité du reporting, les décisions/objectifs, les restrictions d'accès et la concurrence entre responsables.

Cette version conserve dix scénarios de la V2, en corrige les incohérences avec D1/D2 désormais validés, et ajoute cinq scénarios de raisonnement métier issus des réponses de Maxime. Les cas exposés dans le prompt ou le référentiel sont utilisables pour le développement et la vérification du comportement, mais une évaluation indépendante exige des variantes inédites réservées, avec attendus validés avant exécution.

### Règle de préparation de chaque jeu d'essai

Avant le test, constituer un dossier de recette contrôlé comprenant :

1. **Un reporting de référence**, avec période, établissement, libellés, unités, sources et toutes les variations significatives attendues ; quand les chiffres de test sont arbitraires, ne pas les transformer en seuils génériques.
2. **Un référentiel des éléments témoins**, chacun avec identifiant de recette, dates, pôle, type de source, provenance, éventuelle autorisation, et relation attendue avec les sujets : `indispensable`, `contradictoire`, `contexte utile`, `non pertinent`, `interdit`, ou `inconnu / non concluable`.
3. **Les pièges intentionnels** : ancien statut désormais modifié, homonymie, changement de définition de KPI, événement hors période, relation inter-pôles, indisponibilité d'une source, hypothèse passée réfutée.
4. **Un résultat attendu vérifiable**, incluant les sujets à restituer, faits incontournables, limites devant être explicitées, actions interdites, qualification éventuelle *complet/partiel/refus*, et les conditions empêchant la publication d'une conclusion donnée.
5. **Une grille contradictoire d'évaluation**, indiquant non seulement ce que Brain a trouvé, mais aussi ce qu'il a raté, affirmé sans preuve, ou laissé de côté sans l'indiquer. L'évaluateur peut consulter les données témoins hors de Brain ; Brain ne peut pas s'auto-certifier pertinent.

Ces éléments sont à fournir à l'équipe chargée de la recette ; ils ne doivent pas être présentés à Brain comme une liste de bonnes réponses. **La préparation du jeu d'essai n'autorise pas une sélection technique imposée à l'utilisateur final.**

### Règles de verdict communes

- **Réussite :** les constats et limites sont compatibles avec les faits témoins, les éléments déterminants accessibles et pertinents sont pris en compte, et aucun comportement interdit n'est observé.
- **Échec fonctionnel :** une affirmation injustifiée est publiée, une contradiction déterminante et accessible du scénario est manquée sans réserve appropriée, une donnée interdite est révélée, une décision est exécutée sans validation, ou une analyse est qualifiée à tort de complète.
- **Résultat limité mais maîtrisé :** si Brain ne peut pas achever un examen, il déclare précisément l'insuffisance et n'affirme pas avoir vérifié les éléments manquants. Ce résultat n'est pas automatiquement une *réussite* du scénario : le scénario précise si une publication partielle est attendue ou si le moteur doit être considéré comme incapable de rendre le service attendu.
- **Indicateurs à relever sans seuil universel :** sujets identifiés/manqués, témoins indispensables retrouvés/manqués, contradictions examinées/manquées, comparaisons justifiées/non comparables, couverture déclarée, statut de publication, provenance des conclusions, volume relatif de contexte mobilisé et raison d'arrêt. Des objectifs mesurables de performance et de coût seront définis ensuite à partir des contraintes réelles, sans déguiser une préférence technique en critère fonctionnel.

## 2. Cinq scénarios fondamentaux renforcés

### SC-01 — Reporting court, historique massif, preuve décisive inter-pôles

**Situation.** Un reporting de restauration portant sur sept jours indique une diminution de fréquentation. L'établissement possède plusieurs années de signaux, plans et exécutions, majoritairement sans rapport avec ce sujet.

**Témoins à préparer (fictifs, mais déterministes).**
- `R-01` : baisse de fréquentation restauration pour la période confirmée.
- `S-01` : incidents de service en restauration pendant seulement une partie de la semaine, hypothèse possible mais non suffisante.
- `S-02` : baisse datée des clients hébergés ou des événements du site, issue d'un **autre pôle** et concordant davantage avec la période de baisse de fréquentation ; ce fait constitue une piste concurrente indispensable à examiner, **pas une causalité démontrée**.
- `P-01` : plan lancé à la fin de la période, ne pouvant expliquer rétrospectivement les journées antérieures.
- `D-01…D-n` : événements anciens, sans relation connue, ajoutés en grand nombre comme distracteurs.

**Attendus vérifiables.** Brain identifie le sujet, examine les pistes `S-01` **et** `S-02`, respecte les dates de `P-01`, justifie les éventuels antécédents retenus et n'assimile pas automatiquement le volume historique au périmètre nécessaire. Une piste peut rester incertaine. Une limitation empêchant de consulter `S-02` doit être explicite et empêcher toute conclusion exclusive en faveur de `S-01`.

**Échec.** Explication certaine par `S-01` seulement ; omission silencieuse de la piste inter-pôles déterminante ; conclusion fondée sur l'effet rétroactif de `P-01` ; refus automatique uniquement parce que `D-01…D-n` grossit ; affirmation d'avoir consulté toutes les sources.

**Essai différentiel indispensable.** Rejouer avec le même reporting et les mêmes témoins déterminants, puis augmenter massivement les distracteurs anciens sans lien. Les conclusions justifiées et l'accès aux témoins indispensables ne doivent pas se dégrader **du seul fait de ces distracteurs**. Noter les effets de coût/durée, sans choisir ici de seuil chiffré.

**Liens V2 :** AC-02, AC-03, AC-18, AC-19, AC-26.

### SC-02 — Trois sujets, résultats différents, comparaisons non homogènes

**Situation.** Un même reporting comporte une baisse, une amélioration et une stabilité inhabituelle susceptibles d'intéresser un dirigeant.

**Témoins.** `M-01` (baisse), `M-02` (amélioration), `M-03` (stabilité atypique documentée). Préparer des éléments terrain distincts ; pour `M-02`, rendre la comparaison historique discutable (périmètre, durée ou unité ayant changé) ; pour `M-03`, fournir une explication plausible mais non démontrée.

**Attendus vérifiables.** Les trois sujets restent visibles. Brain identifie la non-comparabilité de `M-02`, refuse de présenter une hausse calculée sur deux bases différentes comme une performance prouvée, et n'invente pas de cause pour `M-03`. Un sujet correctement investigué mais sans cause déterminable reste « non concluant » ; cela ne transforme pas automatiquement l'ensemble en analyse partielle.

**Échec.** Sélection du négatif uniquement ; faux calcul sur des bases incomparables ; causalité inventée pour `M-03` ; confusion entre *examiné mais non concluant* et *non examiné*.

**Liens V2 :** AC-01, AC-04, AC-18, AC-21.

### SC-03 — Hypothèse séduisante réfutée par la chronologie

**Situation.** Une baisse de performance et des incidents de service coexistent dans le reporting. Un lien paraît intuitif mais le détail temporel le fragilise.

**Témoins.** `H-01` incidents concentrés au début de la période ; `H-02` détérioration des résultats principalement à la fin ; `H-03` fait alternatif pertinent correspondant à cette seconde période ; `H-04` signal aujourd'hui résolu mais encore ouvert pendant la période étudiée.

**Attendus vérifiables.** La réponse distingue coïncidence, relation possible et causalité établie ; examine `H-02` et `H-03` avant d'attribuer la baisse aux incidents ; restitue le statut historique de `H-04` sans le remplacer par son statut courant. Les contradictions et pièces consultables sont rattachées au constat, non reléguées à une liste globale.

**Échec.** Votes à la majorité de sources, explication affirmative incompatible avec `H-02`, masquage de `H-03`, usage du statut actuel comme preuve historique.

**Liens V2 :** AC-03, AC-09, AC-18, AC-23.

### SC-04 — Capacité atteinte : distinction complète / partielle / refus

**Situation.** Trois sujets significatifs : `C-01` exploré et appuyé par des preuves robustes ; `C-02` effectivement exploré mais sans conclusion causale ; `C-03` non suffisamment exploré à cause d'une limitation identifiable.

**Variante A — publication partielle justifiée.** Les vérifications indispensables à `C-01` sont achevées ; aucune contradiction déterminante accessible dans le scénario ne reste non traitée. **Attendu :** qualification *partielle*, source et portée de `C-01` explicites, `C-02` marqué *non concluant*, `C-03` marqué *insuffisamment examiné*. Le résultat n'est pas déclaré complet ; le traitement terminé et sa qualification partielle ne sont pas confondus.

**Variante B — aucune conclusion publiable.** Les seules hypothèses explicatives sont non vérifiées et une contradiction déterminante reste inaccessible ou non traitée. **Attendu :** refus de publier une conclusion trompeuse avec motif compréhensible. Le constat d'échec n'est pas une analyse partielle déguisée.

**Variante C — *arbitrage PO ouvert*.** Brain n'a pu faire aucune investigation terrain mais peut reproduire fidèlement la baisse figurant dans le reporting. Le cadrage V2 permet sous conditions un constat factuel du reporting seul ; il ne fixe pas clairement la valeur minimale justifiant la publication d'une *analyse* sur ce seul fondement. **Ne pas transformer cette variante en critère de passage obligatoire avant décision PO.**

**Échec dans toutes les variantes.** Déclarer « complète » une couverture lacunaire ; requalifier automatiquement une erreur technique en succès partiel ; masquer un sujet significatif ; prétendre que les témoins non examinés sont sans importance ; annoncer une causalité sans preuve.

**Liens V2 :** AC-06, AC-07, AC-17, AC-21, AC-22, AC-23, AC-30.

### SC-05 — Mémoire, correction et réévaluation explicite

**Situation.** Une hypothèse a été rejetée dans une analyse ancienne et une décision humaine a suivi. Un nouveau reporting apporte un fait qui justifie de la réexaminer. Après publication, un utilisateur pose une question libre puis corrige une date importante.

**Témoins.** `A-01` hypothèse ancienne ; `A-02` motif documenté de son rejet ; `D-01` décision humaine et son état historique ; `N-01` fait nouveau daté ; `N-02` rectification apportée en conversation, non vérifiée lors de l'analyse initiale.

**Attendus vérifiables.** Brain sait rappeler `A-01`, `A-02` et `D-01` comme antécédents ; explique **pourquoi** `N-01` ouvre légitimement une nouvelle investigation ; ne présente pas les conclusions anciennes comme preuves ; répond à la question libre sans sélection de mode technique ; identifie `N-02` comme apport postérieur et demande le déclenchement explicite d'une réanalyse si cette correction change la conclusion. L'ancienne publication reste identifiable et inchangée.

**Échec.** Effacement de l'ancien rejet ; présentation de `D-01` comme décision toujours active sans vérification ; intégration silencieuse de `N-02` dans la publication passée ; nouvelle analyse, plan ou objectif déclenchés sans confirmation.

**Liens V2 :** AC-05, AC-10, AC-11, AC-27, AC-29, AC-31, AC-32.

## 3. Cinq scénarios complémentaires indispensables avant validation globale du produit

### SC-06 — Qualité d'entrée, comparaison trompeuse et reporting multisite

**Témoins.** Un indicateur comparé sur sept jours et cinq jours, ou dont la définition/unité a changé ; une seconde version du même fichier contenant deux établissements sans séparation exploitable ; un document avec donnée déterminante dans une image non lisible.

**Attendus.** Brain ne normalise ni n'interprète silencieusement des bases non comparables ; il signale la réserve et demande, lorsque nécessaire, une clarification de l'utilisateur avant de prétendre conclure. Un reporting multisite non séparable ne devient jamais un reporting monosité par supposition. Le contenu visuel illisible n'est pas inventé.

**Échec.** Affichage d'une amélioration trompeuse ; attribution arbitraire d'un site ; prétention d'avoir lu une donnée visuelle inaccessible.

**Liens V2 :** AC-18, AC-24, AC-25.

### SC-07 — Objectif incertain et plan déjà ouvert

**Témoins.** Une conclusion fondée et une proposition de plan équivalente à un plan ouvert ; un indicateur dont la période ou la base est trop incertaine pour fixer une cible chiffrée défendable ; un autre indicateur à définition stable permettant une proposition d'objectif vérifiable.

**Attendus.** Brain présente le plan similaire **avant** confirmation ; distingue une piste d'objectif insuffisamment définie d'une proposition vérifiable (mesure, cible, période, justification) ; permet modification/refus et ne crée rien sans validation humaine. L'objectif n'est pas fixé arbitrairement pour remplir une carte UI.

**Échec.** Doublon silencieux ; cible chiffrée fabriquée ; création de plan ou objectif à la publication.

**Liens V2 :** AC-13, AC-14, AC-31.

### SC-08 — Frontière d'accès et sources autorisées

**Témoins.** Deux établissements disposant de données semblables mais séparées ; un signal structuré autorisé ; des commentaires, transcriptions ou observations brutes attachés à l'événement mais exclus du périmètre de preuve ; un utilisateur dont les droits changent après publication.

**Attendus.** Aucun croisement entre établissements ni révélation des contenus exclus ; seuls le titre, la description et les métadonnées métier autorisées du Signal servent de référence pour l'événement ; les accès à une analyse passée et aux actions suivent les droits effectifs de l'utilisateur. Brain n'accède jamais à l'observation brute, y compris pour vérifier un détail ou résoudre une ambiguïté. Si le contrôle d'accès ou la provenance est incertain, aucune divulgation n'est acceptable.

**Échec.** Fuite directe ou indirecte (citation, résumé, recherche, conversation, lien), décision au-delà des habilitations.

**Liens V2 :** AC-20 et principes 3.6–3.8.

### SC-09 — Knowledge utile, absent, périmé ou non applicable

**Témoins.** Une connaissance active pertinente, une autre non activée, une règle active mais hors sujet, puis une évolution du référentiel après publication. Prévoir un cas où un mécanisme théorique semble plausible mais manque de preuve locale.

**Attendus.** Seules les connaissances actives pertinentes orientent l'interprétation ; une connaissance ne devient pas un fait terrain ; Brain n'invente pas d'autorité en cas de manque ; l'analyse passée conserve la référence de Knowledge utilisée, sans réécriture silencieuse.

**Échec.** Usage d'une connaissance non active ; présentation d'un mécanisme métier comme preuve de terrain ; modification rétroactive d'une conclusion.

**Liens V2 :** AC-12, AC-28.

### SC-10 — Demandes simultanées, reprise et annulation

**Témoins.** Deux responsables habilités demandent, presque simultanément, des analyses *différentes* pour le même établissement ; un utilisateur relance la *même* demande ; une analyse est annulée alors qu'elle est en cours.

**Attendus validés.** La reprise identique n'est pas présentée comme nouvelle ; les deux demandes distinctes sont acceptables et individuellement retrouvables, quitte à attendre ; une annulation ne provoque pas une publication tardive valide ; les utilisateurs retrouvent l'état réel.

**Décision produit D2 validée.** Deux demandes distinctes doivent pouvoir coexister, y compris en attente ; une seule exécution à la fois reste autorisée. Un doublon véritable est reconnu, sans créer un faux nouveau traitement. L'utilisateur voit le statut réel de chacune des demandes. La stratégie de capacité reste un choix d'implémentation.

**Échec.** Confusion des analyses entre responsables ; résultat substitué ; publication tardive après annulation ; fausse confirmation de lancement.

**Liens V2 :** AC-15, AC-16, AC-30 et §4.1.

## 4. Recette : comment éviter le « tout est vert » trompeur

### Ordre conseillé

1. **Revue des jeux d'essai sans lancer Brain** : cohérence des dates, des sources, des droits et des témoins ; distinguer les faits incontournables des hypothèses seulement plausibles.
2. **Exécution en boîte noire** : présenter au produit les seuls éléments que posséderait réellement l'utilisateur, sans lui fournir la grille des bonnes réponses.
3. **Évaluation contradictoire** : comparer les résultats aux éléments témoins, y compris contradictoires et inattendus ; un résultat élégant mais incomplet ne vaut pas réussite.
4. **Tests différentiels** : faire varier seulement un élément à la fois — ajout de distracteurs, contradiction, date, droit d'accès, correction nouvelle — pour vérifier l'effet observable sur le résultat.
5. **Décision de recette** : classer chaque scénario `réussi`, `échoué`, `limité mais correctement signalé` ou `bloqué par arbitrage PO`. Seuls les cas réussis démontrent la capacité attendue ; un refus correctement signalé est sûr, mais ne prouve pas à lui seul que Brain remplit sa mission d'investigation.

### Ce que cette annexe ne prétend pas garantir

Aucun assistant ne peut prouver qu'il n'existe **aucune** preuve pertinente dans un historique qu'il n'a pas entièrement examiné. La promesse réaliste est une recherche justifiable, des obligations de couverture métier, des vérifications anti-contradiction adaptées aux conclusions et des limites déclarées. Les données témoins de recette rendent ces engagements vérifiables dans un environnement contrôlé ; elles ne définissent pas un algorithme ou un score universel de « pertinence ».

## 5. Cinq scénarios métier supplémentaires issus du retour de Maxime

Ces cas servent de **spécifications de résultat**. Leur formulation étant désormais connue, ils constituent des contrôles de développement ; préparer des variantes inédites et réservées pour mesurer la généralisation du modèle.

### SC-11 — Fidélité du Signal et origine déclarative

**Données de référence.** Le **Signal structuré** contient, dans son titre et sa description, le fait rapporté suivant : « Au déjeuner, trois tables ont renoncé au dessert en raison d'une attente jugée trop longue. » Les métadonnées autorisées portent la provenance et les dates disponibles. Prévoir une variante avec plusieurs faits rapportés et une date de survenue différente de la date de saisie. L'observation initiale n'est pas une entrée de Brain ni une ressource consultable pendant cette recette.

**Attendus.** Brain se fonde sur le titre, la description et les métadonnées métier autorisées du Signal, distingue les trois renoncements **rapportés** de toute causalité démontrée, et respecte les dates disponibles. Il ne consulte jamais l'observation initiale. Si une précision n'apparaît pas dans le Signal, il la considère comme non établie et ne l'invente pas.

**Échec.** Consultation directe ou indirecte de l'observation brute ; complément du Signal avec un détail absent obtenu hors des sources métier autorisées ; confusion entre témoignage et causalité démontrée ; date de création présentée sans réserve comme date du fait.

**Note de qualification.** Un test en production a confirmé, sur le cas vérifié par le référent technique, la fidélité du titre et de la description du Signal. La recette Brain ne doit pas recréer un accès au brut pour contrôler cette fidélité ; d'éventuels tests propres au pipeline restent distincts du périmètre Brain.

### SC-12 — Arithmétique prouvée et cause terrain non prouvée

**Données de référence.** CA restauration −12 %, couverts −12 %, panier moyen stable sur deux périodes comparables ; des Signaux relatent une attente excessive au déjeuner. Aucun fait n'établit de diminution de fréquentation *à cause* de l'attente.

**Attendus.** Brain montre que la diminution de couverts rend compte arithmétiquement de l'évolution du CA, sous les hypothèses de comparabilité ; il ne présente pas l'attente comme la cause démontrée. Il vérifie les facteurs de fréquentation effectivement disponibles (jours d'ouverture, réservations/annulations, disparités par service et autres faits pertinents), indique ce qui manque, et peut proposer une correction réversible de l'attente **pour ce problème constaté**, sans promettre un rétablissement de fréquentation.

**Échec.** « Le CA baisse à cause de l'attente » sans preuves, aucune autre piste examinée malgré des indices disponibles, ou refus d'une décomposition chiffrée utile au seul motif que la cause opérationnelle reste inconnue.

### SC-13 — Formule promotionnelle : popularité et intérêt économique distincts

**Données de référence.** Deux semaines après une formule déjeuner à prix réduit : panier moyen −8 %, fréquentation stable, quelques retours positifs ; inconnues sur le remplissage par service, la substitution des offres, la marge contributive et les nouveaux clients. M-REST-002 constitue une hypothèse métier applicable sous conditions.

**Attendus.** Brain ne recommande pas immédiatement le maintien ou l'arrêt de la formule. Il priorise les informations discriminantes, reconnaît qu'une fréquentation stable n'exclut pas un effet de compensation, et suggère une courte vérification puis, si justifié, un test ciblé et daté (offre, créneau ou communication), avec bilan. Les coûts et substitutions sont pris en compte avant une décision durable.

**Échec.** « Les clients aiment donc c'est rentable », « les couverts sont stables donc la promotion est inutile », ou reprise des chiffres d'un mécanisme fictif comme données de l'établissement.

### SC-14 — Aucun délai de référence : proposer une mesure, pas une cible inventée

**Données de référence.** Des Signaux documentent des attentes au déjeuner, mais aucune mesure fiable du délai entre commande et service n'est disponible. Un changement de répartition des heures est envisagé sans certitude sur son effet.

**Attendus.** Brain propose d'établir une référence sur des déjeuners représentatifs, puis de mesurer un test sur des services comparables avant de fixer une amélioration chiffrée. Il peut suggérer délai médian, attentes extrêmes et renoncements, ainsi que les vigilances pertinentes : heures/coût par couvert, qualité, erreurs, charge des équipes et effets sur les autres créneaux. Les durées ou effectifs cités dans le cas restent des exemples, pas des règles universelles.

**Échec.** Cible chiffrée arbitraire présentée comme validée, confusion date de l'action/date du bilan ou objectif automatique sans décision humaine.

### SC-15 — Knowledge expert, origine synthétique et efficacité non démontrée

**Données de référence.** Le mécanisme M-REST-001 est expert-validé sur un cas fictif ; aucun résultat terrain vérifié. Un établissement montre un panier moyen en baisse et des attentes, mais aucune donnée sur l'affectation du personnel aux créneaux.

**Attendus.** Brain expose une hypothèse conditionnelle et les vérifications utiles (couverture effective, affluence par créneau, éventuelles alternatives). Il ne prescrit pas automatiquement des renforts. Un test limité est envisageable uniquement si les faits réunis le rendent pertinent et sous confirmation humaine. Le statut « validé par un expert » ne devient pas une preuve d'efficacité. Un résultat réel ultérieur reste contextualisé et ne prouve pas un effet causal universel.

**Échec.** Renfort automatique, gains promis, assimilation de l'avis expert à un résultat empirique ou transposition sans justification à un autre secteur.

## 6. Décisions produit intégrées, sans nouveau chantier d'arbitrage

- **D1 — Analyses partielles : validé.** Une investigation publiée doit apporter une valeur analytique vérifiable. Une décomposition chiffrée pertinente peut suffire sans cause opérationnelle établie ; une simple paraphrase ne suffit pas. Les scénarios SC-04 et SC-12 en éprouvent la distinction.
- **D2 — Coexistence de demandes : validé.** Les analyses distinctes peuvent coexister dans un établissement, éventuellement en attente ; l'exécution parallèle n'est pas obligatoire. SC-10 en vérifie le comportement.
- **Signal canonique : confirmé par le référent technique.** Le titre et la description du Signal font foi pour Brain, avec ses métadonnées métier autorisées. **Aucun accès aux observations brutes n'est autorisé dans Brain, même exceptionnellement.** SC-08 et SC-11 vérifient explicitement cette frontière. La qualité de transformation du pipeline relève d'une recette distincte, hors Brain.

## 7. Points de qualification de recette — sans choix technique imposé

1. Constituer au moins une variante inédite et réservée des scénarios SC-11 à SC-15 ; ne pas utiliser C01/C02 déjà exposés pour mesurer une performance indépendante.
2. Valider avant exécution les faits témoins, la provenance, les comparaisons de KPI et les actions acceptables/interdites.
3. Conserver les statuts `réussi`, `échoué`, `limité mais correctement signalé` et `bloqué par arbitrage PO` ; une limitation bien affichée n'est pas automatiquement une réussite.
4. Mesurer séparément exactitude et comparabilité des calculs, fidélité des sources, découverte des preuves pertinentes, traitement des contradictions, prudence causale, utilité économique de la recommandation et absence d'actions automatiques.
5. Ne pas présupposer le type de moteur de recherche, le nombre d'appels IA ou les mécanismes de plafonnement.

---

**Note de validation :** cette annexe V3 transpose les décisions D1/D2 et les cinq réponses métier de Maxime. Elle reste une proposition à faire approuver conjointement avant de considérer la référence comme figée pour l'implémentation.
