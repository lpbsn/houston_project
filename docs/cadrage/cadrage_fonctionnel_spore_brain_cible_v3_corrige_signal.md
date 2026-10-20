# SPORE Brain — Cadrage fonctionnel cible

**Statut :** V3 candidate à validation conjointe produit/métier — consolide les arbitrages D1/D2 validés et les réponses métier de Maxime du 16 octobre 2026. Aucun choix de mise en œuvre technique imposé.  
**Périmètre :** expérience et comportements métier de SPORE Brain  
**Hors périmètre :** choix d'architecture, algorithmes, technologies, découpage des développements et détails de présentation de l'interface.

**Références d'interprétation :** les arbitrages fonctionnels validés et le cadrage métier priment sur les exemples visuels de la maquette en cas de divergence. La maquette exprime l'expérience recherchée, sans autoriser l'accès à des données exclues par les règles métier. Les constats de l'audit décrivent l'existant, et ne constituent pas à eux seuls des exigences cibles.

**Frontière de ce cadrage :** il décrit l'analyse de reportings d'un établissement et les échanges, recherches et décisions qui en découlent. Il ne crée pas implicitement un assistant généraliste capable de répondre à toute question indépendante d'un reporting.

## 1. Finalité

SPORE Brain est un assistant d'investigation opérationnelle destiné à aider les responsables d'un établissement à comprendre leurs reportings à la lumière des faits terrain, de l'historique pertinent, des connaissances validées et des décisions antérieures.

Brain doit :
- identifier les sujets significatifs, qu'ils traduisent une dégradation, une amélioration, une stabilité notable ou une contradiction ;
- rechercher et confronter les informations utiles, sans obliger l'utilisateur à choisir les données techniques à consulter ;
- distinguer faits, calculs, interprétations, hypothèses et incertitudes ;
- produire des conclusions compréhensibles, vérifiables et actionnables ;
- permettre à l'utilisateur de questionner, corriger et approfondir l'analyse ;
- suggérer des investigations, plans d'action et objectifs, sans décision ni création opérationnelle automatique.

**Principe structurant :** les données métier autorisées de l'établissement constituent les ressources de l'investigation. Pour les faits issus des remontées terrain, Brain utilise les Signaux structurés, jamais les observations brutes. Les ressources métier disponibles ne doivent pas être intégrées systématiquement à chaque analyse. L'exhaustivité et la traçabilité s'appliquent au périmètre effectivement examiné, qui doit être explicite.

## 2. Périmètre et vocabulaire métier

- **Établissement :** entité à laquelle appartiennent les données et les décisions étudiées. Une analyse ne mélange pas silencieusement plusieurs établissements.
- **Reporting :** document apporté par l'utilisateur, associé à une période confirmée, contenant des mesures et/ou des éléments qualitatifs.
- **Sujet significatif :** mesure, évolution, fait qualitatif, stabilité notable ou contradiction du reporting dont l'examen peut modifier la compréhension ou une décision ; sa significativité ne se réduit pas à un seuil chiffré ou à un écart négatif.
- **Couverture d'un sujet :** examen suffisamment documenté pour distinguer ce qui est établi, non concluant et encore à rechercher ; elle n'implique pas la lecture de chaque donnée disponible.
- **Donnée découverte / examinée / retenue :** donnée respectivement repérée comme candidate, effectivement prise en compte pour examiner un sujet, puis éventuellement citée ou mobilisée dans un constat. Ces étapes ne doivent pas être confondues dans la restitution.
- **Observation brute :** expression ou média d'origine traité par le pipeline SPORE. Ce n'est pas une source de Brain et Brain n'y accède pas, ni directement ni comme recherche complémentaire.
- **Signal structuré :** objet métier issu du pipeline et source faisant foi pour les faits terrain exploités par Brain. Son **titre et sa description** constituent le contenu sémantique de référence ; les métadonnées métier autorisées apportent la date, la provenance, le périmètre et les rattachements. Brain ne doit pas compléter ou corriger ce contenu à partir de l'observation brute.
- **Fait rapporté / cause déclarée :** un propos consigné dans un Signal peut établir qu'un témoin a *rapporté* un fait ou une explication ; il ne transforme pas cette explication en causalité indépendante démontrée.
- **Données terrain :** informations métier structurées et autorisées, notamment Signaux, plans et exécutions, nécessaires pour examiner un sujet. Brain utilise exclusivement le Signal pour comprendre une remontée terrain ; les observations brutes ne font pas partie de ses sources.
- **Historique pertinent :** faits, comparaisons, événements et décisions antérieurs utiles pour comprendre la période analysée ; sa profondeur dépend du sujet.
- **Knowledge :** connaissances métier validées, distinctes des faits propres à l'établissement. Elles orientent l'interprétation mais ne constituent pas à elles seules une preuve terrain.
- **Constat :** proposition descriptive étayée par le reporting ou des faits vérifiables.
- **Hypothèse :** explication possible, présentée comme telle et confrontée aux éléments disponibles.
- **Conclusion suffisamment étayée :** constat ou interprétation utile dont les sources accessibles, la méthode de lecture et les limites permettent une utilisation responsable ; une contradiction importante identifiée mais non examinée interdit une conclusion affirmative qui en dépend.
- **Sujet non concluant :** sujet effectivement examiné mais pour lequel aucune explication fiable n'est établie. Il se distingue d'un sujet non examiné faute de capacité, d'accès ou de disponibilité.
- **Analyse partielle :** résultat qui apporte des conclusions suffisamment étayées sur une partie des sujets, tout en indiquant clairement ce qui n'a pas pu être examiné ou conclu.
- **Déclaration nouvelle :** fait, rectification ou document apporté après une analyse, susceptible de changer le contexte sur lequel reposent ses conclusions.
- **Mémoire décisionnelle :** trace des hypothèses, décisions et suites d'analyses antérieures, consultée pour contextualiser un nouvel examen, sans valeur de preuve terrain autonome.

## 3. Principes non négociables

1. **Pertinence et absence d'angle mort trompeur.** Brain couvre initialement tous les sujets significatifs et recherche activement les informations susceptibles de contredire les explications envisagées.
2. **Périmètre compréhensible.** L'utilisateur peut connaître les sujets examinés, les familles de sources et périodes consultées, ainsi que les limites ou exclusions significatives. Cela n'impose pas un inventaire individuel de toutes les données non consultées de l'établissement.
3. **Pas d'omission silencieuse.** Une recherche limitée, une source inaccessible ou un sujet non approfondi ne sont jamais présentés comme traités exhaustivement. Les exclusions ou limites susceptibles de changer une conclusion sont rendues visibles avec leur motif intelligible.
4. **Traçabilité.** Une affirmation factuelle ou chiffrée importante peut être rapprochée de ses sources ; une hypothèse n'est jamais présentée comme un fait établi.
5. **Temporalité correcte.** Les faits et états de la période étudiée sont distingués des événements ou statuts postérieurs.
6. **Décision humaine.** Aucun plan, objectif, activation de Knowledge ou autre engagement opérationnel n'est adopté automatiquement à partir d'une analyse.
7. **Confidentialité et autorisations.** L'accès aux données et aux actions reste limité aux établissements et personnes habilités.
8. **Continuité maîtrisée.** Une analyse publiée conserve son périmètre, ses sources de référence, ses conclusions et leur statut ; un changement ultérieur des données, du Knowledge ou des décisions ne les réécrit pas silencieusement.
9. **Limites explicites.** Lorsque la qualité minimale ne peut être garantie, Brain refuse de publier une conclusion plutôt que de fabriquer une certitude.
10. **Distinction des états.** Le statut du traitement (en attente, en cours, terminé, annulé ou en échec) et la qualification du résultat publié (complet ou partiel) désignent deux notions différentes. Une analyse refusée n'est pas une analyse partielle publiée.
11. **Valeur analytique démontrable.** Une simple paraphrase du reporting n'est jamais présentée comme une investigation réussie. Une décomposition chiffrée vérifiée peut constituer une contribution utile même si la cause opérationnelle demeure inconnue.
12. **Indépendance du raisonnement.** Les méthodes métier et mécanismes de Knowledge orientent l'analyse sans transformer des exemples fictifs, des témoignages ou des corrélations en faits avérés pour cet établissement.

## 4. Parcours d'analyse d'un reporting

### 4.1 Préparation et déclenchement

- L'utilisateur fournit un reporting à analyser pour son établissement. Un document fourni correspond à un reporting ; les formats prévus sont CSV, XLSX, PDF à texte exploitable et DOCX. Le format DOC ancien n'est pas pris en charge. Les éléments visuels ou non lisibles ne sont pas présentés comme ayant été extraits ; les limitations de lecture et les refus doivent être compréhensibles.
- Le reporting et la période couverte sont rendus compréhensibles et confirmés avant lancement. Une période éventuellement reconnue dans le fichier reste soumise à confirmation ; son affichage utilise des dates métier compréhensibles et ne fait pas porter à l'utilisateur une convention technique de borne exclusive.
- L'analyse concerne un seul établissement. Un document manifestement multisite n'est pas arbitrairement attribué à l'établissement courant : si ses données ne peuvent pas être isolées et confirmées sans ambiguïté, le lancement est refusé avec une explication.
- L'import d'un document ne déclenche pas implicitement l'analyse.
- L'utilisateur lance explicitement **Analyser**, voit l'état du traitement, peut quitter l'écran et revenir au résultat.
- Plusieurs demandes distinctes d'analyse d'un même établissement peuvent coexister, y compris en attente. Elles restent individuellement identifiables et ne se remplacent pas silencieusement. Une demande effectivement identique est reconnue comme telle pour maîtriser les doublons.
- L'utilisateur connaît le statut réel de chaque demande, notamment lorsqu'elle est en attente. Le produit n'exige pas que plusieurs analyses s'exécutent simultanément ; la politique d'exécution et de capacité reste à concevoir.
- L'annulation est disponible tant que l'analyse n'a pas atteint un état terminal ; elle ne doit pas publier ensuite un résultat présenté comme valide.

### 4.2 Compréhension initiale

Brain examine le reporting afin d'identifier :
- toutes les mesures et informations qualitatives significatives du reporting, positives ou négatives ;
- les changements, tendances, comparaisons et situations inhabituelles ;
- les sujets qui nécessitent une explication terrain ;
- les contradictions internes, lacunes documentaires et incertitudes initiales.

La compréhension initiale vérifie, lorsque disponibles, les définitions et conditions de comparaison des mesures : périodes, jours d'ouverture, unité, périmètre et pôle, réalisé/budget/prévision, HT/TTC et changements éventuels de méthode. Une comparaison non valable n'est ni présentée comme une évolution fiable, ni corrigée par une supposition.

La compréhension initiale couvre le reporting dans son ensemble, y compris ses éléments qualitatifs, sans réduire par défaut l'analyse aux indicateurs les plus spectaculaires. Un sujet secondaire peut rester traité à un niveau plus léger, mais ne doit pas disparaître sans indication si son importance pour l'analyse est réelle. Si l'identification de tous les sujets est incertaine, cette limite doit être déclarée plutôt que de revendiquer une couverture complète.

### 4.3 Recherche progressive du contexte

- Brain effectue une **couverture initiale suffisamment large** pour considérer chaque sujet significatif, repérer des liens métier plausibles et rechercher activement des éléments inattendus ou contradictoires. Cette exploration peut conclure qu'une catégorie de données n'apporte aucun élément utile ; ce constat n'équivaut pas à une vérification exhaustive de toute cette catégorie.
- Il approfondit ensuite les sujets et hypothèses qui le justifient, en tenant compte de leur importance, de l'incertitude restante et de la valeur attendue des informations supplémentaires. Une hypothèse séduisante ne doit pas exclure les pistes concurrentes pertinentes.
- Le choix des données pertinentes appartient à Brain dans le cadre des autorisations et règles métier ; l'utilisateur n'a pas à choisir tables, catégories, requêtes ou fenêtres techniques.
- Les données retenues peuvent inclure faits contemporains, précédents comparables, événements récurrents, décisions, plans et résultats antérieurs.
- Les informations qui contredisent une hypothèse restent éligibles à l'examen.
- Une information non consultée ne peut pas être utilisée comme preuve et ne doit pas être présentée comme ayant été vérifiée. Une information consultée mais non mobilisée ne doit pas être citée comme appui d'une conclusion qu'elle n'étaye pas.
- Le périmètre de recherche doit rester intelligible : sujets, périodes, familles de sources consultées, et limites ou exclusions pertinentes pour l'interprétation. L'absence de résultat dans une recherche définie n'autorise pas à conclure à l'absence de tout phénomène dans l'établissement.
- Une limite de temps, de volume, de budget ou de disponibilité peut interrompre un approfondissement ; son effet sur la couverture et la fiabilité du résultat doit être explicité, sans sélection arbitraire des seules preuves favorables.

**Distinction essentielle :** une couverture initiale large ne signifie ni collecte exhaustive de tout l'établissement, ni examen intégral de chaque élément découvert.

### 4.4 Historique adaptatif

- La profondeur historique dépend de la nature des sujets : comparaison rapprochée, saisonnalité, répétition d'incidents, antécédents d'une action ou d'une décision.
- Aucune fenêtre fixe ne vaut universellement pour tous les reportings et sujets.
- Les périodes comparées sont identifiables et mises en perspective ; les différences de disponibilité ou de comparabilité des données sont signalées.
- Les événements survenus après la période étudiée servent au suivi et ne sont pas présentés comme des causes déjà établies pendant la période.
- Brain doit pouvoir retrouver des hypothèses, décisions et suites données aux analyses précédentes lorsqu'elles sont pertinentes et accessibles à l'utilisateur habilité.
- Une analyse passée fournit de la **mémoire décisionnelle**, non une preuve autonome. Une hypothèse écartée peut être réexaminée si des faits nouveaux le justifient ; le changement doit être expliqué. Une décision ancienne n'est pas présumée encore applicable, et les éléments devenus caducs ou révisés sont distingués.

### 4.5 Interprétation et qualité des conclusions

Pour chaque sujet traité, Brain distingue autant que nécessaire :
- ce que montre le reporting ;
- les faits terrain et calculs vérifiables ;
- les concordances et contradictions ;
- les interprétations et hypothèses ;
- les informations manquantes et les limites ;
- les suites possibles : action, investigation complémentaire ou absence d'action justifiée.

Brain sépare systématiquement :
- **l'explication arithmétique**, c'est-à-dire les composantes calculables d'une variation (volume, prix, fréquentation, panier, composition, etc.), dans la limite des mesures disponibles et comparables ;
- **l'explication opérationnelle**, qui relie éventuellement des faits terrain à cette variation et exige une portée, une chronologie et des preuves adaptées ;
- **la décision opérationnelle**, qui tient compte de l'incertitude, des plans existants, des ressources, des coûts, des effets secondaires et des indicateurs permettant d'évaluer le résultat.

Brain ne transforme pas une simple corrélation temporelle, une cause déclarée par un auteur ou une proximité de vocabulaire en causalité démontrée. Il peut exposer plusieurs explications plausibles et les éléments qui permettraient de les départager. Une correction limitée et réversible d'un problème opérationnel établi peut être proposée sans prétendre qu'elle résoudra une variation de KPI dont la cause reste inconnue.

Un plan réalisé ne prouve pas son efficacité. Une évolution positive après intervention ne constitue pas à elle seule la preuve que l'intervention l'a causée. Une décision peut être pertinente pour un pôle tout en ayant un coût ou un effet défavorable sur l'établissement : ces compromis doivent être signalés lorsqu'ils sont déterminants et documentés.

## 5. Analyse complète, partielle et refus

### 5.1 Analyse complète

Une analyse peut être qualifiée de **complète en couverture** lorsqu'elle a examiné suffisamment **tous les sujets significatifs identifiés** et réalisé les vérifications nécessaires à la fiabilité des constats publiés. Elle peut comporter des sujets *non concluants*, dès lors qu'ils ont été effectivement examinés et que cette absence de conclusion est explicite. « Complète » ne signifie ni que chaque sujet dispose d'une explication causale, ni que toutes les données historiques autorisées ont été lues.

Une analyse ne peut pas être qualifiée de complète lorsque l'identification des sujets significatifs ou l'examen d'une partie importante d'entre eux a été interrompu, ou qu'une incertitude non explorée pourrait invalider les constats principaux.

La complétude de couverture n’est pas, à elle seule, une preuve de valeur analytique : un résultat qui ne fait que paraphraser le reporting n’est pas présenté comme une investigation Brain réussie.

### 5.2 Analyse partielle publiée

Une analyse partielle peut être publiée si **au moins un résultat analytique utile, vérifiable et correctement qualifié** a été établi, si les contrôles indispensables à sa fiabilité ont été effectués et si les sujets non examinés ou non concluants sont explicitement distingués. Une **décomposition chiffrée qui éclaire réellement la performance** peut suffire, même si aucun Signal ne permet de démontrer une cause opérationnelle. En revanche, **une simple reformulation des chiffres du reporting ne suffit jamais** à qualifier une investigation réussie. Brain indique explicitement lorsque le terrain ne permet pas d'expliquer une variation.

La publication partielle n'est pas permise lorsqu'un sujet non examiné ou une contradiction potentiellement déterminante empêche de considérer les constats publiés comme fiables. Le simple fait d'avoir déjà traité quelques sujets ne suffit pas.

La restitution doit alors indiquer :
- les sujets couverts et les conclusions publiables ;
- les sujets non couverts ou insuffisamment étayés ;
- les limites de recherche ou de disponibilité et leurs conséquences ;
- les investigations ou informations nécessaires pour compléter l'analyse.

La qualification **partielle** doit être visible dans le résultat et dans l'historique. Brain ne généralise pas les conclusions publiables aux sujets restés ouverts.

### 5.3 Refus de publication

Si **aucun résultat analytique fiable et utile** ne peut être établi, ou si les vérifications indispensables aux conclusions envisagées ne sont pas possibles, Brain ne publie pas une analyse artificiellement rassurante. Une lecture factuelle peut rester présentée comme telle sans être qualifiée de succès de l'investigation. Brain distingue un refus pour données insuffisantes, impossibilité d'examen ou limite de capacité, et explique les prochaines actions utiles lorsque celles-ci peuvent être identifiées.

Un dépassement de capacité ou une source indisponible ne doit pas être confondu avec une absence de phénomène métier.

## 6. Restitution et lisibilité des preuves

L'expérience de résultat comporte :
- une **synthèse** hiérarchisant les sujets et enseignements importants ;
- des **constats détaillés** accessibles à la demande ;
- pour chaque constat, les preuves, calculs, contradictions, hypothèses, limites et orientations qui lui sont associés ;
- l'accès aux sources pertinentes, avec une identification intelligible de leur origine, de leur nature et de leur période ;
- une indication claire de la couverture de l'analyse et de son statut complet ou partiel.

La présentation évite d'exposer comme libellés principaux des codes internes, identifiants de pièces ou noms techniques de recherches. L'utilisateur peut accéder au détail nécessaire sans devoir reconstruire lui-même le raisonnement. Les preuves et contradictions sont rattachées aux constats concernés, plutôt que disponibles uniquement dans un inventaire global.

Les liens vers un élément opérationnel **actuel** sont distingués des copies ou états historiques qui fondent l'analyse. Les sources autorisées restent les données métier structurées. Pour un événement issu d'une remontée terrain, **le titre et la description du Signal structuré font foi** : Brain s'appuie sur ce contenu et ses métadonnées métier autorisées (provenance, dates, périmètre), sans consulter l'observation brute, y compris à titre exceptionnel. Les commentaires et transcriptions exclus du périmètre ne deviennent pas des sources supplémentaires. Si une précision ne figure pas dans le Signal ou les données métier autorisées, Brain la signale comme inconnue ou insuffisamment étayée ; il ne la reconstitue pas à partir du brut.

## 7. Conversation et approfondissements

- Chaque analyse possède un espace de conversation associé à son résultat et à son contexte de référence.
- L'utilisateur écrit naturellement dans un **champ de message libre**, avec des options contextuelles lorsqu'elles améliorent le parcours.
- Brain interprète une demande d'explication, une exploration d'hypothèse, une correction ou l'apport d'un fait/document nouveau sans imposer de catégorisation préalable. Si la portée du message est ambiguë et pourrait changer les conclusions, Brain demande une clarification plutôt que de deviner l'intention.
- Une demande d'explication peut s'appuyer sur le contexte et les preuves déjà examinés, en conservant leurs limites. Si la réponse exige des faits nouveaux ou une recherche non couverte par l'analyse, Brain le signale au lieu de prétendre les avoir vérifiés.
- Un fait nouveau, un document nouveau ou une correction matérielle peut être conservé comme apport à examiner, mais ne modifie pas silencieusement les conclusions publiées : Brain indique lorsqu'une nouvelle analyse est nécessaire et laisse son déclenchement à l'utilisateur. L'apport non encore vérifié reste identifiable comme tel.
- Les échanges restent intelligibles dans l'historique de l'analyse et distinguent les réponses fondées sur le dossier de référence des apports nouveaux non encore réexaminés.

## 8. Knowledge

- Brain peut s'appuyer sur plusieurs mécanismes métier **validés et actifs au moment de l'analyse**, lorsqu'ils sont pertinents pour le secteur, le sujet et les conditions documentées. Une nouvelle connaissance indépendante ne rend pas automatiquement inutilisable une autre connaissance déjà validée ; la révision d'un même mécanisme remplace sa version applicable selon les règles de validation. Les références utilisées restent identifiables dans l'analyse.
- Les connaissances servent à interpréter ou envisager des mécanismes, mais ne constituent pas à elles seules une preuve de ce qui s'est produit dans un établissement. Un mécanisme « validé par un expert » peut l'être sur la **cohérence de son raisonnement**, sans validation empirique de son efficacité. Son origine synthétique, ses conditions d'application, ses explications alternatives et les limites de preuve restent identifiables.
- Un mécanisme peut motiver une hypothèse, une vérification ciblée ou, si les faits le justifient, un test limité. Il ne permet pas de prescrire un renfort, un objectif chiffré ou une intervention simplement parce qu'il ressemble au cas examiné. Les résultats de terrain réellement mesurés et les contextes comparables permettent progressivement de préciser sa portée ; un succès isolé ne prouve pas une efficacité universelle.
- L'absence de Knowledge pertinent ou actif n'autorise ni invention de règles ni prétention à une expertise documentée inexistante.
- Les connaissances proposées par un utilisateur ne deviennent pas automatiquement des connaissances globales actives ; leur validation et leur activation sont des décisions distinctes.
- Le Knowledge dispose d'une **vue distincte au sein du module Brain**, séparée du fil de conversation principal.

## 9. Décisions, plans d'action et objectifs

### 9.1 Orientations

Brain peut recommander une action, une investigation ou l'absence d'action, avec sa justification et son niveau d'incertitude.

### 9.2 Plans d'action

- Une proposition de plan reste une **suggestion**, modifiable et refusable avant confirmation, clairement reliée aux constats et aux limites qui la motivent. Une information insuffisante peut justifier une enquête courte ou un test limité plutôt qu'une modification durable. Une action réversible visant un problème constaté peut être pertinente avant d'avoir prouvé un effet sur un KPI distinct.
- Les actions et plans existants potentiellement similaires sont portés à la connaissance de l'utilisateur **avant** la confirmation, pour éviter un doublon non intentionnel.
- La création effective passe par une décision explicite de l'utilisateur habilité, selon les règles métier habituelles de SPORE, notamment les responsabilités requises.
- Une suggestion déjà convertie ne provoque pas une seconde création silencieuse.

### 9.3 Objectifs

- Brain peut proposer un objectif lorsque les données permettent de définir **une mesure, une cible, une période et une justification compréhensibles**.
- En l'absence d'une référence de mesure suffisamment fiable, Brain propose d'abord un **objectif de mesure ou d'établissement d'une référence**, avec périmètre, période et méthode compréhensibles, puis une évaluation ou un objectif d'amélioration une fois cette référence disponible. Il ne fabrique ni valeur de départ ni cible justifiée fictive. Un seuil indicatif à discuter n'est jamais présenté comme une cible démontrée.
- La date de réalisation de l'action, la période d'observation de son effet et la date du bilan ne sont pas confondues. Lorsqu'une action peut déplacer des coûts ou dégrader un autre indicateur, Brain propose des indicateurs de vigilance appropriés.
- Une proposition insuffisamment définie est présentée comme piste à préciser, pas comme objectif chiffré prêt à accepter.
- L'utilisateur habilité peut examiner, modifier, accepter ou refuser une proposition. Si la modification change substantiellement la cible ou la période, l'objectif final correspond à la décision de l'utilisateur et non à une adoption implicite de la proposition initiale.
- Aucun objectif n'est créé ni modifié automatiquement par la seule publication d'une analyse.
- Les objectifs déjà décidés peuvent également être évalués au regard des données pertinentes.

## 10. Structure fonctionnelle du module Brain

- **Analyse / résultat :** lieu de consultation des conclusions et de leurs preuves.
- **Historique :** intégré à la page Brain, permettant de retrouver les analyses, leurs états de traitement, leur éventuelle qualification complète/partielle et leurs limites. Un refus, une annulation ou un traitement encore actif ne sont pas présentés comme des résultats publiés.
- **Conversation :** associée à l'analyse consultée ; champ libre et options contextuelles, sans catégorisation technique préalable imposée.
- **Knowledge :** vue distincte dans le module Brain, sans être mêlée au fil principal.
- **Propositions et décisions :** liées aux constats qui les justifient, avec leur état et les confirmations humaines nécessaires.

Ces éléments définissent les parcours et leur articulation, **pas** leur position exacte, leurs composants visuels ou leur navigation détaillée.

## 11. Gestion des cas limites

- **Reporting pauvre ou ambigu :** Brain explicite les éléments manquants ; il ne fabrique pas de comparaison ou de cause.
- **Reporting multisite ou période incertaine :** le périmètre est clarifié avant lancement ; un mélange non isolable de plusieurs établissements empêche l'analyse comme reporting d'un seul établissement.
- **Fichier partiellement lisible :** les contenus non exploités sont signalés avec leur incidence ; Brain ne revendique pas une couverture des éléments visuels ou illisibles.
- **Aucune donnée terrain pertinente :** une décomposition chiffrée peut conserver une valeur analytique, mais l'absence de corroboration terrain est visible ; elle ne devient ni une cause inventée ni une preuve d'absence d'incident. Une simple paraphrase n'est pas une analyse réussie.
- **Signal et observation initiale :** le titre et la description du Signal font foi pour Brain. Si une information décisive n'y figure pas, Brain ne retourne pas à l'observation brute : il qualifie ce qui manque et évite toute interprétation non fondée. La fidélité du pipeline de transformation est une exigence de qualité distincte, à contrôler en dehors du parcours Brain.
- **Sources contradictoires :** elles sont conservées et exposées ; Brain ne choisit pas silencieusement la version la plus favorable.
- **Historique insuffisant :** aucune comparaison non fondée n'est inventée ; la limite est indiquée.
- **Capacité insuffisante :** Brain privilégie des conclusions réellement fondées et qualifie les sujets non traités ; il refuse de publier si le contenu incomplet empêche de garantir la fiabilité minimale des constats envisagés. Les limites ne sont pas automatiquement assimilées à une absence de phénomène.
- **Contexte nouveau après publication :** le résultat initial reste identifiable ; une réévaluation explicite peut être proposée.
- **Déconnexion ou départ de l'écran :** l'utilisateur peut retrouver l'état du traitement et le résultat, sans double lancement involontaire.
- **Droits perdus :** la restitution et les opérations respectent les habilitations en vigueur.

## 12. Critères d'acceptation fonctionnels

| ID | Scénario | Comportement attendu vérifiable |
|---|---|---|
| AC-01 | Reporting avec hausse notable, baisse et sujet stable | Brain examine les trois sujets s'ils sont significatifs ; il ne retient pas uniquement le négatif. |
| AC-02 | Reporting court, historique terrain abondant | Brain ne considère pas automatiquement chaque événement historique comme nécessaire à l'analyse. |
| AC-03 | Une première explication contredite par un signal pertinent | Brain examine et signale la contradiction plutôt que de la masquer. |
| AC-04 | Sujet saisonnier et sujet ponctuel dans le même reporting | Les comparaisons historiques sont adaptées à chacun ; aucune profondeur unique n'est imposée. |
| AC-05 | Une hypothèse précédente a été écartée puis un fait nouveau apparaît | Brain rappelle l'antécédent et peut réexaminer l'hypothèse en expliquant ce qui a changé. |
| AC-06 | Plusieurs sujets, capacité insuffisante pour tous | Si au moins un constat utile reste fiable malgré les limites, Brain publie une analyse partielle et explicite les sujets ouverts ; sinon, il refuse la publication. |
| AC-07 | Aucun sujet ne permet une conclusion fiable | Brain refuse une conclusion artificielle et indique la raison et les suites utiles. |
| AC-08 | Analyse complète consultée | L'utilisateur retrouve les sujets couverts et peut consulter les preuves et calculs attachés à chaque constat. |
| AC-09 | Source historique et état opérationnel courant différents | L'interface identifie clairement ce qui relève de la période analysée et ce qui est actuel. |
| AC-10 | Question libre sur une hypothèse | Brain répond sans imposer au préalable un choix de catégorie technique. |
| AC-11 | Nouvelle information modifiant potentiellement une conclusion | Brain distingue le nouvel apport du dossier déjà analysé et propose une réanalyse explicite sans la lancer seul. |
| AC-12 | Knowledge inexistant, non actif ou non pertinent | Brain ne le transforme pas en autorité et explicite les limites de référentiel. |
| AC-13 | Suggestion de plan similaire à un plan déjà ouvert | Le rapprochement est présenté avant confirmation ; l'utilisateur décide de la suite. |
| AC-14 | Proposition d'objectif suffisamment définie | Mesure, cible, période et justification sont consultables ; aucune création avant validation humaine. |
| AC-15 | Relance d'une demande déjà active | L'utilisateur est informé qu'il retrouve un traitement existant, sans fausse création distincte. |
| AC-16 | Utilisateur revient après avoir quitté l'écran | Le traitement, son état et son résultat éventuel restent retrouvables. |
| AC-17 | Analyse partielle dans l'historique | Sa qualification partielle et ses limites restent visibles lors d'une consultation ultérieure. |
| AC-18 | Recommandation fondée sur une corrélation uniquement | Brain la qualifie d'hypothèse et n'affirme pas une causalité démontrée. |
| AC-19 | Recherche n'ayant pas consulté certaines données | Brain ne présente pas ces données comme vérifiées ; la limite du périmètre est compréhensible. |
| AC-20 | Utilisateur non habilité | Ni données hors de son périmètre, ni décisions interdites ne deviennent accessibles via Brain. |
| AC-21 | Sujet exploré correctement mais aucune explication causale fiable | Le sujet est déclaré non concluant ; cela n'impose pas à lui seul le statut partiel si la couverture de tous les sujets est suffisante et qu'un résultat utile peut être publié. |
| AC-22 | Analyse interrompue avant d'avoir repéré tous les sujets significatifs | Brain ne revendique pas une couverture complète et indique l'incertitude sur le périmètre restant. |
| AC-23 | Conclusion localement convaincante, mais contradiction décisive identifiée et non examinée | Cette conclusion n'est pas publiée comme suffisamment étayée, y compris dans une analyse partielle. |
| AC-24 | Reporting contenant des données de plusieurs établissements sans séparation fiable | Le traitement de ce reporting pour un seul établissement est refusé avec une explication compréhensible. |
| AC-25 | Fichier comportant du texte exploitable et des éléments visuels illisibles | Les éléments non lus et leur conséquence sur l'analyse sont signalés ; aucune lecture fictive n'est revendiquée. |
| AC-26 | Recherche bornée ne retournant aucun élément | Brain distingue « rien trouvé dans le périmètre examiné » de « rien ne s'est produit dans l'établissement ». |
| AC-27 | L'utilisateur questionne une information hors du dossier de référence | Brain signale la limite et propose l'approfondissement ou la réanalyse nécessaire sans présenter une recherche non faite comme réalisée. |
| AC-28 | Knowledge modifié après publication d'une analyse | Le résultat antérieur reste associé au référentiel utilisé lors de sa publication ; il n'est pas réécrit silencieusement. |
| AC-29 | Décision passée devenue caduque | Brain peut la rappeler comme historique, sans la présenter comme encore applicable. |
| AC-30 | Analyse interrompue ou refusée | L'historique distingue l'état du traitement d'une analyse partielle effectivement publiée. |
| AC-31 | Suggestion de plan ou d'objectif non validée | Aucune création ou modification opérationnelle n'est effectuée du seul fait de la publication ou de la conversation. |
| AC-32 | Correction déclarée sans demande de nouvelle analyse | L'apport reste identifiable comme non encore intégré aux conclusions publiées et ne déclenche pas de réanalyse automatique. |
| AC-33 | Signal dont le titre et la description rapportent trois tables ayant renoncé au dessert faute de temps | Brain s'appuie exclusivement sur le contenu du Signal et ses métadonnées autorisées, conserve le caractère déclaré de la cause, n'affirme pas de causalité prouvée et ne consulte aucune observation brute. |
| AC-34 | CA et fréquentation diminuent de 12 % ; panier moyen stable ; Signal d'attente au déjeuner | Brain expose la décomposition chiffrée, ne prétend pas que l'attente explique la perte de fréquentation et recherche les informations discriminantes disponibles. |
| AC-35 | Attente excessive établie mais lien avec la fréquentation non démontré | Brain peut proposer un traitement réversible du problème d'attente indépendamment de la baisse de CA, sans promettre de rétablir la fréquentation. |
| AC-36 | Nouvelle formule moins chère ; fréquentation stable ; marges et substitutions inconnues | Brain ne décide pas de maintien ou d'arrêt sur la seule popularité ; il recherche les informations économiques déterminantes puis, si justifié, propose un test limité. |
| AC-37 | Retards signalés mais aucune mesure fiable du délai | Brain propose d'abord de constituer une référence mesurable, avec période d'observation et indicateurs de vigilance ; aucune cible chiffrée inventée n'est présentée comme justifiée. |
| AC-38 | Mécanisme « validé par un expert » issu d'un cas fictif | Brain distingue validation du raisonnement et efficacité empirique, vérifie les conditions locales et n'en déduit pas un gain garanti ni une prescription automatique. |
| AC-39 | Deux analyses différentes demandées pendant qu'un traitement existe déjà | Les deux demandes sont reconnues et retrouvables ; l'une peut être mise en attente, sans substitution silencieuse ni obligation d'exécution parallèle. |
| AC-40 | Reporting lisible mais simple reproduction des chiffres, sans décomposition ni autre apport analytique | Le résultat n'est pas qualifié d'investigation Brain réussie, même partielle ; les limites ou l'impossibilité d'investigation sont explicites. |

## 13. Limites et décisions à ne pas inventer dans le plan technique

Le présent cadrage ne décide pas :
- des méthodes algorithmiques de compréhension, recherche, classement ou contextualisation ;
- du nombre d'étapes, d'appels aux modèles, d'agents ou de traitements ;
- des structures de stockage, index ou mécanismes de mémoire ;
- des budgets numériques, tailles de lots et modalités techniques de reprise ;
- de la mise en page détaillée des écrans ;
- des valeurs de seuil universelles pour qualifier un sujet significatif ou une conclusion suffisamment étayée ;
- d'une nouvelle capacité de conversation autonome hors de toute analyse de reporting ;
- du format précis des indicateurs de couverture et des raisons de limitation.

Ces choix devront être justifiés ultérieurement par le code, les contraintes existantes, la qualité attendue et les scénarios d'acceptation, sans altérer les décisions fonctionnelles ci-dessus.

## 14. Cadre de validation du chantier

La validation produit porte en priorité sur :
1. la **pertinence** des éléments effectivement recherchés et examinés ;
2. l'absence d'omission ou d'exhaustivité trompeuse ;
3. la **solidité des conclusions** et la restitution des contradictions ;
4. la possibilité de publier des conclusions partielles réellement fondées ;
5. la **simplicité des parcours** utilisateur ;
6. la continuité entre analyse, conversation, mémoire et décisions humaines.

Une recette ne peut pas être considérée comme réussie au seul motif qu'un traitement se termine ou respecte son budget : elle doit également produire une investigation métier pertinente, justifiée et intelligible.

---

**Référence de décision :** onze premiers arbitrages validés, complétés par D1 (valeur réelle de l'analyse partielle) et D2 (coexistence de demandes distinctes), eux aussi validés. Les cinq réponses métier de Maxime du 16 octobre précisent le contenu attendu, avec l'arbitrage technique explicite du 16 octobre : **le titre et la description des Signaux font foi ; Brain n'accède jamais aux observations brutes.** Cette V3 demeure candidate à validation conjointe pour ses autres dispositions. Les choix de la PR #317 et les comportements du moteur existant ne sont pas érigés automatiquement en exigences.
