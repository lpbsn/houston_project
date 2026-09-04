# Native / store brand sources

## Android launcher + splash

Source of truth: `spore-icone-green.png` (green mark, transparency). Do not overwrite it.

```bash
apps/web/scripts/generate-store-brand-assets.sh --android
```

Writes only `android/app/src/main/res` mipmaps and splashes (white background, contain, 66% safe zone for adaptive foreground and round icons).

## iOS / Play listing intermediates

Committed outputs of `apps/web/scripts/generate-store-brand-assets.sh` (no flag):

- `icon.png` — 1024×1024 opaque cream + mark (iOS / Play listing)
- `icon-foreground.png` — leftover cream-era foreground (not used by `--android`)
- `splash.png` — 2732×2732 cream + centered mark (iOS)

That invocation writes iOS xcassets and `docs/product/store_assets/`. It does **not** write Android.

Web/landing mark: `apps/web/src/assets/brand/spore-icon-source.png`. Do not treat Capacitor default PNGs as brand.
