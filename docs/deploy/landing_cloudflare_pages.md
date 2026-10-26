# Landing publique Spore — déploiement

## Architecture

| Domaine | Surface | Hébergement |
|---------|---------|-------------|
| `https://spore-os.com` | Landing MPA (`dist-landing/`) | Cloudflare Pages (recommandé) |
| `https://app.spore-os.com` | Application web | Service Railway existant (`houston_project`) |

Même dépôt GitHub, **deux builds indépendants**. Ne pas attacher `spore-os.com` au service Railway applicatif.

## Build local

```bash
cd apps/web
npm ci
npm run build:landing
```

Sortie validée :

```text
apps/web/dist-landing/
├── index.html
├── mentions-legales/index.html
├── politique-de-confidentialite/index.html
├── conditions-d-utilisation/index.html
├── supprimer-compte/index.html
├── support/index.html
├── discover/index.html
├── discover/poster-v1.jpg
├── robots.txt
├── sitemap.xml
├── _redirects
└── assets/
```

Commandes utiles :

- `npm run dev:landing` / `make web-dev-landing`
- `npm run build:landing` / `make web-build-landing`
- `npm run preview:landing`

## Cloudflare Pages (manuel)

1. Créer un projet Pages branché sur ce dépôt.
2. Configuration de build :
   - **Root directory** : `apps/web` (ou racine repo avec commande adaptée)
   - **Build command** : `npm ci && npm run build:landing`
   - **Build output directory** : `dist-landing` (si root = `apps/web`) ou `apps/web/dist-landing`
3. Attacher le domaine custom `spore-os.com` (et `www` si besoin) au projet Pages.
4. Laisser `app.spore-os.com` sur Railway uniquement.
5. **Ne pas** activer le fallback SPA 404 vers `index.html` (sinon `/supprimer-compte/` sert l’accueil). Le fichier `_redirects` du build réécrit explicitement les pages légales vers leurs HTML.
6. Vérifier après déploiement :
   - `https://spore-os.com/`
   - `https://spore-os.com/mentions-legales/` (accès direct, titre mentions légales)
   - `https://spore-os.com/politique-de-confidentialite/`
   - `https://spore-os.com/conditions-d-utilisation/`
   - `https://spore-os.com/supprimer-compte/` (titre **Supprimer un compte Spore**, pas le hero landing)
   - `https://spore-os.com/support/`
   - `https://spore-os.com/discover/`
   - `https://spore-os.com/discover/poster-v1.jpg`
   - `https://spore-os.com/robots.txt`
   - `https://spore-os.com/sitemap.xml`
   - `https://app.spore-os.com/`

Les pages restent statiques. Le formulaire utilise une Pages Function dédiée (`apps/web/functions/api/contact.ts`). Voir [la configuration du formulaire](landing_contact.md) avant de l’activer. Aucun Dockerfile, nginx ou `railway.toml` landing supplémentaire n’est nécessaire.

## Découverte

La page publique est `https://spore-os.com/discover/`. Le chemin `/decouvrir/` n’est pas publié et n’a pas de redirection.

| Ressource | URL stable | Hébergement |
|-----------|------------|-------------|
| Page | `https://spore-os.com/discover/` | Cloudflare Pages, production |
| Miniature | `https://spore-os.com/discover/poster-v1.jpg` | Cloudflare Pages, production |
| Vidéo | `https://media.spore-os.com/spore-discovery-v1.mp4` | Bucket R2 public du même compte que `spore-os.com` |

La landing et la vidéo vont sur le Cloudflare de production. Pas de déploiement Preview, pas d’hôte de staging, pas de restriction d’accès.

Le MP4 conserve l’audio d’origine. Cette V1 ne publie pas de transcription ni de piste de sous-titres. Le MP4 n’est pas dans Git et n’entre pas dans `public-landing` : le build de la landing échoue si un `.mp4` est présent dans `dist-landing`. Le fichier préparé pour l’upload est `spore-discovery-v1.mp4` (H.264 Main, AAC, `+faststart`), hors dépôt. Clé d’objet : `spore-discovery-v1.mp4`. `Content-Type` : `video/mp4`.

Domaine média : `media.spore-os.com`, domaine propre du bucket. Pas d’URL `r2.dev`. Désactiver `r2.dev` une fois le domaine actif. Le proxy Cloudflare de ce nom d’hôte doit laisser passer `Range` : règle de cache en contournement pour `media.spore-os.com`. Ce contournement est une condition de lecture, pas un contrôle d’accès. Pas de Worker, de jeton ou de bucket privé.

Contrôle, sur l’URL de production, avant de considérer la lecture acceptable :

```bash
curl -D - -o /dev/null -H 'Range: bytes=0-1' https://media.spore-os.com/spore-discovery-v1.mp4
curl -D - -o /dev/null -H 'Range: bytes=1000000-1000001' https://media.spore-os.com/spore-discovery-v1.mp4
```

Les deux réponses doivent être `206` avec `Content-Range`. Si ce n’est pas le cas, corriger le cache ou l’en-tête du domaine, puis revérifier.

Une miniature déjà citée par un email reste servie. Ne pas supprimer `poster-v1.jpg` lors d’un remplacement. La page peut ensuite citer une nouvelle miniature. Remplacer la vidéo consiste à publier une nouvelle clé et à faire pointer la page vers elle, en laissant l’ancienne clé.

Annuler le déploiement de l’application ou de l’email ne supprime ni la page Pages ni l’objet R2. Les URL déjà envoyées continuent de répondre.
