# Expression de besoin fonctionnelle — Plateforme interne Spore V1

**Statut :** validé pour cadrage fonctionnel  
**Version :** 1.0  
**Date :** 17 septembre 2026  
**Périmètre :** V1 minimale et évolutive

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

La plateforme interne Spore V1 est un **explorateur opérationnel en lecture seule**.

Elle permet à un opérateur interne autorisé de retrouver une organisation, un établissement ou un utilisateur, de comprendre leurs relations et de consulter les principaux états nécessaires au support.

Elle n'est ni :

- un tableau de bord de pilotage ;
- un espace d'administration métier pour le compte d'un client ;
- un outil d'accès aux contenus opérationnels des clients ;
- un mode permettant de contourner les droits normaux d'un espace client.

---

## 4. Objectifs de la V1

### 4.1 Objectifs principaux

La V1 doit permettre de :

1. rechercher et consulter l'ensemble des organisations Spore ;
2. rechercher et consulter l'ensemble des établissements Spore ;
3. rechercher et consulter l'ensemble des utilisateurs Spore ;
4. comprendre les rattachements entre utilisateurs, établissements et organisations ;
5. visualiser les rôles, statuts et périmètres associés à ces rattachements ;
6. identifier l'état synthétique de l'onboarding d'un établissement ;
7. naviguer entre ces informations sans dépendre d'un établissement actif ;
8. garantir qu'un accès interne à la plateforme ne confère aucun droit supplémentaire dans les espaces clients.

### 4.2 Résultat attendu

Un opérateur interne doit pouvoir répondre, sans accès direct aux données techniques, à des questions telles que :

- « Cette organisation existe-t-elle et quel est son statut ? »
- « Quels établissements appartiennent à cette organisation ? »
- « Où en est l'onboarding de cet établissement ? »
- « Ce compte utilisateur est-il actif ? »
- « Dans quels établissements cet utilisateur intervient-il ? »
- « Quel rôle possède-t-il dans chacun d'eux ? »
- « Sur quelles unités métier son accès porte-t-il ? »

---

## 5. Principes fonctionnels non négociables

### PF-01 — Séparation des contextes

L'espace interne Spore et les espaces clients sont deux contextes distincts. L'utilisateur doit toujours savoir dans lequel il se trouve.

### PF-02 — Absence d'élévation implicite

Être autorisé à utiliser la plateforme interne ne donne aucun droit supplémentaire dans une organisation ou un établissement client.

### PF-03 — Lecture seule

La V1 ne permet aucune modification depuis l'espace interne.

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

---

## 6. Acteurs

### 6.1 Opérateur Spore actif

Utilisateur interne autorisé à consulter la plateforme.

En V1, tous les opérateurs actifs disposent du même périmètre fonctionnel de lecture.

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
- consultation des organisations ;
- consultation des établissements ;
- consultation des utilisateurs ;
- consultation des rattachements entre utilisateurs et établissements ;
- recherche par ressource ;
- filtres adaptés à chaque liste ;
- navigation contextuelle entre ressources liées ;
- affichage synthétique de l'état d'onboarding d'un établissement ;
- gestion des états d'absence de résultat, d'accès refusé et de donnée indisponible ;
- accès depuis la version Web de Spore.

### 7.2 Exclus

- création, modification, suspension ou suppression d'une organisation ;
- création, modification, suspension ou suppression d'un établissement ;
- création, modification, suspension ou suppression d'un utilisateur ;
- modification d'un rôle, d'un statut ou d'un périmètre d'accès client ;
- invitation d'un utilisateur ;
- réinitialisation de mot de passe ;
- révocation de sessions ;
- relance ou réparation d'un onboarding ;
- impersonation d'un utilisateur ;
- accès aux contenus métier d'un client ;
- accès détaillé aux sessions, adresses réseau ou appareils ;
- consultation des consentements ;
- recherche globale mélangeant plusieurs types de ressources ;
- tableau de bord, indicateurs ou statistiques Platform ;
- export de données ;
- gestion autonome des opérateurs depuis l'interface ;
- interface Platform dans les applications mobiles natives ;
- rôles internes différenciés ou droits personnalisables par opérateur ;
- journal d'audit général des consultations.

---

## 8. Organisation fonctionnelle de l'espace

L'espace comporte trois entrées principales :

1. **Organisations** ;
2. **Établissements** ;
3. **Utilisateurs**.

Les rattachements sont consultés dans le contexte d'une organisation, d'un établissement ou d'un utilisateur. Ils ne nécessitent pas une rubrique principale supplémentaire dans la navigation.

L'entrée dans l'espace doit présenter une identité visuelle et un libellé suffisamment explicites pour éviter toute confusion avec un espace client.

La page d'entrée oriente directement vers une liste utile. La V1 ne comporte pas de page d'accueil analytique.

---

## 9. Besoins fonctionnels détaillés

### 9.1 Accès à la plateforme

#### BF-ACC-01 — Visibilité de l'accès

Un utilisateur autorisé voit un accès explicite à « Spore Platform » dans la version Web.

Un utilisateur non autorisé ne voit pas cet accès.

#### BF-ACC-02 — Accès direct

Lorsqu'un utilisateur tente d'ouvrir directement l'espace Platform :

- un opérateur actif y accède ;
- tout autre utilisateur reçoit un refus sans divulgation de données internes.

#### BF-ACC-03 — Utilisateur à double contexte

Après connexion, un utilisateur disposant aussi d'un accès client conserve son arrivée habituelle dans le contexte client. Il rejoint « Spore Platform » par une action explicite.

#### BF-ACC-04 — Utilisateur exclusivement interne

Après connexion, un utilisateur qui ne dispose d'aucun accès client actif mais possède un accès Platform actif est orienté vers l'espace interne.

#### BF-ACC-05 — Désactivation de l'accès

La désactivation d'un opérateur prend effet lors de sa prochaine tentative d'accès ou action dans l'espace Platform. Elle ne doit pas attendre une nouvelle connexion.

#### BF-ACC-06 — Version mobile native

Les applications mobiles natives ne présentent ni entrée, ni navigation, ni interface Platform en V1.

---

### 9.2 Organisations

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

---

### 9.3 Établissements

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

- l'état courant ;
- l'étape courante ou la dernière étape atteinte ;
- le mode d'entrée dans l'onboarding ;
- le dernier motif d'échec exploitable par le support.

La plateforme ne montre ni contenu généré, ni brouillon détaillé, ni données intermédiaires de l'onboarding.

#### BF-EST-05 — Navigation liée

Depuis l'établissement, l'opérateur peut ouvrir son organisation et les utilisateurs qui y sont rattachés.

---

### 9.4 Utilisateurs

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

### 9.5 Rattachements

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

### 9.6 Recherche, listes et navigation

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

---

## 10. Règles fonctionnelles d'accès

| Situation | Espace client | Espace Platform |
|---|---:|---:|
| Utilisateur client sans accès Platform | Selon ses rattachements | Refusé |
| Rôle client élevé sans accès Platform | Selon ses rattachements | Refusé |
| Opérateur actif sans rattachement client | Refusé | Autorisé en lecture |
| Opérateur actif avec rattachement client | Selon ses rattachements | Autorisé en lecture |
| Opérateur désactivé avec rattachement client | Selon ses rattachements | Refusé |
| Compte utilisateur globalement inactif | Refusé | Refusé |

Règles complémentaires :

1. L'accès Platform ne permet jamais d'ouvrir un espace client comme si l'opérateur en était membre.
2. L'absence d'accès à un espace client n'empêche pas un opérateur actif de consulter ses métadonnées autorisées depuis Platform.
3. Le rôle détenu dans un espace client n'influence pas les droits Platform.
4. Un refus d'accès ne doit révéler aucune donnée interne issue de la ressource demandée.

---

## 11. Données visibles et données exclues

| Domaine | Visible en V1 | Exclu de la V1 |
|---|---|---|
| Organisation | identité, nom, statut, dates disponibles | modifications, données métier agrégées |
| Établissement | identité, organisation, statut, fuseau horaire, onboarding synthétique | configuration détaillée, contenu métier |
| Utilisateur | identité, e-mail, statut, dates disponibles | secrets, sessions détaillées, appareils, consentements |
| Rattachement | relations, rôle, statut, périmètres métier | toute modification de droits |
| Onboarding | état, étape, mode d'entrée, dernier motif d'échec | brouillons, charges utiles, contenu IA détaillé |
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
4. Il consulte l'état, l'étape atteinte, le mode d'entrée et le dernier motif d'échec disponible.
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
3. Il choisit explicitement l'entrée « Spore Platform ».
4. L'interface change clairement de contexte.
5. Ses droits dans l'espace client ne sont ni étendus ni altérés.

### Parcours P5 — Accès révoqué

1. Un opérateur utilise la plateforme.
2. Son accès Platform est désactivé par le processus interne prévu à cet effet.
3. À sa prochaine action Platform, l'accès est refusé.
4. S'il possède par ailleurs des accès clients valides, ceux-ci restent utilisables normalement.

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

### 13.6 Onboarding absent

L'absence de parcours d'onboarding est distinguée d'un onboarding en attente, en erreur ou terminé.

### 13.7 Perte d'autorisation pendant l'utilisation

Si l'accès Platform est perdu pendant une session, la prochaine action protégée est refusée et aucune donnée Platform supplémentaire n'est affichée.

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

### QF-07 — Web uniquement

Le périmètre de validation de la V1 couvre l'expérience Web. La plateforme ne doit pas alourdir les parcours ou la navigation des applications natives.

---

## 15. Critères d'acceptation transverses

| ID | Étant donné | Lorsque | Alors |
|---|---|---|---|
| CA-01 | un opérateur actif sans aucun rattachement client | il ouvre Platform | il peut consulter les ressources autorisées |
| CA-02 | un opérateur actif sans rattachement à l'établissement A | il consulte A depuis Platform | il voit uniquement les métadonnées prévues par la V1 |
| CA-03 | ce même opérateur sans rattachement à A | il tente d'ouvrir A dans l'espace client | l'accès reste refusé |
| CA-04 | un utilisateur client avec le rôle client le plus élevé | il tente d'ouvrir Platform | l'accès est refusé s'il n'est pas opérateur actif |
| CA-05 | un utilisateur à double contexte | il se connecte | il conserve son arrivée client habituelle et peut ouvrir explicitement Platform |
| CA-06 | un utilisateur exclusivement opérateur | il se connecte | il est orienté vers Platform |
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
| CA-18 | un opérateur consulte une ressource | il cherche une action de modification | aucune mutation n'est disponible dans la V1 |

---

## 16. Hors périmètre conditionnel et déclencheurs d'évolution

Les fonctions suivantes ne sont pas anticipées dans la V1. Leur ajout doit déclencher un nouveau cadrage fonctionnel et de sécurité.

### 16.1 Première action de modification

Exemples : suspendre un compte, révoquer des sessions, relancer un onboarding.

Avant ajout, il faudra définir au minimum :

- les opérateurs autorisés ;
- la confirmation requise ;
- la justification éventuelle ;
- la traçabilité complète de l'action ;
- les possibilités de retour arrière ;
- le besoin de renforcer temporairement l'authentification.

### 16.2 Premier accès à un contenu métier client

Avant tout accès à un signal, plan, commentaire, message, pièce jointe ou contenu généré, il faudra définir :

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
2. il peut comprendre leurs relations et leurs statuts sans accès aux outils techniques ;
3. il peut diagnostiquer le niveau d'avancement ou d'échec d'un onboarding ;
4. aucune action ne lui permet de modifier une donnée client ;
5. aucun contenu métier client ou secret technique n'est exposé ;
6. les droits Platform et les droits clients restent strictement indépendants ;
7. les parcours restent utilisables avec un volume important de ressources ;
8. l'espace Web Platform est clairement séparé du produit client et absent des applications natives.

---

## 18. Décisions actées

| Sujet | Décision V1 |
|---|---|
| Nature du produit | explorateur opérationnel interne |
| Mode d'accès | utilisateurs internes explicitement autorisés |
| Niveau de droit | lecture seule uniforme |
| Ressources | organisations, établissements, utilisateurs, rattachements |
| Contenu métier client | exclu |
| Actions de modification | exclues |
| Impersonation | exclue |
| Recherche | séparée par type de ressource |
| Rattachements | consultés dans leur contexte, sans chargement non borné |
| Tableau de bord | exclu |
| Accès natif mobile | exclu |
| Accès Web | inclus |
| Gestion des opérateurs dans l'interface | exclue |
| Droits internes différenciés | exclus |
| Audit général des lectures | exclu à ce stade |
| Audit des futures modifications | obligatoire avant leur introduction |
| Point d'entrée d'un utilisateur à double contexte | espace client habituel, puis bascule explicite |
| Point d'entrée d'un opérateur sans accès client | Platform |

---

## 19. Définition de « terminé »

Le besoin V1 est livré lorsque :

- tous les besoins fonctionnels marqués BF sont couverts ;
- tous les critères d'acceptation CA sont vérifiés ;
- les exclusions de données sont contrôlées sur les listes, détails, recherches et erreurs ;
- les scénarios d'autorisation du tableau de la section 10 sont validés ;
- aucun parcours Platform ne dépend d'un rattachement client actif ;
- aucune fonction hors périmètre n'est exposée, même partiellement ;
- les parcours P1 à P5 peuvent être exécutés de bout en bout sur le Web ;
- aucune entrée Platform n'est visible dans les applications mobiles natives.

