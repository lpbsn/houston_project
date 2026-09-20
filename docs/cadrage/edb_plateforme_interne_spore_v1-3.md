# Expression de besoin fonctionnelle — Plateforme interne Spore V1

**Statut :** validé pour cadrage fonctionnel  
**Version :** 1.3  
**Date :** 19 septembre 2026  
**Périmètre :** V1 minimale et évolutive  

Ce document décrit la **cible fonctionnelle** de Spore Platform V1. Ce n’est pas la spec d’implémentation ni un runbook produit. L’implémentation live appartient au code et aux documents de domaine (identité, RBAC, onboarding).

---

## 1. Objet du document

Ce document définit le besoin fonctionnel de la première version de la plateforme interne Spore.

Il décrit :

- la finalité du produit ;
- les utilisateurs concernés ;
- les informations consultables ;
- les parcours attendus ;
- les règles d'accès et de séparation avec les espaces clients ;
- les limites de la V1 ;
- les critères permettant de valider son fonctionnement.

Il ne prescrit aucun choix d'implémentation : modèle de données, architecture logicielle, API, framework, stockage, protocole d'authentification ou méthode de pagination.

---

## 2. Contexte

Spore est une plateforme multi-organisation et multi-établissement. Son fonctionnement quotidien nécessite de pouvoir comprendre rapidement :

- quelles organisations et quels établissements existent ;
- quels utilisateurs disposent d'un compte ;
- à quels établissements ils sont rattachés ;
- quels rôles, statuts et périmètres leur sont attribués ;
- où se situe un éventuel blocage d'onboarding.

Aujourd'hui, ces informations sont liées au fonctionnement interne de Spore mais ne doivent pas être confondues avec l'administration métier réalisée par les clients dans leurs propres espaces.

La V1 doit donc fournir un espace interne de consultation transverse, utilisable pour l'observation et le diagnostic, sans créer de « super-administrateur » capable d'agir arbitrairement sur les données des clients.

---

## 3. Vision produit

La plateforme interne Spore V1 est un **control plane opérationnel minimal** permettant d'exécuter les onboardings, d'explorer les ressources existantes et de nettoyer celles abandonnées avant activation.

Elle permet à un opérateur interne autorisé de réaliser intégralement un onboarding, de retrouver une organisation, un établissement ou un utilisateur, de comprendre leurs relations, de consulter les principaux états nécessaires au support et de supprimer les ressources abandonnées avant leur mise en service.

Elle n'est ni :

- un tableau de bord de pilotage ;
- un espace d'administration métier pour le compte d'un client ;
- un outil d'accès aux contenus opérationnels des clients ;
- un mode permettant de contourner les droits normaux d'un espace client.

Les suppressions autorisées sont des opérations de nettoyage du cycle de vie Platform. Elles ne permettent pas d'administrer l'activité métier d'un client.

L'onboarding est une opération interne Spore. **Platform est son unique point d'entrée.** Il est lancé, réalisé, repris et terminé depuis Platform, sur **desktop Web** uniquement. Aucun utilisateur client ne démarre, ne reprend ni ne renseigne le wizard depuis la page de connexion, un espace client, le Web mobile ou une application native. Un Owner ou un Director invité se limite à accepter son invitation et à activer son compte.

---

## 4. Objectifs de la V1

### 4.1 Objectifs principaux

La V1 doit permettre de :

1. démarrer, réaliser, reprendre et terminer un onboarding depuis Platform ;
2. créer les ressources nécessaires uniquement dans le cadre de cet onboarding ;
3. rechercher et consulter l'ensemble des organisations Spore ;
4. rechercher et consulter l'ensemble des établissements Spore ;
5. rechercher et consulter l'ensemble des utilisateurs Spore ;
6. comprendre les rattachements entre utilisateurs, établissements et organisations ;
7. visualiser les rôles, statuts et périmètres associés à ces rattachements ;
8. identifier l'état synthétique de l'onboarding d'un établissement ;
9. naviguer entre ces informations sans dépendre d'un établissement actif ;
10. supprimer un établissement abandonné avant activation ;
11. supprimer une organisation vide qui n'est jamais devenue opérationnelle ;
12. garantir qu'un accès interne à la plateforme ne confère aucun droit supplémentaire dans les espaces clients.

### 4.2 Résultat attendu

Un opérateur interne doit pouvoir répondre, sans accès direct aux données techniques, à des questions telles que :

- « Cette organisation existe-t-elle et quel est son statut ? »
- « Quels établissements appartiennent à cette organisation ? »
- « Où en est l'onboarding de cet établissement ? »
- « Ce compte utilisateur est-il actif ? »
- « Dans quels établissements cet utilisateur intervient-il ? »
- « Quel rôle possède-t-il dans chacun d'eux ? »
- « Sur quelles unités métier son accès porte-t-il ? »
- « Puis-je démarrer ou reprendre cet onboarding depuis Platform ? »
- « Cet établissement abandonné peut-il être supprimé sans affecter de données métier ? »
- « Cette organisation vide peut-elle être nettoyée ? »

---

## 5. Principes fonctionnels non négociables

### PF-01 — Séparation des contextes

L'espace interne Spore et les espaces clients sont deux contextes distincts. L'utilisateur doit toujours savoir dans lequel il se trouve.

### PF-02 — Absence d'élévation implicite

Être autorisé à utiliser la plateforme interne ne donne aucun droit supplémentaire dans une organisation ou un établissement client.

### PF-03 — Gestion du cycle de vie strictement limitée

La V1 permet uniquement les opérations de cycle de vie suivantes :

- démarrer, renseigner, reprendre et terminer un onboarding ;
- créer les ressources nécessaires au travers de ce parcours ;
- supprimer un établissement abandonné avant activation ;
- supprimer une organisation vide qui n'est jamais devenue opérationnelle.

Une organisation **devient opérationnelle** lorsqu'au moins un de ses établissements a été activé. Cette notion est indépendante du statut courant de l'organisation.

Aucune autre modification n'est permise.

### PF-04 — Accès explicite

Seuls les utilisateurs auxquels l'accès interne a été explicitement attribué peuvent ouvrir cet espace.

### PF-05 — Révocation indépendante

L'accès à la plateforme interne peut être désactivé sans modifier les accès éventuels de l'utilisateur aux espaces clients, et réciproquement.

### PF-06 — Minimisation des données

La plateforme n'affiche que les données nécessaires à l'identification, à la compréhension des rattachements et au diagnostic de premier niveau.

### PF-07 — Pas de contenu métier client

La V1 ne donne pas accès au contenu des signaux, plans d'action, commentaires, conversations, pièces jointes ou productions d'intelligence artificielle d'un client.

### PF-08 — Utilisabilité à grande échelle

Les fonctions de recherche, de filtrage et de navigation doivent rester utilisables lorsque le nombre d'organisations, d'établissements, d'utilisateurs ou de rattachements augmente fortement.

### PF-09 — Refus par défaut

Tout accès non explicitement autorisé doit être refusé, y compris lorsqu'un utilisateur possède un rôle élevé dans un espace client.

### PF-10 — Suppression sûre et explicite

Une suppression n'est proposée que si toutes ses conditions fonctionnelles sont réunies. Son impact est présenté avant une confirmation explicite et son éligibilité est vérifiée au moment de l'action.

### PF-11 — Traçabilité des opérations de cycle de vie

Le démarrage, la finalisation et la suppression d'un onboarding ou d'une ressource conservent au minimum l'identité de l'opérateur, l'action, la ressource concernée, la date et le résultat. Une suppression conserve également la justification saisie.

### PF-12 — Onboarding exclusivement interne

Seul un opérateur Spore actif peut démarrer, reprendre ou réaliser le wizard d'onboarding. Platform est le seul point d'entrée de ce parcours. La page de connexion et les espaces clients n'en constituent pas.

Un Owner ou un Director n'intervient que pour accepter une invitation émise pendant ce parcours et activer son compte. Il n'accède pas au wizard et ne renseigne aucune étape.

L'établissement ne peut pas être activé tant qu'aucun Owner ou Director n'a un rattachement actif.

### PF-13 — Séparation d'autorisation

L'autorisation d'utiliser Platform est distincte des permissions d'un espace client. Elle ne s'appuie pas sur un rattachement tenant et n'en crée pas pour l'opérateur. Un opérateur peut par ailleurs posséder, indépendamment, des rattachements client. Ces rattachements ne lui donnent aucun droit Platform supplémentaire et l'accès Platform ne lui en donne aucun dans un espace client.

### PF-14 — Desktop Web uniquement

L'interface Platform n'est proposée que sur desktop Web. Elle est absente des applications natives et de l'expérience Web hors desktop.

---

## 6. Acteurs

### 6.1 Opérateur Spore actif

Utilisateur interne autorisé à consulter la plateforme.

En V1, tous les opérateurs actifs disposent du même périmètre fonctionnel, comprenant l'exécution complète du wizard d'onboarding, la consultation et les deux opérations de nettoyage prévues. Ils n'ont pas besoin d'un rattachement client. S'ils en possèdent un, il reste indépendant.

### 6.2 Opérateur Spore désactivé

Utilisateur dont l'accès interne a été retiré. Il ne peut plus consulter la plateforme, même si sa session utilisateur générale est encore active.

Ses éventuels accès clients restent régis indépendamment par ses rattachements à ces espaces.

### 6.3 Utilisateur client

Utilisateur disposant uniquement d'un ou plusieurs accès à des espaces clients. Quel que soit son rôle client, il ne peut pas accéder à la plateforme interne.

### 6.4 Utilisateur à double contexte

Utilisateur disposant à la fois :

- d'un accès interne Spore ;
- d'un ou plusieurs accès à des espaces clients.

Ses deux contextes restent séparés. Il accède explicitement à la plateforme interne et conserve le fonctionnement normal de ses espaces clients.

---

## 7. Périmètre fonctionnel V1

### 7.1 Inclus

- accès à un espace clairement identifié « Spore Platform » ;
- démarrage, réalisation, reprise et finalisation d'un onboarding par un opérateur Spore ;
- création d'une organisation et d'un établissement uniquement au travers de l'onboarding ;
- consultation des organisations ;
- consultation des établissements ;
- consultation des utilisateurs ;
- consultation des rattachements entre utilisateurs et établissements ;
- recherche par ressource ;
- filtres adaptés à chaque liste ;
- navigation contextuelle entre ressources liées ;
- affichage synthétique de l'état d'onboarding d'un établissement ;
- suppression d'un établissement abandonné avant activation ;
- suppression d'une organisation vide qui n'est jamais devenue opérationnelle ;
- confirmation et traçabilité de ces suppressions ;
- gestion des états d'absence de résultat, d'accès refusé et de donnée indisponible ;
- invitations Owner et Director **uniquement** dans le parcours d'onboarding Platform (acceptation de compte hors wizard) ;
- accès à l'interface depuis **desktop Web** uniquement.

### 7.2 Exclus

- création autonome d'une organisation en dehors de l'onboarding ;
- création autonome d'un établissement en dehors de l'onboarding ;
- modification ou suspension d'une organisation en dehors des données nécessaires à l'onboarding ;
- modification ou suspension d'un établissement en dehors des données nécessaires à l'onboarding ;
- suppression d'une organisation qui contient encore un établissement ou qui est déjà devenue opérationnelle ;
- suppression d'un établissement qui a terminé son onboarding, a déjà été activé ou contient des données métier ;
- création, modification, suspension ou suppression d'un utilisateur ;
- modification d'un rôle, d'un statut ou d'un périmètre d'accès client ;
- invitation d'un utilisateur **en dehors** du parcours d'onboarding ;
- réinitialisation de mot de passe ;
- révocation de sessions ;
- réparation technique ou réouverture forcée d'un onboarding terminé ;
- impersonation d'un utilisateur ;
- accès aux contenus métier d'un client ;
- accès détaillé aux sessions, adresses réseau ou appareils ;
- consultation des consentements ;
- recherche globale mélangeant plusieurs types de ressources ;
- tableau de bord, indicateurs ou statistiques Platform ;
- export de données ;
- gestion autonome des opérateurs depuis l'interface ;
- interface Platform dans les applications mobiles natives et sur le Web hors desktop ;
- rôles internes différenciés ou droits personnalisables par opérateur ;
- journal d'audit général des consultations ;
- accès à l'onboarding depuis la page de connexion ou un espace client ;
- onboarding réalisé, même partiellement, par un utilisateur client.

Aucune autre opération de cycle de vie n'est incluse dans la V1.

---

## 8. Organisation fonctionnelle de l'espace

L'espace comporte quatre entrées principales :

1. **Onboardings** ;
2. **Organisations** ;
3. **Établissements** ;
4. **Utilisateurs**.

Les rattachements sont consultés dans le contexte d'une organisation, d'un établissement ou d'un utilisateur. Ils ne nécessitent pas une rubrique principale supplémentaire dans la navigation.

L'entrée dans l'espace doit présenter une identité visuelle et un libellé suffisamment explicites pour éviter toute confusion avec un espace client.

La page d'entrée oriente directement vers une liste utile. La V1 ne comporte pas de page d'accueil analytique.

---

## 9. Besoins fonctionnels détaillés

### 9.1 Accès à la plateforme

#### BF-ACC-01 — Visibilité de l'accès

Un utilisateur autorisé voit un accès explicite à « Spore Platform » **sur desktop Web**.

Un utilisateur non autorisé ne voit pas cet accès. L'accès n'apparaît pas non plus sur le Web hors desktop ni dans les applications natives.

#### BF-ACC-02 — Accès direct

Lorsqu'un utilisateur tente d'ouvrir directement l'espace Platform :

- un opérateur actif **sur desktop Web** y accède ;
- tout autre utilisateur authentifié reçoit un refus, sans divulgation de données internes.

#### BF-ACC-03 — Utilisateur à double contexte

Après connexion, un utilisateur disposant aussi d'un accès client conserve son arrivée habituelle dans le contexte client. Sur desktop Web, il rejoint « Spore Platform » par une action explicite. Ses rattachements client restent régis uniquement par les permissions tenant.

#### BF-ACC-04 — Utilisateur exclusivement interne

Après connexion **sur desktop Web**, un utilisateur qui ne dispose d'aucun accès client actif mais possède un accès Platform actif est orienté vers l'espace interne. Hors desktop Web, il n'est pas orienté vers Platform.

#### BF-ACC-05 — Désactivation de l'accès

La désactivation d'un opérateur prend effet lors de sa prochaine tentative d'accès ou action dans l'espace Platform. Elle ne doit pas attendre une nouvelle connexion.

#### BF-ACC-06 — Version mobile native

Les applications mobiles natives ne présentent ni entrée, ni navigation, ni interface Platform en V1.

#### BF-ACC-07 — Absence d'entrée depuis la connexion

La page de connexion ne présente aucune action permettant de démarrer, demander ou rejoindre un onboarding.

Une personne non autorisée qui tente d'ouvrir directement le parcours d'onboarding ne peut ni créer de ressource, ni consulter un onboarding existant.

#### BF-ACC-08 — Web hors desktop

Sur le Web hors desktop, Platform n'est pas proposée : pas d'entrée de navigation, pas d'interface, pas d'orientation post-connexion vers cet espace.

---

### 9.2 Onboardings

#### BF-ONB-01 — Point d'entrée unique

Le démarrage d'un onboarding est disponible uniquement depuis « Spore Platform » pour un opérateur actif.

#### BF-ONB-02 — Démarrage

Depuis Platform, l'opérateur peut démarrer un nouvel onboarding. Le parcours crée les ressources nécessaires à sa réalisation sans proposer de création autonome en dehors de ce contexte.

#### BF-ONB-03 — Réalisation complète

L'opérateur Spore renseigne et valide lui-même **toutes** les étapes du wizard. Aucun relais de saisie vers un utilisateur client n'est prévu.

Pendant le parcours, l'opérateur peut consulter et modifier les informations, brouillons et résultats nécessaires à la configuration.

Les invitations Owner et Director ne sont émises **que** depuis ce parcours. L'invité n'accède pas au wizard : il accepte l'invitation et active son compte. La finalisation de l'établissement reste impossible tant qu'aucun Owner ou Director n'a un rattachement actif.

#### BF-ONB-03b — États fonctionnels

Hors du détail du wizard, Platform présente un **état fonctionnel unique** par onboarding. Lorsqu'plusieurs conditions coexistent, l'ordre de priorité est :

1. activé ;
2. en erreur ;
3. prêt à finaliser ;
4. en attente d'acceptation Owner/Director ;
5. en cours.

L'absence de parcours d'onboarding n'est aucun de ces états.

#### BF-ONB-04 — Enregistrement et reprise

Un onboarding non terminé peut être quitté puis repris depuis Platform sans recommencer les étapes déjà validées.

La liste et la fiche de l'établissement permettent d'identifier et de reprendre un onboarding incomplet.

#### BF-ONB-05 — Finalisation

La finalisation n'est proposée que lorsque l'état fonctionnel est « prêt à finaliser », ce qui suppose notamment qu'au moins un Owner ou Director a un rattachement actif.

Avant la finalisation, l'opérateur voit une synthèse des informations qui vont être validées.

La finalisation :

- marque l'onboarding comme terminé (état fonctionnel « activé ») ;
- rend l'organisation et l'établissement disponibles selon leur état opérationnel attendu ;
- empêche leur suppression au titre d'une ressource abandonnée ;
- présente clairement le résultat à l'opérateur.

#### BF-ONB-06 — Client exclu du wizard

Un utilisateur client, y compris avec le rôle client le plus élevé, ne peut ni démarrer, ni reprendre, ni modifier le wizard d'onboarding.

S'il a été invité comme Owner ou Director pendant le parcours, il n'en accepte que l'invitation et active son compte. Son accès ultérieur à Spore suit le parcours normal prévu pour un compte dont l'onboarding a été finalisé par l'opérateur.

#### BF-ONB-07 — Diagnostic hors parcours

En dehors de l'exécution de l'onboarding, les listes et fiches Platform présentent uniquement son état synthétique. Les données détaillées du parcours ne sont ouvertes que lorsque l'opérateur consulte ou reprend cet onboarding.

#### BF-ONB-08 — Traçabilité

Le démarrage et la finalisation d'un onboarding sont tracés avec l'opérateur, la date, les ressources concernées et le résultat.

---

### 9.3 Organisations

#### BF-ORG-01 — Liste

L'opérateur peut consulter les organisations par ensembles de taille maîtrisée et poursuivre la navigation dans les résultats.

Pour chaque organisation, la liste présente au minimum :

- son identifiant ;
- son nom ;
- son statut ;
- sa date de création.

#### BF-ORG-02 — Recherche et filtres

L'opérateur peut retrouver une organisation à partir de son nom ou de son identifiant et filtrer la liste par statut.

#### BF-ORG-03 — Détail

L'opérateur peut ouvrir une organisation et consulter :

- son identifiant ;
- son nom ;
- son statut ;
- ses dates principales de cycle de vie disponibles ;
- la liste de ses établissements.

#### BF-ORG-04 — Navigation liée

Depuis une organisation, l'opérateur peut ouvrir chacun de ses établissements et consulter les rattachements associés à son périmètre.

#### BF-ORG-05 — Suppression d'une organisation vide

L'opérateur peut supprimer une organisation uniquement lorsque :

- elle ne contient plus aucun établissement ;
- elle n'est jamais devenue opérationnelle ;
- elle ne contient aucune donnée métier ;
- aucune autre dépendance fonctionnelle n'empêche sa suppression.

La suppression d'un établissement ne supprime jamais automatiquement son organisation. La suppression de l'organisation constitue une action distincte.

---

### 9.4 Établissements

#### BF-EST-01 — Liste

L'opérateur peut consulter les établissements par ensembles de taille maîtrisée.

Pour chaque établissement, la liste présente au minimum :

- son identifiant ;
- son nom ;
- son organisation ;
- son statut ;
- son état synthétique d'onboarding.

#### BF-EST-02 — Recherche et filtres

L'opérateur peut rechercher un établissement par son nom ou son identifiant et filtrer la liste par :

- organisation ;
- statut ;
- état d'onboarding, lorsqu'il est disponible.

#### BF-EST-03 — Détail

L'opérateur peut ouvrir un établissement et consulter :

- son identifiant ;
- son nom ;
- son organisation ;
- son statut ;
- son fuseau horaire ;
- ses dates principales de cycle de vie disponibles ;
- son état synthétique d'onboarding ;
- ses rattachements utilisateurs.

#### BF-EST-04 — Diagnostic d'onboarding

Lorsque l'information existe, l'état synthétique d'onboarding permet de connaître :

- l'état fonctionnel, selon la priorité de BF-ONB-03b ;
- l'étape courante ou la dernière étape atteinte ;
- le mode d'entrée dans l'onboarding ;
- le dernier motif d'échec exploitable par le support.

Hors du parcours d'exécution ou de reprise **par un opérateur**, la plateforme ne montre ni contenu généré, ni brouillon détaillé, ni données intermédiaires de l'onboarding.

#### BF-EST-05 — Navigation liée

Depuis l'établissement, l'opérateur peut ouvrir son organisation et les utilisateurs qui y sont rattachés.

#### BF-EST-06 — Suppression d'un établissement abandonné

L'opérateur peut supprimer un établissement uniquement lorsque :

- son onboarding n'a jamais été terminé ;
- il n'a jamais été activé ou utilisé opérationnellement ;
- il ne contient aucun signal, plan d'action, commentaire ou autre donnée métier ;
- aucune autre dépendance fonctionnelle n'empêche sa suppression.

Un onboarding simplement en cours ou en erreur n'est pas considéré comme abandonné par défaut : l'opérateur décide explicitement de supprimer la ressource éligible.

---

### 9.5 Utilisateurs

#### BF-USR-01 — Liste

L'opérateur peut consulter les utilisateurs par ensembles de taille maîtrisée.

Pour chaque utilisateur, la liste présente au minimum :

- son identifiant ;
- son nom affiché ;
- son adresse e-mail ;
- son statut ;
- sa date de création.

#### BF-USR-02 — Recherche et filtres

L'opérateur peut retrouver un utilisateur à partir de son nom, de son adresse e-mail ou de son identifiant et filtrer la liste par statut.

#### BF-USR-03 — Détail

L'opérateur peut ouvrir un utilisateur et consulter :

- son identifiant ;
- son identité affichée ;
- son adresse e-mail ;
- son statut ;
- ses dates principales de cycle de vie disponibles ;
- ses rattachements aux établissements.

#### BF-USR-04 — Navigation liée

Depuis un utilisateur, l'opérateur peut ouvrir chaque établissement et chaque organisation auxquels un rattachement le relie.

#### BF-USR-05 — Données volontairement absentes

Le détail utilisateur ne présente pas :

- les informations détaillées de session ;
- les adresses réseau ;
- les appareils ou agents utilisateurs ;
- les secrets, jetons ou informations d'authentification ;
- l'état détaillé des consentements ;
- les contenus produits ou consultés par l'utilisateur.

---

### 9.6 Rattachements

Un rattachement décrit la relation d'un utilisateur avec un établissement client.

#### BF-RAT-01 — Consultation contextualisée

Les rattachements peuvent être consultés depuis :

- un utilisateur ;
- un établissement ;
- une organisation.

#### BF-RAT-02 — Informations affichées

Chaque rattachement présente au minimum :

- l'utilisateur ;
- l'établissement ;
- l'organisation ;
- le rôle client ;
- le statut du rattachement ;
- les unités métier couvertes, lorsqu'un périmètre spécifique existe.

#### BF-RAT-03 — Filtres

Selon le contexte de consultation, l'opérateur peut filtrer les rattachements par :

- utilisateur ;
- établissement ;
- organisation ;
- rôle ;
- statut.

#### BF-RAT-04 — Volume non borné

L'affichage d'une organisation, d'un établissement ou d'un utilisateur ne suppose jamais que tous ses rattachements puissent être présentés en une seule fois.

#### BF-RAT-05 — Lecture seule

Aucun rôle, statut, établissement ou périmètre d'un rattachement ne peut être modifié depuis la plateforme V1.

---

### 9.7 Recherche, listes et navigation

#### BF-NAV-01 — Recherche par ressource

Chaque rubrique dispose de sa propre recherche. La V1 ne fusionne pas organisations, établissements et utilisateurs dans une recherche unique.

#### BF-NAV-02 — Résultats maîtrisés

Les listes ne chargent pas un volume non borné de résultats. L'opérateur peut parcourir progressivement les résultats disponibles.

#### BF-NAV-03 — Stabilité de navigation

Le parcours des résultats doit éviter les doublons ou omissions provoqués par des créations ou mises à jour survenant pendant la consultation, dans la mesure nécessaire à un usage support normal.

#### BF-NAV-04 — Conservation du contexte

Lorsqu'un opérateur ouvre un détail puis revient à la liste, sa recherche et ses filtres courants sont conservés lorsque cela est raisonnablement possible.

#### BF-NAV-05 — Absence de résultat

Une recherche sans résultat affiche un état explicite distinguant :

- l'absence de données ;
- l'absence de résultat correspondant aux critères ;
- l'impossibilité temporaire de récupérer les données.

### 9.8 Nettoyage du cycle de vie

#### BF-NET-01 — Présentation de l'éligibilité

La fiche d'une organisation ou d'un établissement indique clairement si la ressource peut être supprimée. Lorsqu'elle ne l'est pas, l'action n'est pas proposée et le motif peut être compris par l'opérateur.

#### BF-NET-02 — Confirmation

Avant toute suppression, l'opérateur voit :

- la ressource concernée ;
- la raison de son éligibilité ;
- les données associées qui seront supprimées ;
- le caractère définitif de l'action.

La suppression nécessite une confirmation explicite et une justification.

#### BF-NET-03 — Vérification au moment de l'action

Les conditions de suppression sont vérifiées à nouveau lors de la confirmation. Si la ressource n'est plus éligible, aucune donnée n'est supprimée et l'opérateur en est informé.

#### BF-NET-04 — Cohérence du nettoyage

La suppression retire la ressource et les données exclusivement liées à son onboarding sans laisser de rattachement ou de donnée orpheline.

Elle ne supprime pas automatiquement :

- l'organisation parente d'un établissement ;
- les comptes utilisateurs ;
- une autre ressource autonome.

#### BF-NET-05 — Résultat et traçabilité

L'opérateur reçoit un résultat explicite de l'action. Qu'elle réussisse ou échoue, la tentative est tracée avec :

- l'opérateur ;
- la ressource ciblée ;
- la date ;
- la justification ;
- le résultat.

---

## 10. Règles fonctionnelles d'accès

| Situation | Espace client | Espace Platform |
|---|---:|---:|
| Utilisateur client sans accès Platform | Selon ses rattachements | Refusé |
| Rôle client élevé sans accès Platform | Selon ses rattachements | Refusé |
| Opérateur actif sans rattachement client | Refusé | Consultation et suppressions V1 autorisées |
| Opérateur actif avec rattachement client | Selon ses rattachements | Consultation et suppressions V1 autorisées |
| Opérateur désactivé avec rattachement client | Selon ses rattachements | Refusé |
| Compte utilisateur globalement inactif | Refusé | Refusé |

Règles complémentaires :

1. L'accès Platform ne permet jamais d'ouvrir un espace client comme si l'opérateur en était membre.
2. L'absence d'accès à un espace client n'empêche pas un opérateur actif de consulter ses métadonnées autorisées depuis Platform.
3. Le rôle détenu dans un espace client n'influence pas les droits Platform.
4. Un refus d'accès ne doit révéler aucune donnée interne issue de la ressource demandée.
5. Un utilisateur authentifié sans accès opérateur actif se voit refuser Platform, y compris s'il connaît l'adresse de l'espace.
6. Un opérateur sans rattachement client peut réaliser l'onboarding et consulter les métadonnées V1. Un opérateur qui possède par ailleurs des rattachements client les conserve, sans mélange des deux autorisations.

---

## 11. Données visibles et données exclues

| Domaine | Visible en V1 | Exclu de la V1 |
|---|---|---|
| Organisation | identité, nom, statut, dates disponibles, éligibilité à la suppression | autres modifications, données métier agrégées |
| Établissement | identité, organisation, statut, fuseau horaire, onboarding synthétique, éligibilité à la suppression | autres modifications, configuration détaillée, contenu métier |
| Utilisateur | identité, e-mail, statut, dates disponibles | secrets, sessions détaillées, appareils, consentements |
| Rattachement | relations, rôle, statut, périmètres métier | toute modification de droits |
| Onboarding | état fonctionnel synthétique (priorité BF-ONB-03b) dans les listes et fiches ; données du wizard uniquement pendant l'exécution ou la reprise **par un opérateur** | wizard côté client, secrets, informations étrangères au parcours |
| Signaux et plans | rien | texte, statut, historique, pièces jointes |
| Communications | rien | commentaires, messages, conversations |

Lorsqu'une information n'existe pas ou n'est pas applicable, l'interface l'indique explicitement plutôt que d'afficher une valeur trompeuse.

---

## 12. Parcours de référence

### Parcours P1 — Retrouver un utilisateur et comprendre ses accès

1. L'opérateur ouvre la rubrique Utilisateurs.
2. Il recherche par nom, e-mail ou identifiant.
3. Il ouvre la fiche correspondante.
4. Il consulte le statut du compte.
5. Il consulte les rattachements de l'utilisateur.
6. Pour chaque rattachement, il identifie l'organisation, l'établissement, le rôle, le statut et les unités métier concernées.
7. Il peut ouvrir l'établissement ou l'organisation liée.

### Parcours P2 — Diagnostiquer un onboarding

1. L'opérateur ouvre la rubrique Établissements.
2. Il recherche l'établissement.
3. Il ouvre sa fiche.
4. Il consulte l'état fonctionnel (priorité BF-ONB-03b), l'étape atteinte, le mode d'entrée et le dernier motif d'échec disponible.
5. Il identifie l'organisation concernée sans accéder aux données détaillées ou au contenu généré pendant l'onboarding.

### Parcours P3 — Explorer une organisation

1. L'opérateur ouvre la rubrique Organisations.
2. Il recherche l'organisation.
3. Il consulte son statut et ses informations principales.
4. Il parcourt ses établissements.
5. Il ouvre un établissement puis consulte ses rattachements utilisateurs.

### Parcours P4 — Basculer depuis un espace client

1. Un utilisateur à double contexte se connecte.
2. Il arrive dans son environnement client habituel.
3. Sur desktop Web, il choisit explicitement l'entrée « Spore Platform ».
4. L'interface change clairement de contexte.
5. Ses droits dans l'espace client ne sont ni étendus ni altérés. L'accès Platform n'utilise pas ses rattachements client.

### Parcours P5 — Accès révoqué

1. Un opérateur utilise la plateforme.
2. Son accès Platform est désactivé par le processus interne prévu à cet effet.
3. À sa prochaine action Platform, l'accès est refusé.
4. S'il possède par ailleurs des accès clients valides, ceux-ci restent utilisables normalement.

### Parcours P6 — Supprimer un établissement abandonné

1. L'opérateur ouvre un établissement dont l'onboarding n'a jamais été terminé.
2. La plateforme vérifie qu'il n'a jamais été activé et ne contient aucune donnée métier.
3. L'opérateur ouvre l'action de suppression.
4. Il consulte les conséquences, saisit une justification et confirme explicitement.
5. Les conditions sont vérifiées une dernière fois.
6. L'établissement et ses données d'onboarding exclusivement associées sont supprimés.
7. L'organisation parente et les comptes utilisateurs sont conservés.
8. Le résultat est affiché et tracé.

### Parcours P7 — Supprimer une organisation vide

1. L'opérateur ouvre une organisation ne contenant aucun établissement.
2. La plateforme vérifie qu'elle n'est jamais devenue opérationnelle et ne contient aucune donnée métier.
3. L'opérateur consulte les conséquences, saisit une justification et confirme explicitement.
4. Les conditions sont vérifiées une dernière fois.
5. L'organisation est supprimée et le résultat est affiché et tracé.

### Parcours P8 — Réaliser un onboarding

1. L'opérateur ouvre la rubrique Onboardings dans Platform (desktop Web).
2. Il démarre un nouvel onboarding.
3. Les ressources nécessaires au parcours sont créées dans ce contexte, sans rattachement de l'opérateur à l'établissement.
4. L'opérateur renseigne et valide lui-même toutes les étapes du wizard.
5. Il envoie les invitations Owner et Director depuis ce parcours uniquement.
6. Tant qu'aucun Owner ou Director n'a de rattachement actif, l'état fonctionnel est « en attente d'acceptation » et la finalisation est impossible.
7. L'invité accepte l'invitation et active son compte. Il n'ouvre pas le wizard.
8. Lorsque la configuration est complète et qu'au moins un Owner ou Director est actif, l'état passe à « prêt à finaliser ».
9. L'opérateur contrôle la synthèse puis finalise. L'état passe à « activé ».
10. L'organisation et l'établissement deviennent disponibles selon leur état opérationnel attendu. Le résultat est affiché et l'opération est tracée.
11. L'opérateur peut interrompre le parcours puis le reprendre depuis Platform sans recommencer les étapes déjà validées.

Aucune étape du wizard n'est réalisée depuis la page de connexion, un espace client, le Web hors desktop ou une application native.

---

## 13. États et cas limites

### 13.1 Ressource introuvable

La plateforme indique qu'une ressource n'existe pas ou n'est plus disponible, sans rediriger l'utilisateur vers un autre tenant ou une autre ressource supposée équivalente.

### 13.2 Donnée partielle

Si une donnée secondaire est indisponible, la plateforme distingue clairement :

- la valeur absente ;
- la valeur non applicable ;
- l'erreur temporaire de récupération.

### 13.3 Relation devenue inactive

Les rattachements inactifs restent identifiables comme tels lorsqu'ils font partie des données de cycle de vie consultables. Ils ne doivent pas être présentés comme des accès actuels.

### 13.4 Organisation ou établissement inactif

Son statut doit être visible et ne doit pas être déduit uniquement de l'état de ses utilisateurs ou rattachements.

### 13.5 Utilisateur sans rattachement

Un utilisateur sans rattachement reste consultable. L'interface indique explicitement qu'aucun rattachement n'est disponible.

### 13.6 Onboarding absent ou incomplet

L'absence de parcours d'onboarding est distinguée des états fonctionnels : en cours, en attente d'acceptation Owner/Director, prêt à finaliser, en erreur, activé.

### 13.7 Perte d'autorisation pendant l'utilisation

Si l'accès Platform est perdu pendant une session, la prochaine action protégée est refusée et aucune donnée Platform supplémentaire n'est affichée.

### 13.8 Ressource devenue non supprimable

Si une ressource devient active, termine son onboarding ou reçoit une donnée métier entre l'affichage de sa fiche et la confirmation, la suppression est refusée sans suppression partielle.

### 13.9 Échec partiel interdit

Une suppression ne doit pas laisser une ressource partiellement supprimée ou des dépendances orphelines. En cas d'échec, l'opérateur reçoit un résultat explicite et peut transmettre la référence de l'opération au support technique.

### 13.10 Accès direct à l'ancien parcours d'onboarding

Toute tentative d'accès à l'onboarding depuis un ancien point d'entrée, une page de connexion ou un lien non autorisé est refusée sans créer ni modifier de ressource.

### 13.11 Onboarding interrompu

Une interruption ne finalise pas l'onboarding. Les informations déjà validées restent disponibles pour une reprise par un opérateur actif depuis Platform.

### 13.12 Perte d'accès pendant l'onboarding

Si l'opérateur perd son accès Platform pendant le parcours, aucune nouvelle étape ne peut être consultée ou validée. L'onboarding reste incomplet et pourra être repris par un opérateur actif.

### 13.13 Acceptation sans wizard

Un Owner ou Director qui accepte une invitation pendant un onboarding incomplet n'est pas orienté vers le wizard. Il attend la finalisation par un opérateur, ou accède à l'espace client une fois l'établissement activé.

---

## 14. Exigences de qualité fonctionnelle

### QF-01 — Clarté du contexte

Le contexte « Spore Platform » doit être identifiable sans ambiguïté sur toutes ses pages.

### QF-02 — Efficacité support

Les parcours de référence doivent être réalisables sans connaître l'organisation ou l'établissement actif de l'opérateur.

### QF-03 — Cohérence

Une même information métier, par exemple le statut d'un utilisateur ou le rôle d'un rattachement, est présentée avec le même sens partout dans Platform.

### QF-04 — Traçabilité des erreurs

Une erreur fonctionnelle ou temporaire doit pouvoir être corrélée à une demande de support sans exposer de secret ni de donnée sensible à l'utilisateur.

### QF-05 — Protection des données

Aucune donnée exclue du périmètre ne doit apparaître dans les listes, détails, résultats de recherche ou messages d'erreur.

### QF-06 — Montée en charge fonctionnelle

L'utilisateur ne doit pas dépendre du chargement exhaustif d'une collection pour consulter ou retrouver une ressource.

### QF-07 — Desktop Web uniquement

Le périmètre de validation de la V1 couvre l'expérience **desktop Web**. Platform n'est pas une surface native ni une surface Web hors desktop. Elle ne doit pas alourdir les parcours ou la navigation des applications natives.

### QF-08 — Intégrité des suppressions

Une suppression est réalisée intégralement ou n'a aucun effet. Elle ne doit jamais laisser un état fonctionnel incohérent.

### QF-09 — Traçabilité

Chaque tentative de suppression doit pouvoir être attribuée à un opérateur, une ressource, une date, une justification et un résultat.

Le démarrage et la finalisation d'un onboarding doivent également pouvoir être attribués à un opérateur, une date, des ressources et un résultat.

### QF-10 — Point d'entrée maîtrisé

La page de connexion reste limitée à l'accès aux comptes existants. Elle ne permet aucune création d'organisation, d'établissement ou d'onboarding.

---

## 15. Critères d'acceptation transverses

| ID | Étant donné | Lorsque | Alors |
|---|---|---|---|
| CA-01 | un opérateur actif sans aucun rattachement client | il ouvre Platform | il peut consulter les ressources autorisées |
| CA-02 | un opérateur actif sans rattachement à l'établissement A | il consulte A depuis Platform | il voit uniquement les métadonnées prévues par la V1 |
| CA-03 | ce même opérateur sans rattachement à A | il tente d'ouvrir A dans l'espace client | l'accès reste refusé |
| CA-04 | un utilisateur client avec le rôle client le plus élevé | il tente d'ouvrir Platform | l'accès est refusé s'il n'est pas opérateur actif |
| CA-05 | un utilisateur à double contexte, sur desktop Web | il se connecte | il conserve son arrivée client habituelle et peut ouvrir explicitement Platform |
| CA-06 | un utilisateur exclusivement opérateur, sur desktop Web | il se connecte | il est orienté vers Platform |
| CA-06b | un opérateur, hors desktop Web ou en application native | il se connecte ou navigue | aucune interface Platform n'est proposée |
| CA-07 | un opérateur dont l'accès vient d'être désactivé | il effectue une nouvelle action Platform | l'accès est refusé sans attendre une nouvelle connexion |
| CA-08 | un opérateur désactivé possédant un rattachement client valide | il revient dans son espace client | ses droits client restent inchangés |
| CA-09 | une organisation possède de nombreux établissements | l'opérateur ouvre sa fiche | il peut parcourir les établissements sans chargement exhaustif obligatoire |
| CA-10 | un utilisateur possède de nombreux rattachements | l'opérateur ouvre sa fiche | il peut parcourir les rattachements sans tous les embarquer en une seule fois |
| CA-11 | une recherche ne correspond à aucune ressource | l'opérateur la lance | un état « aucun résultat » explicite est affiché |
| CA-12 | une récupération échoue temporairement | l'opérateur consulte une liste ou une fiche | l'erreur est distinguée d'une absence de données |
| CA-13 | un onboarding est en erreur | l'opérateur ouvre l'établissement | il voit le dernier motif d'échec prévu, sans contenu intermédiaire sensible |
| CA-14 | un établissement n'a aucun onboarding | l'opérateur ouvre l'établissement | l'absence est distinguée d'un onboarding en attente ou en erreur |
| CA-15 | un opérateur consulte un utilisateur | il ouvre son détail | aucun secret, jeton, détail de session, appareil ou contenu métier n'est exposé |
| CA-16 | un opérateur utilise l'application mobile native | il navigue dans l'application | aucune entrée ou interface Platform n'est proposée |
| CA-17 | un opérateur se trouve dans Platform | il consulte plusieurs pages | le contexte interne reste clairement identifiable |
| CA-18 | un opérateur consulte une ressource | il cherche une action de modification | seules les suppressions explicitement prévues par la V1 peuvent être proposées |
| CA-19 | un établissement n'a jamais terminé son onboarding, n'a jamais été actif et ne contient aucune donnée métier | l'opérateur consulte sa fiche | la suppression peut être engagée |
| CA-20 | un établissement a terminé son onboarding, a déjà été actif ou contient une donnée métier | l'opérateur consulte sa fiche | aucune suppression n'est possible |
| CA-21 | un onboarding est simplement en cours ou en erreur | l'établissement reste éligible techniquement | aucune suppression ne se produit sans décision et confirmation explicites de l'opérateur |
| CA-22 | un établissement éligible devient actif ou reçoit une donnée métier avant confirmation | l'opérateur confirme | la suppression est refusée sans effet partiel |
| CA-23 | un établissement éligible est supprimé | l'action réussit | ses données d'onboarding exclusivement associées disparaissent, mais son organisation et les comptes utilisateurs sont conservés |
| CA-24 | une organisation est vide, n'est jamais devenue opérationnelle et ne contient aucune donnée métier | l'opérateur confirme sa suppression | l'organisation est supprimée |
| CA-25 | une organisation contient encore un établissement ou est déjà devenue opérationnelle | l'opérateur consulte sa fiche | sa suppression est impossible |
| CA-26 | une suppression est tentée | elle réussit ou échoue | l'opérateur, la cible, la date, la justification et le résultat sont tracés |
| CA-27 | un opérateur actif se trouve dans Platform | il démarre un onboarding | le parcours est créé et accessible à cet opérateur |
| CA-28 | un onboarding est incomplet | un opérateur actif le reprend depuis Platform | les étapes déjà validées sont conservées et le parcours peut continuer |
| CA-29 | un opérateur est en état « prêt à finaliser » | il demande la finalisation | une synthèse est présentée avant validation définitive ; la finalisation est refusée tant qu'aucun Owner ou Director n'a de rattachement actif |
| CA-30 | un onboarding est finalisé | l'opérateur consulte les ressources produites | l'organisation et l'établissement sont disponibles dans leur état opérationnel attendu et ne sont plus supprimables comme ressources abandonnées |
| CA-31 | un utilisateur client, quel que soit son rôle | il tente d'accéder au wizard d'onboarding | l'accès est refusé |
| CA-31b | un Owner ou Director invité pendant l'onboarding | il accepte l'invitation | son compte peut être activé ; il n'accède pas au wizard |
| CA-32 | une personne consulte la page de connexion | elle cherche à démarrer un onboarding | aucune entrée vers l'onboarding n'est disponible |
| CA-33 | une personne utilise un ancien lien direct vers l'onboarding sans accès Platform | elle ouvre le lien | l'accès est refusé sans création ni modification de ressource |
| CA-34 | un opérateur cherche à créer directement une organisation ou un établissement | il se trouve hors du parcours d'onboarding | aucune création autonome n'est proposée |
| CA-35 | un onboarding est démarré ou finalisé | l'action aboutit ou échoue | l'opérateur, la date, les ressources et le résultat sont tracés |
| CA-36 | un onboarding a plusieurs conditions simultanées | l'opérateur consulte l'état synthétique | un seul état fonctionnel s'affiche, selon la priorité : activé, en erreur, prêt à finaliser, en attente d'acceptation, en cours |

---

## 16. Hors périmètre conditionnel et déclencheurs d'évolution

Les fonctions suivantes ne sont pas anticipées dans la V1. Leur ajout doit déclencher un nouveau cadrage fonctionnel et de sécurité.

### 16.1 Toute nouvelle action de modification

L'exécution de l'onboarding et les suppressions encadrées de ressources abandonnées sont les seules mutations de la V1. Toute autre action, par exemple suspendre un compte, révoquer des sessions ou réouvrir un onboarding terminé, nécessite un nouveau cadrage.

Avant son ajout, il faudra définir au minimum :

- les opérateurs autorisés ;
- la confirmation requise ;
- la justification éventuelle ;
- la traçabilité complète de l'action ;
- les possibilités de retour arrière ;
- le besoin de renforcer temporairement l'authentification.

### 16.2 Premier accès à un contenu métier client

Avant tout accès à un signal, plan, commentaire, message, pièce jointe ou contenu métier généré en dehors du parcours d'onboarding, il faudra définir :

- le cas support précis ;
- le niveau de sensibilité ;
- la justification de l'accès ;
- la visibilité de cet accès pour le client ;
- la traçabilité des consultations ;
- la durée et le périmètre de l'autorisation.

### 16.3 Différenciation des opérateurs

La création de profils internes distincts ne sera justifiée que lorsque des personnes devront réellement disposer de droits différents.

### 16.4 Recherche globale ou analytique

Une recherche multi-ressources ou un tableau de bord ne sera envisagé qu'à partir d'usages réels permettant d'identifier :

- les recherches fréquentes ;
- les indicateurs utiles ;
- les volumes à traiter ;
- les décisions que ces informations doivent permettre de prendre.

---

## 17. Conditions de réussite de la V1

La V1 est considérée comme fonctionnellement réussie si :

1. un opérateur peut identifier rapidement une organisation, un établissement ou un utilisateur ;
2. il peut démarrer, réaliser, reprendre et terminer intégralement un onboarding depuis Platform ;
3. aucun utilisateur client ne peut entrer dans le parcours d'onboarding ;
4. il peut comprendre les relations et statuts des ressources sans accès aux outils techniques ;
5. il peut diagnostiquer le niveau d'avancement ou d'échec d'un onboarding ;
6. seules les ressources abandonnées et explicitement éligibles peuvent être supprimées ;
7. aucun contenu métier client ou secret technique n'est exposé ;
8. les droits Platform et les droits clients restent strictement indépendants ;
9. les parcours restent utilisables avec un volume important de ressources ;
10. les opérations de cycle de vie sont cohérentes et tracées ;
11. l'espace Platform est clairement séparé du produit client, limité au **desktop Web**, et absent des applications natives et du Web hors desktop.

---

## 18. Décisions actées

| Sujet | Décision V1 |
|---|---|
| Nature du produit | control plane minimal pour onboarding, exploration et nettoyage avant activation |
| Mode d'accès | utilisateurs internes explicitement autorisés |
| Niveau de droit | onboarding interne, consultation uniforme et deux suppressions strictement encadrées |
| Ressources | onboardings, organisations, établissements, utilisateurs, rattachements |
| Contenu métier client | exclu |
| Actions de modification | onboarding complet et suppression d'un établissement abandonné ou d'une organisation vide jamais devenue opérationnelle |
| Impersonation | exclue |
| Recherche | séparée par type de ressource |
| Rattachements | consultés dans leur contexte, sans chargement non borné |
| Tableau de bord | exclu |
| Accès natif mobile | exclu |
| Accès Web hors desktop | exclu |
| Accès desktop Web | inclus |
| Gestion des opérateurs dans l'interface | exclue |
| Droits internes différenciés | exclus |
| Audit général des lectures | exclu à ce stade |
| Traçabilité des suppressions V1 | obligatoire |
| Traçabilité du démarrage et de la finalisation d'un onboarding | obligatoire |
| Audit des futures modifications | obligatoire avant leur introduction |
| Point d'entrée onboarding | Platform uniquement |
| Réalisation du wizard | opérateur Spore intégralement |
| Owner / Director pendant l'onboarding | acceptation d'invitation et activation de compte uniquement ; pas de wizard |
| Activation établissement | bloquée tant qu'aucun Owner ou Director n'a de rattachement actif |
| Invitations Owner / Director | uniquement dans le parcours d'onboarding |
| Autorisation Platform | distincte des permissions tenant ; pas d'élévation croisée |
| Memberships d'un opérateur | possibles séparément, sans lien avec l'autorisation Platform |
| Page de connexion | aucune entrée vers l'onboarding |
| Création organisation/établissement | uniquement au travers de l'onboarding |
| Point d'entrée d'un utilisateur à double contexte | espace client habituel, puis bascule explicite (desktop Web) |
| Point d'entrée d'un opérateur sans accès client | Platform (desktop Web) |

---

## 19. Définition de « terminé »

Le besoin V1 est livré lorsque :

- tous les besoins fonctionnels marqués BF sont couverts ;
- tous les critères d'acceptation CA sont vérifiés ;
- les exclusions de données sont contrôlées sur les listes, détails, recherches et erreurs ;
- les scénarios d'autorisation du tableau de la section 10 sont validés ;
- aucun parcours Platform ne dépend d'un rattachement client actif ;
- les parcours P6 et P7 et les critères CA-19 à CA-26 sont validés ;
- le parcours P8 et les critères CA-27 à CA-36 sont validés ;
- les suppressions impossibles sont refusées sans effet partiel ;
- chaque tentative de suppression est tracée ;
- le démarrage et la finalisation des onboardings sont tracés ;
- la page de connexion et les espaces clients ne présentent aucune entrée vers l'onboarding ;
- aucune fonction hors périmètre n'est exposée, même partiellement ;
- les parcours P1 à P8 peuvent être exécutés de bout en bout sur **desktop Web** ;
- aucune entrée Platform n'est visible dans les applications mobiles natives ni sur le Web hors desktop.
