# Native / store brand sources

Shared mark: `spore-icone-green.png` (green mark, transparency). Do not overwrite it. Do not use `src/assets/brand/spore-icon-green.png` as a second native source.

## Android launcher + splash

```bash
apps/web/scripts/generate-store-brand-assets.sh --android
```

Writes only `android/app/src/main/res` mipmaps and splashes (white background, contain, 66% safe zone for adaptive foreground and round icons).

## iOS / Play listing intermediates

Committed outputs of `apps/web/scripts/generate-store-brand-assets.sh` (no flag):

- `icon.png` — 1024×1024 opaque white + trimmed mark, contain ~720 (iOS / Play listing)
- `splash.png` — 2732×2732 white + trimmed mark at ~38% of the side (iOS)

That invocation writes iOS xcassets and `docs/product/store_assets/`. It does **not** write Android. It does not write `icon-foreground.png` (leftover cream-era file, unused).

Web/landing mark: `apps/web/src/assets/brand/spore-icon-green.png`. Do not treat Capacitor default PNGs as brand.
