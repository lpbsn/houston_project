# SPORE — Feed contracts & pagination

Version 1.2 — 27 septembre 2026 — revue de cohérence, cas limites et séparation des arbitrages résiduels

Statut : décisions produit validées. Implémentation Lots 0–7 et hardening final PR1–PR5D clos le 29 septembre 2026. Ce document reste la référence produit ; le code et les tests décrivent le comportement livré. Les réécritures SQL mesurées en PR5 n’ont pas été retenues.

## 1. Objectif et autorité du document

Construire des feeds rapides, compréhensibles et maintenables pour le terrain mobile et le back-office desktop/mobile. Favoriser le travail vivant sans perdre les priorités métier ni déplacer brutalement la lecture.

Ce document fixe la cible produit. Le code et les tests décrivent l’existant. Cursor doit vérifier les hypothèses techniques sur la branche réellement utilisée et signaler tout conflit ; il ne doit ni inventer une nouvelle règle produit ni conserver une mécanique legacy au seul motif qu’elle existe.

Les sections « À instruire » ne sont pas des décisions validées. Leurs options doivent être proposées dans le plan puis arbitrées avant implémentation si elles modifient le comportement utilisateur.

### Contexte

- SPORE : application Capacitor iOS/Android et version desktop web ; pas une PWA.
- Mobile web et Capacitor partagent la même UI mobile et les mêmes composants.
- Desktop et mobile servent des usages terrain et de supervision. Les permissions dépendent des rôles et du périmètre, jamais de la taille de l’écran.
- Django/DRF/PostgreSQL, Celery, Channels ; React/TypeScript/TanStack Query ; contrats OpenAPI générés.
- Pas encore d’utilisateurs réels en production : refonte coordonnée autorisée, sans double API ou compatibilité hypothétique. Préserver les données de démonstration et l’intégrité métier. Reconstituer des builds Capacitor alignés avant recette.
- UI déjà refondue : tous les écrans desktop ; mobile /reporting, feed Signals, détail Signals, feed Exécution. Préserver cette direction visuelle, les cartes et les lignes ; adapter les contrôles et regroupements nécessaires au présent contrat.
- Affichage, périodes et regroupements : Europe/Paris, y compris Cross, avec changements saisonniers d’heure. Aucune architecture multi-fuseaux supplémentaire dans ce chantier.

## 2. Décisions remplacées et exclusions

- Abandon définitif de la rétention opérationnelle Exécution de 7 jours pour les terminés et de 24 heures pour les annulés : sortie immédiate.
- Abandon de la cible à six sections indépendamment paginées pour Exécution : une liste filtrée, avec séparateurs visuels non repliables dans Tout.
- Chargement automatique progressif validé ; le bouton « Afficher plus » n’est plus le parcours nominal.
- Signals : aucune répétition carrousel/liste. La proposition de conserver un signal épinglé dans sa liste est abandonnée.
- Pas de moteur universel de feed, de refonte générale de toute l’UI, de remplacement de stack ou de synchronisation hors ligne complète.
- Aucune nouvelle clôture automatique métier n’est créée par ce chantier. On trace les transitions existantes et on organise leur consultation.
- Ne pas confondre données historiques des éléments actuellement clos et journal exhaustif des transitions.
- « Date avancée par un événement accepté » désigne une transition métier réussie. Un refus métier de validation peut lui-même être un événement accepté ; il ne doit pas être confondu avec une requête HTTP rejetée.

## 3. Périmètre commun et architecture attendue

### Responsabilités

| Couche | Responsabilité |
|---|---|
| Services métier backend | Transitions, activité opérationnelle, épingles, intégrité et effets après commit |
| Selectors/lectures backend | RBAC, périmètre, filtres, appartenance aux collections, ordre, pagination et compteurs |
| Serializer/OpenAPI/types générés | Contrat de données réellement échangé |
| TanStack Query | Données chargées, continuations, mutations, réconciliation et fraîcheur |
| React | Rendu, navigation et état temporaire de lecture |

Partager les accès API, query keys, règles de cache et mutations entre mobile/desktop pour un même feed. Garder des rendus carte/ligne distincts si utiles. Ne mutualiser entre Signals et Exécution qu’une responsabilité effectivement identique, avec consommateurs identifiés.

Les filtres métier et exclusions d’épingles s’appliquent côté serveur avant LIMIT/pagination. Pas de récupération non autorisée masquée ensuite par l’UI. Les hints de permissions ne remplacent pas les contrôles backend.

Préserver les règles personal/general et établissement/Cross existantes, sauf décision métier explicite. General n’est pas présumé sur-ensemble de personal. Les nouvelles sélections de statut s’ajoutent à ces dimensions, elles ne les remplacent pas.

### Pagination et metadata

- Ordre déterministe avec identifiant unique comme dernier tie-breaker.
- Correspondance exacte entre ordre SQL et prédicat de continuation ; expliciter directions et valeurs nulles.
- Curseurs opaques pour les clients ; valider leur contexte (collection, filtres, périmètre, vue). Format/version et stratégie de rejet à proposer.
- has_more et next_cursor ne sont jamais déduits d’un total affiché. Au terme du parcours : has_more=false et aucun curseur de suite utilisable. Une réponse vide ne termine pas arbitrairement la collection si le serveur annonce encore une suite : le contrat doit empêcher une boucle sans progression et expliciter ce cas sous mutations.
- Counts calculés sur le périmètre autorisé complet correspondant à leur contrat, pas sur les cartes chargées.
- Les metadata ne doivent pas être recalculées/retransférées par habitude à chaque continuation. Définir leur fraîcheur et leur remplacement dans le cache.
- Un ancien count à zéro ne doit pas masquer des items autorisés effectivement reçus.
- À arbitrer — produit : les counts des filtres alternatifs restent-ils visibles et calculés indépendamment de la sélection de statut ? Recommandation non encore validée : appliquer périmètre, personal/general et autres filtres, mais pas le statut sélectionné pour calculer ces alternatives. Le compteur de la zone épinglée, lui, correspond toujours à son contenu filtré. Ne pas présenter cette recommandation comme une décision acquise.
- Aucun snapshot immuable entre requêtes n’est promis : les clés métier peuvent changer. Déduplication et réconciliation n’autorisent pas à prétendre que les déplacements ne créent jamais d’omissions temporaires.

### Partitions, compteurs et listes vides

Pour un même périmètre autorisé et les mêmes filtres effectifs, noter P les éléments épinglés éligibles et L les non épinglés éligibles. Ils forment deux collections disjointes ; la page de L et la page/aperçu de P sont indépendants.

- Exécution : le total métier est |P| + |L|. Les compteurs des trois catégories incluent leurs éléments de P. Le compteur Épinglés est un sous-total : ne pas l’ajouter une seconde fois aux totaux métier.
- Signals : les compteurs de statut décrivent uniquement L. Le total métier Tout, s’il est affiché, est |P| + |L|. Le total de la liste seule est |L|, pas le total Tout.
- Ces égalités décrivent un état logique cohérent. Sous concurrence, ne pas promettre que plusieurs réponses HTTP prises à des instants différents satisfont toujours immédiatement l’égalité ; réconcilier sans afficher de nombres fabriqués.
- Liste vide avec P non vide : ne pas afficher « aucune exécution/observation » pour tout le feed. Montrer les épingles et un état local adapté pour L.
- Signaux Intéressants non épinglés=0 avec des intéressants épinglés : le filtre reste utilisable ; un badge à zéro n’autorise pas à le désactiver. Le carrousel porte son propre compteur.
- Si P ou L échoue, ne pas considérer la collection échouée comme vide et ne pas rapatrier ses éléments dans l’autre collection. Préserver l’exclusion serveur et proposer une reprise locale.
- Le repli Cross Exécution est spécifique à Mes épingles. Les catégories de la liste principale restent non repliables.

## 4. Feed Exécution

### 4.1 Éligibilité et filtres

| État | Surface |
|---|---|
| pending_validation | Feed opérationnel, À valider |
| in_progress avec échéance dépassée | Feed opérationnel, En retard |
| in_progress sans retard, avec ou sans échéance | Feed opérationnel, En cours |
| scheduled | À venir, hors curseur opérationnel |
| done | Historique immédiatement |
| canceled | Historique immédiatement |
| Réactivation | Retour dans le feed suivant le nouvel état et les permissions |

Sélection exclusive : **Tout · À valider · En retard · En cours**. Tout est la valeur initiale. À valider n’appartient pas aussi à En retard, même lorsque son échéance est dépassée. Respecter les règles existantes de mise à disposition/visibilité.

Dans Tout : une pagination globale, des séparateurs visuels non repliables quand les items d’une catégorie sont effectivement chargés. Pas de section vide générée uniquement par un count positif. Le filtre permet d’accéder directement à une catégorie, sans parcourir les pages des précédentes.

### 4.2 Classement

Ordre des catégories : **À valider → En retard → En cours datées → En cours sans échéance**.

| Catégorie | Ordre principal |
|---|---|
| À valider | Demande de validation la plus ancienne d’abord |
| En retard | Échéance la plus ancienne d’abord |
| En cours datées | Échéance la plus proche d’abord |
| Sans échéance | Dernière activité opérationnelle décroissante, puis création décroissante |

Ajouter un tie-breaker unique ; compléter les égalités des tris datés dans le plan. Ne pas réordonner les catégories datées sur chaque commentaire. La date de demande de validation doit correspondre au cycle courant, pas à une ancienne demande rejetée/réouverte.

« Favoriser le travail vivant » s’applique au tri des sans échéance ; il ne remplace pas les priorités ci-dessus. Les éléments silencieux peuvent descendre : le feed n’est pas une détection automatique de l’oubli.

### 4.3 Mes épingles

- Épingles personnelles par utilisateur/membership et établissement ; ne jamais changer le tri de tous les utilisateurs.
- Zone Mes épingles en tête, trois maximum par utilisateur et établissement.
- Éligibilité limitée au travail restant visible. Respect des permissions, personal/general et du filtre actif : une épingle En cours n’apparaît pas sous À valider.
- Ordre stable : première épinglée en premier. Activité ultérieure sans effet sur cet ordre.
- Pas de consommation du budget de page de la liste ; pas de répétition entre zone épinglée et liste.
- **Counts Exécution incluent les épinglées** : épingler ne diminue pas la quantité de travail d’une catégorie.
- Quatrième tentative : proposer le retrait d’une épingle existante, sans remplacement silencieux. Vérifier la limite côté serveur sous concurrence.
- Terminaison/annulation : retirer les épingles de tous les membres concernés par cette exécution, pas uniquement celles de l’auteur de la transition ; une réactivation ne les restaure pas.
- Les plafonds s’appliquent à l’ensemble de la sélection épinglée dans l’établissement, pas séparément par filtre, par appareil ou par vue. Changer de filtre ne libère pas de places. Les droits de remplacement restent vérifiés au moment de l’action.
- Cross : aperçu initial de trois cartes dans une zone Mes épingles extensible sur place ; commande « Afficher les N autres épingles » si nécessaire. Pas de page séparée Voir toutes. Après ouverture, chargement progressif et borné. Établissement identifié sur chaque carte.
- Toutes les épinglées éligibles au périmètre, à la vue et aux filtres sont exclues de la liste principale, même si la zone est réduite ou si elles ne sont pas encore chargées. Déplier/replier ne change pas cette appartenance. Le compteur de zone expose le total correspondant ; les compteurs métier incluent ces épinglées.
- Ordre Cross : date d’épinglage croissante, identifiant unique comme départage. Une nouvelle épingle ne remplace pas les trois premières ; retour visuel après épinglage local confirmé et possibilité d’ouvrir la zone. La limite reste trois par utilisateur et établissement, sans plafond global Cross supplémentaire.

### 4.4 À venir et calendrier

Conserver les accès et contrats distincts. Le feed principal utilise le count et l’information utile sur la prochaine occurrence ; ne pas lui transférer 50 objets complets pour ce résumé. Conserver la sémantique du calendrier existant, sauf impacts directement nécessaires du contrat. Pas de refonte calendrier dans ce chantier.

## 5. Feed Signals / Observations

### 5.1 Éligibilité et présentation

- Feed : open, in_progress, interesting.
- resolved et canceled : sortie immédiate vers l’Historique, sans suppression.
- Sélection exclusive : **Tout · Ouverts · En cours · Intéressants**.
- Conserver l’UI mobile/desktop actuelle et sa direction visuelle ; intégrer les contrôles validés sans refonte esthétique supplémentaire.
- Conserver les filtres métier pertinents existants : pôles, sujets, besoin de qualification, ainsi que leurs contrôles RBAC.
- Tout : ouverts → en cours → intéressants. Dans chaque catégorie : activité opérationnelle décroissante, puis critères de départage déterministes.
- Pagination globale de la liste non épinglée sur la sélection active : première page de 25 signaux au total, pas 25 par statut. Une continuation poursuit ouverts → en cours → intéressants dans Tout ; un filtre accède directement à sa catégorie. Le carrousel possède son chargement indépendant.
- Compromis validé : dans Tout, tous les ouverts précèdent les en cours, puis les intéressants, même si plusieurs pages sont nécessaires. Pas de mélange artificiel des catégories. Les séparateurs visuels éventuels ne sont pas repliables. Préserver cartes, lignes et styles actuels.
- Cette décision remplace la pagination Signals par statut existante ; elle ne prescrit pas un moteur technique commun avec Exécution.

### 5.2 Carrousel collectif d’épinglés

| Règle | Décision |
|---|---|
| Portée | Collectif, par établissement |
| Droits | Permissions backend actuelles à vérifier ; aucune extension implicite |
| Statuts éligibles | Ouvert et intéressant uniquement |
| Ouvert ↔ intéressant | Épingle conservée |
| Passage en cours, résolu ou annulé | Épingle retirée atomiquement avec la transition |
| Retour à un état éligible | Pas de restauration automatique |
| Limite | Cinq par établissement, contrôlée côté serveur sous concurrence |
| Sixième tentative | Choix explicite de l’épingle à retirer si autorisé ; remplacement cohérent et atomique |
| Ordre | Date d’épinglage décroissante, identifiant comme départage |
| Épingler un signal déjà épinglé | Aucun changement de date/position |
| Commentaire/agrégation | Ne change pas l’ordre du carrousel |
| Expiration | Aucune durée automatique ; désépinglage ou transition inéligible |
| Gestion | Pouvoir identifier qui a épinglé et quand, sans surcharger les cartes |

Un signal épinglé apparaît uniquement dans le carrousel, pas dans la liste. L’épingle reste un groupe de présentation, pas un nouveau statut métier.

**Counts Signals :** les épinglés sont exclus des compteurs Ouverts/En cours/Intéressants et comptés séparément dans Épinglés. Le total Tout, s’il existe, compte chaque signal une seule fois.

Exemple : intéressant épinglé → +1 Épinglés et +0 Intéressants. Désépingler → −1 Épinglés, +1 Intéressants. Passer en cours → −1 Épinglés, +1 En cours. Aucun signal en cours ne peut rester épinglé. Les plafonds Signals s’appliquent à l’établissement entier, indépendamment des filtres, de la vue ou des droits de lecture plus restreints d’un acteur. Un utilisateur ne doit pas recevoir des informations sur des épingles non autorisées pour pouvoir gérer le plafond ; l’API refuse l’ajout si aucun remplacement autorisé n’est possible.

Le carrousel respecte tous les filtres : sous Intéressants, seuls les intéressants épinglés correspondants sont visibles ; sous En cours, le carrousel est absent. Zone masquée si vide.

Interaction : balayage manuel mobile sans autoplay ; commandes précédent/suivant accessibles au clavier desktop ; position si plusieurs cartes. Préserver les composants et la DA actuelle autant que compatible.

Cross : collection chargée progressivement, date d’épinglage décroissante, établissement clairement identifié. Cinq par établissement, aucune limite globale cachant définitivement certaines épingles. Pas de récupération intégrale en arrière-plan.

## 6. Dernière activité opérationnelle

### 6.1 Définition réutilisable

Date du dernier événement métier significatif devenu effectif sur l’objet. Distincte conceptuellement de updated_at et des dates de cycle de vie. Vérifier tous les writers de last_activity_at avant de décider de réutiliser ce champ ou d’en introduire un autre. Pas de nouveau champ sans justification.

Invariants :

1. Initialisée à la création.
2. Mise à jour par les services backend lors d’événements acceptés, dans la transaction du changement métier.
3. Ne recule jamais sous concurrence.
4. Requêtes rejetées, retries sans nouvel effet et doublons ne l’avancent pas. Un refus de validation enregistré comme transition métier réussie reste à classifier selon les événements du domaine.
5. Une consultation, notification, épingle ou sauvegarde technique ne constitue pas une activité.
6. Modification/suppression d’un ancien commentaire ne remonte pas artificiellement l’objet.
7. Jamais reconstruite à partir des seuls événements chargés côté frontend.
8. Utilisable pour le tri, l’affichage de fraîcheur et une analyse future d’inactivité ; ne mesure pas l’avancement et ne remplace aucune échéance.

### 6.2 Événements Exécution

| Événement | Avance la date |
|---|---|
| Création | Initialisation |
| Démarrage ou réactivation | Oui |
| Tâche accomplie, ignorée ou rouverte | Oui |
| Demande de validation, validation, annulation | Oui |
| Changement effectif d’échéance ou d’affectation | Oui |
| Nouveau commentaire humain directement lié | Oui |
| Retouche titre/description | Non |
| Épinglage, consultation, notification, traitement sans effet métier | Non |

### 6.3 Événements Signals

| Événement | Avance la date |
|---|---|
| Création | Initialisation |
| Nouvelle observation agrégée | Oui |
| Nouveau commentaire humain directement lié | Oui |
| Changement effectif de statut | Oui |
| Création d’une exécution liée | Oui |
| Changement effectif de qualification ou routage | Oui |
| Retouche titre/résumé | Non |
| Épinglage/désépinglage | Non ; date d’épinglage distincte |
| Consultation, notification, traitement sans changement | Non |

Agrégation différée : utiliser la date d’effet serveur de l’agrégation pour l’activité, conserver la date d’origine de l’observation. Une répétition technique n’est pas une nouvelle activité.

L’activité d’une exécution liée ne fait pas automatiquement remonter le signal. Une véritable transition du signal induite par cette exécution avance sa date ; si elle le résout, il sort du feed.

À instruire : exhaustivité des transitions existantes non nommées ici (ex. rejet de validation), chemins automatiques et champs temporels disponibles. Proposer leur classification sans l’inventer silencieusement.

## 7. Chargement, actualisation et navigation

### 7.1 Chargement continu

- Listes feeds et Historique : première page de 25, maximum accepté par l’API 50.
- À l’approche de la fin, charger automatiquement la page suivante ; une seule continuation en vol par liste.
- Aucun téléchargement intégral en arrière-plan. Borner le préchargement ; empêcher une boucle automatique qui vide tout le dataset.
- Épinglés : budgets distincts de ceux de la liste, conformément aux limites propres à chaque feed.
- Erreur de continuation : conserver les cartes et proposer Réessayer. Commande accessible pour demander la suite lorsque nécessaire.
- Fin atteinte : indication claire.
- Les répétitions d’identifiant dans une même collection doivent être réconciliées, jamais rendues comme deux cartes. La stratégie doit préciser quelle version gagne.

### 7.2 Actualisation volontaire

- Mobile web/Capacitor : tirer pour actualiser uniquement en haut du conteneur de feed, indicateur de chargement.
- Desktop : bouton clavier-accessible « Actualiser le feed ».
- « Mises à jour disponibles » cliquable, permettant aussi l’actualisation depuis une lecture profonde.
- Actualiser : données, compteurs, épingles et classement ; retour au début de la liste ; conserver filtre et périmètre ; abandonner les anciennes continuations.
- Défiler prolonge le parcours existant ; actualiser reconstruit ce parcours.
- À instruire : engagement du reset en cas d’échec réseau. Conserver les données disponibles, sans les faire passer pour une actualisation réussie.

### 7.3 Actions et changements externes

- Action locale confirmée : réconcilier la carte ou la retirer, retour visuel bref, préserver la position autant que possible ; pas de retour systématique en haut.
- Épinglage/désépinglage local confirmé : déplacer entre collections et réconcilier les counts propres au domaine.
- Échec : annuler seulement les effets optimistes de l’action concernée ; ne pas écraser une mutation concurrente réussie.
- Changements externes : actualiser le contenu disponible, différer les reclassements pendant une lecture défilée. En haut sans interaction en cours, reclassement automatique possible.
- Terminal confirmé ou accès révoqué : retirer les éléments concernés, même si le reclassement général est différé. Une carte dont le nouveau statut, l’affectation ou le routage ne satisfait plus le filtre/périmètre actif ne doit pas être maintenue comme si elle y appartenait encore. Préserver l’ancre voisine. Le classement différé concerne les objets toujours éligibles.
- Une épingle externe confirmée ne doit pas créer de double affichage : réconcilier l’appartenance P/L tout en préservant la position de lecture. Si le contenu requis n’est pas disponible, invalider de façon ciblée au lieu de fabriquer une carte partielle.
- Ne pas déplacer une cible sous le doigt. Ne pas ajouter de mutation optimiste complexe nécessitant une copie du moteur métier serveur.
- À instruire : continuation alors que des changements d’ordre attendent. Choisir une règle explicite (continuer avec limites annoncées ou exiger une actualisation), sans mélange silencieux de générations incohérentes.

### 7.4 Retour et reprise

- Retour du détail : retrouver filtres, personal/general, état utile et ancre de lecture, avec données réconciliées. Si l’objet a quitté la liste, reprendre près d’un voisin.
- Reprise réseau/application : garder l’affichage disponible, indiquer l’actualisation et revérifier les données visibles en priorité. Le cache ne confirme jamais une nouvelle action métier.
- Réutiliser et vérifier les mécanismes de reconnexion et reprise native existants avant toute réécriture.
- Filtres mémorisés pendant la session, séparément pour chaque établissement et Cross ; première visite sur Tout. Pas de synchronisation du scroll/filtre temporaire entre appareils.
- Annuler/ignorer les réponses d’un ancien contexte après changement de scope. Purge à la déconnexion/révocation suivant les règles du repo.
- À instruire : plafond de pages/objets en mémoire, éviction et reconstruction compatibles avec le retour au détail. Ne pas choisir maxPages arbitrairement en cassant le scroll.

### 7.5 Changements dus au temps, sans événement utilisateur

Une échéance peut être dépassée pendant que la page reste ouverte. À instruire techniquement : référence temporelle autoritative, classement is_overdue, badge/compteur et curseur doivent rester cohérents. Prévoir un mécanisme borné de revalidation au franchissement pertinent ou à la reprise ; ne pas dépendre exclusivement d’un événement WebSocket métier qui peut ne jamais être émis. Pas de reclassement arbitraire sur chaque rendu ou chaque horloge de carte. La frontière exacte à égalité end_at/référence doit être écrite et testée dans le plan.

### 7.6 Erreurs et fraîcheur

Une erreur du carrousel ne bloque pas la liste ; une continuation échouée ne vide pas les données. Distinguer vide, chargement, erreur et résultat périmé. Une erreur d’autorisation/révocation retire les données concernées. Une rafale realtime doit être regroupée plutôt que provoquer un refetch complet par événement. Les événements manqués nécessitent une réconciliation à la reconnexion.

## 8. Historique dans /general

- Entrée commune Historique, choix Observations / Exécutions ; pas de nouvelle entrée principale de navigation.
- Périmètre établissement ou Cross conservé depuis le contexte et explicitement affiché ; RBAC backend conservé. Si aucun contexte n’est défini, comportement à préciser dans le plan.
- Observations : résolues et annulées. Exécutions : terminées/validées et annulées.
- Valeur initiale : 30 derniers jours, tous statuts terminaux.
- Périodes : 7, 30, 90 jours, personnalisée, toutes les dates ; sélection de statut. Définir précisément les bornes calendaires et leur traduction en timestamps Europe/Paris dans le plan.
- Ordre par transition terminale décroissante, départage unique.
- Groupes quotidiens avec les mêmes en-têtes visuels que /upcoming (« LUN. 28 SEPT. »), mais basés sur la transition terminale et non sur start_at.
- Année affichée si nécessaire pour éviter l’ambiguïté. Un jour qui traverse deux pages ne crée pas deux groupes distincts.
- Même fuseau Europe/Paris pour tous, Cross compris. Gestion correcte des journées de changement d’heure.
- Historique consultatif : ouvrir le détail ; actions éventuelles depuis le détail avec contrôles existants. Pas d’épinglage terminal ni de nouvelles actions rapides.
- Réactivation : l’objet quitte l’Historique des éléments clos, rejoint son feed ; conserver les événements de traçabilité antérieurs. Ne pas inventer une capacité de réactivation absente du métier.

### Dates sources

| Objet terminal | Date de classement/filtre |
|---|---|
| Signal résolu | Résolution |
| Signal annulé | Annulation |
| Exécution terminée sans validation | marked_done_at ou champ métier équivalent vérifié |
| Exécution validée | validated_at |
| Exécution annulée | canceled_at |

Un commentaire ultérieur ne change pas ce classement. Dates terminales manquantes : proposer une stratégie fondée sur les événements fiables ; ne pas substituer silencieusement updated_at.

### Accès au détail des éléments clos

L’éligibilité au feed opérationnel ne doit pas devenir le contrôle d’accès au détail. Après exclusion des terminaux, les liens directs et les détails ouverts depuis l’Historique doivent continuer à fonctionner avec le RBAC autorisé. Vérifier et découpler les selectors de détail qui réutilisent actuellement un queryset de feed. Ne pas modifier globalement un ensemble de statuts partagé sans suivre ses consommateurs (notifications, détails, calendrier, À venir, analyses).

### Origine de terminaison

Conserver pour les transitions terminales : date, origine manuelle/automatique, acteur lorsqu’il existe et contexte disponible. Auditer les champs/events existants (notamment cancel_origin et événements de cycle de vie Exécution), puis compléter si nécessaire. Ne pas créer un second journal concurrent sans besoin.

Un acteur absent ne prouve pas une origine automatique. Anciennes données non démontrables : origine inconnue, jamais inventée. Préserver la traçabilité des cycles successifs après réactivation. Cette exigence ne crée aucun nouveau mécanisme de clôture automatique. L’origine doit décrire le chemin d’exécution réel de la transition, pas uniquement la présence d’un humain dans la chaîne causale : une résolution automatique induite par une validation humaine exige de distinguer origine et acteur initiateur. À arbitrer dans la matrice des transitions, sans déduction silencieuse ni backfill fictif.

## 9. Existant audité : points de départ, pas obligations de conception

Référence lue : main, commit 09ff9ac1eb69244025f462f6ede6d27c4e625e1e. Cursor doit relever branche, commit et working tree réels au début de sa revue.

| Zone | Points d’entrée à vérifier |
|---|---|
| Signals backend | houston/signals/selectors.py, feed_cursor.py, feed_pagination.py, feed_filters.py, api/views.py, api/cross_views.py, services.py |
| Exécution backend | houston/action_plans/selectors.py, execution_feed.py, feed_cursor.py, feed_serializers.py, feed_pin_services.py, lifecycle_promotion.py, materialization.py, lifecycle_events.py |
| Signals frontend | features/signals/hooks.ts, api.ts, pages/signal-feed-page.tsx, lib/signal-feed-cache.ts, lib/signal-display.ts |
| Exécution frontend | features/action-plans/hooks.ts, api.ts, lib/action-plan-execution-feed-cache.ts ; features/execution/pages/execution-feed-page.tsx |
| Navigation/historique | pages /general, execution-upcoming-page.tsx et son regroupement quotidien, mémoires de lecture des feeds |
| Cache/realtime | lib/query-invalidation.ts ; features/realtime/components/operational-realtime-provider.tsx ; lib/apply-operational-invalidation.ts et hooks de connexion |

Chemins backend relatifs à apps/api, frontend à apps/web/src. Ces points de départ ne dispensent pas de suivre leurs consommateurs, tests et règles applicables.

### Constats à résoudre

- Le chargement mobile/desktop est déjà partagé par feed ; pas quatre implémentations à fusionner.
- Signals Cross matérialise tous les identifiants visibles avant pagination : supprimer ce coût non borné.
- Exécution mélange actuellement terminaux et actifs ; counts/aperçu planifié répétés à chaque page.
- Signals restaure manuellement la profondeur chargée ; Exécution conserve des pages infinies sans borne explicite dans le hook audité. Examiner les coûts et les courses réelles.
- Les index existants ne prouvent pas une couverture du tri. Mesurer les plans SQL.
- Le chemin de lecture Exécution effectue des vérifications et écritures potentielles de matérialisation/promotion. Définir un chemin nominal asynchrone et un éventuel rattrapage borné sans supprimer les garanties métier.

### Corrections au rapport Cursor fourni

- Des terminaux non épinglés ne passent pas devant les actifs dans le tri actuel. Ne pas reproduire ce faux scénario.
- Un rattrapage à la reconnexion est câblé via onReconnect/applyOperationalReconnectInvalidation ; des tests native existent. Vérifier couverture et scopes, ne pas déclarer ce mécanisme absent.
- as_of est interne/encodé dans le curseur Exécution, pas exposé par le serializer de réponse audité.
- Épinglage Signals actuel réservé aux ouverts : l’absence d’épingles en cours n’est pas une preuve de bug.
- Promotion Exécution utilise un verrou et une revérification d’état. Deux tentatives concurrentes ne démontrent pas une double transition.

## 10. Scénarios d’acceptation minimaux

| ID | Scénario | Résultat attendu |
|---|---|---|
| EX01 | Terminer sans validation / valider / annuler | Sortie immédiate du feed, Historique correct, pas de suppression |
| EX02 | Marquer terminé avec validation requise | Reste en travail restant dans À valider |
| EX03 | Échéance dépassée puis passage à valider | Une seule catégorie, À valider prioritaire |
| EX04 | Sélection En cours | Aucun retard ; sans échéance incluses |
| EX05 | Activité sur une sans échéance | Date avancée et tri conforme après actualisation |
| EX06 | Épingler avec filtre et scope | Trois maximum, pas de répétition, counts métier inchangés |
| EX07 | Deux épinglages concurrents au plafond | Limite respectée côté serveur, résultat explicite |
| EX08 | Cross avec plus de trois épingles correspondantes | Aperçu de trois, total explicite, ouverture sur place et suite bornée ; toutes exclues de la liste, aucun doublon |
| EX09 | Nouvelle épingle Cross, dépliage puis repliage | Ordre ancienneté stable, pas de changement d’appartenance à la liste, retour visuel et accès à la zone |
| SI01 | Résoudre/annuler un signal | Sort du feed et des épingles, rejoint l’Historique |
| SI02 | Ouvert épinglé → intéressant | Épingle conservée ; filtre respecté |
| SI03 | Signal épinglé → en cours | Épingle retirée atomiquement, count En cours augmenté |
| SI04 | Épingler/désépingler | Aucun doublon carrousel/liste, counts transférés, pagination réconciliée |
| SI05 | Sixième épingle / remplacement concurrent | Pas de dépassement ni remplacement silencieux |
| SI06 | Tout contient plus de 25 ouverts et des en cours/intéressants | 25 signaux non épinglés au total en première page ; continuation ordonnée ; accès direct par filtre |
| AC01 | Agrégation différée, puis retry | Date d’effet à la première agrégation ; retry sans nouvelle activité |
| AC02 | Tâche/commentaire sur exécution liée | Pas d’activité signal sans événement propre au signal |
| AC03 | Deux activités concurrentes | Date jamais reculée, aucune mutation métier perdue |
| PG01 | Égalités de dates et valeurs nulles | Ordre déterministe, parcours statique sans trous/doublons |
| PG02 | Changement de filtre/scope avec réponse en vol | Pas de contamination du nouveau cache |
| PG03 | Mutation/refetch/continuation concurrents | Pas d’append d’une ancienne génération incohérente ni double rendu |
| PG04 | Défilement proche de fin | Une continuation, 25 items par page nominale, fin explicite |
| PG05 | Erreur de suite/carrousel | Données conservées, retry local ; autre collection utilisable |
| UI01 | Retour du détail, carte retirée entre-temps | Contexte conservé, ancre voisine raisonnable |
| UI02 | Actualisation volontaire | Haut de liste, même filtre/scope, nouveau parcours |
| UI03 | Changement externe pendant lecture | Pas de cible déplacée sous le doigt, notification de mise à jour |
| RT01 | Suspension/reconnexion avec événements manqués | Réconciliation visible et autorisée |
| RB01 | Membership/permissions révoqués | Retrait des données concernées, counts sans fuite |
| HI01 | Jour réparti sur deux pages | Un seul groupe quotidien |
| HI02 | Changement d’heure Paris / limites de période | Inclusion correcte des transitions, aucun jour décalé |
| HI03 | Réactivation puis nouvelle terminaison | Liste fondée sur l’état actuel, cycles antérieurs tracés |
| HI04 | Origine ancienne inconnue | Aucun auteur absent converti arbitrairement en automatique |
| HI05 | Ouvrir un terminal depuis Historique ou lien direct | Détail accessible selon RBAC malgré son exclusion du feed |
| CT01 | Tout le travail correspondant est épinglé | Zone visible, liste vide locale, aucun faux vide global |
| CT02 | Intéressants=0 non épinglés mais carrousel intéressant non vide | Filtre utilisable, compteur carrousel exact, aucun doublon |
| CT03 | Plafond d’épingles atteint puis changement de filtre/appareil | Aucun contournement du plafond établissement |
| TM01 | Échéance franchie sans événement utilisateur | Classification/counts/continuation réconciliés selon la référence définie |
| MU01 | Mutation externe rend un objet incompatible avec le filtre | Retrait de cette collection, ancre préservée, pas de carte sous mauvais filtre |
| ER01 | Refresh échoue après début de reset | Données disponibles conservées, échec explicite, anciennes réponses non mélangées |
| RB02 | Plafond Signals atteint par des épingles partiellement invisibles | Pas de fuite de titres/ids/acteurs, aucun dépassement ni remplacement interdit |

Décliner les scénarios pertinents établissement/Cross et personal/general avec les rôles existants. Vérifier rendu desktop, mobile web et Capacitor, sans réécrire les mêmes tests à toutes les couches. Les assertions de permissions et de transition vivent d’abord au niveau propriétaire backend.

## 11. Mesures de performance et conditions de livraison

Mesurer avant/après sur mêmes données, rôles, requêtes et environnement. La démo Mama Shelter seule ne démontre pas la montée en charge : ajouter des données synthétiques représentatives hors production.

Profils : historique volumineux/faible actif ; beaucoup d’actifs ; beaucoup de relations par item ; Cross avec nombre d’établissements croissant ; sessions longues ; mutations simultanées et rafales d’événements.

Mesures : latence p50/p95 première page/continuation ; EXPLAIN (ANALYZE, BUFFERS) des pages et counts séparément ; nombre de requêtes et lignes/objets chargés ; octets de réponse ; travail de matérialisation séparé ; requêtes réseau après mutation selon profondeur ; mémoire et durée de rendu mobile.

Invariants de coût : aucune collecte de tous les UUID avant LIMIT, aucun historique complet en mémoire, aucun refetch de toute la profondeur par défaut sans justification, aucun fan-out de chargements non borné par événement. Un count peut dépendre du volume : ne pas promettre un coût constant sans preuve.

Les seuils chiffrés de latence/mémoire et l’éventuelle virtualisation doivent être justifiés par les mesures. Ne pas transformer chaque optimisation en ajout de cache Redis ou d’infrastructure.

Livraison : tests métier/contrat ciblés, génération OpenAPI si contrat externe modifié, adaptation de tous les consommateurs, suppression des chemins remplacés, vérification web/native et recette fonctionnelle. Suivre les commandes réelles du repo ; pas de tests backend host contournant les règles Docker/Make.

## 12. Points résiduels : produit versus technique

Les choix principaux (pagination globale Signals, trois cartes Cross extensibles, plafonds, catégories, tri principal, origine persistée, Historique) sont validés. Ne pas les rouvrir par défaut.

### 12.1 Arbitrages produit encore nécessaires

Ils doivent être exposés à l’utilisateur, avec recommandation, avant de déclarer le plan prêt à implémenter :

1. **Counts des filtres alternatifs** : appliquer ou non le statut sélectionné à leur calcul. La règle recommandée en section 3 n’est pas encore validée ; aucun compteur de chargement ne remplace un total métier.
2. **Historique** : sens calendaire exact de 7/30/90 jours (aujourd’hui inclus ou durée glissante), bornes d’une période personnalisée ; comportement à l’entrée de /general sans contexte explicite.
3. **Origine des transitions en cascade** : qualification manuelle/automatique d’une clôture induite par une action humaine sur un autre objet. Compléter aussi les événements métier existants absents des tableaux d’activité.
4. **Cross et actions** : les surfaces Cross auditées ont des comportements de lecture seule. La cible de lecture des épingles est validée, mais aucune extension des droits/actions en Cross ne l’est. Conserver les restrictions actuelles par défaut ; si le parcours proposé nécessite épinglage, remplacement ou mutation directement en Cross, soumettre ce changement explicitement.
5. **Attente de reclassement** : si la stratégie technique nécessite de bloquer la continuation jusqu’à actualisation, faire valider cette interruption du parcours. Ne pas la déduire de la seule présence du bandeau de mises à jour.

### 12.2 Choix techniques à proposer et vérifier dans le plan

- Curseurs : contexte, version, référence temporelle des retards, égalités/nulls et invalidation.
- Coordination refresh/continuation/mutations ; réponses d’anciennes générations ; engagement du reset en cas d’erreur.
- Cache borné compatible avec le retour au détail, durée de la session de mémoire UI et état des filtres dans la navigation. Pas de nouveau stockage durable de données opérationnelles sans besoin validé.
- Stratégie de metadata, fraîcheur et comptes exacts cohérents sans scans répétés inutiles.
- Réutilisation de last_activity_at, représentation des transitions et du cycle courant ; intégrité de la date et compatibilité des détails historiques.
- Anciennes données : timestamps/origines incomplets, épingles excédant les plafonds ou devenues inéligibles. Vérifier leur existence puis proposer une remise en cohérence explicite ; pas de suppression arbitraire ni données historiques inventées.
- Matérialisation/promotion : fiabilité du chemin asynchrone, instrumentation et rattrapage minimal de lecture.
- Budgets des pages d’épingles Cross, seuil de préchargement et absence de boucle automatique sur viewport insuffisamment rempli.

Ces points ne justifient pas un nouvel audit général. Les propositions doivent s’appuyer sur les propriétaires réels du code et produire un plan vérifiable.

## 13. Prompt Cursor — revue de cadrage et proposition de plan

À utiliser dans une nouvelle conversation Cursor en mode Plan, en joignant ce fichier.

> Analyse le document SPORE_Feed_contracts_pagination_cadrage_v1.md et confronte-le à l’état actuel du repo. Prépare un plan d’implémentation, sans écrire de code ni modifier les fichiers du projet. Retourne le rapport et le plan dans la conversation pour validation.
>
> Lis les AGENTS.md et règles applicables. Relève branche, commit, working tree et changements en cours. Le cadrage fixe les décisions produit ; le code et les tests décrivent l’existant. Ne considère pas les anciennes propositions abandonnées comme des exigences.
>
> Suis les flux backend → contrat API → types générés → hooks/cache → rendus mobile/desktop, et les consommateurs liés (détails, À venir, calendrier, /general, realtime). Pars des points d’entrée du document puis explore leurs dépendances réelles. Ne réaudite pas toute l’application sans lien avec ce chantier.
>
> Vérifie les contradictions factuelles listées dans le document. Pour chaque constat, cite fichiers, symboles et lignes ; distingue faits, risques et mesures non effectuées. Ne transforme pas une absence de test repérée en preuve d’un bug.
>
> Traite explicitement les deux catégories de la section 12 : décisions produit résiduelles et choix techniques. Ne présente pas une recommandation non validée comme acquise. Recommande une solution motivée par les usages et le repo. Pose uniquement les questions produit qui bloquent réellement un plan correct. N’invente ni helpers existants, ni contrats, ni événements de cycle de vie. Les détails techniques restent à ta charge, mais tu ne changes pas silencieusement les règles validées.
>
> Propose les contrats et les stratégies de pagination/réconciliation, les responsabilités propriétaires, ce qu’on conserve/remplace/supprime/factorise, puis des lots cohérents de bout en bout. Pas de moteur universel de feed, pas de compatibilité hypothétique, pas de refonte esthétique additionnelle. Explique tout nouvel état persistant ou abstraction et ses consommateurs réels.
>
> Prévois les mesures avant/après, les tests déterminants de concurrence/contrat/RBAC et la validation mobile web, Capacitor et desktop. Respecte la chaîne de génération du repo ; ne modifie pas les fichiers générés à la main. Préserve les données démo et les modifications utilisateur.
>
> Retour attendu : 1) verdict sur le cadrage et écarts ; 2) décisions techniques proposées et questions bloquantes ; 3) contrats cibles et invariants ; 4) plan par lot avec fichiers, dépendances, suppressions et critères d’acceptation ; 5) mesures/tests ; 6) limites non vérifiées. Arrête-toi avant implémentation et attends la validation du plan.

