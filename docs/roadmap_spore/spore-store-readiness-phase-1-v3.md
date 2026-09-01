# Spore --- Roadmap Store Readiness --- Phase 1

> **Statut :** cadrage cible\
> **Projet :** `houston_project`\
> **Application :** Spore\
> **Cible :** préparation App Store + Google Play avant les opérations
> qui nécessitent réellement les comptes, capacités ou consoles de
> distribution

## 1. Objectif de la Phase 1

Amener Spore au point où le produit et le repo sont prêts pour entrer
dans les flux de distribution Apple et Google sans découvrir tardivement
de chantier produit, conformité ou mobile majeur.

À la sortie de cette phase :

-   Android doit être prêt à entrer dans le flux Google Play Closed
    Testing ;
-   iOS doit être préparé aussi loin que raisonnablement possible avant
    les opérations nécessitant l'Apple Developer Program / App Store
    Connect ;
-   les éléments de conformité, de présentation et de review nécessaires
    aux stores doivent être préparés ;
-   les actions restantes doivent relever principalement des comptes,
    consoles, identités de distribution, signatures finales ou
    validations qui ne peuvent réellement être effectuées plus tôt.

Cette roadmap est une **source de cadrage**, pas un plan
d'implémentation.

------------------------------------------------------------------------

## 2. Comment utiliser cette roadmap avec Cursor

### 2.1 Liberté d'analyse

Chaque lot décrit :

-   un contexte ;
-   un objectif ;
-   un résultat attendu ;
-   éventuellement des éléments déjà connus à vérifier ;
-   des critères de sortie.

Il ne décrit volontairement **pas la solution technique à appliquer**.

L'agent doit analyser l'état réel du repo avant de proposer quoi que ce
soit. Il reste libre de :

-   confirmer ou invalider le diagnostic initial ;
-   identifier des sujets non anticipés par cette roadmap ;
-   proposer une approche différente ;
-   regrouper ou séparer des travaux si l'architecture réelle le
    justifie ;
-   conclure qu'un lot est déjà satisfait ;
-   challenger une exigence de la roadmap si elle est obsolète,
    incorrecte ou mal placée.

Toute divergence importante doit être explicitée avant implémentation.

### 2.2 Sources de vérité

Par ordre de priorité :

1.  état réel du repo ;
2.  comportement produit attendu ;
3.  exigences officielles Apple / Google / Capacitor à jour ;
4.  cette roadmap comme cadrage de l'objectif.

Les constats techniques issus d'audits précédents sont des **indices à
revérifier**, pas des vérités immuables.

### 2.3 Processus de travail

Pour chaque chantier :

1.  analyser ;
2.  challenger le cadrage si nécessaire ;
3.  identifier les décisions ou zones d'ombre ;
4.  proposer un plan ;
5.  faire valider le plan ;
6.  implémenter ;
7.  valider le résultat ;
8.  documenter ce qui mérite de l'être.

Ne pas transformer directement cette roadmap en série de modifications
de code.

### 2.4 Proportionnalité

Spore est maintenu par un seul développeur. La première publication doit
être fiable et reproductible sans construire prématurément une
infrastructure de release complexe.

Une solution simple et manuelle est acceptable lorsqu'elle répond
correctement au besoin.

Fastlane, CI de publication, automatisation avancée du versioning,
automatisation des screenshots, TestFlight ou autres outils similaires
ne constituent pas des objectifs de Phase 1.

Ils restent possibles si l'analyse démontre un bénéfice concret ou une
nécessité.

### 2.5 Découpage PR cible

Le regroupement suivant est une **guideline organisationnelle**, pas une
contrainte technique. Il vise des PR lisibles ; il ne prescrit ni
l'architecture ni l'ordre interne d'implémentation.

-   **PR1 --- Data & Account Lifecycle :** P1.1 + P1.2
-   **PR2 --- Privacy & Store Compliance :** P1.3 + P1.4 + P1.13
-   **PR3 --- Native Release Readiness :** P1.6 + P1.7 + P1.8 + P1.9
    + P1.14
-   **PR4 --- App Links :** P1.10
-   **PR5 --- Store Presentation & Review :** P1.5 + P1.11 + P1.12
-   **PR6 --- Release Validation & Gate :** P1.15 + P1.16

PR1, PR3, PR4 et PR5 peuvent avancer en parallèle. PR2 dépend
principalement de PR1. PR6 intervient après convergence des autres PR.

Si l'analyse réelle du repo révèle une dépendance imprévue ou un
meilleur découpage, Cursor doit le signaler dans son plan **avant
implémentation**.

------------------------------------------------------------------------

## 3. Contexte initial

Un audit préalable indique que le socle Capacitor existe déjà et que
Spore dispose de projets iOS et Android fonctionnels.

Il indique également que plusieurs sujets nécessaires à une distribution
store restent incomplets ou non finalisés : conformité liée aux données,
suppression de compte, identité visuelle native, configuration de
distribution, préparation des releases, deep links E2E, contenu store et
procédures de review.

Ces constats doivent être **revérifiés par Cursor au moment de chaque
chantier**.

L'objectif de la Phase 1 n'est pas de reconstruire le socle mobile mais
de compléter ce qui est réellement nécessaire à la publication.

------------------------------------------------------------------------

# 4. Chantiers Phase 1

## P1.1 --- Data & Privacy

### Contexte

Les déclarations Apple et Google ainsi que la Privacy Policy doivent
refléter le comportement réel de Spore et de ses dépendances.

L'audit initial a identifié plusieurs catégories potentielles de données
et plusieurs services tiers, mais cette photographie peut être
incomplète.

### Objectif

Obtenir une compréhension fiable et maintenable des données manipulées
par Spore, de leur cycle de vie et des tiers impliqués.

### Résultat attendu

À la fin du chantier, nous devons pouvoir répondre sans ambiguïté aux
questions nécessaires pour :

-   rédiger la Privacy Policy ;
-   préparer Apple App Privacy ;
-   préparer Google Data Safety ;
-   raisonner correctement sur la suppression et la conservation des
    données.

L'agent choisit la forme de documentation la plus adaptée.

### Points connus à vérifier

Sans constituer une liste exhaustive : données utilisateur et métier,
contenus envoyés par les utilisateurs, fonctionnalités utilisant des
capacités du device, authentification, stockage, logs, services tiers,
IA, notifications, conservation, purge et suppression.

### Critère de sortie

La cartographie est suffisamment complète pour servir de source de
vérité aux chantiers de conformité suivants, et les incertitudes
restantes sont explicitement identifiées.

------------------------------------------------------------------------

## P1.2 --- Suppression de compte

### Contexte

Spore permet l'utilisation de comptes authentifiés. Les stores imposent
des exigences relatives à la suppression des comptes et des données
associées.

Dans Spore, cette opération peut avoir des conséquences métier au-delà
d'un simple utilisateur technique.

### Objectif

Définir puis rendre disponible un comportement de suppression de compte
cohérent avec :

-   le modèle métier réel ;
-   les règles de conservation applicables ;
-   l'expérience utilisateur ;
-   les exigences Apple et Google actuelles.

### Résultat attendu

Un utilisateur doit pouvoir exercer la suppression de son compte selon
un parcours compréhensible.

Le système doit traiter les accès et données associés selon des règles
explicites. Les données éventuellement conservées doivent l'être pour
une raison identifiée et documentable.

Les éventuelles exigences hors-app imposées par les stores doivent
également être couvertes.

### Liberté laissée à l'agent

La roadmap ne présume pas :

-   du contrat backend ;
-   de l'UX ;
-   du mécanisme de suppression ;
-   de la stratégie de rétention ;
-   de la manière de satisfaire une éventuelle exigence web.

Ces choix doivent découler de l'analyse.

### Critère de sortie

Le comportement est fonctionnel, testé à un niveau proportionné au
risque et suffisamment documenté pour alimenter les éléments de
conformité.

------------------------------------------------------------------------

## P1.3 --- Privacy Policy

### Contexte

Les mentions légales de la landing page ne constituent pas
nécessairement la politique de confidentialité de l'application.

### Objectif

Disposer d'une Privacy Policy publique qui décrit correctement Spore et
puisse être utilisée dans l'application et les stores.

### Résultat attendu

La politique doit être cohérente avec la cartographie Data & Privacy et
avec les comportements réellement implémentés.

Elle doit couvrir les informations nécessaires au regard des exigences
applicables et être accessible aux utilisateurs et aux stores.

### Critère de sortie

Une URL publique stable existe, le contenu est cohérent avec le produit
et Spore permet à l'utilisateur d'y accéder lorsque cela est requis.

------------------------------------------------------------------------

## P1.4 --- Déclarations Privacy des stores

### Contexte

Apple App Privacy et Google Data Safety demandent des déclarations
structurées qui doivent rester cohérentes avec le produit, les SDK
utilisés et la Privacy Policy.

### Objectif

Préparer des réponses fiables afin que la configuration future des
consoles ne nécessite pas un nouvel audit du produit.

### Résultat attendu

Les informations nécessaires aux deux stores sont préparées à partir de
la source de vérité Data & Privacy.

Les divergences éventuelles entre comportement réel, Privacy Policy et
déclarations attendues doivent être identifiées et résolues.

### Critère de sortie

Les déclarations peuvent être reportées dans les consoles stores sans
devoir reconstruire l'analyse des données.

------------------------------------------------------------------------

## P1.5 --- Identité visuelle native et store

### Contexte

L'audit initial indique que des éléments visuels Capacitor / Android par
défaut sont encore présents.

### Objectif

Faire en sorte que l'application distribuée et les assets nécessaires
aux stores utilisent correctement l'identité Spore.

### Résultat attendu

Aucun élément visuel générique ou provenant du scaffold mobile ne doit
apparaître là où l'identité Spore est attendue.

Le rendu doit être adapté aux plateformes ciblées et suffisamment
préparé pour les futures fiches stores.

### Liberté laissée à l'agent

L'agent doit identifier les assets réellement utilisés et les exigences
actuelles des plateformes avant de proposer les modifications
nécessaires.

### Critère de sortie

L'identité Spore est correctement représentée sur les builds concernés
et les assets nécessaires à la distribution sont disponibles ou
clairement identifiés.

------------------------------------------------------------------------

## P1.6 --- Configuration de production Native

### Contexte

Un build store ne doit pas dépendre accidentellement d'une configuration
locale, de test ou incorrecte.

L'audit initial a identifié des mécanismes existants de configuration du
runtime Native qu'il faudra revérifier.

### Objectif

Garantir qu'un build destiné à la distribution utilise de manière
reproductible la configuration de production attendue.

### Résultat attendu

Le développeur doit pouvoir produire un build Native en sachant :

-   quelle configuration il embarque ;
-   vers quels services il communique ;
-   qu'aucune valeur locale ou de test non voulue n'est présente ;
-   que le mécanisme utilisé est reproductible.

### Liberté laissée à l'agent

Les variables, fichiers, scripts et garde-fous à utiliser doivent être
déterminés à partir du repo.

Les noms ou mécanismes identifiés lors d'audits précédents ne sont que
des points de départ à vérifier.

### Critère de sortie

La configuration d'un build destiné aux stores est maîtrisée, vérifiable
et documentée au niveau nécessaire.

------------------------------------------------------------------------

## P1.7 --- Services Native / Firebase / Push

### Contexte

Spore possède déjà des fonctionnalités Native dépendant de services
externes, notamment autour des notifications.

Certaines parties peuvent être préparées immédiatement ; d'autres
peuvent dépendre des capacités de distribution Apple.

### Objectif

Comprendre et préparer les dépendances nécessaires à des builds de
distribution fonctionnels sans exposer de secrets ni essayer de
contourner les limitations liées aux comptes de distribution.

### Résultat attendu

Pour chaque plateforme :

-   les dépendances nécessaires sont connues ;
-   leur configuration de production est comprise ;
-   ce qui peut être rendu reproductible maintenant l'est ;
-   ce qui dépend réellement d'Apple ou d'une opération future est
    clairement isolé.

### Liberté laissée à l'agent

La roadmap ne présume ni du mécanisme d'injection de configuration, ni
du stockage des secrets, ni de l'outillage.

### Critère de sortie

Les services concernés ne constituent plus une zone d'incertitude pour
la préparation des releases, et les dépendances Phase 2 sont clairement
identifiées.

------------------------------------------------------------------------

## P1.8 --- Android Release Readiness

### Contexte

Le compte Google Play est un compte personnel récent. La production
nécessitera donc de passer par le parcours de Closed Testing applicable.

L'audit initial indique que le repo n'est pas encore prêt à produire
directement un artefact de distribution exploitable par Google Play.

### Objectif

Amener Android au point où un artefact Release valide peut entrer dans
le flux Google Play.

### Résultat attendu

Le développeur doit pouvoir produire de manière reproductible un AAB :

-   destiné à Spore ;
-   utilisant la configuration de production attendue ;
-   correctement versionné ;
-   correctement préparé pour les exigences de distribution Google Play
    ;
-   sans exposer les éléments sensibles nécessaires aux futures
    releases.

### Liberté laissée à l'agent

L'agent doit déterminer, après analyse du projet et des exigences Google
actuelles :

-   la stratégie de signature appropriée ;
-   la configuration de build nécessaire ;
-   la gestion des éléments sensibles ;
-   les vérifications pertinentes.

La roadmap n'impose aucun mécanisme Gradle ou outillage particulier.

### Critère de sortie

Un AAB Release réellement exploitable par le flux Google Play peut être
produit et reproduit.

------------------------------------------------------------------------

## P1.9 --- iOS Release Readiness avant Apple Developer Program

### Contexte

Spore fonctionne déjà sur iPhone via Xcode, mais un fonctionnement local
ne garantit pas qu'un projet soit prêt pour une distribution App Store.

Certaines opérations ne pourront être finalisées qu'après activation des
capacités Apple nécessaires.

### Objectif

Amener le projet iOS aussi loin que raisonnablement possible vers une
distribution App Store **sans essayer de réaliser prématurément ce qui
dépend réellement de l'Apple Developer Program ou d'App Store Connect**.

### Résultat attendu

À la fin du chantier :

-   les éléments du projet pouvant bloquer ultérieurement une
    archive/distribution ont été recherchés ;
-   ce qui peut être corrigé ou préparé maintenant l'est ;
-   les choix produit influençant la distribution sont explicités ;
-   les étapes impossibles à finaliser sans Apple sont clairement
    identifiées.

### Points connus à vérifier

L'audit précédent a notamment relevé des sujets autour de la
configuration Release, des permissions, des capacités Native, des
dépendances, du support des devices et de la confidentialité.

Cette liste n'est ni exhaustive ni prescriptive.

### Critère de sortie

Le prochain travail iOS significatif non réalisable en Phase 1 dépend
réellement des capacités ou consoles Apple.

------------------------------------------------------------------------

## P1.10 --- Liens applicatifs

### Contexte

Spore contient déjà une logique permettant de traiter des liens ouvrant
l'application, mais l'audit initial indique que le fonctionnement E2E
n'est pas entièrement finalisé.

### Objectif

Préparer un comportement fiable des liens applicatifs sur les
plateformes ciblées.

### Résultat attendu

Les liens que Spore doit prendre en charge, leur destination et leur
comportement sont compris.

Les mécanismes nécessaires côté application, plateforme et domaine sont
cohérents.

Tout ce qui peut être finalisé avant les identités de distribution doit
l'être ; ce qui en dépend doit être explicitement reporté.

### Liberté laissée à l'agent

La roadmap ne présume ni des fichiers à créer, ni de leur emplacement,
ni du mécanisme de déploiement.

### Critère de sortie

La chaîne est préparée au maximum raisonnablement possible en Phase 1 et
les dépendances restantes sont connues.

------------------------------------------------------------------------

## P1.11 --- Review readiness

### Contexte

Les reviewers des stores doivent pouvoir comprendre et tester une
application authentifiée sans dépendre d'une intervention manuelle du
développeur.

### Objectif

Préparer Spore et son environnement afin qu'une review store puisse
réellement parcourir les fonctionnalités nécessaires.

### Résultat attendu

Il doit exister un moyen fiable pour un reviewer d'accéder au produit
dans un contexte représentatif, avec les informations nécessaires pour
comprendre les éventuelles particularités du parcours.

Aucune donnée personnelle réelle ne doit être nécessaire.

### Liberté laissée à l'agent

La forme exacte du compte, des données, des instructions ou de
l'environnement doit être déterminée selon le fonctionnement réel de
Spore et les exigences actuelles des stores.

### Critère de sortie

Une review externe peut être réalisée sans dépendance fragile ou
intervention ad hoc du développeur.

------------------------------------------------------------------------

## P1.12 --- Présentation Store

### Contexte

La publication nécessite du contenu et des assets qui ne vivent pas
nécessairement dans les projets Native mais doivent être préparés avant
la soumission.

### Objectif

Préparer les éléments nécessaires pour présenter Spore correctement sur
les stores.

### Résultat attendu

Les contenus textuels, visuels, URLs et informations demandés par les
stores sont identifiés et préparés dans la mesure où ils peuvent l'être
avant l'accès aux consoles.

### Liberté laissée à l'agent

L'agent doit vérifier les exigences actuelles Apple et Google et ne pas
se limiter aux éléments traditionnellement demandés si les stores ont
évolué.

La roadmap ne prescrit pas où ces contenus doivent être stockés dans le
repo.

### Critère de sortie

L'ouverture/configuration des fiches stores ne doit pas déclencher un
nouveau chantier important de production de contenu.

------------------------------------------------------------------------

## P1.13 --- Conformité Store hors Privacy

### Contexte

Les stores demandent d'autres informations ou décisions que les seules
déclarations liées aux données.

### Objectif

Identifier et préparer les éléments de conformité nécessaires à la
soumission qui peuvent être anticipés en Phase 1.

### Résultat attendu

Les questionnaires, classifications, déclarations ou décisions
pertinentes pour Spore sont identifiés à partir :

-   du comportement réel du produit ;
-   des capacités Native ;
-   des fonctionnalités proposées ;
-   des exigences officielles actuelles.

Les éléments qui ne peuvent être finalisés qu'en console doivent être
préparés autant que possible.

### Critère de sortie

Aucune exigence de conformité connue ne devrait découvrir tardivement un
changement produit majeur.

------------------------------------------------------------------------

## P1.14 --- Procédure de Release V1

### Contexte

La première release n'a pas besoin d'une infrastructure de publication
sophistiquée, mais elle doit être reproductible.

### Objectif

Disposer d'un chemin fiable depuis le repo jusqu'aux artefacts destinés
aux stores.

### Résultat attendu

Le développeur sait :

-   comment préparer un build de distribution ;
-   comment produire les artefacts pertinents ;
-   quelles vérifications effectuer avant upload ;
-   quels prérequis ou éléments sensibles sont nécessaires ;
-   quelles étapes restent volontairement en Phase 2.

### Liberté laissée à l'agent

Les commandes, scripts, outils et niveau d'automatisation doivent être
déduits du repo et des solutions retenues dans les autres chantiers.

### Critère de sortie

Une procédure suffisamment claire permet de reproduire une release sans
connaissance implicite importante.

------------------------------------------------------------------------

## P1.15 --- Validation Release Candidate

### Contexte

Le fait que Spore fonctionne en développement ou via un run Xcode ne
suffit pas à valider le comportement d'une future release store.

### Objectif

Valider le produit dans des conditions suffisamment proches des builds
destinés à la distribution.

### Résultat attendu

Les parcours et capacités réellement critiques pour une release sont
identifiés puis vérifiés sur les plateformes concernées.

La validation doit également rechercher les problèmes spécifiques au
contexte Release : configuration, permissions, services externes,
authentification, réseau, navigation Native et fonctionnalités
dépendantes du device.

### Liberté laissée à l'agent

La roadmap ne définit pas une checklist exhaustive de tests.

L'agent doit proposer une couverture adaptée au produit réel, aux
changements effectués pendant la Phase 1 et aux risques identifiés.

### Critère de sortie

Aucune anomalie bloquante connue ne subsiste dans ce qui est testable
avant la Phase 2, et les validations impossibles à réaliser plus tôt
sont explicitement reportées.

------------------------------------------------------------------------

## P1.16 --- Gate Phase 1

### Objectif

Rechallenger l'ensemble de la préparation avant de considérer la Phase 1
terminée.

### Résultat attendu

Effectuer un nouvel audit du repo, du produit et des exigences stores
**sans supposer que la roadmap a nécessairement identifié tous les
sujets**.

L'audit doit notamment déterminer :

### Android

Android peut-il entrer dans le flux Google Play Closed Testing sans
nouveau chantier produit ou mobile majeur ?

### iOS

Les travaux significatifs restant avant une soumission App Store
dépendent-ils réellement de l'Apple Developer Program, d'App Store
Connect ou d'éléments impossibles à finaliser plus tôt ?

### Global

Existe-t-il un angle mort de conformité, configuration, distribution,
review ou produit qui rendrait prématuré le passage en Phase 2 ?

### Critère de sortie

La Phase 1 est terminée uniquement si le nouvel audit conclut que le
passage aux opérations de distribution est raisonnable.

La Gate peut rouvrir un chantier précédent ou en créer un nouveau si
nécessaire.

------------------------------------------------------------------------

# 5. Ordonnancement

Il n'existe volontairement **pas de graphe de dépendances obligatoire**.

Les relations suivantes sont des indications logiques, à challenger
selon l'état réel du projet :

-   comprendre les données avant de finaliser Privacy Policy et
    déclarations stores ;
-   comprendre les règles de suppression avant de finaliser les
    déclarations de rétention ;
-   stabiliser suffisamment la configuration Native avant de considérer
    les builds Release comme validés ;
-   disposer d'un candidat Release suffisamment représentatif avant la
    validation finale ;
-   effectuer la Gate seulement lorsque les autres sujets significatifs
    ont été traités.

Cursor peut proposer un ordre différent s'il réduit les dépendances,
évite du travail inutile ou correspond mieux à l'architecture réelle.

Le regroupement cible en PR (section 2.5) suit la même logique : à
challenger, pas à appliquer mécaniquement.

------------------------------------------------------------------------

# 6. Phase 2 --- Frontière actuelle

La Phase 2 n'est pas détaillée dans cette roadmap.

Elle commence lorsque la Gate P1.16 est validée.

Elle couvrira principalement les opérations devenues possibles ou
pertinentes avec les comptes et consoles de distribution.

## Apple

La cible produit actuelle est une **soumission App Store directe**.
TestFlight n'est pas une étape obligatoire.

La Phase 2 devra déterminer et exécuter les opérations Apple réellement
nécessaires à partir de l'état atteint en Phase 1.

## Google Play

Le compte Google Play est un compte personnel récent.

La publication devra donc intégrer le parcours de testing et d'accès
Production imposé par Google au moment de la soumission.

Les valeurs précises (nombre de testeurs, durée, conditions) doivent
être **revérifiées dans la documentation officielle au moment d'exécuter
cette phase**, et non considérées comme figées par cette roadmap.

------------------------------------------------------------------------

# 7. Règles de décision pour Cursor

Pour chaque chantier, l'agent doit privilégier :

**nécessité réelle \> conformité \> simplicité \> cohérence avec
l'existant \> automatisation / sophistication**

L'agent doit :

-   partir du repo, pas de la roadmap seule ;
-   distinguer faits observés, exigences externes, décisions produit et
    propositions techniques ;
-   signaler les hypothèses ;
-   rechercher les angles morts ;
-   challenger les constats historiques devenus faux ;
-   vérifier les exigences store susceptibles d'avoir évolué ;
-   éviter les modifications non nécessaires à l'objectif ;
-   préserver les comportements existants qui ne nécessitent pas de
    changement ;
-   proposer les tests adaptés au risque ;
-   documenter les décisions qui devront être comprises lors des futures
    releases.

L'agent ne doit pas :

-   implémenter une solution uniquement parce qu'elle est mentionnée
    dans un ancien audit ;
-   transformer les « points connus à vérifier » en checklist exhaustive
    ;
-   ajouter une abstraction ou infrastructure uniquement pour anticiper
    un futur hypothétique ;
-   considérer un lot comme terminé simplement parce que ses exemples
    ont été traités ;
-   contourner artificiellement une limitation qui sera naturellement
    levée en Phase 2.

------------------------------------------------------------------------

# 8. Non-objectifs

La Phase 1 ne cherche pas à :

-   reconstruire l'architecture mobile ;
-   perfectionner des domaines sans impact raisonnable sur la
    publication ;
-   automatiser pour le principe ;
-   reproduire en local des opérations qui nécessitent réellement les
    stores ;
-   rendre la release process plus complexe que nécessaire ;
-   imposer une architecture cible différente de celle du projet sans
    justification.

Ces éléments peuvent néanmoins être proposés si l'analyse démontre
qu'ils sont nécessaires pour atteindre l'objectif.

------------------------------------------------------------------------

# 9. Définition globale de Done

La Phase 1 est terminée lorsque la Gate P1.16 confirme que :

### Produit et conformité

Les comportements nécessaires à la publication sont présents ou
suffisamment préparés, les pratiques liées aux données sont comprises,
et les informations destinées aux stores peuvent être renseignées de
manière cohérente.

### Android

Un artefact Release réellement destiné à Google Play peut être produit
de manière reproductible et Android peut entrer dans le parcours de
Closed Testing sans chantier majeur supplémentaire.

### iOS

Le projet et le produit ont été préparés aussi loin que raisonnablement
possible avant les opérations dépendantes d'Apple, et aucun bloqueur
significatif pouvant être traité plus tôt n'est connu.

### Review et présentation

Les stores pourront comprendre, présenter et tester Spore sans
nécessiter la création tardive d'un nouveau chantier important.

### Processus

La procédure de release est suffisamment comprise et documentée pour
continuer vers la distribution.

------------------------------------------------------------------------

# 10. Cible de sortie

``` text
PHASE 1
Repo + produit + conformité + préparation Release
                    │
                    ▼
              Gate P1.16
             /           \
            /             \
       Android             iOS
          │                 │
          ▼                 ▼
 Google Play flow    Apple distribution
 Closed Testing      capabilities / console
          │                 │
          ▼                 ▼
     Production        App Review
                            │
                            ▼
                       Production
```

La Phase 1 est réussie si la Phase 2 devient principalement un **travail
de distribution et de validation store**, et non la découverte tardive
de problèmes fondamentaux dans Spore.
