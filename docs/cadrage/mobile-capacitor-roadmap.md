# Spore — Roadmap Web + Capacitor

Status: authoritative  
Last reviewed: 2026-09-03

Record of the delivered Capacitor foundation. **Capacitor Lots 1–10 are closed.** Resume product work on this socle. **Capacitor Lot 11** (DX / CI `cap sync` / publication pipeline) is **deferred**, not abandoned. A local Play AAB procedure exists at [`docs/deploy/native_release.md`](../deploy/native_release.md); it does not reopen Lot 11.

These **Capacitor Lots** (1–11) are distinct from product/domain lots (taxonomy Lot 5, test Lot 4 helpers, product Lot 11 stabilization). Write **Capacitor Lot N** when referring to this roadmap.

## Objectif

Construire Spore comme **client unique multi-runtime** :

- un seul frontend React partagé ;
- **Web** (navigateur / desktop) et **Native (Capacitor)** comme deux runtimes du même produit ;
- le terrain en cible de premier rang sur iOS/Android, sans deuxième application frontend.

La **PWA n’est plus une cible produit ni un runtime à maintenir**. Le service worker, le manifeste PWA et les comportements d’installation PWA ne sont pas des contraintes à préserver par principe. Le chantier n’est pas un wrapping de l’existant dans Capacitor : il vise à supprimer les hypothèses trop spécifiques au navigateur (same-origin, proxy Vite, cookies HttpOnly, service worker, `history` navigateur) pour obtenir une base plus simple, propre et maintenable.

Contexte : un seul développeur, aucun utilisateur réel en production. Les Lots 1–10 ont visé l’architecture cible sans mécanismes transitoires de compatibilité. Ne pas les rouvrir pour empiler des fallbacks.

## Cible produit

| Usage | Runtime principal | Priorité UX |
|-------|-------------------|-------------|
| Équipes terrain | Native iOS/Android ; desktop web possible | Mobile-first |
| Direction / management / Analytics | Desktop web | Desktop-first |

Deux runtimes, un seul arbre de sources :

| Runtime | Usage | Rôle |
|---------|-------|------|
| **Web** | Navigateur desktop et mobile | Build classique, sans service worker ni manifeste PWA comme socle |
| **Native** | iOS et Android via Capacitor | Shell natif, distribution App Store / Play Store |

L’application reste **online-first**. Spore est destiné à des équipes terrain pouvant travailler ponctuellement dans des chambres froides, parkings, caves ou autres zones à connectivité faible ou intermittente. Perdre une saisie Observation critique tant que le process reste vivant n’est pas acceptable.

Cela n’implique pas un **offline-first généralisé** : pas de réplication locale complète de l’application, pas de cache durable généralisé, pas de synchronisation universelle de toutes les mutations, pas de file de mutations durable.

La protection ciblée retenue (checkpoint Offline capture, **done**) est la **survie de la saisie Observation tant que le process reste vivant** (blip, background sans kill, picker si le process reste intact, navigation interne), plus ne plus exiger l’upload photo pour composer. Elle est portée par le **Lot 10 (done)**. Elle ne promet pas la survie après process kill / cold start, ni une file, ni une sync. Audio, chat, commentaires, et commandes de cycle de vie (tâches, signaux, plans) restent online-only.

## Besoins fonctionnels vs ancienne implémentation PWA

Certains mécanismes PWA couvraient des besoins réels. La suppression de la PWA **ne doit pas** se transformer en chantier de reconstruction de toutes ses capacités ailleurs. Une capacité n’est conservée ou remplacée **que si un besoin fonctionnel réel le justifie**. PWA artefacts are already removed (Lot 4).

| Besoin fonctionnel | Implémentation actuelle (PWA) | Décision / lot |
|--------------------|-------------------------------|----------------|
| Détection réseau / états hors-ligne | Événements navigateur + bannière UI | Capacitor Lot 6 — **done**: Web `navigator.onLine` ; Native `@capacitor/network` ; une source `isOnline` par runtime |
| Reconnexion WS / refetch après reprise | TanStack Query + hooks WS | Capacitor Lot 6 — **done**: `visibilitychange` (Web) + native `appStateChange` ; resync via `onReconnect` existant |
| Notifications push terrain | Push natif iOS/Android (FCM) | **Lot 7 done.** Web Push desktop **non** ; Web Push mobile hors cible |
| Mise à jour applicative Web | Service worker + bannière de refresh | Lot 4 — **retrait** ; pas de mécanisme équivalent : build Vite classique (`index.html` revalidé, assets hashés en cache long) |
| Installation sur l’écran d’accueil | Manifeste PWA + prompts navigateur | Hors scope Web — distribution native (lot 5) |
| Cache assets / shell offline | Service worker `injectManifest` | Lot 4 — **retrait** ; cache HTTP navigateur/CDN suffit ; pas de shell offline ni de stratégie offline dédiée |

Ne pas replacer le service worker, le manifeste, ni l’installabilité PWA.

## Cible architecturale

- Les features métier ne dépendent pas de Capacitor.
- Les différences Web/Native sont isolées **uniquement lorsqu’elles deviennent concrètes**.
- HTTP, WebSocket, auth, navigation et lifecycle fonctionnent dans les deux runtimes ; le push terrain est le canal FCM natif (Lot 7).
- Pas d’abstraction anticipée : n’introduire une différence Web/Native que lorsqu’elle est concrète.
- Backend, OpenAPI, RBAC, isolation tenant et cache frontend restent les sources de vérité existantes.

Le code et les tests priment. Archi utile : [`../engineering/frontend_architecture.md`](../engineering/frontend_architecture.md), [`../architecture/authentication_charter.md`](../architecture/authentication_charter.md), [`../product/domains/realtime_domain.md`](../product/domains/realtime_domain.md), [`../product/domains/notification_domain.md`](../product/domains/notification_domain.md).

## Statut d’exécution

**Do not reopen Capacitor Lots 1–10.** They are closed. **Do not open Capacitor Lot 11** (CI `cap sync` / publication pipeline) for Fastlane or store CI. Local Play AAB prep is [`docs/deploy/native_release.md`](../deploy/native_release.md) and does not reopen Lot 11. If Lot 11 is later reopened, still do not open durable Observation storage, queue, or sync (régime B) inside it.

Lots 1–10 were sequential. Remaining items under **Limitations non bloquantes** are external dependencies, a distinct ticket, or unfinished device QA — they do not reopen a lot.

Contexte de migration (historique des lots 1–10, toujours vrai pour le produit) : un seul développeur, aucun utilisateur réel en production. Pas de stratégies “safe” destinées à préserver temporairement l’existant (doubles chemins, feature flags, fallbacks). Une rupture plus simple et durable reste préférable. Le repository doit rester fonctionnel.

PAS BESOIN
- backward compatibility
- rollout progressif
- feature flags temporaires
- ancienne + nouvelle implémentation en parallèle
- fallback uniquement pour rassurer
- migrations de transition inutiles
- préserver service worker, manifeste PWA ou installabilité PWA comme cibles produit
- remplacer le service worker par un mécanisme équivalent (mise à jour applicative, shell offline, cache dédié)
- reconstruire ailleurs les capacités PWA par défaut

TOUJOURS BESOIN
- architecture propre
- sécurité
- tests
- validation
- repo fonctionnel

---

## Lots

Capacitor Lot status: **1–10 closed** · checkpoint Offline capture terrain **done** · **11 deferred**.

### 1. Runtime / API / WebSocket — done

**Objectif.** Rendre explicites le runtime et la configuration réseau. Le frontend ne doit plus dépendre implicitement du same-origin ni du proxy Vite.

**Responsabilité.** Introduire une notion de runtime (Web vs Native) et une configuration d’accès HTTP / WebSocket utilisable hors origin partagée. Les features consomment cette configuration ; elles ne calculent pas l’hôte API. CORS, hosts et tickets WS côté backend doivent supporter un client qui n’est plus same-origin. Capacitor n’est pas ajouté dans ce lot.

### 2. Auth multi-runtime — done

**Objectif.** Faire évoluer l’authentification pour Web et Native, avec une logique de session commune.

**Responsabilité.** Conserver un modèle de session backend unique (`UserSession`, rotation, révocation). Isoler le mécanisme de persistance du refresh : cookie HttpOnly côté Web si pertinent, équivalent natif sûr côté Native. La mémoire frontend reste le seul lieu de l’access token. Les features métier ne voient qu’une session authentifiée, pas le canal de stockage. Ne pas introduire Capacitor ici, mais lever les hypothèses « navigateur + cookie » qui bloqueraient Native.

**Décision d’implémentation validée.** Le contrat explicite `refresh_token_transport: cookie | body`, qui décrit uniquement le transport du credential et jamais le runtime ou le niveau de confiance. `cookie` possède cookies + CSRF ; `body` envoie explicitement le refresh avec cookies omis et sans effet `Set-Cookie`. La rotation stricte one-shot reste commune. Le plugin Keychain/Keystore est branché au composition root (Capacitor Lot 5).

### 3. Routing — done

**Objectif.** Disposer d’une base de navigation adaptée au Web, aux deep links et aux comportements natifs.

**Responsabilité.** Les destinations produit restent adressables par URL. Le routeur ne doit plus être indissociable de `history` navigateur seul : il doit pouvoir être piloté par le runtime (lien Web, deep link, notification) sans dupliquer les routes métier. Les deep links et le wiring natif ne sont pas implémentés ici — seule la fondation de navigation l’est.

### 4. Builds Web / Native — done

**Objectif.** Séparer clairement le build **Web** du build **Native** (Capacitor).

**Responsabilité.** Un seul arbre de sources React, deux pipelines de build. Service worker, manifeste PWA, registration SW et autres artefacts PWA retirés ; ils n’appartiennent à aucun des deux runtimes cibles. Le build Web repose sur le **comportement standard d’un build Vite classique** : `index.html` revalidé normalement, assets hashés en cache long, pas de mécanisme spécifique de mise à jour applicative. Le cache HTTP navigateur/CDN suffit ; pas de remplacement du shell offline. Le build Native embarque le même frontend sans hériter d’artefacts ou d’hypothèses Web-only. Capacitor shells were added in Capacitor Lot 5 (`apps/web/ios`, `apps/web/android`, `make web-cap-sync`). Appliquer le tableau « Besoins fonctionnels vs implémentation PWA actuelle » : retrait PWA, sans reconstruction par défaut.

### 5. Bootstrap Capacitor iOS / Android — done

**Objectif.** Ajouter Capacitor et obtenir un premier parcours fonctionnel sur iOS et Android.

**Responsabilité.** Le même frontend React tourne dans deux shells natifs. Valider un parcours réel (auth + un flux terrain) contre l’API, avec HTTP, session et WS déjà rendus multi-runtime. Preuve de faisabilité, pas de polish UX ni de push. Si un choix des lots 1–4 est insuffisant, le corriger ici plutôt que d’empiler un workaround.

### 6. Lifecycle / Network / Realtime — done

**Objectif.** Adapter l’app aux coupures réseau, au background/resume et aux reconnexions WebSocket.

**Responsabilité.** HTTP, WS opérationnel, WS chat et cache TanStack Query se comportent correctement quand l’app passe en arrière-plan, reprend, ou perd le réseau. Reconnexion WS et resynchronisation du cache restent online-first. Ce lot ne met pas en œuvre d’offline capture ; sa conception (lifecycle, état réseau, reconnexion) ne doit pas la rendre inutilement difficile plus tard. Isoler les hooks de lifecycle runtime des features métier. La détection réseau et les états UI associés ne dépendent pas du service worker — elles restent nécessaires dans les deux runtimes.

**Fait.** Banner Web `navigator.onLine` conservé. Native : `@capacitor/app` `appStateChange` + `@capacitor/network`. Reconnect WS au foreground natif même si le client croyait le socket ouvert ; pas de reconnect après close d’accès. Query : pas d’`invalidateQueries` global au foreground.

### Checkpoint — Offline capture terrain — done

**Objectif.** Cadrer, à partir des workflows réels, lesquels doivent survivre à une connectivité intermittente, et si une implémentation d’offline capture ciblée doit être avancée avant le Push (lot 7).

**Décision (2026-08-19).** Pas de lot d’implémentation Offline avant Push. **Lot 7 was the next implementation lot (now done).** La seule capture critique identifiée est l’**Observation** (rapport direct `/reporting`, et observation-depuis-tâche texte seul). Traitement ciblé au **Lot 10**, régime **process vivant** uniquement.

Deux régimes — ne pas les mélanger :

- **Régime A (Lot 10)** — le process JS/WebView tourne encore : blip réseau, background sans kill, picker fichier/caméra **si** le process n’est pas recréé, navigation interne. Ne pas perdre texte + photos locales in-process. Ne plus exiger l’upload photo pour composer. Aucune persistance hors process n’est requise ni promise.
- **Régime B (non promis)** — kill OS, swipe-away, recréation d’activité, cold start. Restaurer la saisie exigerait persistance + exception sécurité/RGPD + éventuellement auth hors-ligne. Hors Lot 10. Un picker qui **tue** le process n’est pas du régime A ; le constater sur device au Lot 10 rouvre B explicitement.

Hors périmètre de capture : audio (transcription online-only, jamais persistée), chat, commentaires, lifecycle Signal, mark-done / skip / exécution, création/édition de plan, lectures de feeds. File universelle, sync, et survie après kill sont du sur-engineering pour ce checkpoint.

Cette protection Observation régime A est un **prérequis avant un vrai usage ou pilote terrain à connectivité intermittente**. **Capacitor Lot 10 (done)** : draft in-memory process-scoped ; photos `File` locales ; upload uniquement à Envoyer ; bouton Envoyer désactivé hors ligne.

Ticket auth orthogonal (wipe refresh Native sur erreur réseau) : hors ce checkpoint, hors Lot 10, hors séquencement Push — [issue #181](https://github.com/lpbsn/houston_project/issues/181), [`../architecture/authentication_charter.md`](../architecture/authentication_charter.md).

### 7. Push multi-channel — done

**Objectif.** Découpler les notifications métier de leur canal de livraison.

**Responsabilité.** Le domaine Notification reste la source des messages d’attention (in-app + règles). Canal unique : **push natif iOS/Android** (FCM). **Web Push desktop** : non. **Web Push mobile** : hors cible. L’inscription, les permissions et le payload de delivery restent spécifiques au canal ; le contenu notifié et le deep link cible restent communs. Ne pas coupler les features au plugin de push.

**Fait (2026-08-19).** Canal unique FCM HTTP v1 + `@capacitor-firebase/messaging`. `PushDevice` user-scoped ; envoi filtré par membership `push_enabled`. Web Push / VAPID retirés. Web Push desktop **non**. Tap OS (foreground / background / terminated) : `establishment_id` + `url` du payload. Sync token si session + permission OS granted (pas le `push_enabled` de l’établissement actif). Device QA manuel iOS physique + Android.

**Validation (2026-08-19).** Implémentation Lot 7 terminée. `npx cap sync` validé. Build Android avec Firebase validé. Build iOS avec `@capacitor-firebase/messaging` + Firebase validé (`GoogleService-Info.plist` embarqué dans la target iOS ; entitlement `aps-environment=development` présent et référencé). Push iOS sur device réel **non validé** : le compte Apple actuel est une Personal Team ; APNs sur iPhone physique attend l’Apple Developer Program. That leftover does not reopen this lot.

### 8. Deep links / navigation native — done

**Objectif.** Les URLs métier, notifications et liens externes ouvrent la bonne destination sur Web ou dans l’app native.

**Responsabilité.** Une URL produit résout la même route dans les deux runtimes. Clics de notification, liens d’invitation et liens externes passent par cette résolution. Auth et établissement courant restent des préconditions backend ; le client n’ouvre pas une ressource non autorisée. S’appuie sur le routeur du lot 3, sans le réinventer.

**Fait (2026-08-19).** Universal Links / App Links HTTPS sur `app.spore-os.com` (`getLaunchUrl` + `appUrlOpen`, dédup handshake seulement). Parser : origine HTTPS exacte + `parseAppRoute`. Destination `{ href, establishmentId? }` portée via `/login` et `/select-establishment`. Switch établissement seulement si l’id est explicite. Pas de custom scheme, pas de fichiers AASA/assetlinks placeholder.

**Validation (2026-08-19).** Handler Android (`adb` VIEW intent → app → navigation) est le niveau de QA du lot.

Store Readiness P1.10 (2026-09-03) : **socle** de publication web fermé (`public/.well-known/`, nginx 404 dédié). Association Play (`assetlinks.json` avec les SHA-256 App Signing listées par la console) et AASA (Team ID App Store, pas Personal Team) restent des **dépendances d’identité store** — voir [`docs/deploy/native_release.md`](../deploy/native_release.md). Ne pas rouvrir ce lot.

### 9. UX native — done

**Objectif.** Traiter les écarts d’expérience vraiment utiles en native : safe areas, clavier, status bar, permissions, et le minimum d’équivalent.

**Responsabilité.** Isoler ces adaptations du métier. Le terrain reste mobile-first ; Analytics et le management restent desktop-first — ne pas forcer une UX native sur les surfaces direction. N’introduire que ce qui est constaté comme bloquant ou dégradant sur device, pas un catalogue de plugins.

**Fait (2026-08-20).** Navigation produit inchangée : topbar « Retour » + `backPath`. Android : `backButton` → overlay dismissible → `backPath` → `minimizeApp()` (pas `history.back`, pas `exitApp`). iOS : pas de listener ; le topbar reste la navigation arrière. Safe areas : token `--app-safe-*` = `var(--safe-area-inset-*, env(...))` sur les paddings existants. Clavier : `@capacitor/keyboard` `resize: native` (iOS WKWebView / `h-dvh`) + Android `adjustResize`. Micro : `NSMicrophoneUsageDescription` + `RECORD_AUDIO` pour la transcription Observation déjà livrée. Pas de plugin Camera / StatusBar.

**Validation (2026-08-20).** Tests jsdom du handler Android et de `resolveTerrainBackPath`. Device QA iOS (Personal Team) + Android : safe areas, clavier login/reporting/chat/commentaires (T0/T1/T2), retour Android vs topbar, prompt micro.

### 10. Résilience terrain — done

**Objectif.** Renforcer l’app face aux connexions instables, interruptions et saisies importantes, sans basculer en offline-first généralisé.

**Responsabilité.** Mieux échouer et mieux reprendre : retries, états réseau explicites, et la protection Observation **régime A** tranchée au checkpoint : ne pas perdre la saisie (texte + photos locales in-process) tant que le process reste vivant ; ne plus exiger l’upload photo pour composer ; UX honnête (pas de faux « envoyé »). Surfaces : `/reporting` et observation-depuis-tâche. **Prérequis** avant un vrai usage/pilote terrain à connectivité intermittente.

Interdit : offline-first généralisé ; réplication locale complète ; cache durable généralisé ; file ou sync de mutations ; survie après process kill / cold start ; persistance hors process « au cas où » ; capture locale de chat, commentaires, tâches, signaux, plans, ou audio. Si le QA device montre qu’un picker **tue** le process, rouvrir le régime B en chantier séparé — ne pas l’absorber ici. Si un besoin d’offline-first généralisé apparaît plus tard, ce sera un chantier distinct.

**Fait (2026-08-20).** Store compose in-memory (pas de disque) : texte + `File` photos sur `/reporting`, texte seul pour observation-depuis-tâche. Survît unmount / navigation interne. Clear sur 201, `clearAuthState` (logout / révocation), login/register (`purgeNonAuth`), et switch établissement. Pas sur un refresh réseau / 401 (`clearVolatileAuthState`). **Aucun** `POST temporary-uploads` avant Envoyer. Pipeline unique : upload des `File` puis `POST observations/`. Échec : draft intact, IDs de la tentative oubliés, l’utilisateur retape Envoyer. Pas de retry 404 dédié (le contrat ne distingue pas expiration / `LINKED` / ID inconnu). Envoyer **désactivé** hors ligne ; composer reste possible. Banner Lot 6 inchangée. Audio / chat / commentaires / lifecycle : online-only.

**Validation (2026-08-21).** Tests jsdom du store, du pipeline upload-then-POST, de `/reporting` (unmount, hors ligne, échec conserve les `File`) et de la sheet tâche (Annuler conserve, 201 clear). Device :
- Android émulateur : nav interne, background sans kill, avion → reconnect → Envoyer, picker DocumentsUI — **PASS** (même pid).
- iOS Simulator : nav, background, picker Photos — **PASS** ; avion → reconnect — **non testé** (pas de signal Capacitor exploitable).
- iPhone physique : **offline → reconnect encore ouvert**. Kill / survie post-process hors lot. Si un picker tue le process, noter et rouvrir B — ne pas l’absorber ici.

### 11. DX / CI / release mobile — deferred

**Objectif.** Simplifier développement, build, validation et release Web / iOS / Android.

**Responsabilité.** Un workflow tenable pour un développeur unique : lancer Web et Native en local, vérifier les deux runtimes, produire et publier sans procédure opaque. CI et release restent proportionnés à l’équipe. Pas de plateforme de release surdimensionnée. Le déploiement Web suit le build Vite classique défini au lot 4 — pas de mécanisme de versioning ou de mise à jour applicative supplémentaire à prévoir ici.

**Pourquoi deferred.** Lots 1–10 sont le socle nécessaire pour reprendre le développement produit. Le projet se développe et se valide localement sur Web + Capacitor iOS/Android. La distribution bêta iOS/Android n’est pas ouverte ; l’Apple Developer Program et les canaux Google Play ne sont pas activés. Construire maintenant une automatisation de release / signing / store qui ne peut pas être validée de bout en bout n’apporte pas de valeur pour un développeur unique. Deferred does not mean abandoned.

**Déclencheur de reprise.** Préparation **réelle** de TestFlight et/ou Google Play Internal Testing (comptes et canaux utilisables). Not a hypothetical “later”. Store Readiness Phase 1 is a separate `cadrage cible` for preparatory store work; it can advance without automatically reopening this lot — see [`../roadmap_spore/spore-store-readiness-phase-1-v3.md`](../roadmap_spore/spore-store-readiness-phase-1-v3.md).

**À traiter à la reprise** (périmètre du lot, pas de design d’implémentation) : signing / distribution ; identifiers et credentials nécessaires ; version / build numbers ; archives iOS / AAB Android ; procédures de publication ; checks CI/release réellement utiles à ce moment-là ; documentation opératoire.

**Déjà couvert — ne pas reconstruire.** Builds locaux Web / Native (`npm run build`, `npm run build:native`) ; `make web-cap-sync` / `cap:sync` ; validations Web et native existantes (tests, smoke locale, CI `build:native:bundle`). Do not treat local `cap sync` as missing work for this lot.

---

## Décisions produit et technique

### Fermées

- Deux runtimes : **Web classique** + **Native Capacitor** ; un seul arbre React ; online-first.
- Suppression PWA : retrait SW, manifeste, installabilité — **sans remplacement équivalent**.
- Build Web : Vite classique : assets fingerprintés/hashés ; politique HTTP configurée au niveau du serveur/CDN pour permettre la revalidation de index.html et le cache long des assets immuables. Aucun mécanisme applicatif spécifique de mise à jour n’est prévu.
- Cache / shell offline PWA : pas de shell offline ni de stratégie offline dédiée héritée du service worker.
- Offline-first généralisé : hors cible — pas de réplication locale complète, pas de cache durable généralisé, pas de synchronisation universelle de toutes les mutations, pas de file de mutations durable.
- Push terrain : **natif iOS/Android** (Lot 7 done) ; Web Push mobile hors cible ; **Web Push desktop : non**.
- Suppression PWA ≠ reconstruction systématique des capacités PWA ailleurs.
- **Offline capture terrain (checkpoint done, 2026-08-19)** : seule capture critique = Observation. **Capacitor Lot 10 done** : régime process-vivant seulement (pas de survie après kill). Audio / chat / commentaires / commandes de cycle de vie exclus. Pas de file, sync, ni persistance hors process.
- **Capacitor Lot 10 implémentation (2026-08-20)** : draft in-memory ; photos uploadées seulement à Envoyer ; Envoyer désactivé hors ligne ; pas d’upload opportuniste ; pas de retry 404. Purge draft : 201, fin de session, nouvelle identité, switch établissement — pas un échec refresh.
- **Capacitor Lot 11 (2026-08-21)** : DX / CI `cap sync` / publication pipeline **deferred**. Not abandoned. Daily `cap sync` unchanged. Local signed AAB: [`docs/deploy/native_release.md`](../deploy/native_release.md) (2026-09-02).

### Limitations non bloquantes (hors lots)

These do **not** reopen Lots 1–10 or open Lot 11:

- Push iOS physique / APNs : Apple Developer Program (Personal Team today).
- App Links Play vérifiés : empreintes **Play App Signing** (toutes celles listées) dans `assetlinks.json` + redéploy web. Pas de placeholders. La clé upload n’est pas la cible store. Handler Android `adb` VIEW → app → navigation is the Lot 8 QA bar.
- Universal Links iOS E2E : Team ID App Store + AASA (même barre ADP que l’APNs Lot 7). Pas d’AASA Personal Team.
- Capacitor Lot 10 régime A is delivered. Device leftovers: iPhone physique offline → reconnect encore ouvert ; iOS Simulator avion → reconnect non testé (pas de signal Capacitor exploitable).
- Native refresh wipe on network error — [issue #181](https://github.com/lpbsn/houston_project/issues/181) (distinct ticket).

---

## Hors scope de cette roadmap

- Deuxième frontend ou app native séparée.
- PWA comme runtime produit distinct (service worker, manifeste, installabilité navigateur).
- Offline-first généralisé (réplication locale complète, cache durable généralisé, synchronisation universelle de toutes les mutations, file de mutations durable).
- Survie Observation après process kill / cold start (régime B) — persistance hors process, exception RGPD, auth hors-ligne.
- Capture locale de chat, commentaires, audio, ou commandes de cycle de vie.
- Refonte métier (Observation, Signal, Action Plan, Chat, Analytics).
- Décisions d’implémentation (fichiers, APIs internes, plugins, stores).
- Wipe refresh token Native sur erreur réseau ([issue #181](https://github.com/lpbsn/houston_project/issues/181) ; pas ce checkpoint).

Ne pas rouvrir un lot Capacitor pour ces sujets. Inspecter le code avant tout changement.
