# Spore — Modernisation du chat

## Document de cadrage

**Statut :** décisions finales validées  
**Version :** 1.2  
**Date :** 20 septembre 2026  
**Finalité :** figer le périmètre produit et les invariants d’architecture du chat moderne. L’implémentation suit le code et les tests ; ce document ne les remplace pas.

---

## 1. Objet du chantier

Moderniser le chat Spore pour qu’il soit robuste et naturel sur mobile comme sur desktop, sans le transformer en plateforme de collaboration générique.

Cette évolution couvre exclusivement :

1. l’envoi de photos/images et de documents ;
2. la réponse ciblée à un message (`reply-to`) ;
3. la mention des participants d’une conversation ;
4. un envoi fiable malgré les pertes de connexion ou de WebSocket ;
5. la consultation des médias et documents partagés dans une conversation ;
6. la rétention des messages et fichiers à 30 jours.

Le chantier est une évolution ciblée du modèle de message, du transport et de l’interface existants. Ce n’est pas une refonte complète du domaine chat.

---

## 2. Principes directeurs

### 2.1 Mobile-first, sans dégrader le desktop

Le parcours principal fonctionne naturellement dans l’application native, y compris avec un réseau instable. Le desktop ajoute les interactions attendues : glisser-déposer, collage depuis le presse-papiers et actions au survol.

### 2.2 Le message reste l’unité centrale

Un message peut contenir du texte, une ou plusieurs pièces jointes, des mentions et une réponse à un message antérieur.

```text
ChatMessage
├── body
├── attachments[]
├── mentions[]
└── reply_to
```

Pas de type de message distinct par contenu, ni de système générique de blocs.

### 2.3 Simplicité produit

Le chat facilite les échanges entre participants. Il ne devient pas un second système de navigation vers les objets métier Spore.

### 2.4 Fiabilité avant richesse fonctionnelle

La perte du WebSocket ou une coupure réseau temporaire ne doit pas empêcher la rédaction ni provoquer de doublons. Les états d’envoi sont explicites et récupérables.

### 2.5 Sécurité et isolation existantes préservées

Une pièce jointe, une mention ou une réponse n’élargit jamais les droits d’accès à une conversation ou à un établissement.

---

## 3. Périmètre fonctionnel

### 3.1 Messages enrichis

Un message peut être :

- du texte seul ;
- une image seule ;
- un document seul ;
- du texte accompagné d’une ou plusieurs pièces jointes ;
- une réponse contenant du texte et/ou des pièces jointes ;
- un message contenant une ou plusieurs mentions.

Invariant : un message doit contenir un texte non vide ou au moins une pièce jointe. Une mention ou un `reply_to` seul ne suffit pas.

### 3.2 Pièces jointes

Deux catégories visibles :

- **Médias** : photos et images ;
- **Documents** : fichiers autorisés par la politique de sécurité (V1 : images courantes et PDF).

Expérience :

- sélection depuis le bouton `+` ;
- aperçu avant envoi ;
- affichage de la progression d’upload (texte ou barre + `aria-valuenow`, pas la couleur seule) ;
- annulation avant l’envoi du message ;
- reprise ou nouvel essai après un échec ;
- miniature pour les images dans la conversation ;
- ouverture de l’original via un accès privé Houston ;
- nom, type et taille pour un document ;
- rédaction possible pendant l’upload.

Desktop : glisser-déposer, collage d’image, sélecteur de fichier.  
Mobile : bouton `+` identifiable, accès photos et documents, interaction tactile.

### 3.3 Reply-to

Réponse à un message de la même conversation.

- mobile : swipe et action accessible sans geste ;
- desktop : action au survol et alternative clavier ;
- composer : aperçu compact avec annulation ;
- message envoyé : citation compacte de l’auteur et de l’extrait d’origine ;
- sélection de la citation : retour au message d’origine s’il est encore dans le fil.

Contraintes : même conversation ; parent léger et non récursif ; parent expiré ou absent → « Message d’origine indisponible » ; pas de threads.

### 3.4 Mentions

Le caractère `@` ouvre un picker limité aux participants actifs.

- recherche par nom parmi les participants éligibles ;
- insertion visuelle claire ;
- **relation structurée** : `membership_id`, `start`, `end` en **points de code Unicode** (même convention que `Array.from` / Python) ;
- le serveur valide l’appartenance active au moment de l’envoi ;
- le nom affiché n’est **pas** la source d’autorité : pas de parsing du texte pour déduire la mention.

Une mention n’invite personne, n’accorde aucun droit, ne vise aucun objet métier.

Les notifications spécifiques aux mentions ne font pas partie de cette V1, sauf conservation d’un mécanisme déjà existant sans élargissement.

### 3.5 Médias et documents de la conversation

```text
Informations de la conversation
├── Participants
└── Médias et documents
    ├── onglet Médias (galerie)
    └── onglet Documents (liste)
```

Depuis un élément, retour au message d’origine s’il existe encore dans le fil (ancre `chat-msg-{message_id}`). Sinon, même libellé d’indisponibilité que pour un reply. Les liens dans les messages sont hors V1.

### 3.6 États d’envoi

```text
pending → sending → sent
                  ↘ failed → retry
```

Le texte et les pièces déjà sélectionnés ne doivent pas être perdus au changement d’écran, au passage en arrière-plan ou à une coupure réseau raisonnablement récupérable. Le brouillon **avant Send** est persisté dans le même store d’outbox (métadonnées + octets copiés à la sélection), scoped `userId` / `establishmentId` / `conversationId`. Hydratation au montage ; purge au logout, au changement d’établissement et sur `access.revoked`.

Le composer reste utilisable lorsque le WebSocket est déconnecté. Après un HTTP 200, le message est fusionné dans le cache client **sans attendre** le fan-out WS.

---

## 4. Décisions d’architecture finales

### 4.1 HTTP unique pour l’envoi

- **HTTP** `POST …/messages/` est la seule commande d’envoi.
- **WebSocket** = fan-out et bannière (`message.created`, événements d’accès / structure). Plus de `message.send`.
- Un frame `message.send` est une erreur de protocole (fermeture, aucune persistance).
- Fan-out uniquement après `transaction.on_commit`, et seulement si `created=true`.

### 4.2 Envoi idempotent

`client_message_id` par `(conversation, author_membership)`. Un retry HTTP retourne le message existant (`created=false`) sans second fan-out. L’idempotence est serveur.

### 4.3 Outbox locale — aucune URL présignée persistée

File locale des envois non confirmés (IndexedDB sur web ; `@capacitor/filesystem` **`Directory.Data`** sur native).

Chemin des octets Native, dès la sélection :

```text
chat-outbox/{userId}/{establishmentId}/{localAttachmentId}
```

Métadonnées persistées : état d’envoi, `uploadId`, expiration de réservation, identifiants locaux. **Aucune URL présignée (`put_url`) n’est stockée** dans IndexedDB, le Filesystem ou les métadonnées.

Reprise :

- réservation encore valide → **renouveler** l’URL présignée côté Houston pour le même `uploadId`, puis PUT ;
- réservation expirée ou absente → **recréer** la réservation à partir des octets locaux ;
- jamais de PUT vers une URL vide ; le proxy Django n’est pas le contrat V1.

TTL, succès, annulation, logout, switch d’établissement et `access.revoked` purgent outbox et brouillons.

### 4.4 Pipeline d’upload

Upload direct vers le stockage objet via URL présignée, finalisation Houston, puis association au message.

- les octets ne transitent pas par le WebSocket ;
- `put_url` n’est émis que pour un PUT S3 présigné (sans auth Houston) ; le fallback filesystem local utilise `PUT …/content/` authentifié, jamais une URL Houston présentée comme présignée ;
- Django/Daphne n’est pas un proxy durable des fichiers en production ;
- progression, annulation (`AbortController` / `xhr.abort`) et retry avant `POST` message ;
- stockage privé.

### 4.5 Traitement asynchrone des médias

Validation approfondie, miniatures et nettoyage hors du chemin synchrone d’envoi lorsque l’infra le permet. Le fil et la galerie utilisent des miniatures ; l’original se charge à la demande via `preview_url` déjà autorisé.

### 4.6 PostgreSQL reste la source de vérité

Messages, pièces jointes, mentions et replies restent relationnels, interrogeables et protégés par des invariants serveur.

### 4.7 Stockage Railway : bucket dédié `chat-attachement`

Bucket privé Railway **`chat-attachement`** (nom validé, région `ams`). Pipeline logiciel partagé avec les médias Signal (stockage Django S3, présign, authz, validation, Celery, miniatures). **Pas** le bucket Signal (`HOUSTON_S3_*`). `get_chat_private_media_storage()` ne fallback pas sur ce bucket.

Variables Houston : `HOUSTON_CHAT_S3_*` (références Railway, pas de secrets copiés). Style d’adressage aligné sur les Credentials du bucket, pas inventé.

Si le bucket n’offre pas de lifecycle objet, Spore gère la purge à 30 jours et les orphelins (Celery beat + helpers de suppression).

---

## 5. Sécurité et permissions

Chaque opération vérifie côté serveur : accès à la conversation, appartenance active, mentions et parent dans cette conversation, upload lié à l’utilisateur / tenant / contexte, interdiction de réutiliser un upload consommé ou expiré.

Les fichiers restent privés. Consultation et téléchargement : autorisation vérifiée ou lien temporaire court après contrôle.

Aucune donnée privée via WebSocket, miniatures, URLs, galerie, erreurs de validation, ou citation d’un parent inaccessible.

Toute lecture ou mutation suit l’isolation multi-tenant existante.

---

## 6. Rétention et suppression

Rétention par défaut : **30 jours** (`HOUSTON_CHAT_MESSAGE_RETENTION_DAYS`).

- la purge d’un message supprime ses relations dépendantes et les objets de stockage de façon fiable et observable ;
- les uploads abandonnés sont également purgés ;
- une erreur de suppression stockage se retente sans restaurer le message ;
- un reply vers un parent expiré ne supprime pas la réponse ;
- la galerie reflète la même rétention ;
- la suppression de compte réutilise le même helper de nettoyage stockage que la purge.

---

## 7. Compatibilité

Préservés : conversations et messages existants, pagination curseur, isolation tenant, types frontend générés depuis OpenAPI, événements WS nécessaires aux autres clients.

`POST …/messages/` accepte un `body` vide si au moins une pièce jointe validée est fournie. Le contrat OpenAPI doit le refléter (`body` non requis).

Les clients non mis à jour qui n’envoient que du texte restent valides.

---

## 8. Exigences non fonctionnelles

**Performance** : pagination curseur ; pas de messages récursifs dans les replies ; miniatures dans le fil et la galerie ; index conversation / date / type ; pas d’octets fichier via WebSocket.

**Résilience** : retries sans duplication ; événements après commit ; états d’upload et d’envoi récupérables ; nettoyage des orphelins.

**Accessibilité** : alternative visible ou clavier à tout geste / survol ; progression et erreur pas uniquement par la couleur ; libellés accessibles.

**Observabilité** : identifiants et transitions d’état uniquement — jamais le corps des messages, les chemins média privés, les URL présignées ou les secrets.

---

## 9. Critères d’acceptation

1. Envoi de texte, image ou document autorisé depuis mobile et desktop.
2. Progression visible, annulation avant envoi, retry après échec.
3. Un retry d’envoi ne crée jamais de doublon.
4. Composer utilisable sans WebSocket ; message HTTP 200 visible sans attendre WS.
5. Message en attente ou en échec identifiable et récupérable ; reprise d’upload sans `putUrl` persisté.
6. Images via miniature, original via preview autorisé.
7. Documents : nom, type, taille ; accès uniquement aux autorisés.
8. Reply depuis mobile et desktop ; parent expiré reste affichable.
9. `@` ne propose que les participants actifs ; mention forgée rejetée serveur.
10. Galerie Médias / Documents filtrée par `kind`, jump `message_id` si le message est encore dans le fil.
11. Rétention 30 jours ; orphelins et pièces jointes nettoyés à la purge et à la suppression de compte.
12. Conversations et messages existants restent lisibles.

---

## 10. Hors périmètre

- références structurées vers plans d’action, signaux ou autres objets Spore ;
- picker d’entités générique ;
- threads, réactions, édition ou suppression manuelle des messages ;
- audio, vidéo, appels ;
- recherche globale, onglet liens, aperçu d’URL ;
- caméra avancée ou éditeur d’image ;
- quotas facturés, plans de rétention payants, E2EE ;
- refonte générale des conversations, membres ou notifications ;
- rename du bucket (`chat-attachement` reste le nom validé) ;
- persistance d’URLs présignées ;
- déploiement applicatif de cette branche sur la production unique avant merge humain.

---

## 11. Références d’implémentation

- Domaine : [`docs/product/domains/chat_domain.md`](../product/domains/chat_domain.md)
- Variables Railway : [`docs/deploy/railway_variables.md`](../deploy/railway_variables.md)
- Backend : `apps/api/houston/chat/`
- Frontend : `apps/web/src/features/chat/`
