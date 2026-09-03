#!/usr/bin/env bash
# One-shot brand derivation for native shell + store listing.
# Reads existing Spore marks; does not replace web/landing assets.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARK="$ROOT/src/assets/brand/spore-icon-source.png"
CREAM='#F5F0E8'
INK='#1A1916'
RESOURCES="$ROOT/resources"
STORE="$(cd "$ROOT/../.." && pwd)/docs/product/store_assets"
FONT_BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
FONT_REG='/System/Library/Fonts/Supplemental/Arial.ttf'

if [[ ! -f "$MARK" ]]; then
  echo "missing mark: $MARK" >&2
  exit 1
fi

mkdir -p "$RESOURCES" "$STORE"

# Full-bleed iOS / Play icon (opaque cream — App Store rejects alpha on 1024).
magick -size 1024x1024 "xc:${CREAM}" \
  \( "$MARK" -resize 720x720 \) -gravity center -composite \
  -alpha off PNG24:"$RESOURCES/icon.png"

# Adaptive foreground: mark inset (~66% safe zone) on transparency.
magick -size 1024x1024 xc:none \
  \( "$MARK" -resize 640x640 \) -gravity center -composite \
  PNG32:"$RESOURCES/icon-foreground.png"

# Splash source: same cream + smaller centered mark.
magick -size 2732x2732 "xc:${CREAM}" \
  \( "$MARK" -resize 920x920 \) -gravity center -composite \
  PNG24:"$RESOURCES/splash.png"

cp "$RESOURCES/icon.png" "$ROOT/ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png"
for splash_name in splash-2732x2732.png splash-2732x2732-1.png splash-2732x2732-2.png; do
  cp "$RESOURCES/splash.png" "$ROOT/ios/App/App/Assets.xcassets/Splash.imageset/${splash_name}"
done

resize_legacy() {
  local size="$1"
  local dest="$2"
  magick "$RESOURCES/icon.png" -resize "${size}x${size}" PNG32:"$dest"
}

resize_fg() {
  local size="$1"
  local dest="$2"
  magick "$RESOURCES/icon-foreground.png" -resize "${size}x${size}" PNG32:"$dest"
}

while read -r density legacy fg; do
  dir="$ROOT/android/app/src/main/res/mipmap-${density}"
  resize_legacy "$legacy" "$dir/ic_launcher.png"
  resize_legacy "$legacy" "$dir/ic_launcher_round.png"
  resize_fg "$fg" "$dir/ic_launcher_foreground.png"
done <<'DENSITIES'
mdpi 48 108
hdpi 72 162
xhdpi 96 216
xxhdpi 144 324
xxxhdpi 192 432
DENSITIES

compose_splash() {
  local w="$1"
  local h="$2"
  local dest="$3"
  local min=$((w < h ? w : h))
  local mark=$((min * 38 / 100))
  magick -size "${w}x${h}" "xc:${CREAM}" \
    \( "$MARK" -resize "${mark}x${mark}" \) -gravity center -composite \
    PNG24:"$dest"
}

compose_splash 480 320 "$ROOT/android/app/src/main/res/drawable/splash.png"
compose_splash 320 480 "$ROOT/android/app/src/main/res/drawable-port-mdpi/splash.png"
compose_splash 480 800 "$ROOT/android/app/src/main/res/drawable-port-hdpi/splash.png"
compose_splash 720 1280 "$ROOT/android/app/src/main/res/drawable-port-xhdpi/splash.png"
compose_splash 960 1600 "$ROOT/android/app/src/main/res/drawable-port-xxhdpi/splash.png"
compose_splash 1280 1920 "$ROOT/android/app/src/main/res/drawable-port-xxxhdpi/splash.png"
compose_splash 480 320 "$ROOT/android/app/src/main/res/drawable-land-mdpi/splash.png"
compose_splash 800 480 "$ROOT/android/app/src/main/res/drawable-land-hdpi/splash.png"
compose_splash 1280 720 "$ROOT/android/app/src/main/res/drawable-land-xhdpi/splash.png"
compose_splash 1600 960 "$ROOT/android/app/src/main/res/drawable-land-xxhdpi/splash.png"
compose_splash 1920 1280 "$ROOT/android/app/src/main/res/drawable-land-xxxhdpi/splash.png"

magick "$RESOURCES/icon.png" -resize 512x512 PNG32:"$STORE/play-icon-512.png"
cp "$RESOURCES/icon.png" "$STORE/app-store-icon-1024.png"

magick -size 1024x500 "xc:${CREAM}" \
  \( "$MARK" -resize 360x360 \) -gravity west -geometry +72+0 -composite \
  -font "$FONT_BOLD" -fill "$INK" -pointsize 86 -gravity west -annotate +500-36 'Spore' \
  -font "$FONT_REG" -fill "$INK" -pointsize 28 -gravity west -annotate +500+42 "L'OS des équipes terrain" \
  PNG24:"$STORE/play-feature-graphic-1024x500.png"

echo "generated native + listing brand assets"
