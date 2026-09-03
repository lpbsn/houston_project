# Store listing — Spore (P1.12)

Status: pack to paste into App Store Connect / Play Console  
Last reviewed: 2026-09-03  
Locale: **French** (product UI)

Do not upload from this file. Console operations stay Phase 2.

Related: [`store_review.md`](store_review.md) · [`store_compliance.md`](store_compliance.md) · [`store_privacy_declarations.md`](store_privacy_declarations.md) · assets in [`store_assets/`](store_assets/)

## URLs

| Field | Value |
|-------|--------|
| Marketing | https://spore-os.com/ |
| Privacy Policy | https://spore-os.com/politique-de-confidentialite/ |
| Terms (Apple) | https://spore-os.com/conditions-d-utilisation/ |
| Support | https://spore-os.com/support/ |
| Account deletion (Play) | https://spore-os.com/supprimer-compte/ |
| App login | https://app.spore-os.com/login |

Support is live only after the landing Cloudflare Pages deploy that includes `/support/`.

## Google Play

**Title** (≤ 30): `Spore`

**Short description** (≤ 80): `Transforme chaque observation terrain en action suivie.`

**Full description** (≤ 4000):

```
Spore est un outil d’exploitation pour les équipes terrain. Un collaborateur capture une observation (texte ou vocal). Spore la structure, notifie les personnes concernées, et permet de suivre un plan d’action jusqu’à la résolution.

Destiné à l’hôtellerie, la restauration, les loisirs, les bureaux et le retail.

Spore n’est pas un réseau social. Le contenu reste dans l’établissement. Les membres peuvent signaler un contenu et bloquer un collègue pour les messages privés et les mentions.

Un compte est requis. L’inscription des propriétaires se fait sur invitation.
```

**Category:** Business (qualification; confirm in Play Console).

**Graphics:**

- App icon: [`store_assets/play-icon-512.png`](store_assets/play-icon-512.png) (512×512 PNG)
- Feature graphic: [`store_assets/play-feature-graphic-1024x500.png`](store_assets/play-feature-graphic-1024x500.png) (1024×500, no alpha)
- Phone screenshots: see [`store_assets/README.md`](store_assets/README.md). Minimum Play: 2. Prefer at least four 9:16 images ≥ 1080×1920 when capturing.

Tablet / TV / Wear screenshots: not required for this phone listing.

## App Store

**Name** (≤ 30): `Spore`

**Subtitle** (≤ 30): `L’OS des équipes terrain`

**Description:** same full text as Play, plus this closing line if space is useful: `Support : https://spore-os.com/support/`

**Keywords** (≤ 100, comma-separated, no app name):

`observation,terrain,hôtel,restaurant,qualité,maintenance,équipe,exploitation`

**Primary category:** Business. Secondary: Productivity (qualification).

**Age rating:** answer the questionnaire in App Store Connect. See [`store_compliance.md`](store_compliance.md). Do not lock a rating number in this repo.

**Icon:** [`store_assets/app-store-icon-1024.png`](store_assets/app-store-icon-1024.png) (1024×1024, no alpha). Same artwork as the iOS `AppIcon` asset.

**Screenshots:** iPhone **6.9"** slot (e.g. 1320×2868). iPad screenshots are out of scope: the V1 binary is iPhone only.

**What’s New (1.0):** `Première version : observations, signaux, plans d’action, commentaires et chat d’équipe.`

## Device targeting (V1)

iOS `TARGETED_DEVICE_FAMILY = 1` (iPhone). iPad installs as iPhone compatibility mode.

## What this pack does not include

- Console upload
- Age / Kids / Data Safety / App Privacy questionnaires (PR2 worksheets)
- Preview video
- English localization
