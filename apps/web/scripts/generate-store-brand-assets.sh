#!/usr/bin/env bash
# Brand derivation. `--android` writes launcher/splash from the green mark only.
# Default (no flag) writes iOS xcassets + store listing; it does not touch Android.
# Does not replace web/landing assets.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARK="$ROOT/src/assets/brand/spore-icon-source.png"
ANDROID_MARK="$ROOT/resources/spore-icone-green.png"
CREAM='#F5F0E8'
WHITE='#FFFFFF'
INK='#1A1916'
RESOURCES="$ROOT/resources"
STORE="$(cd "$ROOT/../.." && pwd)/docs/product/store_assets"
FONT_BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
FONT_REG='/System/Library/Fonts/Supplemental/Arial.ttf'
# Adaptive / round: opaque bbox inside inner 66% of a 1024 canvas (72/108 dp).
ANDROID_SAFE=676

generate_android() {
  if [[ ! -f "$ANDROID_MARK" ]]; then
    echo "missing Android mark: $ANDROID_MARK" >&2
    exit 1
  fi

  local fg_master round_master square_master
  fg_master="$(mktemp -t spore-android-fg.XXXXXX.png)"
  round_master="$(mktemp -t spore-android-round.XXXXXX.png)"
  square_master="$(mktemp -t spore-android-square.XXXXXX.png)"
  trap 'rm -f "$fg_master" "$round_master" "$square_master"' RETURN

  # Transparent foreground: trimmed mark contained in the 66% safe square.
  magick "$ANDROID_MARK" -trim +repage \
    -resize "${ANDROID_SAFE}x${ANDROID_SAFE}" \
    -background none -gravity center -extent 1024x1024 \
    PNG32:"$fg_master"

  # Round launcher is circular-cropped: same inset, composited on white.
  magick -size 1024x1024 "xc:${WHITE}" \
    \( "$ANDROID_MARK" -trim +repage -resize "${ANDROID_SAFE}x${ANDROID_SAFE}" \) \
    -gravity center -composite \
    -alpha off PNG24:"$round_master"

  # Square legacy: contain on white, no extra fill/stretch.
  magick -size 1024x1024 "xc:${WHITE}" \
    \( "$ANDROID_MARK" -trim +repage -resize 1024x1024 \) \
    -gravity center -composite \
    -alpha off PNG24:"$square_master"

  resize_png() {
    local src="$1"
    local size="$2"
    local dest="$3"
    magick "$src" -resize "${size}x${size}" PNG32:"$dest"
  }

  while read -r density legacy fg; do
    local dir="$ROOT/android/app/src/main/res/mipmap-${density}"
    resize_png "$square_master" "$legacy" "$dir/ic_launcher.png"
    resize_png "$round_master" "$legacy" "$dir/ic_launcher_round.png"
    resize_png "$fg_master" "$fg" "$dir/ic_launcher_foreground.png"
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
    magick -size "${w}x${h}" "xc:${WHITE}" \
      \( "$ANDROID_MARK" -trim +repage -resize "${mark}x${mark}" \) \
      -gravity center -composite \
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

  echo "generated Android launcher + splash from spore-icone-green.png"
}

if [[ "${1:-}" == "--android" ]]; then
  generate_android
  exit 0
fi

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

magick "$RESOURCES/icon.png" -resize 512x512 PNG32:"$STORE/play-icon-512.png"
cp "$RESOURCES/icon.png" "$STORE/app-store-icon-1024.png"

magick -size 1024x500 "xc:${CREAM}" \
  \( "$MARK" -resize 360x360 \) -gravity west -geometry +72+0 -composite \
  -font "$FONT_BOLD" -fill "$INK" -pointsize 86 -gravity west -annotate +500-36 'Spore' \
  -font "$FONT_REG" -fill "$INK" -pointsize 28 -gravity west -annotate +500+42 "L'OS des équipes terrain" \
  PNG24:"$STORE/play-feature-graphic-1024x500.png"

echo "generated iOS + listing brand assets (Android: use --android)"
