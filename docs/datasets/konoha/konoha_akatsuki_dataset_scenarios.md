# Dataset KONOHA — Scénarios AKATSUKI pour génération des observations

## 1. Objet du document

Ce document est la source de vérité métier pour générer les **65 observations AKATSUKI** du nouveau dataset local KONOHA.

Il couvre les 6 pôles actifs d’AKATSUKI :

| Pôle d’origine | Nombre d’observations |
|---|---:|
| Commerce | 15 |
| Basic Fit | 14 |
| EMEA | 12 |
| Événements & privatisations | 9 |
| Maintenance | 10 |
| Communication | 5 |
| **Total AKATSUKI** | **65** |

AKATSUKI est un site mixte **retail + sport + loisirs + privatisations**, très différent d’ANBU. Les descriptions d’instance sont vides en DB : les localisations ci-dessous doivent donc rester **sobres, stables et plausibles**, sans inventer un second onboarding ni une liste d’équipements exhaustive.

Le dataset couvre **du 01/08/2025 au 29/08/2026 inclus**. Certains Signals/plans peuvent rester ouverts au 29/08/2026 avec une échéance, un `end_at` ou une action prévue allant jusqu’au **31/10/2026**, mais **aucune observation, aucun commentaire, aucune transition lifecycle et aucun point ne doit être horodaté après le 29/08/2026** dans le dataset initial.

---

## 2. Contexte runtime AKATSUKI à respecter

### 2.1 Pôles actifs

- **Commerce** — dédié : caisse, stock, produit, prix, fournisseurs, propreté, sécurité, RH, signalétique, expérience, administration.
- **Basic Fit** — dédié : expérience membre, planning cours, propreté, sécurité, signalétique, RH, commercialisation.
- **EMEA** — dédié loisirs : billetterie, événements, prestataires, expérience, propreté, sécurité et autres sujets catalogue actifs. Ne pas inventer un sujet custom.
- **Événements & privatisations** — transversal : commercialisation, préparation & logistique, facturation, expérience, communication, RH.
- **Maintenance** — transversal : CVC, Électricité, Équipements d’exploitation, Plomberie & Eau, Bâtiment & second œuvre, Ouverture/fermeture, Réseau & IT, Sécurité & conformité, Prestataires, Logistique & consommables.
- **Communication** — transversal : image, social, site, CRM, e-réputation, contenu, etc.

`OperationalUnit` n’alimente pas le Dashboard Localisations. Toutes les localisations de ce document doivent devenir du **`location_text`**.

### 2.2 Auteurs actifs à utiliser

#### Commerce
- Kakuzu Takigakure — manager
- Sasori Akasuna — manager
- Deidara Tsuchigakure — staff
- Hidan Yugakure — staff
- Zetsu Gedou — staff

#### Basic Fit
- Kisame Hoshigaki — manager
- Konan Ame — manager
- Itachi Uchiha — staff
- Obito Uchiha — staff
- Juugo Tsuchigumo — staff

#### EMEA
- Yahiko Ame — manager
- Orochimaru Oto — manager
- Kabuto Yakushi — staff
- Karin Uzumaki — staff
- Suigetsu Hozuki — staff

#### Événements & privatisations
- Temari Sabaku — manager
- Kankuro Sabaku — manager
- Gaara Sabaku — staff
- Matsuri Sabaku — staff
- Yukata Suna — staff

#### Maintenance
- Killer Bee — manager
- Darui Kumo — manager
- Cee Kumo — staff
- Omoi Kumo — staff
- Karui Kumo — staff

#### Communication
- Shikaku Nara — manager
- Mabui Kumo — manager
- Samui Kumo — staff
- Atsui Kumo — staff
- A Raikage — staff

Naruto reste owner cross KONOHA et Pain director AKATSUKI, mais ils ne sont pas nécessaires comme auteurs de cette matrice : l’objectif est d’utiliser les acteurs réellement scopés sur les pôles.

---

## 3. Règles pour Cursor lors de la génération des observations

### 3.1 Ne pas transformer la matrice en état final

La matrice décrit l’intention métier et les résultats attendus pour validation.

Cursor ne doit pas :

- créer directement les `Signal` ;
- créer directement les motifs / `OperationalPattern` ;
- créer directement les `SignalPatternAssignment` ;
- antidater ensuite des états finaux via ORM ;
- appeler `apply_analytics_history_cutover`.

Le replay final doit passer par le vrai workflow produit prévu par le chantier dataset : observation → pipeline sync déterministe → Signal/agrégation → classification sync → éventuelle qualification → plans/transitions/comments via les writers réels sous horloge contrôlée.

### 3.2 Génération du texte naturel

Pour chaque ligne de scénario, générer une **observation naturelle en français**, généralement 1 à 3 phrases.

Le texte doit :

- ressembler à une remontée faite par quelqu’un réellement sur le terrain ;
- conserver les détails concrets du scénario : lieu, symptôme, fréquence, conséquence ;
- éviter les formulations génériques comme « machine cassée », « problème de caisse », « salle sale », « souci billetterie » ;
- ne pas mentionner artificiellement le sujet catalogue, le pôle responsable, le motif ou le comportement d’agrégation ;
- varier les formulations et le niveau de détail selon l’auteur ;
- rester sur ce que l’auteur peut réellement constater ;
- ne pas inventer de marque/modèle précis d’équipement absent de la DB ;
- ne pas inventer de zones métier excessivement détaillées : utiliser des localisations sobres comme `caisse 2`, `réserve`, `plateau cardio`, `vestiaires`, `accueil billetterie`, `zone d'attente`, `espace privatisable`, `atelier maintenance`.

### 3.3 Voix des auteurs

- **Staff** : observation directe, issue du service, du rangement, de l’accueil ou de l’utilisation quotidienne.
- **Managers** : contexte supplémentaire, fréquence, impact client/membre, organisation et caractère récurrent.
- **Maintenance** : symptômes et constats plus techniques, sans inventer un diagnostic définitif avant intervention.
- **Communication** : incohérences de contenu, parcours web, campagne, CRM, e-réputation ou support.

### 3.4 Routing attendu

Le pôle d’origine n’est pas forcément le pôle responsable.

En particulier :

- panne de caisse, lecteur badge, tourniquet, machine de sport, éclairage, CVC, plomberie, réseau → généralement **Maintenance** ;
- problème de prix, stock, fournisseur, signalétique magasin → **Commerce** ;
- planning cours, propreté, sécurité d’usage, expérience membre → **Basic Fit** ;
- billetterie, accueil loisirs, expérience, prestataire, organisation de la zone loisirs → **EMEA** ;
- préparation/logistique/facturation/communication d’une privatisation → **Événements & privatisations** ;
- site, CRM, réseau social ou campagne transverse → **Communication**.

Lors de l’implémentation, résoudre les **sujets actifs exacts de la DB**. Les intitulés du document expriment l’intention sémantique : ils ne doivent pas conduire à créer un sujet absent.

### 3.5 Agrégation et motifs

Les lignes indiquées **même Signal** doivent être générées de façon compatible avec l’agrégation d’un Signal encore actif.

Les lignes indiquées **nouveau Signal, même motif** correspondent à un incident précédent déjà clos : elles doivent produire une nouvelle occurrence susceptible de retrouver le motif canonique existant.

Ne jamais forcer une fusion Signal→Signal pour atteindre les ordres de grandeur.

---

# 4. AKATSUKI — Commerce — 15 observations

**Contexte :** commerce de détail non alimentaire générique. Ne pas inventer une catégorie de marchandises précise. Les localisations restent `caisses`, `réserve`, `zone de déballage`, `rayon central`, `entrée`, `vitrine`.

| # | Date | Auteur | Localisation | Situation terrain précise | Responsable / sujet attendu | Relation / comportement attendu | Cycle prévu |
|---:|---|---|---|---|---|---|---|
| 1 | 05/08/2025 11:20 | Deidara Tsuchigakure | Rayon central | Une promotion affichée à 24,90 € passe encore à 29,90 € en caisse sur plusieurs articles de la même opération. | Commerce → Prix | Nouveau Signal cohérence prix | Correction le jour même |
| 2 | 05/08/2025 13:05 | Kakuzu Takigakure | Caisse 1 | Même promotion : deuxième client concerné, prix caisse toujours ancien malgré mise à jour annoncée. | Commerce → Prix | **Même Signal #1** | Résolu 06/08 |
| 3 | 13/09/2025 09:40 | Zetsu Gedou | Réserve | Le stock système indique 18 unités d’une référence alors qu’il n’en reste que 7 après comptage physique avant réassort. | Commerce → Stock | Nouveau | Inventaire ciblé |
| 4 | 02/10/2025 10:15 | Hidan Yugakure | Réception livraison / réserve | Une palette et plusieurs cartons restent devant l’accès à la réserve pendant le contrôle, obligeant à déplacer les colis à chaque passage. | Commerce → Stock / Sécurité | Nouveau | Organisation réception |
| 5 | 21/10/2025 15:55 | Sasori Akasuna | Zone de déballage | Deux cutters de déballage ont le mécanisme de rappel qui accroche ; une lame reste partiellement sortie sur l’un d’eux. | Commerce → Sécurité | Nouveau | Retrait immédiat |
| 6 | 18/11/2025 17:25 | Deidara Tsuchigakure | Caisse 2 | Le scanner code-barres s’éteint puis se reconnecte plusieurs fois ; saisie manuelle nécessaire sur une partie des produits. | Maintenance → Réseau & IT / Équipements d’exploitation | Nouveau | Ouvert |
| 7 | 19/11/2025 09:10 | Kakuzu Takigakure | Caisse 2 | Même scanner : panne reproduite dès l’ouverture, câble et alimentation visuellement en place. | Maintenance → Réseau & IT / Équipements | **Même Signal #6** | Résolu 20/11 |
| 8 | 12/12/2025 14:35 | Zetsu Gedou | Rayon central | Une tablette d’étagère s’affaisse légèrement côté droit avec une charge normale ; fixation arrière semble avoir du jeu. | Maintenance → Bâtiment & second œuvre / Équipements | Nouveau | Rayon partiellement neutralisé |
| 9 | 09/01/2026 10:20 | Hidan Yugakure | Entrée magasin | Après nettoyage, le sol reste très glissant près du tapis d’entrée et le panneau de signalement a été retiré avant séchage complet. | Commerce → Propreté / Sécurité | Nouveau | Correction process |
| 10 | 17/02/2026 08:55 | Sasori Akasuna | Réception livraison | Une livraison est arrivée avec 6 colis annoncés sur le bon mais seulement 5 physiquement présents ; aucune réserve n’a été notée au départ du transporteur. | Commerce → Fournisseurs | Nouveau | Réclamation fournisseur |
| 11 | 26/03/2026 16:10 | Kakuzu Takigakure | Rayon promotion | Nouvelle incohérence de prix, sur une autre campagne : étiquette à -20 % mais prix plein appliqué sur le terminal de contrôle. | Commerce → Prix | **Nouveau Signal, motif cohérence prix récurrent #1/#2** | Corrigé |
| 12 | 08/05/2026 12:30 | Deidara Tsuchigakure | Sortie / portiques | Portique antivol déclenche sur plusieurs clients dont les produits ont bien été désactivés en caisse ; phénomène intermittent. | Maintenance → Équipements d’exploitation | Nouveau | Diagnostic |
| 13 | 29/06/2026 09:50 | Zetsu Gedou | Réserve | Les cartons les plus lourds ont été rangés en hauteur alors que le niveau bas est occupé par des petites références légères ; réassort difficile sans déplacer plusieurs piles. | Commerce → Stock / Sécurité | Nouveau | Réorganisation rangement |
| 14 | 25/07/2026 17:40 | Hidan Yugakure | Caisse 1 | Le tiroir-caisse se bloque une fois sur trois à l’ouverture et nécessite de le repousser puis de relancer la commande. | Maintenance → Équipements d’exploitation | Nouveau | Intervention |
| 15 | 28/08/2026 18:05 | Kakuzu Takigakure | Caisses | Les deux postes perdent brièvement la connexion au système de caisse ; paiements reprennent après 1 à 2 minutes mais la coupure s’est produite trois fois ce soir. | Maintenance → Réseau & IT | Nouveau | **Ouvert au cut-off**, diagnostic prévu avant 10/10 |

### Résultat attendu Commerce

Relations fortes :

- #1 + #2 → même Signal ;
- #11 → nouvel incident après clôture, motif cohérence prix connu ;
- #6 + #7 → même Signal ;
- #12, #14 et #15 sont techniques et doivent pouvoir router vers Maintenance ;
- #3, #4, #10, #13 restent réellement Commerce.

**Ordre de grandeur attendu : ~13 Signals.**

---

# 5. AKATSUKI — Basic Fit — 14 observations

**Contexte :** salle de sport générique sous le pôle runtime `Basic Fit`. Ne pas inventer une implantation de marque détaillée. Localisations sobres : `plateau cardio`, `plateau musculation`, `vestiaires`, `accueil`, `entrée / tourniquet`, `salle de cours`.

| # | Date | Auteur | Localisation | Situation terrain précise | Responsable / sujet attendu | Relation / comportement attendu | Cycle prévu |
|---:|---|---|---|---|---|---|---|
| 1 | 22/08/2025 07:35 | Itachi Uchiha | Plateau cardio / tapis 4 | Le bouton d’arrêt rapide du tapis 4 répond seulement après plusieurs pressions ; le reste des commandes fonctionne normalement. | Maintenance → Équipements d’exploitation / Sécurité | Nouveau Signal machine | Machine mise hors service |
| 2 | 22/08/2025 09:10 | Kisame Hoshigaki | Plateau cardio / tapis 4 | Défaut reproduit après redémarrage ; arrêt rapide toujours irrégulier, appareil maintenu indisponible. | Maintenance → Équipements / Sécurité | **Même Signal #1** | Résolu 24/08 |
| 3 | 15/09/2025 18:25 | Juugo Tsuchigumo | Vestiaires / sortie douches | Plusieurs traces d’eau s’étendent jusqu’au passage principal après le pic de fin de journée ; sol très glissant malgré un passage récent. | Basic Fit → Propreté / Sécurité | Nouveau | Nettoyage + contrôle fréquence |
| 4 | 07/10/2025 19:05 | Konan Ame | Vestiaires | Air très humide et buée persistante sur les miroirs plus de 20 minutes après le pic des douches ; extraction nettement moins perceptible. | Maintenance → CVC | Nouveau | Contrôle ventilation |
| 5 | 28/11/2025 10:40 | Obito Uchiha | Plateau musculation / rack haltères | Une fixation basse du rack bouge légèrement quand plusieurs haltères sont reposés ; jeu visible au niveau d’un pied. | Maintenance → Équipements d’exploitation | Nouveau | Zone balisée |
| 6 | 14/12/2025 08:50 | Konan Ame | Accueil / planning cours | L’écran affiche encore le cours de 10h avec l’ancien intervenant alors que le remplacement est confirmé depuis deux jours. | Basic Fit → Planning cours | Nouveau | Mise à jour |
| 7 | 20/01/2026 17:15 | Itachi Uchiha | Fontaine / sortie vestiaires | Petite flaque revient sous la fontaine après plusieurs utilisations ; eau semble venir de la partie basse et non des éclaboussures. | Maintenance → Plomberie & Eau | Nouveau | Intervention |
| 8 | 09/02/2026 12:20 | Juugo Tsuchigumo | Plateau musculation / machine poulie | La gaine d’un câble est abîmée sur quelques centimètres près d’une poulie ; les fils internes ne sont pas visibles mais la surface est nettement entamée. | Maintenance → Équipements d’exploitation / Sécurité | Nouveau | Machine neutralisée |
| 9 | 04/03/2026 18:40 | Obito Uchiha | Plateau musculation | Deux distributeurs de produit de nettoyage sont vides pendant le pic alors que la réserve contient encore des recharges. | Basic Fit → Propreté | Nouveau | Revue réassort |
| 10 | 21/04/2026 07:55 | Itachi Uchiha | Entrée / tourniquet | Le tourniquet reconnaît le badge mais reste verrouillé une fois sur plusieurs ; accueil doit ouvrir manuellement. | Maintenance → Équipements d’exploitation | Nouveau | Ouvert |
| 11 | 21/04/2026 18:05 | Kisame Hoshigaki | Entrée / tourniquet | Même tourniquet bloqué à trois reprises sur le créneau du soir malgré redémarrage du lecteur. | Maintenance → Équipements | **Même Signal #10** | Résolu 22/04 |
| 12 | 11/06/2026 14:10 | Juugo Tsuchigumo | Couloir accès vestiaires | Deux équipements déplacés pour nettoyage réduisent fortement le passage vers la sortie ; circulation difficile lorsque plusieurs personnes se croisent. | Basic Fit → Sécurité | Nouveau | Repositionnement immédiat |
| 13 | 29/07/2026 18:30 | Konan Ame | Plateau cardio | Pendant forte chaleur et forte fréquentation, température reste élevée et sensation d’air stagnant malgré ventilation en marche. | Maintenance → CVC | **Nouveau Signal, motif CVC récurrent avec #4** | Ajustement / intervention |
| 14 | 28/08/2026 20:10 | Obito Uchiha | Plateau cardio / rameur 3 | Rameur 3 émet un claquement à chaque retour et la résistance varie sans changement de réglage ; problème apparu ce soir. | Maintenance → Équipements d’exploitation | Nouveau | **Ouvert au cut-off**, maintenance prévue avant 15/10 |

### Résultat attendu Basic Fit

Relations fortes :

- #1 + #2 → même Signal ;
- #10 + #11 → même Signal ;
- #13 → nouvel incident CVC après clôture de #4 ;
- #3, #9 et #12 restent des problèmes Basic Fit de propreté/sécurité ;
- #5, #7, #8 et #14 doivent router vers Maintenance.

**Ordre de grandeur attendu : ~12 Signals.**

---

# 6. AKATSUKI — EMEA — 12 observations

**Contexte :** pôle loisirs. La DB ne contient pas de description d’instance détaillée : ne pas inventer une attraction ou une activité précise. Utiliser des lieux génériques et plausibles : `accueil billetterie`, `contrôle d'accès`, `zone d'attente`, `espace loisirs principal`, `consignes`, `zone prestataire`.

| # | Date | Auteur | Localisation | Situation terrain précise | Responsable / sujet attendu | Relation / comportement attendu | Cycle prévu |
|---:|---|---|---|---|---|---|---|
| 1 | 31/08/2025 14:20 | Kabuto Yakushi | Contrôle d'accès | Le lecteur refuse plusieurs e-billets pourtant valides ; deuxième scan ou passage par l’accueil nécessaire. | Maintenance → Réseau & IT / Équipements | Nouveau Signal contrôle billets | Ouvert |
| 2 | 31/08/2025 16:00 | Yahiko Ame | Contrôle d'accès | Même problème pendant le pic : file d’attente augmente car environ un billet sur cinq doit être vérifié manuellement. | Maintenance → Réseau & IT / Équipements | **Même Signal #1** | Résolu 01/09 |
| 3 | 17/10/2025 10:30 | Karin Uzumaki | Accueil billetterie | Un créneau apparaît disponible sur l’écran accueil alors qu’il est déjà complet dans la réservation en ligne ; deux ventes ont dû être annulées avant paiement. | EMEA → Billetterie | Nouveau | Correction paramétrage |
| 4 | 22/11/2025 18:10 | Suigetsu Hozuki | Zone d'attente | Le pied d’un potelet de file bouge beaucoup et le potelet penche dès que la sangle est tendue. | Maintenance → Équipements d’exploitation | Nouveau | Remplacement |
| 5 | 18/12/2025 09:45 | Orochimaru Oto | Espace loisirs principal | Le prestataire de nettoyage n’a pas traité la zone prévue avant ouverture ; plusieurs surfaces sont encore marquées au démarrage. | EMEA → Prestataires / Propreté | Nouveau | Relance prestataire |
| 6 | 06/01/2026 15:15 | Kabuto Yakushi | Consignes | Consigne 12 accepte le code mais la porte reste bloquée ; affaires d’un client récupérées avec l’aide de l’équipe. | Maintenance → Équipements d’exploitation | Nouveau | Intervention |
| 7 | 14/02/2026 17:50 | Karin Uzumaki | Zone d'attente | Après nettoyage d’une boisson renversée, le sol reste humide sur le passage et aucune signalisation n’est visible pendant plusieurs minutes. | EMEA → Propreté / Sécurité | Nouveau | Correction immédiate |
| 8 | 28/03/2026 11:05 | Yahiko Ame | Confirmation billetterie | L’email de confirmation indique une heure d’arrivée différente de celle du billet généré pour certains créneaux du week-end. | EMEA → Billetterie / Expérience | Nouveau | Template corrigé |
| 9 | 16/05/2026 08:40 | Orochimaru Oto | Zone prestataire | Une installation prévue avant ouverture n’est pas terminée à l’heure convenue ; matériel encore dans le passage quand les premiers clients arrivent. | EMEA → Prestataires | Nouveau | Suivi fournisseur |
| 10 | 07/07/2026 15:25 | Suigetsu Hozuki | Contrôle d'accès | Nouvel épisode de scans refusés plusieurs mois après l’incident d’août, cette fois sur un seul lecteur ; les billets sont valides sur le second poste. | Maintenance → Réseau & IT / Équipements | **Nouveau Signal, motif contrôle accès récurrent #1/#2** | Résolu |
| 11 | 09/08/2026 17:35 | Karin Uzumaki | Zone d'attente / accès activité | En forte affluence, la file déborde sur le passage principal et bloque régulièrement le flux des personnes qui sortent. | EMEA → Expérience / Sécurité | Nouveau | Organisation de file |
| 12 | 29/08/2026 09:40 | Kabuto Yakushi | Accueil billetterie | L’écran du poste de contrôle reste noir au démarrage alors que le poste est alimenté ; vérifications effectuées sur un seul écran de secours. | Maintenance → Réseau & IT / Équipements | Nouveau | **Ouvert au cut-off**, intervention prévue avant 30/09 |

### Résultat attendu EMEA

Relations fortes :

- #1 + #2 → même Signal ;
- #10 → nouveau Signal, motif contrôle d’accès / lecteur déjà connu ;
- #3 et #8 restent Billetterie/Expérience et ne doivent pas être absorbés par Maintenance ;
- #5 et #9 testent le sujet Prestataires ;
- #11 est une difficulté d’organisation du flux, pas une panne technique.

**Ordre de grandeur attendu : ~11 Signals.**

---

# 7. AKATSUKI — Événements & privatisations — 9 observations

**Contexte :** pôle transversal dédié aux privatisations et événements. Utiliser des localisations génériques : `espace privatisable`, `zone montage`, `accueil événement`, `stock événement`, `entrée événement`. Ne pas inventer une salle nommée absente de l’onboarding.

| # | Date | Auteur | Localisation | Situation terrain précise | Responsable / sujet attendu | Relation / comportement attendu | Cycle prévu |
|---:|---|---|---|---|---|---|---|
| 1 | 12/09/2025 14:30 | Gaara Sabaku | Espace privatisable | Le plan client prévoit 80 places assises mais seulement 72 chaises sont comptées disponibles avant le montage du lendemain. | Événements → Préparation & logistique | Nouveau | Complément matériel |
| 2 | 07/11/2025 16:50 | Matsuri Sabaku | Zone montage | Une multiprise utilisée pour le montage devient chaude au toucher avec plusieurs équipements branchés ; pas d’odeur ni fumée mais utilisation stoppée. | Maintenance → Électricité | Nouveau | Matériel retiré |
| 3 | 18/12/2025 13:20 | Temari Sabaku | Accueil événement | Le panneau directionnel imprimé indique l’entrée opposée à celle prévue dans le brief final, alors que les premiers invités arrivent dans deux heures. | Événements → Communication | Nouveau | Support remplacé |
| 4 | 06/02/2026 09:35 | Kankuro Sabaku | Zone montage | Le matériel livré par un prestataire occupe encore une partie du passage principal alors que le montage devait être terminé avant 9h. | Événements → Préparation & logistique | Nouveau | Reprise avec prestataire |
| 5 | 21/03/2026 11:10 | Temari Sabaku | Administration événement | L’acompte d’une privatisation apparaît deux fois sur le récapitulatif de facturation avant émission du solde. | Événements → Facturation | Nouveau | Correction |
| 6 | 30/04/2026 17:45 | Yukata Suna | Entrée événement | Caisses de matériel temporairement stockées devant une partie du passage vers la sortie pendant la préparation ; circulation réduite. | Événements → Préparation & logistique | Nouveau | Déplacement immédiat |
| 7 | 13/06/2026 10:25 | Matsuri Sabaku | Communication événement | L’email envoyé aux inscrits annonce un début à 18h30 alors que le brief validé et l’accueil prévoient 19h. | Événements → Communication / Expérience | Nouveau | Message correctif |
| 8 | 24/07/2026 15:05 | Kankuro Sabaku | Administration événement | Nouvelle anomalie de facturation : une option logistique annulée figure encore dans le montant final d’une autre privatisation. | Événements → Facturation | **Nouveau Signal, motif facturation récurrent #5** | Corrigé |
| 9 | 28/08/2026 12:40 | Gaara Sabaku | Stock événement | Une rallonge utilisée pour les montages a la gaine entaillée près de la fiche ; elle a été isolée du stock utilisable mais aucun remplacement immédiat n’est disponible. | Maintenance → Électricité / Sécurité | Nouveau | **Ouvert au cut-off**, remplacement prévu avant 05/10 |

### Résultat attendu Événements & privatisations

- 9 observations → environ 9 Signals ;
- #5 et #8 → Signals distincts, motif facturation récurrent possible ;
- #2 et #9 sont des anomalies techniques électriques et doivent router vers Maintenance ;
- #1, #4, #6 restent des problèmes de préparation/logistique ;
- #3 et #7 restent dans le pôle Événements, même s’ils touchent à la communication.

**Ordre de grandeur attendu : ~9 Signals.**

---

# 8. AKATSUKI — Maintenance — 10 observations

**Contexte :** pôle transversal. Les observations sont remontées directement par l’équipe Maintenance lors de rondes, tests, suivi prestataire ou préparation d’intervention. Elles doivent aussi créer quelques motifs comparables avec ANBU sans rendre les deux sites identiques.

| # | Date | Auteur | Localisation | Situation terrain précise | Responsable / sujet attendu | Relation / comportement attendu | Cycle prévu |
|---:|---|---|---|---|---|---|---|
| 1 | 25/09/2025 08:40 | Cee Kumo | Atelier maintenance / consommables | Le stock de batteries compatibles avec plusieurs blocs d’éclairage de sécurité est presque vide alors que des tests mensuels sont prévus. | Maintenance → Logistique & consommables | Nouveau | Réassort |
| 2 | 30/10/2025 09:15 | Darui Kumo | Gaine technique proche Commerce | Petite trace d’humidité au pied d’une canalisation ; pas d’écoulement actif mais le sol est légèrement marqué. | Maintenance → Plomberie & Eau | Nouveau | Surveillance + diagnostic |
| 3 | 04/12/2025 07:55 | Omoi Kumo | Entrée Commerce | Porte automatique ralentit au milieu de l’ouverture puis termine sa course normalement ; phénomène reproduit plusieurs fois à vide. | Maintenance → Équipements d’exploitation | Nouveau | Intervention |
| 4 | 19/01/2026 11:20 | Karui Kumo | Baie réseau | Un équipement réseau affiche une alerte récurrente et l’interface remonte plusieurs pertes de lien courtes dans la matinée. | Maintenance → Réseau & IT | Nouveau | Diagnostic |
| 5 | 27/02/2026 08:10 | Killer Bee | Local ventilation / Basic Fit | Le filtre d’une unité desservant la zone sport est nettement plus chargé que prévu par le planning et le débit perçu est faible. | Maintenance → CVC | Nouveau | Maintenance préventive |
| 6 | 09/04/2026 14:45 | Darui Kumo | Suivi prestataires | Le compte-rendu d’une intervention sur un équipement de contrôle d’accès manque au dossier alors que la remise en service est clôturée. | Maintenance → Prestataires | Nouveau | Relance |
| 7 | 18/05/2026 10:05 | Cee Kumo | Tableau électrique zone loisirs | Un presse-étoupe est desserré sur l’arrivée d’un coffret ; aucun conducteur nu mais le câble bouge légèrement à l’entrée du boîtier. | Maintenance → Électricité / Sécurité & conformité | Nouveau | Mise en sécurité + correction |
| 8 | 02/07/2026 08:35 | Omoi Kumo | Entrée Basic Fit / tourniquet | Lors d’un contrôle après remontée utilisateur, le tourniquet reste une fois verrouillé malgré badge reconnu ; incident d’avril pourtant clos. | Maintenance → Équipements d’exploitation | **Nouveau Signal, motif contrôle d’accès récurrent** | Intervention |
| 9 | 12/08/2026 07:50 | Karui Kumo | Circulation principale | Un bloc d’éclairage de sécurité reste éteint pendant le test alors que les blocs voisins passent correctement sur batterie. | Maintenance → Sécurité & conformité / Électricité | Nouveau | Remplacement |
| 10 | 29/08/2026 08:25 | Killer Bee | Zone loisirs / ventilation | Une unité de ventilation émet un ronflement inhabituel au démarrage et le débit semble plus faible sur la zone desservie. | Maintenance → CVC | Nouveau | **Ouvert au cut-off**, diagnostic prévu avant 20/10 |

### Résultat attendu Maintenance

- 10 observations → environ 10 Signals ;
- #3 peut partager une famille « porte automatique » avec ANBU sans être le même incident ;
- #8 doit retrouver un motif de contrôle d’accès déjà visible dans Basic Fit ;
- #5 et #10 créent une récurrence CVC interne AKATSUKI ;
- #6 teste le suivi prestataire plutôt qu’un équipement lui-même.

**Ordre de grandeur attendu : ~10 Signals.**

---

# 9. AKATSUKI — Communication — 5 observations

**Contexte :** pôle transversal. Les scénarios doivent rester peu nombreux mais utiles au Cross KONOHA : site, CRM, réseaux sociaux, contenu et conformité.

| # | Date | Auteur | Localisation | Situation terrain précise | Responsable / sujet attendu | Relation / comportement attendu | Cycle prévu |
|---:|---|---|---|---|---|---|---|
| 1 | 05/10/2025 10:10 | Samui Kumo | CRM / newsletter | Le lien de désinscription du dernier email commercial retourne une page d’erreur sur mobile et desktop. | Communication → CRM | Nouveau | Correction prioritaire |
| 2 | 11/01/2026 14:20 | Shikaku Nara | Site Commerce | Une page promotionnelle affiche un prix différent de celui validé pour le magasin ; la campagne payante renvoie vers cette page. | Communication → Site / Contenu | Nouveau, affecte Commerce | Corrigé |
| 3 | 22/03/2026 09:55 | Atsui Kumo | Réseaux sociaux Basic Fit | Publication programmée annonce encore l’ancien horaire d’un cours alors que le planning a été modifié depuis plusieurs jours. | Communication → Social / Contenu | Nouveau | Publication corrigée |
| 4 | 18/06/2026 16:35 | Mabui Kumo | Site EMEA / réservation | Sur mobile, le bouton principal de réservation ouvre une page vide alors que le parcours fonctionne sur desktop. | Communication → Site internet | Nouveau | Résolu |
| 5 | 28/08/2026 11:25 | A Raikage | Formulaire campagne | La case d’inscription aux offres commerciales apparaît cochée par défaut sur le formulaire de campagne alors qu’elle devrait nécessiter une action volontaire. | Communication → CRM / Site | Nouveau, famille conformité | **Ouvert au cut-off**, correction prévue début septembre |

### Résultat attendu Communication

- 5 observations → environ 5 Signals ;
- #1 peut converger vers le même motif CRM/désinscription que certains incidents Communication ANBU ;
- #4 peut partager une famille « parcours web mobile cassé » avec ANBU ;
- #5 crée un motif conformité/consentement également observable à l’échelle Cross ;
- aucun problème n’est artificiellement routé vers le pôle Événements.

**Ordre de grandeur attendu : ~5 Signals.**

---

# 10. Résultat AKATSUKI attendu à l’échelle du dataset

| Pôle d’origine | Observations | Signals attendus, ordre de grandeur |
|---|---:|---:|
| Commerce | 15 | ~13 |
| Basic Fit | 14 | ~12 |
| EMEA | 12 | ~11 |
| Événements & privatisations | 9 | ~9 |
| Maintenance | 10 | ~10 |
| Communication | 5 | ~5 |
| **AKATSUKI** | **65** | **~60** |

Ces chiffres sont des **ordres de grandeur de validation**, pas une consigne pour forcer le résultat.

Avec ANBU, la cible globale reste :

- **200 observations** ;
- environ **180 Signals** au total, selon l’agrégation réelle ;
- plusieurs motifs locaux ;
- quelques motifs véritablement Cross KONOHA via Maintenance / Communication / accès / CVC / réseau ;
- des responsabilités différentes du pôle d’origine lorsque le problème est technique ou transverse ;
- quelques Signals/plans ouverts au 29/08/2026 avec échéances futures, sans événement futur.

---

# 11. Motifs Cross KONOHA à favoriser sans les forcer

Le provider scripté et les payloads doivent permettre de tester des rapprochements plausibles entre ANBU et AKATSUKI, sans rendre les sites artificiellement identiques.

Familles utiles :

1. **CVC / ventilation**
   - ANBU : chambres, petit-déjeuner, cabines coworking, hottes/restaurants, atelier.
   - AKATSUKI : vestiaires/plateau sport, zone loisirs, maintenance.
   - Même famille possible ; les incidents restent distincts.

2. **Réseau / IT**
   - ANBU : réception hôtel, coworking Wi-Fi, caisse restaurants.
   - AKATSUKI : caisses Commerce, contrôle billets EMEA.
   - Le classifieur peut distinguer Wi-Fi client et périphériques métier, mais le Cross doit avoir de la matière.

3. **Contrôle d’accès / équipements d’entrée**
   - ANBU : badges hôtel/coworking, ascenseurs/portes.
   - AKATSUKI : tourniquet Basic Fit, lecteur billetterie EMEA, porte automatique Commerce.
   - Favoriser des motifs canoniques cohérents sans fusion de Signals entre établissements.

4. **Électricité / sécurité équipement**
   - rallonges, éclairage de sécurité, commandes ou appareils présentant un symptôme ;
   - responsabilité Maintenance.

5. **Parcours web / CRM**
   - liens cassés mobile, désinscription, consentement, incohérences de contenu ;
   - responsabilité Communication.

Ces familles servent à rendre le **Dashboard Cross KONOHA** intéressant. Elles ne doivent pas conduire à utiliser exactement les mêmes textes ou les mêmes lieux dans les deux établissements.

---

# 12. Références métier utilisées pour concevoir les scénarios

Les scénarios sont fondés sur la configuration runtime AKATSUKI et sur des références publiques officielles.

### Commerce

- **INRS — Commerce de détail non alimentaire : les risques du métier**
  - manutention et rangement ;
  - allées encombrées / sols glissants ;
  - accès en hauteur ;
  - déballage et outils de coupe ;
  - stress et organisation du point de vente.
- **DGCCRF / economie.gouv.fr — information et affichage des prix**
  - prix visible et compréhensible ;
  - cohérence entre prix annoncé et prix appliqué ;
  - règles sur les réductions de prix.

### Basic Fit / sport

- **Ministère des Sports — principaux textes de référence pour les équipements sportifs**
  - obligations générales d’hygiène et de sécurité des établissements d’APS ;
  - sécurité des ERP et prise en compte de l’effectif.
- **Ministère des Sports — normes AFNOR sport**
  - sécurité, confort et exploitation des salles de sport et matériels.
- **INRS — prévention des risques liés à l’utilisation des machines**
  - détection des anomalies ;
  - mise hors service / maintenance ;
  - sécurité pendant utilisation, nettoyage et maintenance.
- **INRS — contrôle des installations de ventilation**
  - vestiaires, sanitaires et lieux de travail concernés par les obligations d’aération et de contrôle.

### Loisirs / événements

- **Service-Public / Entreprendre — sécurité incendie des ERP**
  - dégagements et évacuation ;
  - alarme et organisation de la sécurité ;
  - circulation du public.
- **Service-Public — déclarations / autorisations de manifestations**
  - plans, assurance, mesures de sécurité et organisation.
- Les scénarios EMEA restent volontairement génériques car aucun type d’activité de loisirs précis n’est persisté dans la DB.

### Communication

- **CNIL — communications/prospection commerciale par voie électronique**
  - consentement B2C ;
  - action positive ;
  - case non pré-cochée ;
  - possibilité simple de s’opposer / se désinscrire.

Ces références servent au réalisme des situations. **Les Business Units et Activity Subjects runtime de Spore restent la source de vérité pour le routing.**

---

# 13. Checklist avant génération

Avant que Cursor transforme cette matrice en corpus d’observations, vérifier :

- [ ] les **65 lignes** sont conservées ;
- [ ] aucune date d’observation > 29/08/2026 ;
- [ ] les auteurs correspondent aux memberships actifs AKATSUKI ;
- [ ] les localisations sont injectées dans `location_text` ;
- [ ] aucun `OperationalUnit` n’est inventé ;
- [ ] aucune catégorie précise de produits Commerce n’est inventée ;
- [ ] aucune attraction/activité précise EMEA n’est inventée ;
- [ ] Basic Fit reste une salle de sport générique cohérente avec les sujets runtime ;
- [ ] le texte naturel ne contient pas de métadonnées techniques du scénario ;
- [ ] les relations « même Signal » utilisent une clé d’agrégation compatible et restent actives jusqu’à l’observation suivante ;
- [ ] les relations « même motif, nouveau Signal » interviennent après clôture du Signal précédent ;
- [ ] les sujets/pôles attendus sont résolus contre la DB active ;
- [ ] les anomalies techniques des pôles métier peuvent router vers Maintenance ;
- [ ] les anomalies site/CRM/social peuvent router vers Communication ;
- [ ] les problèmes organisationnels restent dans Commerce / Basic Fit / EMEA / Événements quand c’est cohérent ;
- [ ] les motifs et assignments sont produits par le vrai pipeline, pas seedés directement ;
- [ ] le corpus reste déterministe via le provider scripté ;
- [ ] les rapprochements Cross KONOHA sont plausibles mais non forcés ;
- [ ] `AnalyticsHistoryCoverage.reliable_from` sera recalé au début de la couverture historique complète après replay, sans baseline SQL.
