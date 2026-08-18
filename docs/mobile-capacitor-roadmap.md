# Spore — Roadmap Web + Capacitor

Status: authoritative  
Last reviewed: 2026-08-18

Référence d’exécution pour les agents Cursor. **Capacitor Lots 1–5 are done.** Next is **Capacitor Lot 6** (lifecycle / network / realtime). After Lot 6, a framing checkpoint **Offline capture terrain** precedes Lot 7. This document frames the remaining lots; it does not prescribe implementation.

These **Capacitor Lots** (1–11) are distinct from product/domain lots (taxonomy Lot 5, test Lot 4 helpers, product Lot 11 stabilization). Write **Capacitor Lot N** when referring to this roadmap.

## Objectif

Construire Spore comme **client unique multi-runtime** :

- un seul frontend React partagé ;
- **Web** (navigateur / desktop) et **Native (Capacitor)** comme deux runtimes du même produit ;
- le terrain en cible de premier rang sur iOS/Android, sans deuxième application frontend.

La **PWA n’est plus une cible produit ni un runtime à maintenir**. Le service worker, le manifeste PWA et les comportements d’installation PWA ne sont pas des contraintes à préserver par principe. Le chantier n’est pas un wrapping de l’existant dans Capacitor : il vise à supprimer les hypothèses trop spécifiques au navigateur (same-origin, proxy Vite, cookies HttpOnly, service worker, `history` navigateur) pour obtenir une base plus simple, propre et maintenable.

Contexte d’exécution : un seul développeur, aucun utilisateur réel en production. L’architecture existante n’est pas une contrainte à préserver. Les lots doivent viser directement l’architecture cible et éviter les mécanismes transitoires de compatibilité lorsqu’ils n’apportent pas de valeur durable.

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

L’application reste **online-first**. Spore est destiné à des équipes terrain pouvant travailler ponctuellement dans des chambres froides, parkings, caves ou autres zones à connectivité faible ou intermittente. Perdre une saisie terrain critique à cause d’une coupure réseau n’est pas acceptable.

Cela n’implique pas un **offline-first généralisé** : pas de réplication locale complète de l’application, pas de cache durable généralisé, pas de synchronisation universelle de toutes les mutations.

En revanche, une capacité **ciblée d’offline capture** est une possibilité légitime pour les workflows terrain critiques : conserver localement une saisie ou un média lorsqu’elle ne peut pas être envoyée, puis la synchroniser au retour du réseau. Le stockage, l’idempotence, le rejeu, les médias et l’UX se cadrent à partir des workflows réels — pas d’architecture imposée à l’avance (file de mutations TanStack ou autre).

## Besoins fonctionnels vs implémentation PWA actuelle

Certains mécanismes PWA couvraient des besoins réels. La suppression de la PWA **ne doit pas** se transformer en chantier de reconstruction de toutes ses capacités ailleurs. Une capacité n’est conservée ou remplacée **que si un besoin fonctionnel réel le justifie**.

| Besoin fonctionnel | Implémentation actuelle (PWA) | Décision / lot |
|--------------------|-------------------------------|----------------|
| Détection réseau / états hors-ligne | Événements navigateur + bannière UI | Capacitor Lot 6 — indépendant du service worker ; **partial**: `navigator.onLine` + Terrain banner already exist ; native `appStateChange` still this lot |
| Reconnexion WS / refetch après reprise | TanStack Query + hooks WS | Capacitor Lot 6 — **partial**: `visibilitychange` reconnect exists ; native background/resume still this lot |
| Notifications push terrain | Web Push (navigateur) ; contraintes iOS PWA | Lot 7 — **push natif iOS/Android** (priorité terrain) ; Web Push desktop **optionnel**, à justifier produit au lot 7 ; Web Push mobile **hors cible implicite** |
| Mise à jour applicative Web | Service worker + bannière de refresh | Lot 4 — **retrait** ; pas de mécanisme équivalent : build Vite classique (`index.html` revalidé, assets hashés en cache long) |
| Installation sur l’écran d’accueil | Manifeste PWA + prompts navigateur | Hors scope Web — distribution native (lot 5) |
| Cache assets / shell offline | Service worker `injectManifest` | Lot 4 — **retrait** ; cache HTTP navigateur/CDN suffit ; pas de shell offline ni de stratégie offline dédiée |

Retirer l’implémentation PWA au lot concerné. Ne pas la replacer par défaut.

## Cible architecturale

- Les features métier ne dépendent pas de Capacitor.
- Les différences Web/Native sont isolées **uniquement lorsqu’elles deviennent concrètes**.
- HTTP, WebSocket, auth, navigation et lifecycle doivent fonctionner dans les deux runtimes ; le push est traité au lot 7 selon le canal retenu.
- Pas d’abstraction anticipée : chaque besoin est introduit au lot qui le rend nécessaire.
- Backend, OpenAPI, RBAC, isolation tenant et cache frontend restent les sources de vérité existantes.

Docs à relire selon le lot, après le code : [`engineering/frontend_architecture.md`](engineering/frontend_architecture.md), [`architecture/authentication_charter.md`](architecture/authentication_charter.md), [`product/domains/realtime_domain.md`](product/domains/realtime_domain.md), [`product/domains/notification_domain.md`](product/domains/notification_domain.md). Le code et les tests priment sur ces docs. La documentation historique PWA est nettoyée **progressivement**, lot par lot, avec le code concerné — pas en chantier séparé.

## Règles d’exécution

Chaque lot est un chantier séparé. Un agent qui ouvre un lot doit :

1. **Inspecter le code réel** concerné (frontend, backend, tests, contrat API) avant toute proposition.
2. **Challenger l’architecture existante** si un choix plus simple et durable est possible. La rétrocompatibilité n’est pas un objectif.
3. **Planifier** (périmètre, décisions, validation) avant d’implémenter.
4. **Implémenter et valider ce lot uniquement.** Ne pas anticiper les lots suivants.
5. **Laisser le repository fonctionnel** à la fin du lot (Web au minimum ; Native dès qu’elle existe).
6. **Choisir la solution la plus simple** compatible avec une architecture durable. Pas d’abstraction « pour plus tard ».

Les fichiers, interfaces, plugins Capacitor, librairies et migrations se décident **au début du lot**, après inspection — pas dans cette roadmap.

Ordre des lots : strictement séquentiel. Un lot suivant ne commence que si le précédent est implémenté et validé. Le checkpoint Offline capture terrain (après le lot 6) n’est pas un lot d’implémentation ; il précède le lot 7.

Contexte de migration. Le projet est développé par un seul développeur et n’a aucun utilisateur réel en production. Il n’est donc pas nécessaire de privilégier les stratégies de migration “safe” destinées à préserver temporairement l’existant : compatibilité ascendante, doubles chemins, feature flags, migrations progressives, fallbacks temporaires ou conservation d’anciennes abstractions. Si une rupture ou une refonte rend la cible plus simple, propre et maintenable, elle doit être privilégiée.
Cela ne signifie pas ignorer la qualité ou la sécurité technique : le repository doit rester fonctionnel et validé à la fin de chaque lot.

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

Capacitor Lot status: **1–5 done** · **6 next** · checkpoint Offline capture terrain · 7–11 not started.

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

### 6. Lifecycle / Network / Realtime — next

**Objectif.** Adapter l’app aux coupures réseau, au background/resume et aux reconnexions WebSocket.

**Responsabilité.** HTTP, WS opérationnel, WS chat et cache TanStack Query se comportent correctement quand l’app passe en arrière-plan, reprend, ou perd le réseau. Reconnexion WS et resynchronisation du cache restent online-first. Ce lot ne met pas en œuvre d’offline capture ; sa conception (lifecycle, état réseau, reconnexion) ne doit pas la rendre inutilement difficile plus tard. Isoler les hooks de lifecycle runtime des features métier. La détection réseau et les états UI associés ne dépendent pas du service worker — elles restent nécessaires dans les deux runtimes.

**Déjà en place (ne pas reconstruire) :** banner `navigator.onLine` et reconnect WS sur `visibilitychange`. Ce lot ajoute le lifecycle natif (`appStateChange` / background-resume), pas une nouvelle détection réseau web.

### Checkpoint — Offline capture terrain

**Objectif.** Cadrer, à partir des workflows réels, lesquels doivent survivre à une connectivité intermittente, et si une implémentation d’offline capture ciblée doit être avancée avant le Push (lot 7).

**Responsabilité.** Ce n’est pas un lot d’implémentation. Examiner les saisies terrain critiques — exemples à instruire, pas des décisions déjà prises : observations, photos/audio, autres captures — et déterminer si une conservation locale puis une synchronisation au retour du réseau est justifiée. Trancher le périmètre produit, pas l’architecture : stockage, idempotence, rejeu, médias et UX se décident seulement si le checkpoint conclut à une implémentation. L’offline-first généralisé reste hors cible.

### 7. Push multi-channel

**Objectif.** Découpler les notifications métier de leur canal de livraison.

**Responsabilité.** Le domaine Notification reste la source des messages d’attention (in-app + règles). **Push natif iOS/Android** : cible prioritaire pour les usages terrain. **Web Push desktop** : optionnel — ne l’implémenter qu’au lot 7 si un besoin produit réel le justifie (direction / management). **Web Push mobile** : hors cible implicite. L’inscription, les permissions et le payload de delivery restent spécifiques au canal retenu ; le contenu notifié et le deep link cible restent communs. Ne pas coupler les features au plugin de push.

### 8. Deep links / navigation native

**Objectif.** Les URLs métier, notifications et liens externes ouvrent la bonne destination sur Web ou dans l’app native.

**Responsabilité.** Une URL produit résout la même route dans les deux runtimes. Clics de notification, liens d’invitation et liens externes passent par cette résolution. Auth et établissement courant restent des préconditions backend ; le client n’ouvre pas une ressource non autorisée. S’appuie sur le routeur du lot 3, sans le réinventer.

### 9. UX native

**Objectif.** Traiter les écarts d’expérience vraiment utiles en native : safe areas, clavier, status bar, permissions, et le minimum d’équivalent.

**Responsabilité.** Isoler ces adaptations du métier. Le terrain reste mobile-first ; Analytics et le management restent desktop-first — ne pas forcer une UX native sur les surfaces direction. N’introduire que ce qui est constaté comme bloquant ou dégradant sur device, pas un catalogue de plugins.

### 10. Résilience terrain

**Objectif.** Renforcer l’app face aux connexions instables, interruptions et saisies importantes, sans basculer en offline-first généralisé.

**Responsabilité.** Mieux échouer et mieux reprendre : retries, états réseau explicites, protection des saisies critiques contre une interruption. Une persistance/reprise ciblée des opérations terrain critiques (offline capture) reste possible si le checkpoint l’a justifiée ; ce lot ne l’interdit pas. Interdit uniquement : offline-first généralisé, réplication locale complète, cache durable généralisé, persistance automatique de toutes les mutations. Si un besoin d’offline-first généralisé apparaît plus tard, ce sera un chantier distinct.

### 11. DX / CI / release mobile

**Objectif.** Simplifier développement, build, validation et release Web / iOS / Android.

**Responsabilité.** Un workflow tenable pour un développeur unique : lancer Web et Native en local, vérifier les deux runtimes, produire et publier sans procédure opaque. CI et release restent proportionnés à l’équipe. Pas de plateforme de release surdimensionnée. Le déploiement Web suit le build Vite classique défini au lot 4 — pas de mécanisme de versioning ou de mise à jour applicative supplémentaire à prévoir ici.

---

## Décisions produit et technique

### Fermées

- Deux runtimes : **Web classique** + **Native Capacitor** ; un seul arbre React ; online-first.
- Suppression PWA : retrait SW, manifeste, installabilité — **sans remplacement équivalent**.
- Build Web : Vite classique : assets fingerprintés/hashés ; politique HTTP configurée au niveau du serveur/CDN pour permettre la revalidation de index.html et le cache long des assets immuables. Aucun mécanisme applicatif spécifique de mise à jour n’est prévu.
- Cache / shell offline PWA : pas de shell offline ni de stratégie offline dédiée héritée du service worker.
- Offline-first généralisé : hors cible — pas de réplication locale complète, pas de cache durable généralisé, pas de synchronisation universelle de toutes les mutations.
- Push terrain : **natif iOS/Android** prioritaire ; Web Push mobile hors cible implicite.
- Suppression PWA ≠ reconstruction systématique des capacités PWA ailleurs.

### Encore ouvertes

- **Web Push desktop** : à trancher **au lot 7** uniquement si un besoin produit réel émerge (ex. alertes direction sans app native).
- **Offline capture terrain** : capacité ciblée possible pour des workflows critiques ; à cadrer au checkpoint après le lot 6, à partir des workflows réels. Pas d’architecture imposée (file de mutations, stockage, rejeu, médias, UX).

---

## Hors scope de cette roadmap

- Deuxième frontend ou app native séparée.
- PWA comme runtime produit distinct (service worker, manifeste, installabilité navigateur).
- Offline-first généralisé (réplication locale complète, cache durable généralisé, synchronisation universelle de toutes les mutations).
- Refonte métier (Observation, Signal, Action Plan, Chat, Analytics).
- Décisions d’implémentation (fichiers, APIs internes, plugins, stores).

Ces sujets se tranchent lot par lot, après lecture du code.
