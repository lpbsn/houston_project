# Native / store brand sources

Committed outputs of `apps/web/scripts/generate-store-brand-assets.sh`:

- `icon.png` — 1024×1024 opaque cream + mark (iOS / Play listing)
- `icon-foreground.png` — adaptive Android foreground (mark inset, transparency)
- `splash.png` — 2732×2732 cream + centered mark

The script also writes iOS xcassets, Android mipmaps/splashes, and `docs/product/store_assets/`.

Source mark: `apps/web/src/assets/brand/spore-icon-source.png`. Do not treat Capacitor default PNGs as brand.
