# Spore — cadrage du chantier d’expérience desktop opérationnelle

**Statut :** cadrage produit consolidé · **Référence :** dépôt `lpbsn/houston_project`, chantier desktop PR #252–#256 · **Date :** 25 septembre 2026  
**Usage :** document de besoin et de décisions produit pour le desktop opérationnel. Les décisions validées pendant les PR 2–4 prévalent sur les formulations antérieures (onglets desktop, CTA feed, topbar détail, calendrier).

## 1. Résultat attendu

Spore dispose d’un seul frontend métier React, utilisé sur le web et dans l’application mobile Capacitor. L’expérience terrain mobile et l’expérience desktop web servent des usages différents. Le chantier rend le **desktop web** adapté au pilotage et au travail sur plusieurs établissements, tout en conservant les parcours rapides et les contrôles tactiles mobiles.

Le résultat visible doit être le suivant : un utilisateur desktop choisit **un scope** (Cross ou un établissement), retrouve **une seule navigation fonctionnelle** correspondant à ce scope, peut réduire la sidebar pour travailler dans le calendrier, et utilise des feeds, détails, formulaires et actions composés pour le desktop. Le Chat présente simultanément les conversations et la conversation ouverte. Le mobile conserve son architecture.

**Référence au produit existant :** la PR #251 a déjà réordonné la sidebar, déplacé « Configuration opérationnelle » dans Général, déplacé la déconnexion desktop vers la sidebar, resserré Général et le Profil, et mis la Bibliothèque en grille responsive. Les PR #252–#256 livrent la garde desktop web (`isDesktopWebLanding`), le scope unique, Observations, Exécution, formulaires et Chat.

## 2. Périmètre et invariants

| Surface | Décision |
|---|---|
| Web desktop (shell Terrain) | Cœur du chantier : sidebar, Chat, Observations, Exécution, plans d’action et contrôles. |
| Mobile natif et mobile web | Conserver les parcours, routes métier, navigation basse et interactions tactiles ; corriger uniquement les régressions induites par les composants partagés. |
| Web sous le seuil desktop | Conserver le shell et la navigation mobile web actuels. Ne pas traiter le `max-w-md` global comme un objectif de ce chantier ; une éventuelle révision du shell mobile web se décidera séparément. |
| Tablette | Aucun troisième système de navigation, aucun rail dédié. Les mises en page locales peuvent s’adapter à la place disponible. |
| Dashboard Analytics | Composition desktop validée : aucun réagencement de ses widgets ni changement fonctionnel. Seule l’intégration nécessaire avec la nouvelle sidebar est concernée. |
| Nouvelle observation | Conserver le formulaire focalisé et son parcours actuel ; accès depuis la **sidebar** desktop (pas depuis le feed Observations). Adapter les contrôles desktop sans ajouter de colonne décorative. |
| Général et Bibliothèque | Conserver la direction issue de la PR #251 ; uniquement intégration à la navigation et corrections locales indispensables. |
| Calendrier Exécution | Hors refonte de ce chantier : smoke fonctionnel seulement ; composition et overflow font l’objet d’un chantier séparé. |
| Platform Admin | Hors périmètre ; ni shell ni parcours Platform Admin à refondre. |
| Design system transversal | Chantier dédié ultérieur. Harmoniser seulement les composants touchés, sans lancer une refonte globale de tokens et de toutes les pages. |

Ne pas modifier les règles métier, rôles, autorisations, états des plans, isolation des établissements, contrats API ou routes publiques pour obtenir ce changement de présentation. Les droits continuent d’être déterminés par les mécanismes existants et appliqués côté backend. Le seuil de bascule desktop web reste celui du shell actuel (`lg`, environ 1024 px) : ce chantier n’invente ni seuil « tablette », ni quatrième mise en page « wide ». L’expérience desktop n’est pas « viewport ≥ 1024 » seule : c’est `web` et `lg` (`isDesktopWebLanding`). Le natif large garde le parcours mobile.

## 3. Navigation desktop : scope unique, fonctions stables

### 3.1 Structure attendue

La sidebar Terrain du **web desktop** affiche, du haut vers le bas :

1. La marque **« Spore »**.
2. Un sélecteur de scope affichant le scope courant : « Cross-établissement » ou le nom de l’établissement.
3. Une seule liste de destinations disponibles dans ce scope.
4. L’identité et le contexte utilisateur, puis l’unique commande de déconnexion desktop web dans le pied de sidebar.

Les listes complètes répétées sous chaque établissement disparaissent. Avec 1, 8 ou 30 établissements, la hauteur de navigation **ne croît pas avec le nombre d’établissements**. Les établissements sont listés dans le sélecteur, avec un mécanisme de recherche ou de filtrage utilisable quand la liste est longue. Les noms longs restent identifiables, le choix courant est explicite, et le menu se manipule au clavier.

### 3.2 Scope, destinations et droits

Dans le scope **établissement**, conserver cet ordre pour les entrées effectivement disponibles à ce membre :

- Dashboard ; Paramètres Analytics, lorsque le rôle donne accès à Analytics ;
- Nouvelle observation ; Observations ; Exécution ;
- Chat, seulement lorsque `chat_available` le permet ;
- Général.

« Configuration opérationnelle » reste dans Général pour les personnes autorisées, pas dans la sidebar. « Équipe » et « Bibliothèque » restent accessibles depuis leurs emplacements actuels.

Dans le scope **Cross**, la navigation contient **Observations, puis Exécution**, toutes deux **en lecture seule**. Ni Chat, ni Général, ni « Nouvelle observation » ne s’y affichent. Les destinations non livrées (ex. Spore Brain, Paramètres Analytics) restent non navigables tant qu’elles ne correspondent pas à un écran utilisable.

Le libellé « Cross-établissement » distingue nettement la lecture transverse d’un établissement actif. Les informations et actions d’un établissement ne doivent jamais être présentées sous le mauvais scope.

### 3.3 Comportement du changement de scope

- Le scope visible est cohérent avec la route courante et le contexte d’autorisation réel, y compris après chargement direct d’une URL, rafraîchissement et retour navigateur. Un ancien état de sidebar ne doit pas écraser le scope explicite de l’URL.
- Le passage à un autre établissement utilise le mécanisme existant de changement d’établissement et purge des données isolées par tenant. La navigation n’expose pas brièvement des données de l’établissement précédent dans le nouveau contexte.
- Après sélection, conserver la **fonction du hub courant** si elle est disponible dans le nouveau scope (par exemple Observations établissement → Observations Cross). Depuis un détail, rejoindre le hub parent de même fonction dans le nouveau scope : ne pas supposer que l’objet détaillé y est visible. Si cette fonction est indisponible, ouvrir **Observations** du nouveau scope ; c’est aussi le repli depuis Chat ou Général vers Cross. Le changement de scope ne crée jamais une URL Chat Cross ni une URL de détail transposée à un autre établissement.
- Changer de scope repart sur les filtres et la position de lecture propres au **nouveau** scope ; il ne transporte pas silencieusement les filtres ou une sélection d’objet de l’ancien. La mémoire de lecture des feeds est **conservée par scope** (établissement ou Cross) et **effacée à la déconnexion** ; un retour ultérieur sur le même scope peut retrouver cet état. L’atterrissage initial après connexion garde en revanche ses règles actuelles, distinctes du comportement du sélecteur.
- Les détails d’Observation et d’Exécution indiquent toujours le bon scope et la bonne destination active dans la sidebar. Un lien direct vers un détail reste valide et la navigation de retour mène vers le feed du même scope.
- Perte d’accès, établissement désactivé ou absence de membership actif : ne pas conserver un scope sélectionnable devenu illégitime ; laisser les gardes et états d’accès existants gérer le cas.
- Ne pas changer sans raison la logique d’atterrissage déjà distincte : Cross sur desktop web quand il est accessible, sélection d’établissement sur mobile lorsque requise.

### 3.4 Sidebar ouverte et réduite

La sidebar est rétractable **manuellement**. Ouverte, elle affiche labels et scope lisibles dans une largeur desktop raisonnable (cible indicative : environ 240–256 px au lieu des 288 px actuels). Réduite, elle libère la place horizontale (cible indicative : environ 64–72 px), conserve l’accès au sélecteur de scope, à **toutes** les destinations autorisées, au compte et à la déconnexion. Chaque icône ou commande sans libellé visible possède un nom accessible et une aide contextuelle ; l’état actif reste perceptible.

Le choix ouvert/réduit ne doit pas se réinitialiser à chaque changement de page. Dans l’état réduit, le sélecteur reste une commande ouvrant les scopes avec leurs **noms complets** ; les destinations, le compte et la déconnexion restent atteignables sans devoir redéployer la sidebar. Le calendrier Exécution reste utilisable dans une fenêtre desktop étroite, sidebar réduite comprise (smoke fonctionnel ; pas d’exigence de refonte visuelle dans ce chantier). À la frontière responsive, le web retrouve la navigation mobile prévue ; il n’y a pas de sidebar desktop comprimée dans un viewport mobile. La sidebar ne doit pas apparaître dans le runtime natif, même avec une grande largeur.

## 4. Écrans desktop à adapter

### 4.1 Observations — feed

Conserver le feed vertical, ses sections, sa chronologie, les vues Personnel / Établissement et le comportement Cross. Sur desktop, chaque observation devient une **ligne ou carte horizontale lisible** : titre et extrait dominants, puis statut, classification, lieu, auteur, date/ancienneté, établissement en Cross et indicateurs de plans selon les données déjà disponibles. Les éléments secondaires ne doivent pas tous prendre une ligne chacun comme sur mobile.

**Composition desktop attendue :** en-tête « Observations » avec les vues Personnel / Établissement là où elles existent ; sous cet en-tête, une barre de filtres ; ensuite les éléments épinglés et les sections repliables existantes, dans leur ordre métier. En Cross, afficher le contexte établissement dans chaque ligne, sans introduire des onglets Personnel / Établissement inapplicables. La ligne entière permet d’ouvrir le détail ; le menu `…` reste une commande distincte et n’ouvre pas le détail par erreur.

Les filtres fréquents et le changement de vue sont visibles dans la zone d’en-tête, avec les filtres complémentaires accessibles sans grand panneau tactile. **Il n’y a pas de bouton « Nouvelle observation » dans le feed** : la création autorisée passe par la destination sidebar du même nom ; elle n’apparaît pas en Cross. Les actions secondaires s’ouvrent dans un menu contextualisé. Le feed ne devient ni une grille de deux colonnes ni un tableau d’administration, et ne suppose pas un panneau détail permanent. Sur mobile, garder les cartes et interactions actuelles.

**Retour depuis un détail :** retrouver la vue Personnel/Établissement, les filtres, la section ouverte, la position de lecture et tout autre état utile du feed du **même scope** sans demander à l’utilisateur de refaire sa sélection. Cela vaut pour une navigation interne ; un accès direct par URL doit néanmoins fonctionner de façon autonome.

### 4.2 Observation — page détail

Le détail reste une **page complète** sur toutes les surfaces.

**Desktop web :** barre de page avec retour et actions disponibles (dont « Créer un plan » lorsque le droit et l’état l’autorisent) — **sans** obliger le titre ni le statut dans la topbar ; titre, statut et métadonnées vivent dans le corps. Zone principale (description, photos, demandes de résolution, plans liés) et zone de contexte (classification, lieu, auteur/date, qualification/routage). Lorsque la place manque, le contexte passe sous le contenu. Les **commentaires sont sous le contenu** en flux document, pas dans un onglet. Éviter les panneaux à scroll imbriqué. Pas de footer sticky mobile recyclé.

**Mobile / natif (y compris grand viewport) :** conserver les onglets « Détails / Commentaires » et les contrôles tactiles existants (footer sticky inclus).

Les actions locales de qualification ou de demande de résolution restent au contact de leur contexte. La présentation des photos tire parti de la largeur desktop. Le bouton retour et les liens vers les plans gardent leur sens métier et le scope d’origine.

### 4.3 Exécution — liste et calendrier

Conserver les vues de feed existantes, les modes **Liste / Calendrier**, leurs périodes, leurs filtres et leurs droits. **Composition desktop attendue (liste) :** en-tête « Exécution » et choix de vue existant, commutateur Liste / Calendrier, filtres ou commande de période propres au mode affiché, puis espace de travail. Dans la vue Liste, conserver éléments épinglés, sections et accès « À venir » existants ; chaque plan devient une **ligne opérationnelle dense** : nom, état, pôle, responsable/assignation, progression et échéance quand ces données sont disponibles. Les informations critiques, notamment une échéance proche ou dépassée, restent immédiatement repérables. La ligne ouvre le détail ; ses actions secondaires sont contextuelles. L’action de création permise porte un libellé et ouvre les **choix de création existants** sous une forme desktop, sans les remplacer par une création automatique de plan.

**Calendrier :** hors refonte de ce chantier. Le mode calendrier existant doit rester utilisable (smoke) avec la sidebar réduite près du seuil ; toute évolution d’overflow, de densité ou de composition calendrier est un **chantier séparé**. Le retour depuis un plan restaure **Liste ou Calendrier**, filtres, période affichée et position utile du même scope.

### 4.4 Exécution — page détail

Le détail du plan d’exécution reste une **page complète**.

**Desktop web :** barre de page avec retour et actions de transition autorisées (terminer, valider, rouvrir, annuler selon l’état et les droits), **sans** obligation de titre/état dans la topbar. Zone principale = tâches par pôle ; zone de synthèse = données réellement disponibles (responsable, échéance, progression, pôles, signal lié, description, contexte). Le signal source reste accessible. Si la largeur manque, la synthèse suit la zone principale. Les **commentaires sont sous le contenu** en flux document, pas dans un onglet. Ne pas recycler un grand pied de page sticky mobile en carte desktop.

**Mobile / natif :** conserver les onglets « Détails / Commentaires », le footer sticky et les contrôles tactiles.

Les actions sur une tâche restent au contact de cette tâche. Préserver les règles existantes sur qui peut effectuer chaque transition, ainsi que les états en cours, chargement, erreur et confirmation.

### 4.5 Création et modification des plans d’action

Adapter **tous les parcours de formulaire de plan déjà présents**, sans confondre leurs capacités :

| Parcours existant | UX desktop cible |
|---|---|
| Création depuis Exécution, depuis un signal ou depuis la Bibliothèque | En-tête identifiant l’origine ; titre, description, focus opérationnel éventuel et éditeur de tâches dans la zone principale. Pôle pilote, options, assignation et planification effectivement offertes par ce mode dans une zone complémentaire. Si le plan vient d’un signal, garder le signal source et sa classification héritée clairement visibles ; conserver tout champ verrouillé comme tel. |
| Édition d’un modèle de la Bibliothèque | Même hiérarchie pour identité et tâches, avec ses options propres. Ne pas afficher un bloc de planification d’exécution si ce mode ne le propose pas. Retour au modèle après sauvegarde selon le parcours existant. |
| Édition d’une exécution | Identité et tâches nouvelles ou traitées dans la zone principale ; propriétés et planning de cette exécution dans la zone complémentaire, en distinguant clairement les tâches déjà traitées, non éditables. Garder les contraintes de rôle et de planification existantes. |

**Composition commune desktop :** en-tête « Créer » ou « Modifier » qui nomme l’objet et son contexte, contenu éditable principal à gauche, propriétés secondaires regroupées à droite lorsque la largeur le permet. Les tâches ne deviennent pas un panneau latéral étroit. Si l’espace ne suffit pas, les blocs reviennent dans un ordre vertical lisible ; il ne faut pas inventer une étape de wizard. Les choix complexes peuvent s’ouvrir dans une modal de taille adaptée.

Ne pas créer des champs ou étapes que le parcours existant ne possède pas. En création, conserver le sens et le libellé de l’action de soumission propre au mode ; en édition, grouper « Retour/Annuler » et « Enregistrer » dans une barre d’actions desktop claire. Pas de CTA pleine largeur ni de grand footer tactile recyclé. Les erreurs restent associées aux champs concernés, les champs avancés erronés s’ouvrent comme aujourd’hui et la soumission amène vers la première erreur utile. Les règles de validation, sauvegarde et sortie de formulaire restent celles du produit ; ne pas inventer une nouvelle persistance de brouillon. Sur mobile et natif large, garder le parcours séquentiel et les commandes tactiles (y compris styles `lg:` utiles au natif large sur ces branches).

### 4.6 Chat desktop

Dans un établissement où le Chat est autorisé, afficher simultanément **liste des conversations à gauche** et **conversation sélectionnée à droite**. La colonne gauche contient recherche, création permise, lignes de conversation et états vides/erreur ; elle garde sa position de lecture lorsque l’on change de conversation. La colonne droite contient en-tête et commandes de la conversation, historique défilant et composer fixé en bas de cette zone. Les deux panneaux disposent de leur propre défilement utile, sans que le composer sorte de l’écran. Quand aucune conversation n’est sélectionnée, la seconde zone présente un état invitant à en choisir une ; ne pas ouvrir automatiquement la première conversation. L’URL d’une conversation sélectionnée demeure partageable et rechargeable. Changer de conversation ne renvoie pas à la page de liste ; les messages, le composer, les états d’envoi et les pièces jointes gardent leur fonctionnement existant.

Les actions `…` sont des menus contextualisés sur desktop ; « Infos » ouvre un panneau droit **à la demande**, qui se ferme sans perdre la conversation. « Gérer les membres » se fait dans ce panneau si son contenu tient et reste clair, sinon dans une modal ; il ne s’affiche que si `can_manage` le permet. Création de conversation : modal desktop. Il n’y a pas de troisième colonne permanente. En mobile natif et mobile web, conserver liste → conversation et les bottom sheets existantes. Cross n’acquiert pas de Chat par cette refonte.

### 4.7 Écrans explicitement conservés

**Dashboard :** conserver l’ordre, la taille relative, l’empilement aéré et les widgets validés sur desktop. Le nouveau sélecteur de scope ne doit pas déclencher une refonte de la grille Analytics.

**Nouvelle observation :** formulaire centré de largeur confortable et limitée sur desktop, avec saisie texte/audio, médias et envoi dans le parcours existant. Pas de deuxième colonne, ni d’étapes supplémentaires. Les contrôles desktop peuvent être moins tactiles si cela ne ralentit pas l’envoi. L’entrée desktop depuis la sidebar, pas depuis le feed Observations.

**Général / Profil :** garder la largeur contenue et les regroupements post-PR #251 ; « Configuration opérationnelle » reste sous Opérations pour les rôles autorisés, la déconnexion reste dans la sidebar desktop seulement. **Bibliothèque :** conserver sa grille responsive et son accès depuis Général ; seuls les formulaires d’édition de plan atteints depuis elle sont concernés par la section 4.5. **Platform Admin :** aucun changement de navigation, de layout ou de composants dans ce chantier.

## 5. Contrôles et interactions selon la surface

| Interaction | Mobile / natif | Desktop web cible |
|---|---|---|
| Action primaire de feed | Contrôle tactile actuel | Bouton compact avec libellé lorsqu’il appartient à la toolbar du feed (pas de CTA « Nouvelle observation » sur le feed Observations). |
| Actions secondaires de carte / ligne | Sheet ou contrôle tactile selon l’existant | Menu/popover ancré à l’élément. |
| Filtres | Sheet si nécessaire | Contrôles courants inline ; options longues en popover/panneau. |
| Nouvelle conversation | Bottom sheet | Modal. |
| Infos d’une conversation | Bottom sheet | Panneau contextuel ouvert à la demande. |
| Choix complexe de planning | Sheet existante | Modal adaptée au contenu. |
| Confirmation d’action sensible | Dialogue tactile existant | Dialogue clair et contextualisé. |
| Actions de détail ou formulaire | Sticky footer lorsque pertinent | Barre d’actions de page, sans CTA pleine largeur par défaut ; titre/statut du détail dans le corps, pas imposés dans la topbar. |
| Commentaires (détail Observation / Exécution) | Onglets Détails / Commentaires | Flux sous le contenu (document flow). |

Sur desktop, les boutons sont plus compacts, moins circulaires et moins « téléphone agrandi ». Le texte précise les actions importantes : « Nouvelle observation » (sidebar), « Créer un plan » ou « Nouvelle conversation » **seulement là où ces actions existent et sont permises**. Dans chaque toolbar, une action primaire visible au maximum ; les autres actions deviennent boutons secondaires explicites ou menu `…`. Les commandes de transition sensibles restent libellées, confirmées selon le flux existant et visuellement distinctes du simple retour. Les icônes seules sont réservées aux commandes compréhensibles avec nom accessible et tooltip dans la sidebar réduite. Les actions essentielles fonctionnent au clavier, restent accessibles sans survol et ont un focus visible. Préserver les capacités natives existantes (clavier, safe areas, caméra/fichiers, notifications) là où elles sont déjà utilisées.

## 6. Contrats d’expérience à préserver

- Une même personne peut voir des fonctionnalités différentes selon son établissement et son rôle. Le sélecteur, la navigation, les écrans et les liens directs reflètent toujours les permissions propres au scope courant.
- Les vues Cross restent en lecture seule où elles le sont aujourd’hui. Aucune action d’édition « cachée » simplement par CSS ne remplace les gardes existants.
- Un changement d’établissement vide correctement les données opérationnelles de l’ancien scope avant de présenter celles du nouveau ; l’outbox Chat et les autres données locales suivent leurs règles de purge actuelles. La mémoire de lecture des feeds reste **par scope** et n’est pas vidée globalement à chaque switch ; elle est effacée à la déconnexion.
- Les URLs existantes des feeds et des détails restent utilisables ; rafraîchissement, retour navigateur et liens directs ne cassent pas la sélection du scope ou l’état actif.
- Les changements visuels n’effacent ni les états chargement, vide, erreur et hors ligne, ni les commentaires, médias, plans liés, validations et confirmations déjà présents.
- Aucun réagencement du Dashboard, aucune refonte globale de Général/Bibliothèque/Platform Admin, aucune refonte calendrier et aucun nouveau mode « tablette » n’est une condition de réussite du chantier.

## 7. Scénarios d’acceptation produit

1. **Multi-établissement :** un owner de huit établissements ouvre le web desktop. Une seule liste de fonctions apparaît. Il cherche un établissement dans le sélecteur, l’ouvre, retrouve les seules fonctions autorisées (dont « Nouvelle observation » dans la sidebar, pas dans le feed), puis passe en Cross et ne voit plus Chat ni Général ni « Nouvelle observation ».
2. **Accès direct :** un lien `/e/:establishmentId/signals/:signalId` ouvre la bonne observation, marque Observations actif et affiche le bon établissement, même après rafraîchissement. Une URL Cross de détail reste en lecture seule. Sur desktop, les commentaires du détail sont sous le contenu ; sur mobile/natif, les onglets Détails / Commentaires restent.
3. **Changement de scope :** depuis Chat d’un établissement, l’utilisateur choisit Cross. Il arrive sur Observations Cross ; aucune conversation du précédent établissement ne reste visible. Depuis une observation établissement, il arrive sur Observations Cross sans conserver l’ID du détail ni les filtres de l’établissement. Un retour ultérieur sur le même établissement peut retrouver la mémoire de lecture de ce scope ; la déconnexion efface ces mémoires.
4. **Calendrier (smoke) :** en desktop web à largeur proche du seuil, l’utilisateur réduit la sidebar et consulte la vue calendrier sans blocage fonctionnel. Toute amélioration visuelle ou d’overflow est hors ce scénario de clôture.
5. **Retour aux feeds :** filtres et position dans Observations, puis mode, période et filtres dans Exécution, sont retrouvés après consultation d’un détail par navigation interne **dans le même scope**.
6. **Travail sur un plan :** sur desktop, tâches, synthèse, contexte, commentaires sous le contenu et actions du détail sont identifiables sans footer sticky recyclé. La création depuis un signal conserve le lien et la classification héritée ; l’édition d’un modèle ne montre pas la planification d’exécution ; l’édition d’une exécution distingue ses tâches traitées des tâches éditables. Sur téléphone et natif large, les parcours restent praticables comme aujourd’hui.
7. **Chat :** sur desktop, la liste reste visible lorsque l’on ouvre puis change de conversation ; le lien direct d’une conversation se recharge correctement. Sur mobile, liste et conversation restent deux vues successives.
8. **Rôles et surfaces :** un membre sans Analytics ne voit pas Dashboard/Paramètres Analytics ; un établissement sans Chat ne montre pas Chat ; un grand viewport natif conserve la navigation mobile (pas de sidebar ni de split Chat) ; Platform Admin et le Dashboard conservent leur présentation validée.

## 8. Points d’ancrage dans le dépôt

- `apps/web/src/features/auth/lib/authenticated-landing.ts` : `isDesktopWebLanding` ; atterrissages desktop et mobile distincts.
- `apps/web/src/features/navigation/lib/scoped-desktop-navigation.ts` : scope unique, destinations, Chat via `membership.chat_available`.
- `apps/web/src/components/layout/desktop-terrain-sidebar.tsx` / `terrain-shell.tsx` : sidebar et garde shell.
- `apps/web/src/app/scoped-terrain.ts` : routes `/cross/...`, `/e/:establishmentId/...` et détails.
- `apps/web/src/features/signals/pages/signal-feed-page.tsx` et `signal-detail-page.tsx` : feed (sans CTA création) et détail Observation (document flow desktop / onglets mobile).
- `apps/web/src/features/execution/pages/execution-feed-page.tsx` : liste et calendrier Exécution.
- `apps/web/src/features/action-plans/pages/action-plan-execution-detail-page.tsx`, `action-plan-create-page.tsx` et `action-plan-execution-edit-page.tsx` : détail et formulaires de plans.
- `apps/web/src/features/chat/pages/chat-page.tsx` et `chat-conversation-page.tsx` : split desktop / séquentiel mobile.
- `AGENTS.md` et `apps/web/AGENTS.md` : responsabilité métier et règles de changement du frontend.

Ces fichiers servent de **points de départ**, pas de liste exhaustive : suivre les implémentations et tests propriétaires des écrans réellement concernés.
