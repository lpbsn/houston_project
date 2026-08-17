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
├── robots.txt
├── sitemap.xml
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
5. Vérifier après déploiement :
   - `https://spore-os.com/`
   - `https://spore-os.com/mentions-legales/` (accès direct)
   - `https://spore-os.com/robots.txt`
   - `https://spore-os.com/sitemap.xml`
   - `https://app.spore-os.com/`

Aucun Dockerfile, nginx ou `railway.toml` landing n’est fourni volontairement : la landing est un site statique.
