# Cadrage fonctionnel — Dataset de démonstration Spore

## Mama Shelter Nice

| Propriété | Valeur |
|---|---|
| Statut | Validé pour implémentation du corpus scenario-first |
| Version | 1.6 |
| Date de référence | 22 septembre 2026 |
| Organisation de production | [DEMO] SPORE |
| Établissement | Mama Shelter Nice |
| Produit | Spore — application mobile et version desktop |
| Périmètre temporel historique | 23 septembre 2025 au 22 septembre 2026 |
| Périmètre temporel futur | Jusqu'au 31 mars 2027 |

---

## 1. Objet du document

Ce document définit le cadrage fonctionnel du dataset de démonstration de Spore pour Mama Shelter Nice.

Le dataset doit représenter un établissement vivant sur une année complète, avec suffisamment de profondeur pour démontrer :

1. la remontée et le traitement de situations opérationnelles de terrain ;
2. l'agrégation de plusieurs observations décrivant un même incident ;
3. l'identification de problèmes récurrents à partir de plusieurs signaux distincts ;
4. la transformation de l'historique opérationnel en plans d'action réutilisables ;
5. la coordination entre équipes, rôles et périmètres métier ;
6. la préparation d'opérations et d'événements futurs ;
7. les différences de visibilité et d'action selon les rôles et les scopes.

Le document décrit le résultat fonctionnel attendu. Il ne prescrit pas l'architecture du seed, son découpage en fichiers ou sa stratégie d'implémentation interne.

---

## 2. Objectifs produit

### 2.1 Proposition de valeur à démontrer

Le dataset doit montrer que Spore permet de :

> **Voir ce qui se passe, comprendre ce qui se répète, agir collectivement et anticiper les opérations futures.**

La démonstration repose sur trois narrations complémentaires :

| Axe narratif | Poids éditorial indicatif | Finalité |
|---|---:|---|
| **A — Terrain vers résolution** | ≈ 45 % | Montrer le cycle Observation → Signal → coordination → plan d'action → résolution |
| **B — Intelligence opérationnelle** | ≈ 40 % | Montrer comment plusieurs signaux sur la durée révèlent une récurrence et conduisent à une amélioration |
| **C — Organisation proactive** | ≈ 15 % | Montrer le catalogue, les schedules, le planning et les opérations futures |

Ces proportions sont des règles éditoriales, pas des quotas stricts en base de données. Les axes A et B doivent être presque équivalents et nettement plus présents que l'axe C.

### 2.2 Golden paths

Le corpus doit contenir au minimum les trois chemins de démonstration suivants.

#### Golden path 1 — Incident chambre

1. Une personne sur le terrain remonte un problème dans une chambre.
2. Une seconde observation confirme le même incident.
3. Les observations sont agrégées dans un même Signal.
4. Le Signal est qualifié et routé vers Maintenance.
5. Un plan d'action est créé ou sélectionné.
6. Les tâches sont exécutées, commentées et validées.
7. Le Signal est résolu.

Scénario canonique : chambre fictive 318, dysfonctionnement de climatisation constaté le 21 septembre 2026, deux observations rapprochées provenant de la Réception et de l'équipe Hôtel, intervention Maintenance, validation puis résolution. Ce scénario utilise le plan réutilisable « Diagnostic climatisation d'une chambre ».

#### Golden path 2 — Problème récurrent

1. Plusieurs incidents similaires surviennent dans des chambres ou périodes différentes.
2. Chaque incident possède son propre Signal.
3. Les Signals sont reliés à un même Operational Pattern.
4. La récurrence devient visible dans l'analyse.
5. Une procédure éprouvée est capitalisée sous forme de plan réutilisable.

Scénario canonique : incidents de climatisation distincts en chambres fictives 214, 426 et 318, répartis entre novembre 2025, juillet 2026 et septembre 2026. Ils alimentent le Pattern « Dysfonctionnements de climatisation dans les chambres » sans être agrégés dans un même Signal.

#### Golden path 3 — Séminaire ou événement futur

1. Un plan du catalogue est sélectionné pour une opération future.
2. L'exécution coordonne plusieurs pôles.
3. Les tâches couvrent préparation technique, restauration, accueil, communication et événementiel.
4. L'opération apparaît dans le planning jusqu'au 31 mars 2027.

Scénario canonique : « Séminaire Horizon Azur » — événement privé fictif prévu le 12 novembre 2026 pour 80 participants dans les Ateliers 1 et 2. Le plan coordonne Événements, Restaurant, Maintenance, Hôtel et Communication, avec préparation audiovisuelle, signalétique, accueil, restauration et clôture.

---

## 3. Principes directeurs

Le dataset doit respecter les principes suivants :

- **réalisme opérationnel** : les situations doivent être plausibles pour un hôtel, un restaurant, un rooftop, une piscine et des espaces événementiels ;
- **cohérence métier** : les statuts, transitions, assignations, dates et relations doivent raconter une histoire compréhensible ;
- **densité maîtrisée** : le corpus doit paraître vivant sans saturer les écrans ni rendre les données illisibles ;
- **variété** : les données ne doivent pas être uniformes, parfaites ou artificiellement symétriques ;
- **traçabilité** : chaque Signal provient d'au moins une observation ;
- **capitalisation** : les Patterns et les plans réutilisables doivent résulter de situations visibles dans l'historique ;
- **déterminisme temporel** : le présent du dataset reste fixé au 22 septembre 2026 ;
- **isolation** : le seed concerne uniquement Mama Shelter Nice et ne doit pas altérer d'autres établissements ;
- **confidentialité** : le seed n'introduit aucune donnée personnelle réelle, donnée client réelle ou information interne non publique ; les seuls comptes réels sont les comptes de gouvernance explicitement préexistants ou configurés pour le local.

### 3.1 Niveau de prescription et ordre de priorité

Le document distingue trois niveaux d'exigence :

| Niveau | Portée | Règle d'implémentation |
|---|---|---|
| **Figé** | Nombres annoncés comme exacts, listes numérotées, identifiants de production, comptes de gouvernance, snapshot, plages temporelles, golden paths et table des événements publics | À reproduire sans interprétation ni substitution silencieuse |
| **Contraint** | Fourchettes, proportions approximatives, tonalité, saisonnalité et familles de scénarios | À respecter dans les bornes et selon les règles indiquées |
| **Éditorial** | Noms fictifs, formulations et détails narratifs non listés | Liberté limitée par le réalisme, la confidentialité et la cohérence du corpus |

En cas de doute, l'ordre de priorité est :

1. les contraintes réelles du modèle et des enums du repo, qui doivent être vérifiées et documentées ;
2. les exigences figées et les critères d'acceptation du présent document ;
3. les tableaux de référence ;
4. les exemples narratifs.

Une incompatibilité entre le repo et une exigence figée doit être signalée dans le plan d'implémentation. Elle n'autorise jamais l'implémenteur à inventer un statut, un rôle, un sujet, un volume ou une relation de remplacement.

---

## 4. Périmètre temporel

### 4.1 Snapshot fixe

Le dataset représente l'état de l'établissement au :

> **22 septembre 2026 à 23:59:59, fuseau Europe/Paris**

Cette borne reste fixe, quelle que soit la date réelle d'exécution du seed. Toutes les dates fonctionnelles du document sont exprimées dans le fuseau `Europe/Paris`, puis converties vers le format de stockage attendu par le repo. Les périodes historiques et futures sont inclusives de leurs dates de début et de fin.

### 4.2 Historique

L'historique couvre :

> **23 septembre 2025 à 00:00 → 22 septembre 2026**

Il doit restituer une année complète d'activité, avec :

- saisonnalité ;
- périodes de forte et faible activité ;
- incidents isolés ;
- problèmes récurrents ;
- opérations internes ;
- événements publics ou privés ;
- changements d'état des utilisateurs et des objets métier.

### 4.3 Futur

Le planning futur couvre la période :

> **23 septembre 2026 → 31 mars 2027**

Il combine :

- des occurrences proches matérialisées à partir de schedules ;
- des exécutions one-shot déjà planifiées ;
- des événements publics gelés dans le corpus ;
- des séminaires et privatisations fictifs ;
- des échéances saisonnières, RH, opérationnelles et de maintenance.

---

## 5. Établissement et référentiel organisationnel

Description validée de l'établissement :

> Mama Shelter Nice est un hôtel lifestyle de 102 chambres combinant hébergement, restaurant et bar, petit-déjeuner et brunch, rooftop avec piscine saisonnière, parking avec bornes électriques et espaces dédiés aux séminaires et événements. Son exploitation mobilise les équipes Hôtel, Petit déjeuner, Restaurant, Maintenance, Communication, Événements & privatisations et RH, avec une forte coordination interservices autour de l'expérience client, de la restauration, de la maintenance et de l'événementiel.

Cette description est déjà configurée en production. Le seed la valide mais ne la réécrit pas.

### 5.1 Business Units

Le dataset utilise exactement les sept pôles suivants :

| Business Unit | `catalog_key` | Nature fonctionnelle | Exemples de responsabilités |
|---|---|---|---|
| Hôtel | `hotel` | Opérationnel | Réception, chambres, expérience client, ménage, linge |
| Petit déjeuner | `petit_dejeuner` | Opérationnel | Buffet, ouverture, mise en place, service matinal, stocks |
| Restaurant | `restaurant` | Opérationnel | Service, bar, cuisine, caisse, ouverture et fermeture |
| Maintenance | `maintenance` | Transversal | CVC, plomberie, électricité, équipements, bâtiment, sécurité technique |
| Communication | `communication` | Transversal | Contenus, e-réputation, communication locale, réseaux sociaux |
| Événements & privatisations | `evenements_privatisations` | Transversal | Séminaires, ateliers, logistique, coordination client et interne |
| RH | `rh` | Transversal | Planning, intégration, formation, paie et suivi administratif RH |

Règles :

- utiliser systématiquement les entrées existantes du catalogue Spore ;
- ne pas créer de Business Unit spécifique au dataset si le catalogue couvre le besoin ;
- ne pas ajouter de pôle Comptabilité ;
- conserver la commercialisation comme Activity Subject des pôles concernés, sans créer un huitième pôle ;
- ne pas modéliser Piscine, Rooftop, Cuisine ou Ateliers comme des Business Units.

Descriptions validées :

- **Hôtel** — Le pôle Hôtel regroupe les opérations liées à l'accueil, à la réception, aux séjours, aux chambres, au ménage et au linge. Il assure le suivi de l'expérience client, des arrivées et départs, de la préparation des chambres et des incidents rencontrés pendant le séjour, en coordination avec la Maintenance et les autres pôles concernés.
- **Petit déjeuner** — Le pôle Petit déjeuner est responsable du service matinal quotidien, ouvert de 7 h à 11 h, depuis la préparation et l'ouverture du buffet jusqu'au débarrassage et à la clôture. Il couvre la mise en place, le réassort, les produits dédiés, la propreté de l'espace et l'accueil des clients pendant ce service. Les déjeuners, dîners, brunchs, activités du bar et du rooftop relèvent du pôle Restaurant, avec lequel il coordonne les stocks, la cuisine et les transitions de service.
- **Restaurant** — Le pôle Restaurant est responsable des déjeuners, dîners et brunchs ainsi que des activités du bar, de la cuisine et du rooftop. Il couvre la préparation, la mise en place, le service, l'accueil client, les stocks, les équipements, les ouvertures, les fermetures et le suivi des caisses, en coordination avec Maintenance, Communication et Événements & privatisations.
- **Maintenance** — Le pôle Maintenance est un service transversal qui intervient auprès de l'ensemble des pôles et des espaces de l'établissement. Il assure le bon fonctionnement des bâtiments, installations et équipements, prend en charge les incidents techniques, organise la maintenance préventive et coordonne les contrôles de sécurité ainsi que les prestataires externes.
- **Communication** — Le pôle Communication est un service transversal chargé de l'image et de la visibilité de l'établissement. Il pilote les contenus, les réseaux sociaux, la communication commerciale et locale, l'e-réputation ainsi que la promotion des offres et événements, en coordination avec les pôles concernés.
- **Événements & privatisations** — Le pôle Événements & privatisations organise les séminaires, réunions, célébrations et privatisations accueillis dans les Ateliers, Studios et autres espaces de l'établissement. Il coordonne la préparation, la logistique, les besoins techniques, l'accueil, la restauration et le suivi client avec les équipes concernées.
- **RH** — Le pôle Ressources humaines est un service transversal chargé de l'accompagnement des équipes et du suivi des collaborateurs. Il couvre le recrutement, l'intégration, la formation, les plannings, l'administration du personnel et les besoins de staffing, en coordination avec les managers des différents pôles.

### 5.2 Activity Subjects

Tous les Activity Subjects existants du catalogue pour ces sept pôles sont activés.

En production, ces pôles et sujets ont déjà été créés par l'onboarding : le seed les valide et les réutilise sans les dupliquer ni réécrire leur configuration. Le bootstrap local reproduit la même sélection à partir du catalogue du repo.

Chaque Activity Subject activé doit être utilisé par au moins un objet historique ou futur cohérent. Les volumes peuvent différer selon les sujets, mais aucun pôle ni aucun sujet activé ne doit rester purement décoratif. Les labels et descriptions catalogue restent la source de vérité : aucun sujet custom ne doit être créé pour contourner le catalogue.

Lors du plan d'implémentation, les clés exactes des Activity Subjects disponibles dans la version du repo doivent être extraites et figées dans le manifeste. Une évolution ultérieure du catalogue ne doit pas ajouter silencieusement de nouveaux sujets au dataset : elle déclenche une mise à jour explicite du manifeste.

### 5.3 Operational Units

Les 18 unités opérationnelles suivantes sont créées :

| # | Operational Unit | Usage principal |
|---:|---|---|
| 1 | Réception / Lobby | Arrivées, attente, accueil, passations de shift |
| 2 | Chambres | Problèmes d'hébergement génériques |
| 3 | Circulations chambres | Couloirs et parties communes des étages |
| 4 | Restaurant RDC | Petit-déjeuner, brunch, déjeuner et dîner |
| 5 | Bar central | Service bar et équipements associés |
| 6 | Cuisine | Production restauration |
| 7 | Plonge / économat | Back-office restauration, stocks et lavage |
| 8 | Rooftop | Restauration et bar extérieurs |
| 9 | Piscine | Zone piscine et équipements associés |
| 10 | Atelier 1 | Réunions et événements |
| 11 | Atelier 2 | Réunions et événements |
| 12 | Breakroom | Réunions et événements |
| 13 | Studio 1 | Réunions et événements |
| 14 | Studio 2 | Réunions et événements |
| 15 | Parking | Accès, disponibilité et sécurité |
| 16 | Bornes électriques | Équipements de recharge du parking |
| 17 | Locaux techniques | Maintenance et équipements techniques |
| 18 | Back-office administratif | RH, coordination et opérations administratives |

Une chambre précise n'est pas une Operational Unit. Elle est représentée par :

- `operational_unit = Chambres` ;
- une localisation textuelle fictive, par exemple `Chambre 318`.

Les combinaisons commerciales d'espaces événementiels ne doivent pas créer d'unités supplémentaires si elles correspondent à l'association de plusieurs salles existantes.

---

## 6. Utilisateurs, rôles et scopes

### 6.1 Population cible

Le dataset contient :

| État | Nombre |
|---|---:|
| Membres actifs | **62** |
| Anciens membres désactivés | **4** |
| Invitations en cours | **2** |
| **Total représenté dans l'établissement** | **68** |

En production, l'OWNER et un premier DIRECTOR existent déjà et utilisent des identités réelles de gouvernance. Ils comptent dans les 62 membres actifs mais ne sont ni créés ni administrés par le seed. Tous les autres utilisateurs et toutes les personnes citées dans le corpus sont fictifs.

### 6.2 Répartition des 62 membres actifs

Le retrait du pôle Comptabilité ne réduit pas la taille d'équipe validée. Les quatre postes initialement envisagés pour ce pôle sont réalloués aux équipes opérationnelles et RH.

| Périmètre | Managers | Staff | Autres rôles | Total |
|---|---:|---:|---:|---:|
| Hôtel | 3 | 9 | — | 12 |
| Petit déjeuner | 2 | 5 | — | 7 |
| Restaurant | 5 | 11 | — | 16 |
| Maintenance | 2 | 6 | — | 8 |
| Communication | 2 | 3 | — | 5 |
| Événements & privatisations | 2 | 4 | — | 6 |
| RH | 2 | 3 | — | 5 |
| Direction | — | — | 2 DIRECTOR | 2 |
| Organisation | — | — | 1 OWNER | 1 |
| **Total** | **18** | **41** | **3** | **62** |

Les lignes par pôle comptent chaque personne une seule fois selon son scope principal. Les scopes secondaires définis en section 6.4 ne modifient pas ces totaux.

Les rôles utilisés sont exclusivement les rôles Spore :

- `OWNER` ;
- `DIRECTOR` ;
- `MANAGER` ;
- `STAFF`.

Les intitulés métier servent à construire les personas et les données narratives ; ils ne doivent pas créer de nouveaux rôles d'autorisation.

En production, le seed crée exactement **60 membres actifs** :

- 1 second DIRECTOR fictif ;
- les 59 MANAGER et STAFF décrits dans le tableau ;
- l'OWNER et le premier DIRECTOR préexistants complètent la population pour atteindre 62 actifs.

### 6.3 Personas connectables

Dix comptes doivent être facilement utilisables en démonstration :

| Persona | Intérêt démonstratif |
|---|---|
| Director | Vision globale de l'établissement |
| Manager Hôtel | Management hébergement et visibilité du pôle Hôtel |
| Staff Hôtel | Expérience terrain avec permissions restreintes |
| Manager Restaurant | Gestion F&B et coordination des shifts |
| Staff Restaurant | Expérience terrain d'un second pôle opérationnel |
| Manager Petit déjeuner | Activité matinale dédiée et articulation avec Restaurant |
| Manager Maintenance | Qualification et traitement d'interventions techniques |
| Manager Communication | Contenus, e-réputation et coordination événementielle |
| Manager Événements | Plans multi-pôles et opérations futures |
| Manager RH | Activité support, planning et suivi d'équipe |

L'OWNER réel existe dans l'établissement mais n'est pas un persona principal de la démonstration opérationnelle. Le persona Director alimenté par le corpus correspond au second DIRECTOR fictif créé par le seed ; aucune activité historique fictive n'est attribuée aux deux comptes réels préexistants.

### 6.4 Utilisateurs multi-scopes

Cinq utilisateurs actifs possèdent plusieurs scopes, uniquement pour des cas métier cohérents :

| Profil | Scope principal | Scope secondaire |
|---|---|---|
| Manager F&B matin | Petit déjeuner | Restaurant |
| Manager F&B transversal | Restaurant | Petit déjeuner |
| Manager banqueting | Événements & privatisations | Restaurant |
| Manager Communication événementielle | Communication | Événements & privatisations |
| Manager Événements communication | Événements & privatisations | Communication |

Tous les autres membres restent mono-scope, hors rôles globaux dont la visibilité découle du modèle d'autorisation existant.

### 6.5 Anciennes personnes et invitations

Les quatre membres désactivés doivent conserver un historique cohérent :

- activités antérieures à leur désactivation ;
- assignations ou commentaires historiques toujours attribués correctement ;
- aucune activité postérieure à leur départ.

Les deux invitations en cours ne doivent pas être utilisées comme auteurs d'activité ou assignees actifs avant acceptation.

### 6.6 Identités générées et accès de démonstration

Le roster est déterministe : mêmes identités, mêmes rôles et mêmes scopes à chaque exécution.

Règles :

- les noms générés sont fictifs, plausibles et ne reprennent aucun salarié connu de Mama Shelter Nice ;
- les adresses des comptes fictifs utilisent un domaine réservé non distribuable, compatible avec les validateurs du produit ;
- seuls les 10 personas de démonstration disposent de moyens de connexion configurables ;
- les autres comptes actifs ne doivent pas recevoir d'invitation ou d'email réel ;
- les secrets de connexion ne figurent jamais dans le dépôt ni dans le corpus ;
- les quatre anciens membres et les deux invitations en cours utilisent également des identités fictives stables ;
- aucune activité synthétique n'est attribuée à l'OWNER réel, au premier DIRECTOR réel ou à leurs équivalents locaux de gouvernance.

Les noms, emails, rôles, scopes et dates de désactivation ou d'invitation doivent être définis dans un manifeste versionné. L'utilisation d'un générateur de personnes non déterministe au moment du seed est interdite.

Le seed de production gère donc **66 identités fictives** : 60 membres actifs, 4 désactivés et 2 invités. Les 2 comptes réels préexistants portent le total de l'établissement à 68 personnes représentées.

---

## 7. Dimensionnement global

Sauf mention explicite d'une fourchette ou d'un ordre de grandeur, les volumes de cette section sont des quantités exactes à produire. L'implémentation ne doit pas choisir arbitrairement une valeur plus basse ou plus haute.

| Objet | Cible |
|---|---:|
| Signals | **420 exactement** |
| Observations | **692 exactement** |
| Exécutions historiques de plans d'action | **260 exactement** |
| Plans réutilisables au catalogue | **21 exactement** |
| Operational Patterns | **24 exactement** |
| Schedules récurrents | **28 exactement** |
| Exécutions futures visibles au snapshot | **180 exactement** |
| Membres actifs | **62 exactement** |
| Membres désactivés | **4 exactement** |
| Invitations en cours | **2 exactement** |

Les Signals constituent le principal indicateur de dimensionnement. Les 692 observations se déduisent de la distribution précisée en section 8.2 ; elles ne doivent pas être atteintes par création de contenu artificiel ou déconnecté des scénarios.

### 7.1 Répartition fonctionnelle des Signals

Le corpus contient exactement 420 Signals.

| Pôle principalement responsable | Nombre exact | Part approximative |
|---|---:|---:|
| Hôtel | 105 | 25 % |
| Restaurant | 85 | 20 % |
| Petit déjeuner | 50 | 12 % |
| Maintenance | 85 | 20 % |
| Communication | 30 | 7 % |
| Événements & privatisations | 40 | 10 % |
| RH | 25 | 6 % |
| **Total** | **420** | **100 %** |

Le pôle principalement responsable correspond au routage métier du Signal. L'observation source peut provenir d'un autre pôle, notamment pour les incidents techniques, les événements et les situations client cross-pôles.

Les données textuelles doivent être suffisamment variées pour éviter un corpus manifestement généré : pas de séries de messages identiques avec uniquement un numéro de chambre ou une date modifiés, et pas de duplication exacte d'une observation hors scénario explicitement agrégé.

### 7.2 Familles narratives

Chaque Signal appartient à exactement une famille narrative. Les pannes et problèmes ponctuels ne sont pas le fond du corpus.

| Famille | Nombre exact | Rôle |
|---|---:|---|
| Incident opérationnel | 74 | Panne, rupture ou incident ponctuel qui ne fonde pas encore une amélioration. Les incidents triviaux, au plus 74, sont tous dans cette famille. Les deux Signals `interesting` techniques disparus en font partie. |
| Expérience client | 52 | Séjour, accueil, attente vécue, remarque de chambre ou de salle |
| Qualité de service | 50 | Service, buffet, file, commande, écart de prestation |
| Prévention | 44 | Contrôle, saison, maintenance préventive, sujet pris avant l'incident |
| Inefficacité de processus | 44 | Rotation des chambres, linge, caisse, passation, réassort mal calé |
| Coordination cross-pôles | 50 | Au moins deux pôles sur le même sujet, souvent une agrégation |
| Amélioration continue | 98 | Signals reliés à un Pattern puis à un plan réutilisable et à ses exécutions |
| Opportunité | 8 | Tendance, attente, idée ou amélioration qui ne justifie pas encore un plan ; ce sont huit des dix `interesting` |
| **Total** | **420** | |

Les 170 Signals de Patterns sont une relation, pas une neuvième famille.

### 7.3 Ancrage Mama Shelter Nice

Chaque scénario, pas seulement les exemples, se passe dans l'exploitation de l'établissement : pôles, 18 unités, saison rooftop et piscine, et événements publics figés. Le nom « Mama Shelter Nice » ou « Mama Shelter » n'apparaît dans aucun titre, `issue_focus` ou libellé d'exécution. Les noms publics figés, dont Mama Club Sonore et La Bringue à Mémé, restent autorisés.

Aucun générateur générique ni texte de repli ne produit les lignes manquantes. Chaque scénario est un enregistrement authored portant au minimum `activity`, `narrative_family` et `relations` (observations, Signal, Pattern s'il existe, plan s'il existe, exécutions s'il en existe).

---

## 8. Observations

### 8.1 Ton rédactionnel

Les observations doivent ressembler à des messages terrain, pas à des tickets techniques.

Caractéristiques attendues :

- français naturel ;
- vocabulaire opérationnel ;
- longueurs variables ;
- formulations parfois brèves ;
- abréviations légères possibles ;
- aucune accumulation de fautes artificielles ou caricaturales.

Exemples de ton attendu :

> La clim de la 318 souffle mais ne refroidit plus, le client revient vers 18 h.

> Il manque encore les jus d'orange sur le buffet, deuxième fois cette semaine à l'ouverture.

> Le ClickShare de l'Atelier 2 ne détecte aucun écran depuis ce matin.

### 8.2 Relation aux Signals

Chaque Signal possède au moins une observation source.

La répartition exacte est :

| Configuration | Nombre de Signals | Nombre d'observations sources |
|---|---:|---:|
| 1 observation source | 294 | 294 |
| 2 observations agrégées | 105 | 210 |
| 3 observations agrégées | 7 | 21 |
| 4 observations agrégées | 7 | 28 |
| 5 observations agrégées | 7 | 35 |
| **Total produisant un Signal** | **420** | **588** |

En complément, exactement **104 observations** sont informatives ou non actionnables et ne produisent aucun Signal. Le corpus contient ainsi 588 observations sources de Signals + 104 observations sans Signal = **692 observations**, dont environ 15 % sans Signal.

Cette exception doit rester crédible : information de service, point de vigilance sans anomalie, constat finalement non confirmé ou message ne nécessitant aucune action.

### 8.3 Médias

Aucun média n'est généré automatiquement :

- **0 média d'observation** ;
- aucun faux justificatif ;
- aucune photo commerciale réutilisée comme preuve d'un incident.

Les médias pourront être ajoutés manuellement après le seed.

---

## 9. Signals

### 9.1 État du feed au snapshot

La distribution cible au 22 septembre 2026 est :

| Statut | Nombre exact |
|---|---:|
| Resolved | 350 |
| Canceled | 15 |
| Open | 22 |
| In progress | 23 |
| Interesting | 10 |
| **Total** | **420** |

Cette distribution est obligatoire. Si le modèle réel ne permet pas de représenter l'un de ces statuts, le plan d'implémentation doit signaler l'incompatibilité avant de modifier la distribution ; il ne doit pas choisir silencieusement une approximation.

Les 10 Signals `interesting` sont une veille sans plan : huit opportunités (tendances, remarques, attentes clients, idées) et au plus deux incidents techniques momentanément disparus. Ils couvrent les sept pôles. Un Signal `interesting` n'est jamais relié à un plan ou à une exécution.

### 9.2 Qualification et routage

Parmi les Signals ouverts :

- exactement **2** restent non qualifiés avec un routage non assigné ;
- les autres Signals actifs possèdent un routage cohérent avec leur sujet, leur unité opérationnelle et leur pôle responsable ;
- les Signals cross-pôles doivent refléter une responsabilité principale compréhensible, sans assignation arbitraire.

### 9.3 Agrégation d'observations

L'agrégation représente plusieurs observations décrivant **le même incident**, au même endroit et dans une temporalité compatible.

Exemple :

- 08:12 — Réception : « La 318 signale que la clim ne refroidit plus. »
- 08:34 — Hôtel : « Même souci clim en 318 pendant le passage étage. »

Ces observations alimentent un seul Signal.

Le dataset doit préserver explicitement la trace de l'agrégation selon les mécanismes existants du produit, notamment lorsque le modèle s'appuie sur un résultat de candidat agrégé et un lien de source de type agrégation.

### 9.4 Agrégation et Pattern : distinction obligatoire

| Concept | Signification | Exemple |
|---|---|---|
| Agrégation | Plusieurs observations du même incident | Deux équipes signalent la même panne en chambre 318 le même matin |
| Pattern | Plusieurs incidents distincts mais similaires | Pannes de climatisation en chambres 214, 426 et 318 à plusieurs mois d'intervalle |

Un Pattern ne doit pas fusionner rétroactivement plusieurs incidents distincts dans un même Signal.

### 9.5 Demandes de résolution

Le corpus contient exactement **12 demandes de résolution** sur l'année :

- 9 approuvées ;
- 3 rejetées ;
- parmi les rejets, au moins 1 est suivi d'une reprise du sujet, d'une nouvelle demande puis d'une résolution valide.

---

## 10. Operational Patterns et intelligence opérationnelle

### 10.1 Volume et cycle de vie

Le dataset contient exactement **24 Operational Patterns**.

Il doit montrer plusieurs états du cycle de vie :

- **22 Patterns actifs** ;
- **1 Pattern merged** ;
- **1 Pattern retired**.

Les états merged et retired restent minoritaires afin de démontrer la maturité du produit sans polluer la lecture des analytics.

### 10.2 Référentiel des 24 Patterns

Les 24 Patterns nominaux sont les suivants :

| # | Pattern | Statut | Domaine principal |
|---:|---|---|---|
| 1 | Dysfonctionnements de climatisation dans les chambres | Active | Hôtel / Maintenance |
| 2 | Linge manquant ou livré en retard | Active | Hôtel |
| 3 | Chambres non prêtes à l'heure d'arrivée | Active | Hôtel |
| 4 | Attente excessive au check-in | Active | Hôtel |
| 5 | Anomalies de facturation ou de caisse à la réception | Active | Hôtel |
| 6 | Ruptures récurrentes au buffet du petit-déjeuner | Active | Petit déjeuner |
| 7 | Pannes des équipements café et buffet | Active | Petit déjeuner / Maintenance |
| 8 | Écarts de propreté sur le buffet et sa zone | Active | Petit déjeuner |
| 9 | Attente excessive au restaurant | Active | Restaurant |
| 10 | Erreurs de service ou de commande | Active | Restaurant |
| 11 | Ruptures de stock bar ou restaurant | Active | Restaurant |
| 12 | Écarts lors des clôtures de caisse | Active | Restaurant |
| 13 | Évacuations lentes en cuisine ou plonge | Active | Restaurant / Maintenance |
| 14 | Défaillances d'équipements du rooftop | Active | Restaurant / Maintenance |
| 15 | Incidents d'exploitation de la piscine | Active | Hôtel / Maintenance |
| 16 | Fiabilité audiovisuelle et réseau des Ateliers | Active | Événements / Maintenance |
| 17 | Défauts d'éclairage dans les chambres et circulations | Active | Hôtel / Maintenance |
| 18 | Petites fuites sanitaires récurrentes | Active | Maintenance |
| 19 | Indisponibilité des bornes électriques | Active | Maintenance |
| 20 | Défauts de signalétique événementielle | Active | Événements / Communication |
| 21 | Thèmes négatifs récurrents dans les avis clients | Active | Communication |
| 22 | Sous-effectif ou besoin de formation récurrent | Active | RH |
| 23 | Incidents ClickShare isolés | Merged dans le Pattern 16 | Événements / Maintenance |
| 24 | Signalétique temporaire de lancement de l'établissement | Retired | Communication |

Exactement **170 Signals distincts** doivent contribuer aux Patterns actifs. Aucun Pattern actif ne repose sur moins de 3 Signals distincts et les Patterns majeurs, notamment climatisation, buffet, attente restaurant et audiovisuel, doivent couvrir plusieurs mois.

### 10.3 Cohérence des Patterns

Chaque Pattern doit :

- s'appuyer sur plusieurs Signals distincts et plausibles ;
- couvrir une temporalité suffisante pour justifier la récurrence ;
- utiliser des critères métier compréhensibles ;
- apporter une lecture utile, et pas simplement regrouper des objets portant des mots similaires ;
- pouvoir conduire, pour certains cas, à une action d'amélioration ou à un plan réutilisable.

La liste ci-dessus est le socle fonctionnel attendu. Elle ne doit pas être remplacée par une liste générée librement ; seuls les libellés peuvent être légèrement ajustés pour respecter les contraintes réelles du modèle.

---

## 11. Plans d'action et exécutions historiques

### 11.1 Exécutions historiques

Le corpus contient exactement **260 exécutions historiques**.

Répartition éditoriale :

| Origine | Nombre exact |
|---|---:|
| Signal vers plan d'action | 180 |
| Routine, préventif ou opération planifiée | 80 |

La répartition est bien de 180 + 80 = 260 : les exécutions issues de Signals restent majoritaires.

Cette répartition garantit que Spore est d'abord montré comme un outil de traitement et d'apprentissage opérationnels, et non comme un simple calendrier de tâches.

### 11.2 États et imperfections réalistes

Distribution exacte des 260 exécutions historiques au snapshot :

| État | Nombre exact |
|---|---:|
| Done | 218 |
| Canceled | 16 |
| In progress | 10 |
| Pending validation | 10 |
| Scheduled ou en retard | 6 |
| **Total** | **260** |

Les 6 exécutions « scheduled ou en retard » sont exactement 6 exécutions en `pending_validation` au snapshot, chacune avec un retard de 2 à 7 jours inclus. Aucune exécution `scheduled`, `in_progress` ou `pending_validation` n'a plus de 7 jours de retard. Toute exécution plus ancienne est `done` ou `canceled`. Le tri du feed d'exécution n'est pas modifié : ces six cartes montent en tête.

Le corpus contient en complément :

- exactement 10 tâches ignorées avec une raison explicite ;
- exactement 3 cas réouverts au cours de leur cycle de vie ;
- des durées et niveaux d'avancement variables.

Les annulations, réouvertures et tâches ignorées doivent être justifiées par le scénario. Elles ne servent pas uniquement à remplir des états techniques.

### 11.3 Catalogue de plans réutilisables

Le catalogue contient exactement **21 plans réutilisables** :

| Catégorie | Cible |
|---|---:|
| Plans actifs | 18 |
| Plans inactifs | 3 |
| Plans mono-pôle | 13 |
| Plans cross-pôles | 8 |

Le catalogue nominal est figé ainsi :

| # | Plan réutilisable | Type | Statut | Pôle(s) principal(aux) |
|---:|---|---|---|---|
| 1 | Diagnostic climatisation d'une chambre | Mono-pôle | Active | Maintenance |
| 2 | Traitement d'une fuite sanitaire légère | Mono-pôle | Active | Maintenance |
| 3 | Traitement d'un défaut d'éclairage | Mono-pôle | Active | Maintenance |
| 4 | Remise en service d'une borne électrique | Mono-pôle | Active | Maintenance |
| 5 | Rattrapage d'une chambre non prête | Mono-pôle | Active | Hôtel |
| 6 | Traitement d'une rupture de linge | Mono-pôle | Active | Hôtel |
| 7 | Réassort critique du buffet petit-déjeuner | Mono-pôle | Active | Petit déjeuner |
| 8 | Remise en conformité du buffet | Mono-pôle | Active | Petit déjeuner |
| 9 | Traitement d'un incident de service restaurant | Mono-pôle | Active | Restaurant |
| 10 | Analyse d'une anomalie de clôture de caisse | Mono-pôle | Active | Restaurant |
| 11 | Traitement d'un avis client négatif | Mono-pôle | Active | Communication |
| 12 | Vérification d'un équipement ClickShare | Mono-pôle | Active | Maintenance |
| 13 | Préparation d'un séminaire | Cross-pôles | Active | Événements, Restaurant, Maintenance, Hôtel |
| 14 | Préparation d'une privatisation | Cross-pôles | Active | Événements, Restaurant, Hôtel |
| 15 | Préparation d'un événement DJ | Cross-pôles | Active | Événements, Restaurant, Communication, Maintenance |
| 16 | Ouverture de saison rooftop et piscine | Cross-pôles | Active | Restaurant, Hôtel, Maintenance, Communication |
| 17 | Traitement d'un incident client majeur | Cross-pôles | Active | Hôtel, Maintenance, Communication |
| 18 | Ancienne procédure d'accueil d'un groupe | Cross-pôles | Inactive | Hôtel, Événements |
| 19 | Ancienne check-list d'incident audiovisuel | Cross-pôles | Inactive | Événements, Maintenance |
| 20 | Ancienne procédure de communication de crise événementielle | Cross-pôles | Inactive | Communication, Événements |
| 21 | Routines planning RH | Mono-pôle | Active | RH |

Le plan 21 est le plan actif du pôle RH. Les schedules 26 et 27 et les opérations RH ponctuelles s'y rattachent.

Certains plans historiques doivent être explicitement capitalisés dans le catalogue après plusieurs utilisations ou après l'identification d'un Pattern :

> problème récurrent → méthode éprouvée → plan réutilisable.

Au moins 5 plans actifs doivent être reliés narrativement à un Pattern du référentiel, dont obligatoirement les plans 1, 7, 11, 12 et 16.

Règles minimales de contenu :

- un plan mono-pôle contient 3 à 6 tâches ordonnées, avec un résultat attendu et un rôle responsable pour chaque tâche ;
- un plan cross-pôles contient 5 à 9 tâches, mobilise effectivement au moins deux pôles, identifie un pôle coordinateur et se termine par une validation ou une clôture ;
- deux plans distincts ne peuvent pas partager une liste de tâches strictement identique ;
- une tâche ne doit pas être créée uniquement pour augmenter le volume.

Séquences obligatoires pour les plans structurants :

| Plan | Séquence minimale attendue |
|---|---|
| Diagnostic climatisation d'une chambre | Prendre en charge → diagnostiquer → corriger ou escalader → tester → informer l'Hôtel → clôturer |
| Réassort critique du buffet petit-déjeuner | Constater la rupture → vérifier le stock → définir une substitution si nécessaire → réassortir → confirmer la remise en service |
| Traitement d'un avis client négatif | Qualifier le thème → identifier le pôle concerné → préparer la réponse → suivre l'action corrective → clôturer |
| Vérification d'un équipement ClickShare | Vérifier les branchements → redémarrer → tester l'affichage et le son → confirmer le statut → consigner le résultat |
| Préparation d'un séminaire | Valider le brief → affecter les espaces → vérifier l'audiovisuel → organiser la restauration → préparer signalétique et accueil → effectuer le contrôle final → clôturer après l'événement |
| Ouverture de saison rooftop et piscine | Inspecter les espaces → réaliser les contrôles techniques et de sécurité → préparer stocks et équipements → mettre à jour la communication → valider l'ouverture |

### 11.4 Visibilité par scope

Le catalogue doit contenir des cas permettant de démontrer les différences de visibilité entre :

- un Staff mono-scope ;
- un Manager ;
- un utilisateur multi-scopes ;
- un Director.

Il doit notamment exister des plans actifs utilisables par un Staff dans son scope et des plans cross-pôles qui ne lui sont pas proposés lorsque les règles produit l'interdisent.

---

## 12. Reviews d'exécution

Sur les 218 exécutions terminées, **153** possèdent une review, soit environ 70 %.

Distribution exacte parmi les reviews :

| Note | Nombre exact | Part approximative |
|---|---:|---:|
| 5 étoiles | 69 | 45 % |
| 4 étoiles | 54 | 35 % |
| 3 étoiles | 15 | 10 % |
| 2 étoiles | 8 | 5 % |
| 1 étoile | 4 | 3 % |
| 0 étoile | 3 | 2 % |
| **Total** | **153** | **100 %** |

Principes :

- environ 80 % des reviews sont à 4 ou 5 étoiles ;
- toutes les notes de 0 à 5 sont néanmoins représentées ;
- les mauvaises notes doivent correspondre à des exécutions imparfaites ou à un résultat insatisfaisant ;
- le corpus ne doit jamais donner l'impression d'une satisfaction artificiellement parfaite.

---

## 13. Schedules récurrents

### 13.1 Volume

Le dataset contient exactement **28 schedules récurrents**.

La stratégie consiste à créer peu de routines réellement significatives, plutôt qu'un très grand nombre de routines quotidiennes qui noieraient le planning.

### 13.2 Référentiel des 28 schedules

Les 28 schedules nominaux sont :

| # | Routine | Pôle principal | Fréquence ou période | Chronologie |
|---:|---|---|---|---|
| 1 | Ouverture Restaurant | Restaurant | Quotidienne | Partagée |
| 2 | Fermeture Restaurant | Restaurant | Quotidienne | Partagée |
| 3 | Passation de shift Réception et contrôle caisse | Hôtel | Quotidienne | Partagée |
| 4 | Ouverture du service petit-déjeuner | Petit déjeuner | Quotidienne | Partagée |
| 5 | Clôture du service petit-déjeuner | Petit déjeuner | Quotidienne | Partagée |
| 6 | Préparation du brunch | Restaurant | Hebdomadaire, dimanche | Partagée |
| 7 | Préparation opérationnelle Super Sunday | Événements | Hebdomadaire, dimanche | Partagée |
| 8 | Revue des stocks Restaurant | Restaurant | Hebdomadaire | Partagée |
| 9 | Inventaire Bar central | Restaurant | Hebdomadaire | Partagée |
| 10 | Contrôle des stocks buffet petit-déjeuner | Petit déjeuner | Hebdomadaire | Partagée |
| 11 | Audit qualité des chambres prêtes | Hôtel | Hebdomadaire | Individuelle |
| 12 | Revue linge et coordination ménage | Hôtel | Hebdomadaire | Partagée |
| 13 | Revue e-réputation | Communication | Hebdomadaire | Individuelle |
| 14 | Revue éditoriale des contenus | Communication | Hebdomadaire | Partagée |
| 15 | Préparation communication des événements à venir | Communication | Hebdomadaire | Partagée |
| 16 | Revue du pipeline séminaires et privatisations | Événements | Hebdomadaire | Partagée |
| 17 | Contrôle audiovisuel et connectivité des Ateliers | Maintenance | Hebdomadaire | Partagée |
| 18 | Contrôle d'exploitation du rooftop | Restaurant | Hebdomadaire, saison avril-octobre | Partagée |
| 19 | Contrôle d'exploitation de la piscine | Hôtel | Hebdomadaire, saison avril-octobre | Partagée |
| 20 | Contrôle des bornes électriques | Maintenance | Occurrence unique le lundi 2 novembre 2026 | Partagée |
| 21 | Contrôle sécurité des équipements | Maintenance | Mensuelle | Individuelle |
| 22 | Maintenance préventive CVC | Maintenance | Trimestrielle | Partagée |
| 23 | Contrôle préventif plomberie et évacuations | Maintenance | Mensuelle | Partagée |
| 24 | Contrôle éclairage chambres et circulations | Maintenance | Mensuelle | Individuelle |
| 25 | Revue des fournisseurs opérationnels | Restaurant | Occurrence unique le mardi 3 novembre 2026 | Partagée |
| 26 | Revue planning et staffing | RH | Hebdomadaire | Partagée |
| 27 | Parcours d'intégration et rappels de formation | RH | Mensuelle | Individuelle |
| 28 | Préparation de réouverture rooftop et piscine | Événements | Annuelle, mars | Partagée |

Ces 28 routines constituent la liste attendue. Une adaptation de libellé ou de fréquence n'est acceptable que si une contrainte réelle du modèle l'impose et doit être explicitée dans le plan d'implémentation ; aucune routine supplémentaire ne doit être ajoutée sans justification fonctionnelle.

### 13.3 Saisonnalité

Tous les schedules ne sont pas actifs simultanément.

Le corpus doit représenter :

- la fin de saison piscine et rooftop à l'automne ;
- des contrôles spécifiques tant que les espaces saisonniers sont exploités ;
- des routines suspendues hors saison ;
- une préparation de réouverture au printemps 2027.

### 13.4 Chronologie partagée et individuelle

Les schedules utilisent les deux comportements disponibles :

- 23 chronologies partagées pour les opérations d'équipe ;
- 5 chronologies individuelles, identifiées dans le tableau, lorsque chaque personne doit suivre sa propre occurrence.

---

## 14. Exécutions futures et planning

### 14.1 Volume

Au 22 septembre 2026, exactement **180 exécutions futures** doivent être visibles.

Les occurrences proches produites par les schedules sont comptées dans ce total. Leur nombre dépend du comportement réel de matérialisation du repo. Les exécutions one-shot complètent ensuite le corpus pour atteindre exactement 180 ; elles ne s'ajoutent pas à 180.

### 14.2 Couverture jusqu'en mars 2027

Les schedules seuls ne suffisent pas à rendre le futur lointain visible si leur matérialisation est bornée à un horizon proche. Des exécutions one-shot doivent donc être créées explicitement jusqu'au 31 mars 2027.

Le planning doit contenir du contenu pertinent en :

- septembre et octobre 2026 ;
- novembre et décembre 2026 ;
- janvier et février 2027 ;
- mars 2027.

Répartition exacte des **180 exécutions futures totales**, toutes origines confondues :

| Période | Nombre exact |
|---|---:|
| 23 au 30 septembre 2026 | 60 |
| Octobre 2026 | 50 |
| Novembre 2026 | 14 |
| Décembre 2026 | 14 |
| Janvier 2027 | 14 |
| Février 2027 | 13 |
| Mars 2027 | 15 |
| **Total** | **180** |

Après matérialisation des occurrences récurrentes disponibles au snapshot, le seed crée uniquement le nombre de one-shots nécessaire pour compléter chaque période. Les exécutions lointaines ne doivent pas être artificiellement concentrées en mars ou dans les deux semaines suivant le snapshot.

### 14.3 Types d'opérations futures

Le futur planifié combine :

- événements publics ;
- séminaires ;
- privatisations ;
- maintenance préventive ;
- campagnes ou contenus Communication ;
- opérations RH ;
- préparation des saisons piscine et rooftop ;
- échéances et contrôles internes ;
- ouvertures, fermetures et passations récurrentes.

### 14.4 Événements publics et privés

Règles :

- les événements publics intégrés au dataset doivent correspondre à des événements Mama réellement publiés et connus au 22 septembre 2026 ;
- leur liste et leurs informations sont figées dans le corpus ;
- le seed ne consulte jamais le site Mama au moment de son exécution ;
- les séminaires, réunions et privatisations non publics sont fictifs mais réalistes ;
- la préparation interne associée est fictive et cohérente avec les contraintes opérationnelles.

Référence publique gelée au 22 septembre 2026 :

| Événement public | Date ou récurrence retenue |
|---|---|
| TIM LIENDERSS — DJ set | 26 septembre 2026 |
| Super Sunday — concert | Chaque dimanche du 27 septembre 2026 au 28 mars 2027 |
| La Bringue à Mémé × French Riviera Agency | 15 octobre 2026 |
| Mama ❤️ Club Sonore — DJ set | 22 octobre 2026 |
| La Bringue à Mémé × French Riviera Agency | 5 novembre 2026 |
| La Bringue à Mémé × French Riviera Agency | 28 janvier 2027 |
| La Bringue à Mémé × French Riviera Agency | 11 février 2027 |
| La Bringue à Mémé × French Riviera Agency | 18 mars 2027 |

Cette table est la seule source autorisée pour les événements publics du corpus initial. Les autres événements futurs sont des séminaires, réunions ou privatisations fictifs. Le détail public provient de la [page officielle Mama Shelter Nice](https://fr.mamashelter.com/nice/) telle qu'observée au 22 septembre 2026.

### 14.5 Composition octobre et novembre 2026

Les totaux mensuels de la section 14.2 restent inchangés : 50 en octobre, 14 en novembre, 180 au total.

Pour intégrer les deux événements publics d'octobre sans dépasser 50, les occurrences des schedules #20 et #25 quittent octobre :

- #20 Contrôle des bornes électriques : lundi 2 novembre 2026 ;
- #25 Revue des fournisseurs opérationnels : mardi 3 novembre 2026.

Ces deux occurrences remplacent les one-shots privés « réunion Studio » du 13 novembre et « brief RH » du 24 novembre, qui n'appartiennent plus au corpus.

Composition d'octobre 2026 (50) :

- 30 quotidiennes (5 routines × 6 jours, du 1er au 6 octobre, dans l'horizon de matérialisation) ;
- 12 weeklies (11 routines d'horizon + Super Sunday du 4 octobre) ;
- schedules #21, #24 et #27 ;
- 3 Super Sunday hors horizon : 11, 18 et 25 octobre ;
- 2 événements publics : La Bringue à Mémé le 15 octobre 2026 ; Mama ❤️ Club Sonore le 22 octobre 2026.

Composition de novembre 2026 (14) :

- 5 Super Sunday : 1, 8, 15, 22 et 29 novembre ;
- La Bringue à Mémé le 5 novembre ;
- séminaire Horizon Azur le 12 novembre ;
- schedules #20 et #25 ;
- 5 one-shots privés (hors Horizon Azur).

---

## 15. Commentaires, réponses et mentions

Les commentaires sont alimentés avec parcimonie :

- exactement **19 Signals actifs** possèdent des commentaires ;
- exactement **65 exécutions historiques** possèdent des commentaires ;
- les 84 objets commentés se répartissent ainsi : 42 avec 1 commentaire, 25 avec 2, 12 avec 3 et 5 avec 4, soit 148 commentaires ;
- exactement 12 threads comprennent au moins une réponse ;
- exactement 10 commentaires comprennent une mention structurée ;
- aucun thread ne doit paraître artificiellement long.

Pour ce calcul, un Signal actif est un Signal au statut `Open`, `In progress` ou `Interesting`, soit 55 Signals dans la distribution de la section 9.1.

Les commentaires doivent apporter une information utile : demande de précision, coordination, confirmation de passage, blocage, validation ou décision.

Les 12 threads avec réponse et les 10 commentaires avec mention peuvent se recouper ; les compteurs portent respectivement sur les threads et sur les commentaires.

---

## 16. Chat

Le Chat est entièrement exclu du dataset de démonstration initial.

Le seed crée exactement :

- **0 groupe Chat** ;
- **0 conversation directe** ;
- **0 message** ;
- **0 réponse ou mention Chat** ;
- **0 pièce jointe ou média Chat**.

Le seed ne modifie ni ne supprime les éventuelles données Chat ajoutées manuellement après son exécution. Le Chat reste une fonctionnalité du produit, mais il n'appartient pas au corpus Mama Shelter Nice défini par ce cadrage.

---

## 17. Gamification

La gamification est présente, mais elle reste une donnée dérivée des actions réellement effectuées.

Le dataset doit assurer la cohérence entre :

- saisons de gamification ;
- transactions de points ;
- badges attribués ;
- personnes ayant réellement réalisé les actions correspondantes.

Il ne faut pas écrire un classement indépendamment du corpus opérationnel. Les totaux, classements et badges doivent pouvoir être expliqués par les exécutions, contributions ou validations présentes.

Le produit utilisant des saisons mensuelles, le corpus comprend exactement :

- 6 saisons mensuelles terminées : mars, avril, mai, juin, juillet et août 2026 ;
- 1 saison mensuelle active du 1er au 30 septembre 2026 ;
- des points uniquement pour les utilisateurs fictifs ayant réellement contribué dans le corpus ;
- des badges attribués à exactement 21 membres fictifs éligibles, sans badge automatique pour tous ;
- aucun point ni badge synthétique pour les comptes réels de gouvernance.

Chaque saison couvre un mois civil complet dans le fuseau `Europe/Paris`. Les règles de calcul doivent reprendre les mécanismes existants du produit. Si les points ne peuvent pas être recalculés silencieusement, les transactions matérialisées doivent reproduire exactement le résultat des actions sources.

---

## 18. Réalisme éditorial par pôle

Chaque pôle doit posséder un historique identifiable et des interactions crédibles avec les autres équipes.

### Hôtel

- chambres non prêtes ;
- demandes clients anonymisées ;
- linge, ménage, signalétique ;
- passations de réception ;
- coordination avec Maintenance et Restaurant.

### Petit déjeuner

- mise en place du buffet ;
- ruptures de produits ;
- propreté ;
- variations de fréquentation ;
- articulation avec Restaurant et Maintenance.

### Restaurant

- ouverture et fermeture ;
- service, bar, cuisine et caisse ;
- stocks et fournisseurs opérationnels ;
- attente client et qualité de service ;
- brunch, rooftop et événements.

### Maintenance

- CVC ;
- plomberie et eau ;
- électricité et éclairage ;
- équipements d'exploitation ;
- audiovisuel et réseau ;
- sécurité et prestataires.

### Communication

- réseaux sociaux ;
- contenus ;
- e-réputation ;
- communication événementielle ;
- coordination avec Restaurant et Événements.

### Événements & privatisations

- préparation logistique ;
- audiovisuel ;
- signalétique ;
- restauration ;
- accueil ;
- coordination de plusieurs espaces et équipes.

### RH

- planning et staffing ;
- intégration ;
- formation ;
- suivi administratif RH ;
- accompagnement des équipes ;
- activités dans le Back-office administratif.

---

## 19. Données fictives, confidentialité et usage des sources publiques

### 19.1 Personnes et clients

- l'OWNER et un DIRECTOR de production sont des comptes réels préexistants, exclus de la génération de contenu historique ;
- tous les utilisateurs créés par le seed sont fictifs ;
- toutes les personnes citées dans les observations, Signals, commentaires et plans sont fictives ;
- aucun nom réel de salarié, client ou prestataire n'est utilisé ;
- les clients sont désignés de manière anonyme, par exemple « client chambre 214 » ;
- aucun visage identifiable n'est nécessaire puisque le dataset ne génère aucun média.

### 19.2 Chambres et implantations

- les numéros de chambre utilisés sont plausibles mais fictifs ;
- ils servent uniquement à contextualiser les observations ;
- le dataset ne prétend pas reproduire le plan réel de l'établissement ;
- les unités opérationnelles publiques et confirmées peuvent être utilisées, sans inventer de détails physiques non vérifiés.

### 19.3 Informations publiques

Les informations publiques sur les espaces, services, horaires ou événements servent à rendre le corpus crédible. Elles ne doivent pas être transformées en fausses preuves d'incidents réels.

Les événements publics retenus sont copiés dans une référence figée au 22 septembre 2026. Aucune récupération dynamique n'est autorisée pendant le seed.

---

## 20. Règles de génération et de seed

### 20.1 Cible de production existante

L'organisation, l'établissement, l'OWNER et un premier DIRECTOR ont été créés manuellement via le parcours réel de production avant l'exécution du seed.

| Objet existant | Nom ou rôle | Identifiant de production |
|---|---|---|
| Organisation | `[DEMO] SPORE` | `7a227b49-4019-46b0-854f-e8ed9fd02fba` |
| Établissement | Mama Shelter Nice | `fe29f398-4a6b-4f9b-a92f-00805435ddc2` |
| OWNER | Compte réel existant | `ff1db0bc-45eb-4ff0-ac0c-a5bc164a5170` |
| DIRECTOR | Compte réel existant | `730d4681-77d7-454f-9164-756db59c7f2a` |

Les deux derniers UUID sont des références fournies par la configuration existante. Le plan d'implémentation doit confirmer dans le repo s'ils identifient un utilisateur, un membership ou un autre objet métier, puis les valider selon leur type réel sans en déduire arbitrairement la nature.

En production, le seed doit :

- cibler explicitement l'établissement `fe29f398-4a6b-4f9b-a92f-00805435ddc2` ;
- vérifier avant toute écriture que l'organisation, l'établissement, l'OWNER et le DIRECTOR correspondent aux références attendues ;
- vérifier que les 7 Business Units, leurs `catalog_key`, leurs descriptions et tous leurs Activity Subjects catalogue sont présents ;
- conserver leurs comptes, rôles et rattachements sans modification ;
- conserver la configuration organisationnelle issue de l'onboarding sans la recréer ;
- échouer sans mutation si une référence, un rôle ou un rattachement est incohérent ;
- créer uniquement les données de démonstration qu'il contrôle.

Il ne crée ni l'organisation ni l'établissement en production.

### 20.2 Parité des environnements

Les environnements local et production contiennent le même corpus fonctionnel :

- mêmes 60 identités fictives gérées par le seed et mêmes slots fonctionnels de gouvernance ;
- mêmes chronologies ;
- mêmes objets métier ;
- mêmes scénarios ;
- mêmes relations ;
- mêmes états fonctionnels.

Seuls les paramètres techniques propres à l'environnement peuvent différer. En local, un bootstrap distinct crée ou retrouve les conteneurs organisationnels nécessaires, sans modifier le comportement strict du seed de production.

L'OWNER local utilise l'adresse suivante :

`leonard.p.boisson@gmail.com`

Le bootstrap local doit :

- retrouver ou créer cet utilisateur dans la base locale ;
- lui attribuer directement le rôle OWNER sur l'organisation locale de démonstration ;
- lire son mot de passe depuis la configuration locale, sans l'inscrire dans le dépôt ;
- ne déclencher aucune invitation ni aucun email ;
- ne lui attribuer aucune activité historique fictive.

Le bootstrap local crée également un premier DIRECTOR local de gouvernance avec l'adresse réservée `director.mama.nice@example.com`, sans activité synthétique, afin d'occuper le même slot fonctionnel que le DIRECTOR réel de production. Le seed principal crée ensuite les mêmes **60 membres actifs fictifs** dans les deux environnements : le second DIRECTOR et les 59 MANAGER/STAFF.

Ces comptes locaux sont techniquement indépendants des comptes de production.

### 20.3 Réexécution

Le seed doit pouvoir être réexécuté de manière sûre et prévisible.

Il doit :

- reconstruire ou remettre en cohérence uniquement le corpus Mama Shelter Nice ;
- préserver systématiquement les comptes et memberships réels préexistants ;
- ne pas dupliquer les objets à chaque exécution ;
- identifier de manière stable chaque objet géré par le seed, sans s'appuyer uniquement sur son libellé ;
- mettre à jour les objets existants en place plutôt que supprimer et recréer massivement le corpus en production ;
- préserver les médias, commentaires ou ajustements ajoutés manuellement après le seed lorsqu'ils sont rattachés à un objet toujours attendu ;
- ne jamais supprimer un objet non identifié comme appartenant au seed ;
- ne pas modifier les données d'autres établissements ;
- ne pas dépendre de la date réelle du jour ;
- produire le même snapshot métier à partir de la même version du corpus.

Les identités, textes, scénarios, dates et relations structurantes sont versionnés et déterministes. Une variation pseudo-aléatoire n'est acceptable que pour des détails sans portée métier, avec une graine fixe. Aucun texte métier ne doit être produit par une IA ou un service externe pendant l'exécution.

Le corpus doit être décrit par un manifeste versionné utilisant une clé stable par objet seedé. Pour les objets structurants, ce manifeste porte au minimum : type, clé stable, scénario, date, auteur ou responsable, pôle, sujet, unité opérationnelle, statut et clés des relations. Les textes peuvent provenir de variantes prérédigées et déterministes ; aucun générateur non seedé ne doit décider du contenu au moment de l'exécution.

### 20.4 Exécution silencieuse

La constitution initiale du corpus ne doit pas déclencher comme s'il s'agissait d'événements temps réel :

- notifications ;
- emails ;
- notifications push ;
- traitements IA ;
- tâches asynchrones métier non nécessaires au seed ;
- intégrations externes.

Le résultat final doit cependant être fonctionnellement cohérent avec ce que ces workflows auraient produit.

### 20.5 Absence de dépendances externes à l'exécution

Le seed ne doit pas dépendre :

- d'un site public disponible ;
- d'une API Mama ou Accor ;
- d'un stockage média ;
- d'une génération de texte en temps réel ;
- d'une génération d'image ;
- d'un utilisateur ou d'un client réel.

### 20.6 Export éditorial avant seed

Une commande `export_mama_nice_corpus` relit uniquement le compilateur et écrit un dossier markdown, sans toucher à la base. L'export ouvre sur la répartition par famille narrative, puis les chapitres par activité Mama Nice, puis les parcours Signal → Pattern → plan → exécution. Une famille hors compte, un chapitre d'activité vide ou un parcours d'amélioration continue incomplet fait échouer l'export. Le reseed reste une étape humaine après lecture de cet export.

---

## 21. Règles de cohérence transverses

Le corpus final doit respecter au minimum les invariants suivants :

1. chaque Signal possède au moins une observation source ;
2. une observation agrégée décrit le même incident que le Signal cible ;
3. un Pattern relie plusieurs Signals distincts et non plusieurs observations du même incident ;
4. les dates de création, assignation, exécution, validation et résolution suivent un ordre plausible ;
5. aucune personne désactivée n'agit après sa date de désactivation ;
6. aucune invitation en cours n'est utilisée comme membre actif ;
7. les assignations respectent les rôles, scopes et pôles existants ;
8. les plans cross-pôles utilisent réellement plusieurs pôles ;
9. les plans capitalisés sont justifiés par l'historique ;
10. les Patterns possèdent suffisamment de Signals pour être crédibles ;
11. les reviews ne concernent que des exécutions éligibles et cohérentes ;
12. les mauvaises reviews correspondent à un récit ou un résultat imparfait ;
13. les exécutions futures sont postérieures au snapshot ;
14. le seed ne crée aucun groupe, conversation, message, réponse, mention, pièce jointe ou média Chat ;
15. aucune Observation ne possède de média généré ;
16. les points et badges découlent des activités du corpus ;
17. les événements publics sont figés et ne sont jamais récupérés dynamiquement ;
18. les contenus ne présentent jamais des événements fictifs comme des incidents réels de Mama Shelter Nice ;
19. les comptes réels de gouvernance et leurs équivalents locaux ne reçoivent aucune activité synthétique ;
20. le corpus contient exactement les 24 Patterns, 21 plans réutilisables et 28 schedules définis dans ce document ;
21. les 180 exécutions futures totales respectent la répartition mensuelle définie ;
22. les événements publics proviennent exclusivement de la référence figée du présent document ;
23. une réexécution avec la même version produit les mêmes identités, textes, dates et relations structurantes.

---

## 22. Critères d'acceptation fonctionnels

Le dataset est considéré conforme lorsque les critères suivants sont remplis.

### 22.1 Organisation

- [ ] Les 7 Business Units validées sont présentes et issues du catalogue.
- [ ] Leurs `catalog_key` et descriptions correspondent au référentiel validé.
- [ ] Tous leurs Activity Subjects catalogue sont activés.
- [ ] Chaque Activity Subject activé est utilisé par au moins un objet historique ou futur.
- [ ] Les 18 Operational Units sont présentes.
- [ ] L'établissement contient exactement 62 membres actifs, 4 désactivés et 2 invités.
- [ ] Les 62 actifs comprennent 18 MANAGER, 41 STAFF, 2 DIRECTOR et 1 OWNER.
- [ ] Les 5 profils multi-scopes sont représentés.
- [ ] Les 10 personas de démonstration sont utilisables.

### 22.2 Historique terrain

- [ ] Le corpus contient exactement 420 Signals et 692 observations.
- [ ] La répartition par pôle responsable respecte exactement le tableau de la section 7.1.
- [ ] Le feed contient exactement 350 resolved, 15 canceled, 22 open, 23 in progress et 10 interesting.
- [ ] Exactement 2 Signals ouverts restent non assignés.
- [ ] Les 12 demandes de résolution comprennent 9 approbations et 3 rejets, dont un rejet suivi d'une reprise réussie.
- [ ] Chaque Signal possède au moins une observation source.
- [ ] Les 420 Signals utilisent exactement 588 observations sources selon la distribution de la section 8.2.
- [ ] Exactement 104 observations sont informatives sans produire de Signal.
- [ ] Les observations ont un ton terrain crédible.
- [ ] Aucun média d'observation n'est généré.

### 22.3 Intelligence opérationnelle

- [ ] Le corpus contient exactement les 24 Patterns du référentiel.
- [ ] Le référentiel contient exactement 22 Patterns actifs, 1 merged et 1 retired.
- [ ] Exactement 170 Signals distincts contribuent aux Patterns actifs.
- [ ] Les Patterns s'appuient sur des Signals distincts répartis dans le temps.
- [ ] Plusieurs Patterns conduisent à une amélioration ou à une capitalisation visible.
- [ ] Le golden path du problème récurrent est démontrable de bout en bout.

### 22.4 Action et capitalisation

- [ ] Le corpus contient exactement 260 exécutions historiques.
- [ ] Exactement 180 exécutions historiques sont issues de Signals et 80 de routines ou d'opérations planifiées.
- [ ] La distribution des états est exactement de 218 done, 16 canceled, 10 in progress, 10 pending validation et 6 scheduled ou en retard.
- [ ] Les états imparfaits comprennent notamment 10 tâches ignorées avec motif et exactement 3 cas réouverts.
- [ ] Le catalogue contient exactement 21 plans, dont 18 actifs et 3 inactifs.
- [ ] Le catalogue contient exactement 13 plans mono-pôle et 8 cross-pôles conformément au référentiel.
- [ ] Les plans respectent les tailles, responsabilités et séquences minimales de la section 11.3.
- [ ] Certains plans réutilisables sont clairement issus de l'historique ou d'un Pattern.
- [ ] Exactement 153 des 218 exécutions terminées possèdent une review.
- [ ] Toutes les notes de 0 à 5 sont présentes, avec une majorité de 4 et 5.

### 22.5 Planning futur

- [ ] Le corpus contient les 28 schedules du référentiel, dont 23 à chronologie partagée et 5 à chronologie individuelle.
- [ ] Les routines d'ouverture, fermeture et passation sont présentes.
- [ ] La saisonnalité piscine et rooftop est visible.
- [ ] Le corpus contient exactement 180 exécutions futures.
- [ ] Les 180 exécutions futures, occurrences matérialisées et one-shots confondus, suivent la répartition mensuelle définie.
- [ ] Des exécutions sont visibles dans chaque mois jusqu'en mars 2027.
- [ ] Les événements publics sont figés au 22 septembre 2026.
- [ ] Aucun événement public absent de la table de référence n'est inventé ou récupéré dynamiquement.
- [ ] Les événements privés sont fictifs et cohérents.

### 22.6 Collaboration et données dérivées

- [ ] Les commentaires concernent exactement 19 Signals actifs et 65 exécutions historiques, pour 148 commentaires au total.
- [ ] Les commentaires comprennent exactement 12 threads avec réponse et 10 commentaires avec mention structurée.
- [ ] Le seed ne crée aucune donnée Chat, y compris groupe, conversation directe, message, réponse, mention, pièce jointe ou média.
- [ ] Le corpus contient exactement 6 saisons mensuelles terminées de mars à août 2026 et 1 saison mensuelle active en septembre 2026.
- [ ] Les points sont cohérents avec les activités et exactement 21 membres fictifs éligibles possèdent au moins un badge.

### 22.7 Seed

- [ ] Le résultat fonctionnel est identique en local et en production.
- [ ] En production, le seed cible explicitement l'établissement `fe29f398-4a6b-4f9b-a92f-00805435ddc2`.
- [ ] L'organisation, l'établissement, l'OWNER et le premier DIRECTOR préexistants sont validés puis préservés sans modification.
- [ ] Le seed crée exactement 60 membres actifs supplémentaires : 1 DIRECTOR et 59 MANAGER/STAFF.
- [ ] Le total final contient exactement 62 membres actifs.
- [ ] Toute incohérence de cible provoque un arrêt avant écriture.
- [ ] Le bootstrap local utilise `leonard.p.boisson@gmail.com` comme OWNER, sans invitation ni email.
- [ ] Le bootstrap local crée `director.mama.nice@example.com` comme premier DIRECTOR local de gouvernance, sans invitation ni activité synthétique.
- [ ] Le seed principal crée les mêmes 60 membres actifs fictifs en local et en production.
- [ ] Le mot de passe de l'OWNER local provient uniquement de la configuration locale et n'est pas versionné.
- [ ] Aucune activité historique fictive n'est attribuée aux comptes réels de production ni à leurs équivalents locaux de gouvernance.
- [ ] Le snapshot reste fixé au 22 septembre 2026 à 23:59:59.
- [ ] Toutes les bornes temporelles sont interprétées dans le fuseau `Europe/Paris`.
- [ ] Le seed est réexécutable sans duplication.
- [ ] Les objets seedés conservent une identité stable entre deux exécutions.
- [ ] Les ajouts manuels rattachés aux objets seedés sont préservés lors d'une réexécution normale.
- [ ] Aucun objet extérieur au périmètre possédé par le seed n'est supprimé ou réécrit.
- [ ] Deux exécutions avec la même version produisent le même corpus structurant.
- [ ] Le manifeste versionné porte une clé stable et les relations attendues pour chaque objet seedé structurant.
- [ ] Il ne touche qu'à Mama Shelter Nice.
- [ ] Il ne déclenche aucune notification, email, push, IA ou intégration externe.
- [ ] Il ne dépend d'aucune ressource publique disponible au moment de l'exécution.

---

## 23. Hors périmètre

Sont explicitement exclus de cette version :

- la création de l'organisation ou de l'établissement par le seed de production ;
- la modification ou la suppression de l'OWNER et du premier DIRECTOR réels ;
- l'envoi d'une invitation ou d'un email à l'OWNER lors du bootstrap local ;
- la création d'un pôle Comptabilité ;
- la génération ou l'import automatique de médias ;
- toute génération de données Chat ;
- l'utilisation de vrais salariés, clients ou prestataires ;
- la reproduction exacte du plan des chambres ;
- la récupération dynamique d'événements publics ;
- la génération de contenu par IA pendant le seed ;
- la simulation réelle de notifications, emails ou pushes ;
- la définition de l'architecture technique détaillée du seed ;
- la transformation de chaque routine quotidienne en centaines d'objets futurs lointains.

---

## 24. Livrable attendu après ce cadrage

Le prochain livrable est un **plan d'implémentation fondé sur le repo réel**.

Il devra :

- confronter ce cadrage aux modèles, contraintes et mécanismes existants ;
- identifier les données de référence déjà disponibles ;
- proposer une génération déterministe et maintenable ;
- traiter les listes nominales de Patterns, plans et schedules comme le référentiel à implémenter, et non comme de simples exemples ;
- calculer le nombre réel d'occurrences récurrentes matérialisées au snapshot puis compléter le planning avec des one-shots jusqu'à la distribution attendue ;
- signaler les éventuels écarts entre le besoin fonctionnel et le produit actuel ;
- préserver la réexécution ciblée et la sécurité des données existantes ;
- définir une stratégie de validation des volumes et invariants ;
- éviter d'introduire des hypothèses techniques non vérifiées.

Le plan d'implémentation ne doit pas remettre en cause les décisions fonctionnelles de ce document sans identifier explicitement une incompatibilité avec le produit actuel.

Avant le code du seed, il doit produire la structure du manifeste de données et la matrice de validation permettant de relier chaque exigence figée à un contrôle automatisable.

---

## 25. Références publiques de plausibilité

Ces références servent uniquement à valider la plausibilité de l'établissement, de ses espaces et de ses activités. Elles ne sont pas consultées par le seed.

- [Mama Shelter Nice — présentation de l'établissement](https://mamashelter.com/nice/)
- [Mama Shelter Nice — travailler et célébrer](https://fr.mamashelter.com/nice/travailler-celebrer/)
- [Mama Shelter Nice — restaurant RDC et bar](https://fr.mamashelter.com/nice/restaurants/restaurant-rdc-bar/)
- [Mama Shelter Nice — rooftop](https://fr.mamashelter.com/nice/restaurants/rooftop/)

---

## 26. Synthèse des décisions figées

- 7 pôles, sans Comptabilité.
- Tous les Activity Subjects catalogue activés.
- 18 Operational Units.
- 62 membres actifs, dont 1 OWNER et 1 DIRECTOR réels préexistants ; 4 désactivés et 2 invités.
- Le seed de production conserve ces deux comptes et crée les 60 autres membres actifs.
- 10 personas de démonstration et 5 utilisateurs multi-scopes.
- Snapshot fixe au 22 septembre 2026.
- Historique d'un an et futur visible jusqu'au 31 mars 2027.
- 420 Signals et 692 observations exactement.
- Agrégations visibles et distinctes des Patterns.
- 24 Patterns exactement : 22 actifs, 1 merged et 1 retired.
- 260 exécutions historiques exactement.
- 21 plans réutilisables, dont 18 actifs et 3 inactifs.
- 28 schedules et 180 exécutions futures exactement.
- Reviews sur environ 70 % des exécutions terminées.
- Aucune donnée Chat générée.
- 6 saisons mensuelles terminées de mars à août 2026 et 1 saison active en septembre 2026.
- Aucun média généré.
- Événements publics figés ; événements privés fictifs.
- Données générées fictives pour les personnes et incidents ; comptes réels de gouvernance exclus du contenu historique.
- Seed identique fonctionnellement en local et production, réexécutable, ciblé et silencieux.
- Organisation et établissement créés manuellement en production puis ciblés par leurs identifiants explicites.
- En local, `leonard.p.boisson@gmail.com` est créé ou retrouvé comme OWNER par un bootstrap sans invitation ni activité fictive.
- Le bootstrap local crée aussi `director.mama.nice@example.com` comme premier DIRECTOR de gouvernance ; le seed principal génère ensuite le même roster de 60 membres actifs fictifs dans les deux environnements.
- Narration prioritaire : Terrain vers résolution ≈ Intelligence opérationnelle, puis Organisation proactive.
