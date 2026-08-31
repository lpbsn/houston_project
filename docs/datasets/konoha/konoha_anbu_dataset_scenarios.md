# Dataset KONOHA — Scénarios ANBU pour génération des observations

## 1. Objet du document

Ce document est la source de vérité métier pour générer les **135 observations ANBU** du nouveau dataset local KONOHA.

Il couvre les 6 pôles actifs d’ANBU :

| Pôle d’origine | Nombre d’observations |
|---|---:|
| Hôtel | 35 |
| Ishiraku Ramen | 24 |
| Yakinuku Grill | 25 |
| Coworking | 24 |
| Maintenance | 17 |
| Communication | 10 |
| **Total ANBU** | **135** |

La section **Hôtel** reprend le bloc déjà validé. Les autres pôles suivent le même niveau de précision et la même logique.

Le dataset couvre **du 01/08/2025 au 29/08/2026 inclus**. Certains Signals/plans peuvent rester ouverts au 29/08/2026 avec une échéance, un `end_at` ou une action prévue allant jusqu’au **31/10/2026**, mais **aucune observation, aucun commentaire, aucune transition lifecycle et aucun point ne doit être horodaté après le 29/08/2026** dans le dataset initial.

---

## 2. Règles pour Cursor lors de la génération des observations

### 2.1 Ne pas transformer la matrice en état final

La matrice décrit l’intention métier et les résultats attendus pour validation.

Cursor ne doit pas :

- créer directement les `Signal` ;
- créer directement les motifs / `OperationalPattern` ;
- créer directement les `SignalPatternAssignment` ;
- antidater ensuite des états finaux via ORM ;
- appeler `apply_analytics_history_cutover`.

Le replay final doit passer par le vrai workflow produit prévu par le chantier dataset : observation → pipeline sync déterministe → Signal/agrégation → classification sync → éventuelle qualification → plans/transitions/comments via les writers réels sous horloge contrôlée.

### 2.2 Génération du texte naturel

Pour chaque ligne de scénario, générer une **observation naturelle en français**, généralement 1 à 3 phrases.

Le texte doit :

- ressembler à une remontée faite par quelqu’un réellement sur le terrain ;
- conserver les détails concrets du scénario : lieu, symptôme, contexte, fréquence, conséquence ;
- éviter les formulations génériques comme « problème de clim », « machine cassée », « sol sale » ;
- ne pas mentionner artificiellement le nom du sujet catalogue, le pôle responsable, le motif ou le comportement d’agrégation ;
- varier la formulation et le niveau de détail selon l’auteur ;
- ne pas ajouter de diagnostic technique certain quand l’auteur ne peut raisonnablement constater qu’un symptôme ;
- rester cohérent avec le contexte physique connu d’ANBU.

### 2.3 Voix des auteurs

- **Staff** : observations plus directes, centrées sur ce qui vient d’être vu pendant le service.
- **Managers** : davantage de contexte, fréquence, impact client ou organisationnel.
- **Maintenance** : constat plus technique mais restant une observation, pas un rapport d’expertise inventé.
- **Communication** : contexte publication/campagne/support, incohérences de contenu, impact client ou conformité.

Ne pas caricaturer les voix et ne pas utiliser systématiquement le même template.

### 2.4 Routing attendu

Les colonnes « Responsable / sujet attendu » servent à contrôler le pipeline.

Important :

- le pôle d’origine n’est pas forcément le pôle responsable ;
- les problèmes techniques des pôles Hôtel / restaurant / Coworking doivent généralement router vers le **pôle transversal Maintenance** ;
- un problème de contenu ou de canal peut router vers **Communication** ;
- les sujets purement opérationnels restent dans le pôle métier concerné ;
- `OperationalUnit` n’est pas utilisé pour le Dashboard Localisations : la localisation vient de `location_text`.

Lors de l’implémentation, résoudre les **sujets actifs exacts de la DB**. Les intitulés de ce document expriment l’intention sémantique et ne doivent pas conduire à créer un sujet absent.

### 2.5 Agrégation et motifs

Les lignes indiquées « même Signal » doivent être conçues pour agréger dans le Signal encore actif correspondant.

Les lignes « nouveau Signal, même motif » doivent être assez proches sémantiquement pour converger vers le même motif canonique, tout en représentant un nouvel incident après clôture du précédent.

Ne jamais forcer artificiellement une fusion Signal→Signal pour obtenir ce résultat.

---

# 3. ANBU — Hôtel — 35 observations

**Contexte :** hôtel ~80 chambres sur 5 étages, hall en pierre claire, réception, bagagerie, salle petit-déjeuner et circulations clients. Pas de pôle Petit-déjeuner : les sujets restent Hôtel ou basculent vers le transversal approprié.

| # | Date | Auteur | Localisation | Situation terrain précise | Responsable / sujet attendu | Relation / comportement attendu | Cycle prévu |
|---:|---|---|---|---|---|---|---|
| 1 | 06/08/2025 16:20 | Iruka Umino | Chambre 412 | Climatisation réglée à 20°C mais chambre encore à ~26°C après 45 min ; air à peine frais. | Maintenance → CVC | Nouveau Signal `CVC chambre 412` | Plan maintenance, résolu 08/08 |
| 2 | 07/08/2025 09:10 | Asuma Sarutobi | Chambre 412 | Même chambre, toujours chaude après reset du thermostat ; client relogé la veille. | Maintenance → CVC | **Même Signal #1**, agrégation attendue | Même cycle |
| 3 | 18/08/2025 22:40 | Genma Shiranui | Chambre 305 | Ventilo-convecteur fait un claquement toutes les 20–30 secondes, surtout vitesse 2. | Maintenance → CVC | Nouveau Signal mais **même motif canonique CVC** que #1 | Résolu rapidement |
| 4 | 03/09/2025 11:15 | Anko Mitarashi | Couloir étage 3 | Roue avant droite du chariot de ménage se bloque ; il faut le tirer de travers lorsqu’il est chargé. | Maintenance → Équipements d’exploitation | Nouveau | Remplacement roue |
| 5 | 14/09/2025 14:00 | Kurenai Yuhi | Lingerie étage 2 | Trois sacs de linge sale laissés devant l’accès aux étagères propres ; passage très réduit. | Hôtel → Linge | Nouveau motif organisationnel | Correction même jour |
| 6 | 28/09/2025 10:25 | Iruka Umino | Chambre 214 | Douche s’évacue très lentement ; eau atteint presque le seuil après quelques minutes. | Maintenance → Plomberie & Eau | Nouveau | Plan plomberie |
| 7 | 02/10/2025 08:35 | Anko Mitarashi | Chambre 214 | Après occupation, eau remonte maintenant autour de la bonde et met plusieurs minutes à partir. | Maintenance → Plomberie & Eau | **Même Signal #6**, aggravation | Résolu 03/10 |
| 8 | 12/10/2025 15:05 | Genma Shiranui | Réception | Une chambre apparaît prête alors que l’équipe ménage signale qu’elle est encore en cours ; client envoyé trop tôt à l’étage. | Hôtel → Check in/out | Nouveau, process et coordination | Plan interne |
| 9 | 19/10/2025 18:20 | Kurenai Yuhi | Chambre 508 | Badge fonctionne à l’ascenseur mais porte chambre refuse 2 à 3 lectures sur 5. | Maintenance → Équipements d’exploitation | Nouveau | Serrure/badge contrôlé |
| 10 | 05/11/2025 13:40 | Asuma Sarutobi | Bagagerie | Une fixation de l’étagère haute bouge quand plusieurs valises sont posées dessous. | Maintenance → Bâtiment & second œuvre | Nouveau | Traité prioritairement |
| 11 | 21/11/2025 09:00 | Anko Mitarashi | Local ménage étage 4 | Deux pulvérisateurs transvasés n’ont plus de nom ni dilution indiquée ; impossible d’identifier le produit rapidement. | Hôtel → Ménage | Nouveau motif process ménage | Action interne, pas Maintenance |
| 12 | 03/12/2025 10:50 | Iruka Umino | Salle petit-déjeuner | Après nettoyage de la machine à boissons, une zone reste mouillée devant le meuble pendant l’ouverture clients. | Hôtel → Ménage | Nouveau | Procédure + essuyage |
| 13 | 12/12/2025 17:35 | Kurenai Yuhi | Réception | Imprimante utilisée pour factures perd régulièrement la connexion ; deux check-out ont dû attendre le redémarrage. | Maintenance → Réseau & IT | Nouveau | Résolu 13/12 |
| 14 | 20/12/2025 15:55 | Asuma Sarutobi | Réception | Un des deux encodeurs de badges ne détecte plus les cartes pendant le pic d’arrivées. | Maintenance → Équipements d’exploitation | Nouveau | Signal ouvert |
| 15 | 20/12/2025 18:10 | Genma Shiranui | Réception | Deuxième remontée sur le même encodeur : 7 badges ont dû être préparés sur l’unique poste restant. | Maintenance → Équipements d’exploitation | **Même Signal #14** | Résolu 21/12 |
| 16 | 04/01/2026 16:30 | Anko Mitarashi | Office linge étage 5 | Plus de grandes serviettes propres alors que plusieurs chambres restent à préparer ; stock présent ailleurs dans l’hôtel. | Hôtel → Linge | Nouveau ; problème de répartition stock | Plan interne |
| 17 | 12/01/2026 23:20 | Genma Shiranui | Couloir étage 2 | Porte du local de service claque fortement à chaque passage et plusieurs clients se sont plaints du bruit. | Maintenance → Bâtiment & second œuvre | Nouveau | Réglage ferme-porte |
| 18 | 25/01/2026 07:45 | Iruka Umino | Chambre 402 | Température douche alterne chaud/froid sans toucher au mitigeur ; problème reproduit au lavabo. | Maintenance → Plomberie & Eau | Nouveau motif plomberie | Résolu 27/01 |
| 19 | 08/02/2026 12:05 | Asuma Sarutobi | Bagagerie | Poignée du grand chariot à valises a du jeu et se déforme lorsqu’il est chargé lourdement. | Maintenance → Équipements d’exploitation | Nouveau | Maintenance |
| 20 | 20/02/2026 14:50 | Kurenai Yuhi | Chambre 217 | Chambre marquée prête côté réception, mais poubelle non vidée et salle de bain encore en cours de nettoyage. | Hôtel → Ménage | **Récurrence du problème organisationnel #8**, nouveau Signal | Analyse handover |
| 21 | 05/03/2026 08:15 | Iruka Umino | Hall / sortie ascenseurs | Panneau temporaire « Petit-déjeuner » oriente vers la gauche alors que la salle est à droite depuis le réaménagement. | Hôtel → Signalétique | Nouveau | Correction immédiate |
| 22 | 18/03/2026 11:25 | Anko Mitarashi | Chambre 509 | Rail du rideau occultant commence à s’arracher côté fenêtre ; deux vis sortent du plafond. | Maintenance → Bâtiment & second œuvre | Nouveau | Plan maintenance |
| 23 | 02/04/2026 17:10 | Genma Shiranui | Palier étage 5 | Bouton d’appel ascenseur ne réagit parfois qu’au deuxième ou troisième appui. | Maintenance → Équipements d’exploitation | Nouveau | Signal |
| 24 | 03/04/2026 07:50 | Kurenai Yuhi | Palier étage 5 | Même bouton totalement inactif pendant quelques minutes ce matin ; ascenseur appelé depuis un autre étage. | Maintenance → Équipements d’exploitation | **Même Signal #23**, aggravation | Intervention prestataire |
| 25 | 15/04/2026 10:30 | Asuma Sarutobi | Réception / site hôtel | Site indique petit-déjeuner jusqu’à 11h alors que le service se termine à 10h30 ; plusieurs clients l’ont signalé. | Communication → Site internet / contenu | Nouveau ; affecté Hôtel, responsable Communication | Corrigé 16/04 |
| 26 | 01/05/2026 12:20 | Kurenai Yuhi | Réception | Sur un départ tardif, supplément a été ajouté deux fois avant détection au contrôle de facture. | Hôtel → Facturation & caisse | Nouveau | Procédure/contrôle |
| 27 | 16/05/2026 10:05 | Anko Mitarashi | Office ménage étage 5 | Aspirateur de l’étage tire nettement à droite et gaine du câble commence à se fendre près de la poignée. | Maintenance → Équipements d’exploitation | Nouveau | Retrait matériel |
| 28 | 17/05/2026 09:30 | Iruka Umino | Office ménage étage 5 | Même aspirateur encore présent ce matin malgré l’étiquette hors service ; câble visible au niveau de la fissure. | Maintenance → Équipements d’exploitation | **Même Signal #27**, ajoute problème de mise hors service | Résolution + process |
| 29 | 04/06/2026 13:15 | Genma Shiranui | Chambre 312 | Joint inférieur de douche reste noir après nettoyage approfondi et commence à se décoller sur ~20 cm. | Maintenance → Bâtiment & second œuvre | Nouveau | Remplacement joint |
| 30 | 20/06/2026 15:40 | Asuma Sarutobi | Couloir étage 4 | Porte de la gaine/descente de linge ne verrouille plus correctement et reste parfois entrouverte après usage. | Maintenance → Équipements d’exploitation | Nouveau | Intervention |
| 31 | 02/07/2026 17:05 | Kurenai Yuhi | Bagagerie | Plus de tickets bagages numérotés pendant un pic d’arrivées ; équipe utilise des papiers manuscrits et deux valises ont failli être inversées. | Hôtel → Check in/out | Nouveau | Plan réassort + stock mini |
| 32 | 19/07/2026 21:15 | Genma Shiranui | Chambre 415 | Extraction salle de bain fait un bourdonnement continu et aspire très peu malgré grille propre. | Maintenance → CVC | **Nouveau Signal, motif CVC récurrent** (#1/#3) | Résolu 21/07 |
| 33 | 03/08/2026 09:25 | Iruka Umino | Chambre 108 | Forte odeur remontant de la bonde après plusieurs jours sans occupation ; disparaît temporairement après écoulement d’eau. | Maintenance → Plomberie & Eau | Nouveau Signal, motif plomberie connu | Résolu |
| 34 | 10/08/2026 09:50 | Asuma Sarutobi | Salle petit-déjeuner | Pendant forte chaleur et salle pleine, climatisation ne maintient plus une température confortable malgré consigne basse. | Maintenance → CVC | **Nouvelle occurrence du motif CVC**, nouveau Signal | Plan ouvert puis résolu 13/08 |
| 35 | 28/08/2026 18:10 | Kurenai Yuhi | Bagagerie / arrière réception | Éclairage plafond clignote puis s’éteint par intermittence ; bagagerie encore utilisée mais visibilité mauvaise au fond. | Maintenance → Électricité | Nouveau Signal | **Encore ouvert au 29/08**, action prévue avant 05/10 |

### Résultat attendu Hôtel

Ces 35 observations ne doivent pas devenir 35 Signals.

Relations fortes :

- #1 + #2 → même Signal ;
- #6 + #7 → même Signal ;
- #14 + #15 → même Signal ;
- #23 + #24 → même Signal ;
- #27 + #28 → même Signal ;
- #3, #32 et #34 → Signals distincts mais motif CVC commun ;
- #8 et #20 → Signals distincts, motif de coordination / préparation chambre récurrent ;
- #35 → actif au cut-off.

**Ordre de grandeur attendu : ~30 Signals.**

---

# 4. ANBU — Ishiraku Ramen — 24 observations

**Contexte :** restaurant ~60 couverts, cuisine semi-ouverte, comptoir bois, banquettes rouges, ramen / gyozas / bouillons. Les sujets métier disponibles incluent notamment Menu, Mise en place, Propreté, Service & accueil, Stock, Expérience client, RH, Administration et Commercialisation.

| # | Date | Auteur | Localisation | Situation terrain précise | Responsable / sujet attendu | Relation / comportement attendu | Cycle prévu |
|---:|---|---|---|---|---|---|---|
| 1 | 12/08/2025 10:05 | Chôji Akimichi | Chambre froide cuisine | À l’ouverture, afficheur à 7,1°C ; les bacs du fond sont moins froids au toucher que d’habitude alors que la porte était fermée toute la nuit. | Maintenance → CVC / Équipements d’exploitation | Nouveau Signal froid positif | Contrôle + intervention, ouvert |
| 2 | 12/08/2025 11:10 | Tehuci Ishiraku | Chambre froide cuisine | Même chambre froide : joint côté poignée reste légèrement décollé et condensation visible autour de la porte. | Maintenance → CVC / Équipements d’exploitation | **Même Signal #1** | Résolu 13/08 |
| 3 | 07/09/2025 22:35 | Konohamaru Sarutobi | Plonge | Après le rush, une flaque revient sous le lave-vaisselle malgré essuyage ; elle réapparaît surtout en fin de cycle. | Maintenance → Plomberie & Eau / Équipements | Nouveau | Plan maintenance |
| 4 | 08/09/2025 12:15 | Ayame Ishiraku | Plonge | Même fuite, cette fois visible au raccord sous la machine après deux cycles consécutifs ; zone de passage rapidement mouillée. | Maintenance → Plomberie & Eau / Équipements | **Même Signal #3** | Résolu 09/09 |
| 5 | 24/09/2025 17:20 | Moegi Kazamatsuri | Réserve sèche | Le stock de nori est presque épuisé avant le week-end alors que le niveau de réassort affiché indique encore deux jours de marge. | Ishiraku → Stock | Nouveau motif gestion stock | Corrigé via seuil de réassort |
| 6 | 09/10/2025 16:40 | Tehuci Ishiraku | Comptoir / carte | La fiche allergènes de deux sauces gyoza n’a pas été mise à jour après le changement de fournisseur ; composition différente sur les nouveaux cartons. | Ishiraku → Menu | Nouveau | Correction immédiate |
| 7 | 27/10/2025 19:05 | Chôji Akimichi | Poste bouillons | Un bac de maintien chaud descend à ~56–58°C entre deux services alors que la consigne n’a pas changé ; les autres bacs restent stables. | Maintenance → Équipements d’exploitation | Nouveau motif équipement chaud | Retrait du bac + intervention |
| 8 | 15/11/2025 10:25 | Moegi Kazamatsuri | Mise en place cuisine | Plusieurs bacs préparés le matin sont étiquetés avec le contenu mais sans heure de préparation ; impossible de savoir lesquels sont les plus anciens. | Ishiraku → Mise en place | Nouveau | Rappel process |
| 9 | 29/11/2025 20:15 | Konohamaru Sarutobi | Passe cuisine | L’imprimante tickets se met en pause puis ressort plusieurs commandes d’un coup ; deux tables ont reçu leur ticket avec plusieurs minutes de retard. | Maintenance → Réseau & IT / Équipements | Nouveau | Résolu après diagnostic |
| 10 | 13/12/2025 21:00 | Ayame Ishiraku | Cuisine semi-ouverte | La vapeur reste nettement plus longtemps côté passe pendant le service ; odeurs de cuisson perceptibles jusqu’aux premières tables malgré hottes en marche. | Maintenance → CVC | Nouveau motif extraction | Plan CVC |
| 11 | 21/12/2025 13:10 | Tehuci Ishiraku | Entrée / comptoir | La liste d’attente papier et l’ordre annoncé au comptoir se sont désynchronisés pendant le rush ; deux groupes arrivés après ont été placés avant. | Ishiraku → Service & accueil | Nouveau | Ajustement process |
| 12 | 08/01/2026 10:45 | Chôji Akimichi | Lave-mains cuisine | Distributeur de savon vide à l’ouverture pour la deuxième fois cette semaine alors que la réserve est disponible juste à côté. | Ishiraku → Propreté / Mise en place | Nouveau | Contrôle ouverture |
| 13 | 28/01/2026 09:50 | Moegi Kazamatsuri | Congélateur réserve | Givre épais sur le cadre intérieur ; la porte doit être poussée fortement pour rester fermée. | Maintenance → CVC / Équipements | Nouveau | Dégivrage + contrôle |
| 14 | 17/02/2026 22:10 | Konohamaru Sarutobi | Évier préparation | L’évacuation devient très lente en fin de service ; l’eau monte dans la cuve dès que le débit est un peu fort. | Maintenance → Plomberie & Eau | Nouveau | Résolu 18/02 |
| 15 | 06/03/2026 11:00 | Ayame Ishiraku | Chambre froide cuisine | Nouvelle dérive : affichage à 6,6°C après livraison, température ne redescend pas normalement après 40 minutes porte fermée. | Maintenance → CVC / Équipements | **Nouveau Signal, même motif froid que #1/#2** | Résolu 07/03 |
| 16 | 25/03/2026 18:10 | Chôji Akimichi | Réserve vaisselle | Il reste moins d’une rotation complète de grands bols ramen propres avant le service du soir ; beaucoup de casse ce mois-ci non répercutée dans le stock mini. | Ishiraku → Stock | Nouveau | Réassort |
| 17 | 11/04/2026 14:20 | Tehuci Ishiraku | Vitrine / menu extérieur | Le support affiché devant le restaurant présente encore l’ancien prix d’une formule alors que la carte et la caisse sont à jour. | Communication → Contenu / supports | Nouveau, affecté Ishiraku | Corrigé |
| 18 | 03/05/2026 12:05 | Moegi Kazamatsuri | Poste bouillons | Le couvercle du bac de maintien principal ferme mal depuis ce matin et la température chute plus vite à chaque ouverture pendant le service. | Maintenance → Équipements d’exploitation | Nouveau Signal, même famille que #7 | Intervention |
| 19 | 24/05/2026 21:35 | Konohamaru Sarutobi | Passage cuisine → plonge | Un coin du tapis antidérapant se relève et accroche le pied quand on transporte des bacs vers la plonge. | Ishiraku → Propreté / Mise en place | Nouveau | Tapis retiré/remplacé |
| 20 | 12/06/2026 15:30 | Ayame Ishiraku | Plonge | Le cycle de rinçage termine avec une vaisselle nettement moins chaude qu’habituellement ; résultat correct sur les premiers cycles puis dégrade. | Maintenance → Équipements d’exploitation | Nouveau | Maintenance |
| 21 | 05/07/2026 09:35 | Chôji Akimichi | Réception marchandises / réserve | Les cartons de livraison du matin restent devant l’accès à la réserve pendant le contrôle, ce qui oblige à contourner avec les bacs de préparation. | Ishiraku → Stock / Mise en place | Nouveau | Organisation réception |
| 22 | 19/07/2026 23:00 | Tehuci Ishiraku | Fermeture cuisine | Deux absences sur la fermeture ont décalé le nettoyage et le contrôle des stocks de près d’une heure trois soirs cette semaine. | Ishiraku → RH | Nouveau | Ajustement planning |
| 23 | 09/08/2026 20:25 | Konohamaru Sarutobi | Comptoir caisse | Terminal de paiement perd la connexion plusieurs fois pendant le service ; chaque reprise demande de relancer la transaction. | Maintenance → Réseau & IT | Nouveau | Résolu 10/08 |
| 24 | 27/08/2026 22:20 | Moegi Kazamatsuri | Plonge | Une nouvelle fuite apparaît sous le lave-vaisselle, plus légère qu’en septembre mais continue après plusieurs cycles ; serpillière nécessaire pendant la fermeture. | Maintenance → Plomberie & Eau / Équipements | **Nouveau Signal, même motif que #3/#4** | **Ouvert au 29/08**, intervention prévue avant 15/10 |

### Résultat attendu Ishiraku

Relations fortes :

- #1 + #2 → même Signal ;
- #3 + #4 → même Signal ;
- #15 → nouveau Signal mais motif froid récurrent de #1/#2 ;
- #18 → nouveau Signal dans la famille équipement de maintien chaud de #7 ;
- #24 → nouvel incident après clôture, même motif fuite plonge que #3/#4 ;
- #17 → pôle d’origine Ishiraku, responsabilité Communication ;
- plusieurs incidents techniques doivent renforcer les motifs Maintenance sans absorber les problèmes opérationnels Stock / Menu / Mise en place.

**Ordre de grandeur attendu : ~21 Signals.**

---

# 5. ANBU — Yakinuku Grill — 25 observations

**Contexte :** restaurant ~90 couverts, grills encastrés aux tables, hottes/extraction, commandes de puissance et cloisons bois. La qualité du dataset dépend ici de symptômes très concrets autour des grills, extraction, graisse, froid, mise en place et service.

| # | Date | Auteur | Localisation | Situation terrain précise | Responsable / sujet attendu | Relation / comportement attendu | Cycle prévu |
|---:|---|---|---|---|---|---|---|
| 1 | 16/08/2025 19:10 | Haku Momochi | Table grill 12 | Une des zones du grill met beaucoup plus longtemps à rougir que les autres ; cuisson nettement plus lente sur le côté gauche. | Maintenance → Équipements d’exploitation | Nouveau Signal grill | Ouvert |
| 2 | 17/08/2025 12:40 | Zabuza Momochi | Table grill 12 | Même défaut après remise en route : zone gauche chauffe par à-coups et les clients ont dû être déplacés sur une autre table. | Maintenance → Équipements d’exploitation | **Même Signal #1** | Résolu 18/08 |
| 3 | 06/09/2025 20:50 | Kotetsu Hagane | Rangée B / hottes | La fumée reste visible plus longtemps au-dessus des grills de la rangée B alors que toutes les hottes sont en marche. | Maintenance → CVC | Nouveau motif extraction | Contrôle CVC |
| 4 | 21/09/2025 16:15 | Aoba Yamashiro | Zone filtres hottes | Deux filtres sont beaucoup plus gras que les autres alors que le planning indique un nettoyage effectué la veille. | Yakinuku → Propreté | Nouveau motif process nettoyage | Reprise procédure |
| 5 | 08/10/2025 17:05 | Haku Momochi | Froid préparation | Meuble réfrigéré des marinades affiche 6,4°C avant le service ; les autres meubles sont autour de leur valeur habituelle. | Maintenance → CVC / Équipements | Nouveau | Produits déplacés + contrôle |
| 6 | 25/10/2025 21:20 | Izumo Kamizuki | Table grill 7 | Bouton de puissance a du jeu et devient anormalement chaud après plusieurs changements de niveau pendant le service. | Maintenance → Électricité / Équipements | Nouveau | Table neutralisée |
| 7 | 10/11/2025 23:05 | Haku Momochi | Évier arrière cuisine | Odeur d’évacuation et glouglous après le gros service ; l’eau descend normalement au début puis ralentit. | Maintenance → Plomberie & Eau | Nouveau | Intervention |
| 8 | 26/11/2025 19:45 | Zabuza Momochi | Hotte rangée A | La hotte vibre avec un bruit métallique intermittent à puissance moyenne ; vibration disparaît brièvement quand on baisse l’aspiration. | Maintenance → CVC | Nouveau Signal extraction | Reste ouvert |
| 9 | 05/12/2025 11:25 | Kotetsu Hagane | Salle / cloison table 5 | Une cloison bois bouge quand on s’appuie légèrement dessus ; fixation basse visible et desserrée. | Maintenance → Bâtiment & second œuvre | Nouveau | Fixation |
| 10 | 14/12/2025 16:30 | Aoba Yamashiro | Carte sauces | Le tableau allergènes mentionne toujours l’ancienne recette d’une sauce alors qu’un nouveau produit est utilisé depuis la livraison de vendredi. | Yakinuku → Menu | Nouveau | Correction |
| 11 | 19/12/2025 21:40 | Haku Momochi | Rangée A | Pendant salle pleine, fumée plus présente autour des tables proches de la hotte bruyante ; deux clients ont demandé à changer de place. | Maintenance → CVC | **Même Signal #8** | Résolu 21/12 |
| 12 | 09/01/2026 23:10 | Izumo Kamizuki | Passage derrière rangée A | Fine pellicule grasse encore présente au sol après fermeture ; chaussures glissent légèrement au même endroit près de deux tables. | Yakinuku → Propreté | Nouveau | Nettoyage renforcé |
| 13 | 24/01/2026 20:35 | Kotetsu Hagane | Table grill 4 | Grill se coupe complètement après ~15 minutes à puissance élevée puis repart après quelques minutes sans action. | Maintenance → Électricité / Équipements | Nouveau motif grill électrique | Intervention |
| 14 | 15/02/2026 18:25 | Haku Momochi | Mise en place cuisine | Pinces destinées aux préparations crues et aux aliments prêts à servir ont été rangées ensemble sur le même bac après lavage. | Yakinuku → Mise en place | Nouveau | Organisation matériel |
| 15 | 07/03/2026 15:00 | Zabuza Momochi | Réserve matériel grill | Plus aucune plaque de remplacement disponible alors que deux plaques en service sont déjà marquées et prévues au remplacement. | Yakinuku → Stock | Nouveau | Réassort préventif |
| 16 | 03/04/2026 18:40 | Aoba Yamashiro | Plan de salle / accueil | Le plan utilisé à l’accueil indique encore deux tables disponibles alors qu’elles sont neutralisées pour maintenance de grill. | Yakinuku → Service & accueil | Nouveau | Mise à jour process |
| 17 | 22/04/2026 10:50 | Zabuza Momochi | Ligne de grills | L’étiquette d’identification d’un arrêt d’urgence est presque illisible après nettoyage répété ; bouton fonctionnel mais repère difficile à lire. | Maintenance → Sécurité & conformité | Nouveau | Signalétique technique remplacée |
| 18 | 14/05/2026 20:15 | Haku Momochi | Rangée C / hottes | Nouvelle baisse d’aspiration : vapeur et fumée s’évacuent mal sur trois tables alors que l’incident de décembre était clos. | Maintenance → CVC | **Nouveau Signal, motif extraction récurrent #8/#11** | Résolu 16/05 |
| 19 | 02/06/2026 22:45 | Izumo Kamizuki | Hotte table 16 | Petite trace de graisse liquide au coin inférieur de la hotte après service ; réapparaît après essuyage. | Maintenance → CVC / Équipements | Nouveau | Inspection |
| 20 | 17/06/2026 09:55 | Aoba Yamashiro | Froid préparation | Joint de porte du meuble réfrigéré se déchire sur plusieurs centimètres et la porte ne plaque plus régulièrement. | Maintenance → CVC / Équipements | Nouveau, famille froid | Remplacement |
| 21 | 04/07/2026 17:30 | Haku Momochi | Mise en place sauces | Plusieurs bouteilles transvasées portent le nom de la sauce mais pas la date d’ouverture/préparation. | Yakinuku → Mise en place | Nouveau | Correction |
| 22 | 23/07/2026 21:10 | Kotetsu Hagane | Passe / caisse | Les commandes validées sur deux tables mettent parfois plusieurs minutes à apparaître côté cuisine alors que la caisse reste connectée. | Maintenance → Réseau & IT | Nouveau | Diagnostic réseau |
| 23 | 12/08/2026 19:20 | Izumo Kamizuki | Table grill 18 | Grill chauffe beaucoup plus fort au centre qu’en périphérie malgré niveau identique ; cuisson irrégulière sur la même plaque. | Maintenance → Équipements d’exploitation | Nouveau Signal grill | Ouvert |
| 24 | 13/08/2026 12:35 | Zabuza Momochi | Table grill 18 | Défaut reproduit ce midi ; périphérie reste insuffisamment chaude et table retirée du plan de salle. | Maintenance → Équipements d’exploitation | **Même Signal #23** | Résolu 15/08 |
| 25 | 29/08/2026 18:45 | Aoba Yamashiro | Hotte rangée C | La hotte démarre normalement puis baisse seule de régime après une vingtaine de minutes ; phénomène reproduit deux fois avant le service. | Maintenance → CVC | Nouveau Signal, motif extraction connu | **Ouvert au cut-off**, intervention prévue avant 20/10 |

### Résultat attendu Yakinuku

Relations fortes :

- #1 + #2 → même Signal ;
- #8 + #11 → même Signal ;
- #23 + #24 → même Signal ;
- #18 et #25 → nouveaux Signals mais motif extraction déjà connu ;
- #13, #23/#24 → famille de problèmes grills sans forcément devenir le même motif exact si le classifieur distingue « coupure » et « chauffe irrégulière » ;
- #10, #14, #21 restent des problèmes métier restaurant, pas Maintenance.

**Ordre de grandeur attendu : ~22 Signals.**

---

# 6. ANBU — Coworking — 24 observations

**Contexte :** ~1 000 m², badges, casiers, open space, salles de réunion, cabines, écrans de réservation. Les sujets disponibles incluent Ambiance, Communication & événements, Connexion & IT, Événement, Expérience utilisateur, Facturation membres, Propreté, RH & planning, Service et Commercialisation.

| # | Date | Auteur | Localisation | Situation terrain précise | Responsable / sujet attendu | Relation / comportement attendu | Cycle prévu |
|---:|---|---|---|---|---|---|---|
| 1 | 20/08/2025 08:35 | Sai Yamanaka | Entrée coworking | Lecteur badge refuse certaines cartes au premier passage ; voyant reste orange puis passe vert après 2 ou 3 essais. | Maintenance → Équipements d’exploitation | Nouveau Signal badges | Ouvert |
| 2 | 20/08/2025 09:20 | Shikamaru Nara | Entrée coworking | Même lecteur : trois membres ont dû être ouverts manuellement depuis l’accueil ce matin. | Maintenance → Équipements d’exploitation | **Même Signal #1** | Résolu 21/08 |
| 3 | 11/09/2025 15:10 | Yamato Tenzo | Open space côté salles | Coupures Wi-Fi de quelques secondes toutes les 10–15 minutes ; appels vidéo figent mais la connexion revient seule. | Maintenance → Réseau & IT | Nouveau motif Wi-Fi | Résolu |
| 4 | 02/10/2025 09:45 | Ino Yamanaka | Salle Sakura | Écran de réservation affiche « libre » alors que la salle est occupée et réservée dans l’outil web. | Maintenance → Réseau & IT | Nouveau | Synchronisation corrigée |
| 5 | 23/10/2025 17:30 | Tenten Iwamizawa | Casiers / rangée 40–50 | Casier 47 se déverrouille au badge mais la porte reste bloquée mécaniquement ; affaires d’un membre coincées à l’intérieur. | Maintenance → Équipements d’exploitation | Nouveau | Intervention |
| 6 | 12/11/2025 14:05 | Sai Yamanaka | Cabine téléphonique 6 | Cabine devient très chaude après 10 minutes porte fermée et ventilation presque inaudible par rapport aux autres cabines. | Maintenance → CVC | Nouveau motif ventilation cabine | Résolu |
| 7 | 26/11/2025 11:20 | Yamato Tenzo | Open space / bureau réglable 18 | Plateau électrique reste bloqué en position basse ; moteur fait un clic mais ne monte plus. | Maintenance → Équipements d’exploitation | Nouveau | Réparation |
| 8 | 08/12/2025 10:15 | Ino Yamanaka | Zone imprimantes | Imprimante commune apparaît « hors ligne » pour plusieurs membres alors qu’elle est allumée et accessible depuis le poste accueil. | Maintenance → Réseau & IT | Nouveau | Résolu |
| 9 | 19/12/2025 16:50 | Shikamaru Nara | Administration coworking | Un membre ayant changé de formule a reçu deux lignes d’abonnement sur la facture du mois ; montant doublé avant correction. | Coworking → Facturation membres | Nouveau | Corrigé |
| 10 | 13/01/2026 10:40 | Tenten Iwamizawa | Zone calme / salle vitrée | Conversations de la salle voisine sont nettement audibles porte fermée depuis que le joint latéral s’est décollé. | Coworking → Ambiance, avec action Maintenance possible | Nouveau | Joint remplacé |
| 11 | 27/01/2026 18:00 | Sai Yamanaka | Casiers | Plusieurs casiers restent attribués à d’anciens membres et aucun objet n’est identifié ; presque plus de casiers libres sur cette rangée. | Coworking → Service | Nouveau | Inventaire / libération |
| 12 | 18/02/2026 09:25 | Yamato Tenzo | Open space / boîtier de sol | Toutes les prises d’un même boîtier sont sans alimentation alors que les postes voisins fonctionnent normalement. | Maintenance → Électricité | Nouveau | Intervention |
| 13 | 06/03/2026 13:15 | Tenten Iwamizawa | Salle Sakura | Porte vitrée se referme trop vite et claque ; il faut la retenir en sortant avec du matériel. | Maintenance → Bâtiment & second œuvre | Nouveau | Réglage |
| 14 | 24/03/2026 16:20 | Shikamaru Nara | Open space côté façade vitrée | Nouveau problème Wi-Fi, cette fois de l’autre côté de l’espace : débit chute surtout en milieu d’après-midi alors que l’incident de septembre était clos. | Maintenance → Réseau & IT | **Nouveau Signal, motif connectivité récurrent #3** | Résolu |
| 15 | 10/04/2026 17:45 | Ino Yamanaka | Zone événement / circulation | Mobilier préparé pour l’animation du soir réduit fortement le passage principal entre open space et sortie. | Coworking → Communication & événements / Événement | Nouveau | Reconfiguration avant ouverture |
| 16 | 29/04/2026 08:50 | Sai Yamanaka | Salle Hashirama | Écran de réservation reste noir après redémarrage ; réservation web fonctionne mais aucun statut visible devant la salle. | Maintenance → Réseau & IT | Nouveau, famille écrans #4 | Résolu |
| 17 | 16/05/2026 09:10 | Shikamaru Nara | Entrée coworking | Badge d’un membre encore actif a cessé de fonctionner un jour avant la fin prévue de son abonnement ; accès restauré manuellement. | Coworking → Service / Expérience utilisateur | Nouveau | Correction process |
| 18 | 30/05/2026 15:35 | Tenten Iwamizawa | Cabines téléphoniques | Traces de boisson et miettes retrouvées dans trois cabines en début d’après-midi malgré passage ménage indiqué le matin. | Coworking → Propreté | Nouveau | Contrôle nettoyage |
| 19 | 18/06/2026 14:55 | Yamato Tenzo | Open space côté façade vitrée | Plusieurs postes près des vitrages deviennent inconfortablement chauds l’après-midi malgré climatisation active dans le reste de l’espace. | Maintenance → CVC | Nouveau | Réglage zone CVC |
| 20 | 08/07/2026 12:25 | Sai Yamanaka | Casiers / rangée basse | Bord métallique du casier 18 s’est légèrement relevé et accroche les sacs quand on les retire. | Maintenance → Bâtiment & second œuvre / Équipements | Nouveau | Mise hors service + réparation |
| 21 | 25/07/2026 16:45 | Ino Yamanaka | Cabines 1–4 | Ventilation faible dans plusieurs cabines pendant les fortes chaleurs ; température monte vite porte fermée. | Maintenance → CVC | **Nouveau Signal, motif ventilation proche de #6** | Plan CVC |
| 22 | 05/08/2026 11:35 | Shikamaru Nara | Administration coworking | Une remise mensuelle promise à un membre n’apparaît pas sur la facture générée ; le tarif plein a été prélevé. | Coworking → Facturation membres | Nouveau | Correction |
| 23 | 19/08/2026 10:10 | Tenten Iwamizawa | Couloir salles de réunion | Wi-Fi décroche régulièrement autour des salles ; plusieurs membres basculent sur partage de connexion pour leurs appels. | Maintenance → Réseau & IT | Nouveau Signal connectivité | Ouvert |
| 24 | 28/08/2026 15:20 | Ino Yamanaka | Couloir salles de réunion | Même zone : pertes de connexion encore présentes après redémarrage du point d’accès, particulièrement quand plusieurs salles sont occupées. | Maintenance → Réseau & IT | **Même Signal #23** | **Ouvert au cut-off**, action prévue avant fin septembre |

### Résultat attendu Coworking

Relations fortes :

- #1 + #2 → même Signal ;
- #23 + #24 → même Signal ;
- #14 → nouveau Signal mais motif connectivité déjà connu via #3 ;
- #21 → nouveau Signal mais motif ventilation/cabines proche de #6 ;
- #9 et #22 → Signals distincts pouvant converger vers un motif Facturation membres ;
- #15 doit rester un problème d’organisation événementielle, pas être absorbé dans Maintenance.

**Ordre de grandeur attendu : ~22 Signals.**

---

# 7. ANBU — Maintenance — 17 observations

**Contexte :** pôle transversal couvrant tout le site, atelier au sous-sol avec établis, pièces, EPI et armoires sécurisées. Les observations de cette section sont remontées directement par l’équipe Maintenance et doivent refléter des anomalies détectées lors de rondes, préparation d’intervention, suivi prestataire ou contrôle technique.

| # | Date | Auteur | Localisation | Situation terrain précise | Responsable / sujet attendu | Relation / comportement attendu | Cycle prévu |
|---:|---|---|---|---|---|---|---|
| 1 | 27/08/2025 09:00 | Kiba Inuzuka | Atelier Maintenance / stock | Il ne reste qu’un jeu de filtres compatible avec les unités CVC les plus utilisées alors que deux remplacements préventifs sont prévus le mois prochain. | Maintenance → Logistique & consommables | Nouveau | Réassort |
| 2 | 18/09/2025 08:30 | Raidou Namiashi | Atelier sous-sol / plafond | Trace humide apparue au plafond après les pluies ; peinture légèrement cloquée mais aucune goutte au sol pour l’instant. | Maintenance → Bâtiment & second œuvre | Nouveau | Surveillance + recherche origine |
| 3 | 14/10/2025 07:50 | Shino Aburame | Couloir technique sous-sol | Un bloc d’éclairage de sécurité reste éteint pendant le test alors que les blocs voisins basculent correctement. | Maintenance → Sécurité & conformité / Électricité | Nouveau | Remplacement |
| 4 | 09/11/2025 10:15 | Iwashi Tatami | Tableau électrique zone service | Deux repères de départs sont presque effacés et ne correspondent plus clairement aux étiquettes du schéma disponible dans l’armoire. | Maintenance → Électricité / Sécurité & conformité | Nouveau | Relabellisation contrôlée |
| 5 | 04/12/2025 15:40 | Raidou Namiashi | Suivi prestataires | La visite préventive prévue sur un ascenseur n’a pas de compte-rendu reçu alors que le créneau est passé depuis plus d’une semaine. | Maintenance → Prestataires | Nouveau | Relance fournisseur |
| 6 | 19/01/2026 08:45 | Rock Lee | Atelier Maintenance / EPI | Stock de gants adaptés aux interventions courantes ne contient plus certaines tailles ; plusieurs paires restantes sont déjà très usées. | Maintenance → Logistique & consommables / Sécurité | Nouveau | Réassort |
| 7 | 11/02/2026 11:30 | Iwashi Tatami | Local technique CVC | Une unité de traitement d’air présente une vibration inhabituelle au démarrage et un bruit régulier qui disparaît après quelques minutes. | Maintenance → CVC | Nouveau | Inspection préventive |
| 8 | 05/03/2026 09:20 | Kiba Inuzuka | Local technique eau | Le manomètre du groupe de surpression oscille beaucoup plus que d’habitude pendant les appels d’eau du matin. | Maintenance → Plomberie & Eau | Nouveau | Diagnostic |
| 9 | 21/04/2026 14:10 | Shino Aburame | Baie réseau sous-sol | Onduleur affiche une alerte batterie alors qu’aucune coupure secteur n’est visible ; alarme revient après acquittement. | Maintenance → Réseau & IT / Électricité | Nouveau | Remplacement batterie planifié |
| 10 | 13/05/2026 07:35 | Rock Lee | Entrée principale | Porte automatique ralentit à mi-course puis repart ; phénomène intermittent sur plusieurs ouvertures à vide. | Maintenance → Équipements d’exploitation | Nouveau | Ouvert |
| 11 | 13/05/2026 09:05 | Raidou Namiashi | Entrée principale | Même porte : capteur détecte bien le passage mais le vantail hésite encore à mi-course ; gêne visible avec flux d’arrivées. | Maintenance → Équipements d’exploitation | **Même Signal #10** | Résolu après intervention |
| 12 | 08/06/2026 10:50 | Kiba Inuzuka | Local technique CVC | Isolation d’un tube de condensats est déchirée ; petites gouttes se forment sur la partie découverte quand l’installation tourne. | Maintenance → CVC / Plomberie & Eau | Nouveau | Réfection isolation |
| 13 | 01/07/2026 16:20 | Shino Aburame | Atelier / armoire pièces | Serrure de l’armoire sécurisée ne verrouille plus systématiquement ; il faut reprendre la poignée plusieurs fois. | Maintenance → Ouverture / fermeture | Nouveau | Remplacement serrure |
| 14 | 15/07/2026 09:30 | Iwashi Tatami | Suivi prestataires | Rapport d’intervention d’un prestataire n’est pas joint au dossier alors que l’équipement a été remis en service ; paramètres modifiés non tracés dans le dossier local. | Maintenance → Prestataires | Nouveau | Régularisation documentaire |
| 15 | 07/08/2026 08:20 | Raidou Namiashi | Palier étage 5 / ascenseur | Lors du contrôle après une remontée utilisateur, le bouton d’appel a de nouveau raté une sollicitation alors que l’incident d’avril était clos. | Maintenance → Équipements d’exploitation | **Nouveau Signal, motif ascenseur récurrent** | Prestataire |
| 16 | 21/08/2026 10:40 | Rock Lee | Mur sous-sol proche atelier | Nouvelle auréole humide au pied du mur après fortes pluies ; différente de la trace plafond observée en septembre. | Maintenance → Bâtiment & second œuvre | Nouveau Signal, famille infiltration | Recherche origine |
| 17 | 29/08/2026 09:15 | Shino Aburame | Atelier Maintenance | Extraction d’air de l’atelier semble nettement plus faible ; odeurs de produits et chaleur restent plus longtemps après les petites interventions. | Maintenance → CVC | Nouveau | **Ouvert au cut-off**, diagnostic prévu avant 25/10 |

### Résultat attendu Maintenance

Relations fortes :

- #10 + #11 → même Signal ;
- #15 → nouveau Signal sur un motif Équipements/ascenseur déjà rencontré dans Hôtel ;
- #2 et #16 → deux incidents distincts de bâtiment/infiltration, éventuellement motif commun selon le classifieur ;
- #7, #12, #17 → problèmes CVC distincts avec possibilité d’un motif Maintenance transversal sans fusion abusive.

**Ordre de grandeur attendu : ~16 Signals.**

---

# 8. ANBU — Communication — 10 observations

**Contexte :** pôle transversal avec bureau administratif, photo et imprimantes. Les observations concernent le site, contenus, réseaux sociaux, CRM, e-réputation, supports physiques et cohérence de publication. Elles ne doivent pas inventer un pôle Événements séparé à ANBU.

| # | Date | Auteur | Localisation | Situation terrain précise | Responsable / sujet attendu | Relation / comportement attendu | Cycle prévu |
|---:|---|---|---|---|---|---|---|
| 1 | 30/08/2025 10:30 | Inoichi Yamanaka | Supports Ishiraku / réseaux sociaux | Le carrousel épinglé présente encore un plat retiré de la carte et plusieurs commentaires demandent s’il est toujours disponible. | Communication → Contenu / Social | Nouveau | Publication corrigée |
| 2 | 18/10/2025 14:40 | Tobirama Senju | Profil social ANBU | Le lien principal du profil renvoie vers une ancienne page de réservation qui redirige mal sur mobile. | Communication → Social / Site internet | Nouveau | Corrigé |
| 3 | 24/11/2025 09:50 | Shizune Kato | Newsletter / CRM | Le lien de désinscription du dernier envoi renvoie une page d’erreur ; problème reproduit depuis deux adresses de test. | Communication → CRM | Nouveau, enjeu conformité | Correction prioritaire |
| 4 | 17/12/2025 11:15 | Mozuku Tanzaku | Site + réseaux Yakinuku | Les horaires de fermeture affichés pour la période des fêtes diffèrent entre le site et la publication sociale programmée. | Communication → Site / Social | Nouveau | Harmonisé avant publication |
| 5 | 12/02/2026 16:00 | Ibiki Morino | Support événement Coworking | L’affiche PDF indique une ouverture à 18h30 alors que la page web et le brief interne indiquent 19h. | Communication → Contenu / événement | Nouveau | Fichier remplacé |
| 6 | 20/03/2026 10:20 | Shizune Kato | CRM Coworking | L’email automatique de bienvenue mentionne encore l’ancien horaire d’accès du week-end ; deux nouveaux membres l’ont reçu cette semaine. | Communication → CRM / Contenu | Nouveau | Template corrigé |
| 7 | 09/05/2026 13:30 | Inoichi Yamanaka | Hall ANBU / flyer | QR code d’un flyer encore en circulation ouvre une offre archivée au lieu de la page actuelle. | Communication → Image / supports / Site | Nouveau | Supports retirés |
| 8 | 18/06/2026 09:10 | Tobirama Senju | E-réputation | Les alertes de nouveaux avis n’arrivent plus dans la boîte partagée depuis plusieurs jours ; plusieurs réponses ont pris plus d’une semaine. | Communication → E-réputation | Nouveau | Notification rétablie |
| 9 | 22/07/2026 15:45 | Ibiki Morino | Formulaire newsletter site | Après une mise à jour, la case d’inscription marketing apparaît déjà cochée à l’ouverture du formulaire au lieu de demander une action explicite. | Communication → CRM / Site | Nouveau, contrôle conformité | Corrigé rapidement |
| 10 | 26/08/2026 11:05 | Mozuku Tanzaku | Site hôtel mobile | Le bouton principal « Réserver » sur la page hôtel retourne une page introuvable sur mobile alors que le lien desktop fonctionne. | Communication → Site internet | Nouveau | **Ouvert au cut-off**, correction prévue début septembre |

### Résultat attendu Communication

- 10 observations → environ 10 Signals ;
- #3 et #9 peuvent partager un motif CRM/conformité sans être la même occurrence ;
- #2, #7 et #10 peuvent alimenter une famille « liens / parcours web cassés » sans fusion automatique ;
- les supports concernant Ishiraku, Yakinuku, Hôtel ou Coworking restent des observations du pôle Communication lorsque l’auteur est Communication ;
- #10 reste ouvert au cut-off.

**Ordre de grandeur attendu : ~10 Signals.**

---

# 9. Résultat ANBU attendu à l’échelle du dataset

| Pôle d’origine | Observations | Signals attendus, ordre de grandeur |
|---|---:|---:|
| Hôtel | 35 | ~30 |
| Ishiraku Ramen | 24 | ~21 |
| Yakinuku Grill | 25 | ~22 |
| Coworking | 24 | ~22 |
| Maintenance | 17 | ~16 |
| Communication | 10 | ~10 |
| **ANBU** | **135** | **~121** |

Ces chiffres de Signals sont des **ordres de grandeur de validation**, pas une consigne pour forcer le résultat.

La priorité est de préserver les comportements attendus :

1. quelques observations clairement agrégées à un Signal encore actif ;
2. des occurrences séparées dans le temps qui créent un nouveau Signal mais retrouvent un motif connu ;
3. plusieurs motifs techniques transversaux visibles depuis différents pôles d’origine ;
4. des problèmes opérationnels qui restent dans le pôle métier concerné ;
5. des responsabilités Communication et Maintenance qui émergent naturellement depuis d’autres pôles ;
6. quelques Signals/plans encore actifs au 29/08/2026 avec échéances futures, sans événements futurs.

---

# 10. Références métier utilisées pour concevoir les scénarios

Les scénarios ont été construits à partir du contexte ANBU en base et de références publiques, principalement officielles :

- **INRS — Hôtellerie : les risques du métier** : manutention, chutes, produits d’entretien, contraintes physiques et organisationnelles.
- **INRS — Restauration traditionnelle : les risques du métier / ED 880 / ED 6410** : sols glissants, circulation et stockage encombrés, plonge, coupures, manutention, pression du service.
- **Ministère de l’Agriculture — Sécurité sanitaire des aliments : chaîne du froid** : maintien des températures de conservation et maîtrise des denrées périssables.
- **INRS — Travail de bureau : agir / open spaces** : nuisances de conversations, imprimantes, circulation, ventilation et concentration.
- **INRS — Organisation de la maintenance / Utilisation des machines / Consignations et déconsignations** : détection d’anomalies, maintenance préventive, traçabilité, interventions sur équipements et maîtrise des énergies.
- **CNIL — Prospection commerciale par courrier électronique / consentement** : information, consentement ou opposition, désinscription simple, absence de case pré-cochée en B2C.

Ces références servent uniquement à assurer le réalisme des situations. Elles ne remplacent pas les sujets catalogue et la configuration runtime de Spore, qui restent la source de vérité pour le routing.

---

# 11. Checklist avant génération

Avant que Cursor transforme cette matrice en corpus d’observations, vérifier :

- [ ] les 135 lignes sont conservées ;
- [ ] aucune date d’observation > 29/08/2026 ;
- [ ] les auteurs correspondent aux memberships actifs ANBU ;
- [ ] les localisations sont injectées dans `location_text` ;
- [ ] aucun `OperationalUnit` n’est inventé ;
- [ ] le texte naturel ne contient pas de métadonnées techniques du scénario ;
- [ ] les relations « même Signal » utilisent une clé d’agrégation compatible et restent actives jusqu’à la deuxième observation ;
- [ ] les relations « même motif, nouveau Signal » interviennent après clôture du Signal précédent ;
- [ ] les sujets/pôles attendus sont résolus contre la DB active ;
- [ ] les incidents techniques des pôles métier peuvent router vers Maintenance ;
- [ ] les problèmes web/contenu peuvent router vers Communication ;
- [ ] les motifs et assignments sont produits par le vrai pipeline, pas seedés directement ;
- [ ] le corpus reste déterministe via le provider scripté ;
- [ ] `AnalyticsHistoryCoverage.reliable_from` sera recalé au début de la couverture historique complète après replay, sans baseline SQL.
