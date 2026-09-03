# Native release V1 (Android AAB + iOS pre-ADP)

Status: authoritative  
Last reviewed: 2026-09-03

Manual, reproducible path from this repo to a **Play-ready Android App Bundle**. No Fastlane, no CI `cap sync`, no store upload automation.

Daily Native development stays on `make web-cap-sync` and the repo-root `.env` (loopback API). **Never** use that target for a store artefact.

## Production Native config

Store builds pin both Vite origins to the public nginx host (same `/api/` and `/ws/` as the web app):

```text
VITE_API_BASE_URL=https://app.spore-os.com
VITE_PUBLIC_APP_URL=https://app.spore-os.com
```

`make web-cap-sync-release` exports these **before** Vite so they override `.env`. `scripts/validate-native-release-build.mjs` then requires that origin in `dist-native/` and rejects baked loopback API URLs (`http://localhost`, `10.0.2.2`, …).

## Operator prerequisites

Keep these **off git**. Backup the keystore offline; losing the upload key blocks Play updates until Play’s reset process.

| Item | Local path |
|------|------------|
| Android upload keystore | `apps/web/android/upload-keystore.jks` (or the `storeFile` you set) |
| Gradle signing file | `apps/web/android/keystore.properties` (copy [`apps/web/android/keystore.properties.example`](../../apps/web/android/keystore.properties.example)) |
| Firebase Android | `apps/web/android/app/google-services.json` |
| Firebase iOS | `apps/web/ios/App/App/GoogleService-Info.plist` |

`bundleRelease` **fails** if `keystore.properties`, the store file, or `google-services.json` is missing. That is intentional: AGP would otherwise sign Release with the debug keystore, and skip FCM.

Generate an upload keystore once (RSA 2048+):

```bash
keytool -genkeypair -v -keystore apps/web/android/upload-keystore.jks \
  -alias upload -keyalg RSA -keysize 2048 -validity 10000
```

Railway (already required for Native CORS): `HOUSTON_CLIENT_ORIGINS` includes `capacitor://localhost` and `https://localhost`. `DJANGO_ALLOWED_HOSTS` includes `app.spore-os.com`. For Closed Testing push: `HOUSTON_PUSH_ENABLED` plus `HOUSTON_FCM_SERVICE_ACCOUNT_JSON` on `api-web` and `celery-worker`. APNs `.p8` stays in the Firebase console and needs the Apple Developer Program.

## Android AAB

```bash
make android-bundle-release
```

`make android-bundle-release` runs `web-cap-sync-release` then `./gradlew :app:bundleRelease`. Output:

`apps/web/android/app/build/outputs/bundle/release/app-release.aab`

Before the first Play upload:

- Confirm `applicationId` is `app.spore`.
- Bump `versionCode` in [`apps/web/android/app/build.gradle`](../../apps/web/android/app/build.gradle) for **every** AAB you upload. `versionName` is manual (`1.0`, `1.0.1`, …). Do not sync `apps/web/package.json`.
- Upload the `.aab` (not an APK) in Play Console. First time: enroll **Play App Signing** (this keystore is the upload key).
- Closed Testing for a recent personal Play account (tester count / duration) is a **console** operation. Recheck Play Help at upload time.

## App Links / Universal Links (identities, not the Native handler)

The Capacitor handler, Android `autoVerify` host `app.spore-os.com`, and iOS Associated Domains entitlement are already in the repo. **Verified** OS association is a **console** follow-up.

### Android (`assetlinks.json`)

Production reference: **Play App Signing** certificate SHA-256 fingerprints (all of them Play lists for this app — some Play apps have more than one app-signing cert). Copy the Digital Asset Links snippet from Play Console (Play App Signing / App integrity). Put the real JSON at `apps/web/public/.well-known/assetlinks.json` and **redeploy the web** host. Do not use placeholders. Do not treat the upload-key fingerprint as the Play target. You may add the upload-key SHA-256 to the same `sha256_cert_fingerprints` array later so a sideloaded Release can verify; that does not replace Play certs. Never add the debug certificate.

Until that Play snippet exists, leave the file **unpublished**. nginx 404 on `/.well-known/assetlinks.json` is correct.

### iOS (`apple-app-site-association`)

Keep the existing `applinks:app.spore-os.com` entitlement. Do **not** publish an AASA with Personal Team `PBJM37TNDU`. After the Apple Developer Program, use the Team ID that will ship on the App Store, enable Associated Domains on the App ID, then host AASA on `app.spore-os.com` (modern `appIDs` + `components`). Until then, nginx 404 on `/.well-known/apple-app-site-association` is correct.

## iOS (as far as this repo can go without ADP)

Ready in-repo: bundle id `app.spore`, Release `CAPACITOR_DEBUG=false` ([`apps/web/ios/release.xcconfig`](../../apps/web/ios/release.xcconfig)), usage strings, `ITSAppUsesNonExemptEncryption`, PrivacyInfo collected-data types, Associated Domains `applinks:app.spore-os.com`, `aps-environment=development` for the Personal Team.

Place `GoogleService-Info.plist` locally before an Xcode Release compile. Do **not** export an App Store IPA here.

After Apple Developer Program (Phase 2, not this procedure):

1. Switch the Xcode team from Personal Team `PBJM37TNDU` to the paid team.
2. Enable Push Notifications and Associated Domains on the App ID.
3. Set `aps-environment` to `production` for store builds.
4. Upload an APNs `.p8` to Firebase.
5. Archive / upload from Xcode (App Store Connect). TestFlight is optional.

Universal Links E2E and Play-verified App Links remain **identity** work (section above), not this AAB procedure.

## Explicitly not in this path

CI publication, Fastlane, secret managers, R8/minify, changing `app.spore`, App Store export. Store listing copy, review notes, and brand assets: [`docs/product/store_listing.md`](../product/store_listing.md), [`docs/product/store_review.md`](../product/store_review.md), [`docs/product/store_assets/`](../product/store_assets/).

Capacitor Lot 11 CI `cap sync` remains deferred. This file is the local store-build procedure only.
