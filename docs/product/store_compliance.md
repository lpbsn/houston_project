# Store compliance hors privacy — Spore

Status: worksheet for P1.13 (PR2)
Last reviewed: 2026-09-02

Privacy questionnaires live in [`store_privacy_declarations.md`](store_privacy_declarations.md). This file covers the other store questions that can be prepared from the current product without inventing a moderation platform.

Legend: **fait repo** · **exigence officielle** · **qualification** · **décision produit**.

## Export compliance (Apple)

`ITSAppUsesNonExemptEncryption` = `false` in `Info.plist` (**qualification**).

Apple’s current export-compliance FAQ treats HTTPS / standard encryption as exempt for many apps. Spore’s product encryption in this repo is TLS to the API plus OS secure storage for the native refresh token. No custom crypto library was found in app Swift (**fait repo**). Confirm the checkbox against the [Apple export compliance](https://developer.apple.com/documentation/security/complying-with-encryption-export-regulations) page on submission day (**exigence officielle**).

## User-generated content

**fait repo + décision produit (PR2, store-minimum):**

- Published UGC: observation submit, comments, chat **messages**.
- Not UGC / not CGU-gated: transcription audio (AI consent only).
- CGU version `cgu-v1`, recorded on the user, required before those publishes.
- In-app report persisted (`ContentReport`); operator e-mail with IDs only.
- Block: establishment-scoped, symmetric for **new** DMs and **new** mentions. Existing DM history remains readable. Operational work stays visible. Hide DM ≠ block.

Apple / Google UGC questions: the app **contains** UGC, users can **report**, users can **block** for 1:1 messaging/mentions. There is **no** moderation back-office and **no** automatic filters (**fait repo**). Do not claim 24/7 human moderation.

## Account deletion

Already implemented (PR1): Profil + `https://spore-os.com/supprimer-compte/` (**fait repo**). Use that URL in Play’s deletion-URL field.

## Age / Kids / Made for Kids

Spore is a workplace operations tool, not a kids app (**décision produit** / product positioning). Do not enroll in Designed for Families / Made for Kids.

Apple age rating: **remaining console action**. UGC can contain workplace language. A 12+ / Infrequent/Mild Mature/Suggestive Themes style rating is a common **qualification** for UGC workplace apps, but the questionnaire must be answered in App Store Connect; this repo does not lock a rating number.

## Sign in with Apple / ATT / Health / Tracking

Not applicable on the current binary: email/username auth, no ATT prompt, no HealthKit, `NSPrivacyTracking=false` (**fait repo**).

## Permissions copy (iOS)

- Microphone: transcription of observations (**fait repo**).
- Camera: added because WKWebView file inputs may offer Take Photo (**qualification**). Photo capture is not a native Capacitor Camera plugin in this tree.
- Notifications: remote-notification background mode + FCM (**fait repo**).

## Android

- `RECORD_AUDIO`, `POST_NOTIFICATIONS` (**fait repo**).
- `allowBackup=true` left unchanged (not a store questionnaire item; security follow-up if desired).
- Production HTTPS is a compiled API base URL, not Play’s “all traffic TLS” proof.

## Government / VPN / gambling / tobacco, etc.

Not offered (**fait repo** of product surfaces).

## Manual actions still required in consoles

- Paste Privacy Policy + (Apple) terms URL `https://spore-os.com/conditions-d-utilisation/`.
- Support URL: `https://spore-os.com/support/` (landing deploy). Pack: [`store_listing.md`](store_listing.md).
- Fill App Privacy / Data Safety from the privacy worksheet after an Xcode Privacy Report.
- Confirm encryption exemption checkbox.
- Complete age rating questionnaires.
- App Review / Play App access: [`store_review.md`](store_review.md) (credentials stay off git). Workplace UGC, report+block scope, no public social graph.
