# Spore — Cadrage produit : vidéo de découverte

**Version :** 3.1 — 26 octobre 2026  
**Statut :** validé. Adresse publique définitive : `https://spore-os.com/discover/`.  
**Projet :** Spore / `houston_project`  
**Environnement de référence :** staging, puis promotion ciblée vers main  
**Nature :** exigences produit, expérience attendue et critères d'acceptation. **Ce document ne prescrit ni architecture, ni technologie, ni fichier à modifier.**

## 1. Pourquoi cette évolution ?

Les personnes invitées dans Spore doivent pouvoir comprendre rapidement à quoi sert le produit avant ou après avoir rejoint leur équipe. Les utilisateurs existants doivent pouvoir retrouver la même présentation à tout moment.

Le résultat recherché est **une meilleure compréhension et une meilleure activation des utilisateurs**, et non une augmentation du nombre de vues.

La V1 doit être simple à utiliser, peu coûteuse à exploiter, fiable et adaptée à la croissance de Spore. **La vidéo n'est jamais une étape obligatoire de l'inscription.**

## 2. Expérience fonctionnelle validée

### 2.1 Depuis les emails d'invitation

- Conserver le contenu essentiel et **l'action principale d'acceptation de l'invitation**, sans détour ni étape supplémentaire.
- Ajouter un accès **secondaire** à la présentation : une **miniature statique cliquable** évoquant la vidéo, accompagnée d'un libellé clair (« Découvrir Spore en 1 min 33 » ou formulation équivalente validée).
- Ce nouvel accès conduit directement à la **présentation Spore**, sans passage par une interface YouTube.
- Le lien de découverte est distinct du lien personnel d'invitation : consulter la présentation **ne doit jamais accepter, révoquer, consommer ou modifier l'invitation**.
- L'email doit rester utilisable lorsque les images ne s'affichent pas et dans sa version texte. La découverte reste facultative dans tous les cas.
- L'évolution concerne les **emails d'invitation à rejoindre Spore** réellement identifiés lors de l'audit, y compris les renvois éventuels de ces invitations. Elle ne concerne pas les autres catégories d'emails.

### 2.2 Page de découverte : contenu et direction artistique

Une **page publique pérenne** est accessible aux personnes connectées comme non connectées, depuis un lien direct, un email ou l'application Spore. Son adresse publique est `https://spore-os.com/discover/`. Elle reste stable et partageable. Le chemin `/decouvrir/` n'est pas utilisé : il n'a jamais été publié, et aucune redirection n'est nécessaire.

La page est **sobre, moderne, rapide, responsive et cohérente avec l'identité visuelle officielle de Spore**.

**Contenu visible, dans cet ordre :**

1. **Logo officiel Spore**, avec son identité de marque reconnaissable.
2. **Titre principal :** « Découvrez Spore ».
3. **Court texte explicatif :** « En 1 min 33, découvrez comment Spore aide votre équipe à partager les observations du terrain, à collaborer et à suivre les actions qui en découlent. »
4. **Vidéo complète de présentation**, intégrée visuellement dans la page, avec une image d'aperçu et une action de lecture identifiable.

**Comportement attendu :**

- L'utilisateur choisit de démarrer la vidéo ; elle **ne commence pas automatiquement avec le son**.
- L'utilisateur peut lire, mettre en pause, ajuster le son et se déplacer dans la vidéo ; le plein écran doit être possible lorsque le terminal le permet.
- Aucun affichage de l'interface YouTube, publicité vidéo imposée ou redirection vers une plateforme tierce ne doit interrompre cette expérience.
- L'interface reste facile à utiliser sur ordinateur et mobile, au clavier ou au toucher.
- **Pas de formulaire, d'inscription obligatoire ni de parcours marketing supplémentaire** sur cette page en V1. Elle présente la vidéo, pas toute une nouvelle landing page.
- Si la vidéo ne peut pas être affichée ou lue, le logo, le titre et le texte restent visibles, avec un message simple expliquant l'indisponibilité. La page ne doit pas présenter une erreur générale.
- L'accès à cette page **ne dépend d'aucune invitation** et n'exige pas de donner à la page un lien personnel d'acceptation.

L'adresse publique est décidée : `https://spore-os.com/discover/`. La composition frontend et le mécanisme de lecture ne sont pas prescrits par ce cadrage.

### 2.3 Depuis l'application Spore

- Tout utilisateur authentifié, quel que soit son rôle, doit pouvoir accéder à **« Découvrir Spore » à tout moment**.
- L'accès est disponible sur les surfaces effectivement concernées de Spore, **Web et applications mobiles natives**.
- Le point d'entrée doit être **secondaire et cohérent avec la navigation existante**, sans ajouter un nouvel onglet principal pour cette seule vidéo.
- Il ouvre **la même présentation** que depuis l'email : pas de contenu ou de vidéo dupliqué par surface.
- L'utilisateur doit pouvoir retourner à son utilisation de Spore **sans perte de session, de brouillon ou de contexte métier**.
- L'accès ne disparaît pas après l'onboarding.

L'emplacement concret du lien, son libellé final et le comportement de navigation adapté à chaque surface seront proposés par Cursor à partir de l'application réelle.

## 3. Contenu vidéo et publication

- Une vidéo source d'environ **1 min 33** a été fournie séparément (`spore-video.mov`). Elle doit être accessible à l'équipe ou à Cursor au moment de la préparation des médias ; **ne pas présumer qu'elle est déjà dans le repository**.
- La présentation intégrale doit conserver ses informations utiles, être intelligible et offrir une qualité correcte sur les appareils cibles.
- Prévoir une image d'aperçu de bonne qualité et adaptée à l'email ainsi qu'à la page.
- Vérifier avant publication que le contenu est diffusable publiquement : absence de données réelles sensibles ou secrets, droits sur les contenus audio/visuels et cohérence des fonctionnalités montrées avec les permissions réelles des différents rôles.
- La V1 conserve l'audio d'origine de la vidéo. Une transcription générée et une piste de sous-titres ne font pas partie de cette livraison.
- Une vidéo remplacée ultérieurement ne doit pas casser les liens déjà envoyés.

**Aucun format, processus de conversion, stockage ou prestataire n'est imposé par ce cadrage.** La solution retenue doit préserver une lecture fluide et permettre la navigation dans la vidéo.

## 4. Contraintes et exigences non fonctionnelles

### Sécurité et confidentialité

- Les liens et requêtes de diffusion de la présentation **ne transportent aucun token d'invitation ni donnée personnelle ou métier contextuelle**.
- La nouvelle fonctionnalité ne doit pas exposer les médias privés des utilisateurs ni affaiblir l'isolation entre établissements.
- Aucun changement de comportement des règles d'expiration, d'acceptation, de révocation, de rôles et de permissions des invitations.
- La lecture ou l'indisponibilité de la présentation n'affecte jamais l'authentification, l'acceptation des invitations ni les opérations métier.

### Qualité d'expérience

- Emails compatibles avec les principaux clients utilisés par les destinataires (notamment Gmail, Outlook et Apple Mail) ; **le lien d'invitation doit rester prioritaire**.
- Page lisible et utilisable sur mobile et desktop, y compris en connexion limitée, sans téléchargement média inutile avant que l'utilisateur décide de lire.
- Accessibilité raisonnable : textes lisibles, contraste, navigation clavier et contrôles utilisables.
- Dégradation explicite lorsque le média est inaccessible.

### Coût, scalabilité et exploitation

- Retenir la solution **la plus simple et économique qui satisfait les critères réels**, sans surdimensionnement ni dépendance nouvelle injustifiée.
- Évaluer conjointement **stockage, transfert, coûts récurrents, opérations manuelles, maintenance et fiabilité**.
- La diffusion doit pouvoir accompagner la croissance du nombre de destinataires et utilisateurs sans perturber les fonctions critiques de Spore.
- L'URL de découverte et le média doivent rester disponibles aux destinataires d'anciens emails tant que ces liens sont diffusés.

**Ces critères sont les exigences. Leur réalisation (hébergement, frontend, CDN, configuration, déploiement) relève du plan de Cursor.**

## 5. Hors périmètre V1

- Vidéo jouable directement dans le corps d'un email.
- Nouvelle plateforme d'hébergement ou lecteur imposé pour des raisons de préférence technique.
- Bibliothèque de tutoriels, éditeur vidéo, upload de vidéos par les utilisateurs ou refonte de la landing marketing.
- Obligation de regarder la présentation avant d'accepter une invitation.
- Refonte des parcours d'invitation, de l'authentification ou de la navigation principale.
- Mesure détaillée des comportements de lecture ou nouveau système d'analytics, sauf nécessité concrète révélée par l'audit.
- Transcription générée et piste de sous-titres.

## 6. Critères d'acceptation — GO / NO-GO

La livraison est acceptable si les éléments suivants sont démontrés :

1. **Email HTML** : l'action d'acceptation est intacte et prioritaire ; l'accès vidéo est secondaire et clairement identifié.
2. **Email texte / images bloquées** : le destinataire peut toujours accepter l'invitation et retrouver le lien de découverte.
3. **Invitations** : fonctionnement inchangé des flux effectivement concernés, y compris renvoi et états valide/expiré/révoqué/déjà accepté ; visiter la présentation n'altère pas ces états.
4. **Page publique** : `https://spore-os.com/discover/`, accès direct sans connexion, depuis un navigateur desktop ou mobile et après rechargement ; logo officiel, titre, court texte explicatif et vidéo dans l'ordre décidé. Pas de redirection depuis `/decouvrir/`.
5. **Lecture** : aucune interface YouTube, déclenchement volontaire, lecture/pause, son, progression et comportement mobile correct.
6. **Application** : accès permanent pour chaque rôle et chaque surface concernée, avec retour possible à Spore sans perte de contexte.
7. **Confidentialité** : aucun token d'invitation ni média privé exposé ; vidéo validée pour diffusion publique.
8. **Résilience** : une vidéo indisponible ne compromet ni la page informative ni les emails, les invitations ou l'application.
9. **Accessibilité** : contrôles utilisables. La transcription générée et les sous-titres ne font pas partie de cette V1.
10. **Environnements** : fonctionnement vérifié en staging avant toute exposition en production ; liens et contenus de production autonomes et disponibles.
11. **Promotion** : PR ciblée vers `main`, sans merger les autres changements de `staging`, avec dépendances et diff contrôlés.
12. **Native** : vérifier et planifier, si nécessaire, la distribution du changement aux applications mobiles installées ; une fusion Git ne vaut pas automatiquement mise à jour des applications natives.

Cursor doit déduire la **stratégie de tests exacte** du dépôt et distinguer validations automatisées, manuelles et non réalisables localement. Rien de non testé ne doit être annoncé comme validé.

## 7. Mesure de valeur

- **Priorité :** vérifier que l'évolution ne dégrade pas le taux d'acceptation des invitations.
- **À observer si déjà mesurable :** taux d'acceptation par cohorte comparable, délai d'acceptation et première action utile dans Spore.
- Un nombre de vues élevé ne suffit pas à démontrer une amélioration de l'activation.
- Aucune instrumentation complexe n'est nécessaire pour cette V1.

## 8. Responsabilités et méthode de livraison

**Nous décidons du besoin et validons les arbitrages produit. Cursor examine le code, recommande l'architecture et prépare le plan technique.** Une recommandation technique n'est pas une contrainte tant qu'elle n'a pas été validée.

1. Valider ce cadrage comme **source produit**.
2. Lancer `/create-plan` en lecture seule sur `staging`. Cursor doit examiner les implémentations et règles du repository et proposer l'approche la plus cohérente, y compris une alternative plus simple si elle respecte les critères.
3. Nous validons le plan technique et tout véritable arbitrage restant.
4. Implémenter sur une branche de travail issue de `staging`, puis revue et tests avant PR vers `staging`.
5. Tester l'expérience réelle sur staging : email, page publique, mobile, application native, invitations et défaillances du média.
6. Promouvoir **uniquement le périmètre validé** vers `main` via PR séparée, en vérifiant l'écart de branches, les dépendances et les conditions de déploiement.
7. Préserver les liens déjà envoyés, y compris pendant un éventuel retour arrière.

**Documentation de travail :** ce cadrage peut être versionné temporairement sous `docs/plans/spore_video_discovery_cadrage.md`. La documentation pérenne suit les conventions du repository ; éviter de multiplier les documents obsolètes.

## 9. Résultat attendu de l'audit Cursor

À partir de ce document et des sources de vérité du dépôt, Cursor doit :

- Identifier les composants, parcours et contrats réellement concernés.
- Identifier les écarts éventuels entre l'expérience demandée et les comportements existants.
- Comparer les options raisonnables **sans considérer comme acquise une technologie évoquée lors des échanges**.
- Justifier une architecture cohérente, minimale, évolutive et économiquement pertinente.
- Proposer le plan d'implémentation et de validation, y compris les opérations externes ou manuelles incontournables.
- Signaler les seules décisions produit encore bloquantes et les risques propres à la promotion ciblée de `staging` vers `main`.

**Audit strictement read-only : aucune modification, branche, PR ni intervention sur les services externes.**
