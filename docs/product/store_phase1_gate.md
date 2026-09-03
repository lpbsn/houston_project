# Store Readiness Phase 1 gate

Status: authoritative  
Last reviewed: 2026-09-03

**Verdict: GO**

The internal Phase 1 gate is met. Remaining work is Store / console / identity operations (Phase 2). Those items are listed below; they do **not** reopen this gate.

Related: [`../deploy/native_release.md`](../deploy/native_release.md) · [`store_listing.md`](store_listing.md) · [`store_review.md`](store_review.md) · [`../roadmap_spore/spore-store-readiness-phase-1-v3.md`](../roadmap_spore/spore-store-readiness-phase-1-v3.md)

Re-audit date: 2026-09-03 on `main` at `0421708` (PR #195–#200 merged). P1.15 / P1.16 live in this file.

## Verdict rules used

- **GO** — repo + product + Release bake are ready enough to start distribution operations.
- **GO_WITH_OPERATOR** — an *internal* gap remains (missing Release proof, declared public URL down, Release-specific Native risk still executable without Apple/Google). Not used here.
- **NO-GO** — a Spore product/mobile/compliance blocker. Not used here.

Store console actions (upload, questionnaires, screenshots, reviewer paste, Closed Testing testers, ADP, association files) never by themselves prevent GO.

## Roadmap questions

### Android

Yes: a Play-ready AAB can be produced reproducibly (`make android-bundle-release`). `applicationId` `app.spore`, `versionCode` 1 / `versionName` `1.0`, `targetSdkVersion` 36 (Play API 36 floor as of 2026-08-31). Listing copy, privacy/compliance worksheets, and live legal URLs exist. Entering Closed Testing does not require a new product or mobile chantier.

### iOS

Yes: remaining significant work depends on the Apple Developer Program / App Store Connect (paid team, production APNs, `aps-environment=production`, archive/IPA, AASA Team ID). In-repo: bundle id `app.spore`, Release `CAPACITOR_DEBUG=false`, usage strings, PrivacyInfo, encryption flag, Associated Domains entitlement, Personal Team `aps-environment=development`.

### Global blind spots

None found that would make Phase 2 premature. Known residual [#181](https://github.com/lpbsn/houston_project/issues/181) (Native refresh wipe on network error) is not a store-prep lot and was not observed as a Release-bake failure. Do not reopen Capacitor lots or PR1–PR5 for it unless a later store binary makes it review-blocking.

## P1.1–P1.14 (re-checked, not reopened)

| Lot | In-repo | Notes |
|-----|---------|--------|
| P1.1 inventory | yes | [`data_inventory.md`](data_inventory.md) |
| P1.2 deletion | yes | API + Profil + `https://spore-os.com/supprimer-compte/` live |
| P1.3 privacy policy | yes | `https://spore-os.com/politique-de-confidentialite/` live |
| P1.4 store privacy worksheets | yes | console fill is Phase 2 |
| P1.5 branding | yes | Native icons/splash + store PNGs; screenshots of usage are Phase 2 capture |
| P1.6 prod Native pin | yes | `NATIVE_RELEASE_ORIGIN=https://app.spore-os.com` |
| P1.7 Firebase/push | yes in repo | local gitignored client files present on this machine; iOS production APNs is Phase 2 |
| P1.8 Android AAB | yes | proven this cycle (see evidence) |
| P1.9 iOS pre-ADP | yes | IPA / paid team Phase 2 |
| P1.10 app links socle | yes | no committed `assetlinks.json` / AASA (correct until identities exist) |
| P1.11 review runbook | yes | credentials stay off git; provisioning is Phase 2 |
| P1.12 listing pack | yes | FR copy + icons; screenshots Phase 2 |
| P1.13 compliance hors privacy | yes | questionnaires in console Phase 2 |
| P1.14 release procedure | yes | this file + [`native_release.md`](../deploy/native_release.md) |

## P1.15 Release Candidate (this cycle)

Existing checks only. No new Make target or gate script.

| Check | Result |
|-------|--------|
| `npm test -- src/lib/native-release-origins.test.ts src/features/landing/app-links-association.isolation.test.ts` | 8 passed |
| `make android-bundle-release` (includes `validate-native-build.mjs` + `validate-native-release-build.mjs` + `cap sync`) | BUILD SUCCESSFUL, ~5.0 MiB AAB |
| AAB / bundle manifest | `package=app.spore`, `versionCode=1`, `versionName=1.0`, `minSdk=24`, `targetSdk=36`; Gradle `validateSigningRelease` + `signReleaseBundle` |
| Baked assets after sync | `https://app.spore-os.com` present; no `http://localhost` / `10.0.2.2` API hosts in copied `assets/public` |
| Public legal URLs | privacy, terms, support, account deletion pages served (2026-09-03) |
| `GET https://app.spore-os.com/api/v1/health/` | HTTP 200 `status: ok` |
| Login on a sideloaded Release APK | **Not run.** Origin pin is already enforced by the existing Release validator. Not an internal-gate gap. |
| iOS App Store archive / physical production push | **N/A Phase 2** (ADP) |
| OS-verified App Links / Universal Links | **N/A Phase 2** (Play App Signing SHA-256 / App Store Team ID) |

`localhost` / `127.0.0.1` **strings** still appear in `runtime-*.js` as the web loopback rewrite set. That is not a baked API URL; `validate-native-release-build.mjs` correctly accepts the bundle.

The AAB is gitignored (`*.aab`). Reproduce with `make android-bundle-release`. Output path: `apps/web/android/app/build/outputs/bundle/release/app-release.aab`.

## Internal gaps remaining

None for this gate.

## Remaining before Store / console actions (Phase 2)

Does **not** change the GO verdict.

**Google Play**

- Create/complete the Play app; upload the AAB; enroll Play App Signing.
- Bump `versionCode` for every subsequent upload.
- Paste listing from [`store_listing.md`](store_listing.md); capture phone screenshots into [`store_assets/`](store_assets/) at listing time.
- Data Safety from [`store_privacy_declarations.md`](store_privacy_declarations.md); content rating / other questionnaires from [`store_compliance.md`](store_compliance.md).
- Closed Testing track (recheck Play Help: personal accounts after 2023-11-13 typically need 12 opted-in testers for 14 consecutive days before production access). Recheck at upload time.
- After Play lists App Signing certs: commit real `apps/web/public/.well-known/assetlinks.json` and redeploy web.
- Optional for Closed Testing push: `HOUSTON_PUSH_ENABLED` + `HOUSTON_FCM_SERVICE_ACCOUNT_JSON` on Railway.

**Apple**

- Apple Developer Program; switch off Personal Team `PBJM37TNDU`.
- Enable Push + Associated Domains on the App ID; `aps-environment=production`; APNs `.p8` in Firebase.
- Archive/upload from Xcode; App Privacy from the worksheet after an Xcode Privacy Report; age rating and encryption checkbox in App Store Connect.
- Publish AASA with the **App Store** Team ID (not Personal Team); redeploy web.
- Paste App Review notes from [`store_review.md`](store_review.md) (credentials off git).

**Both**

- Operator sandbox on production (staff login, fictional workplace data) before first review — [`store_review.md`](store_review.md).
- Do not commit secrets, invite codes, or reviewer passwords.
