# Store privacy declarations — Spore

Status: authoritative worksheet for App Store Connect / Play Console (PR2)
Last reviewed: 2026-09-02

Source of truth for **what is collected**: [`data_inventory.md`](data_inventory.md). This file maps that inventory to current Apple / Google questionnaire language. It is **not** a prefilled console dump and **not** a legal opinion.

Legend: **fait repo** · **exigence officielle** · **qualification** · **décision produit**.

Privacy Policy URL to paste in both consoles: `https://spore-os.com/politique-de-confidentialite/` (**fait repo**).

Do not treat Firebase Analytics, ATT, IDFA, or HealthKit as present. They were not found in the current native link set (**fait repo**).

## Apple App Privacy / PrivacyInfo

Official definitions: [App Privacy Details](https://developer.apple.com/app-store/app-privacy-details/) (**exigence officielle**). Tracking follows Apple’s ATT definition (third-party advertising / data broker). Spore does not do that (**qualification** from product + binary).

`PrivacyInfo.xcprivacy` in the iOS app:

- `NSPrivacyTracking` = false; empty tracking domains (**qualification**, aligned with no ads SDK).
- `NSPrivacyAccessedAPITypes` empty at **app** level: app Swift (`AppDelegate` / `SceneDelegate`) does not call Required Reason APIs. Capacitor/Firebase ship their own manifests. Do **not** invent `CA92.1` unless a Required Reason API is found in **our** Swift (**fait repo**).
- Collected types declared at app level (all linked, tracking false, purpose App Functionality) (**qualification** from inventory):

| Apple type | Product mapping |
|---|---|
| Email Address | Account email |
| Name | First / last name |
| User ID | User UUID, username |
| Photos or Videos | Observation photos |
| Audio Data | Request-scoped transcription audio (not stored after the request) |
| Other User Content | Observation text, comments, chat, reports |
| Device ID | FCM token when push is enabled |
| Other Diagnostic Data | Session `ip_metadata` / user agent used for session security — Apple has no IP type; [App Privacy Details](https://developer.apple.com/app-store/app-privacy-details/) says to declare IP according to use, not as location if you do not geolocate (**qualification**) |

Do **not** declare Coarse/Precise Location: the repo does not geocode IP or use Core Location (**fait repo**).

Do **not** declare Product Interaction / Advertising / Crash Data: no product analytics, ads, or crash SDK in the current binary (**fait repo**). If Xcode’s privacy report later shows SDK-collected types (especially FCM), add those in the console to match the merged report, do not guess them here.

Third-party “data collection”: OpenAI (observation text, transcription audio, signal title/summary for analytics classifier). **qualification**: service provider for app functionality, not tracking. Confirm OpenAI’s then-current role against Apple’s “third-party partner” wording at fill time.

## Google Data Safety

Official form: Play Console Data safety. Categories below are **qualifications** from the inventory. Re-read Google’s current definitions when filling.

Collects user data: **Yes**.

| Data type (Play wording) | Collected? | Mapping |
|---|---|---|
| Email | Yes | Account |
| Name | Yes | Account |
| User IDs | Yes | User UUID / username |
| Photos | Yes | Observation photos |
| Audio files | Yes, ephemeral | Transcription request only |
| Other user-generated content | Yes | Observations, comments, chat |
| Device or other IDs | Yes | FCM token |
| IP address | Yes | Session `ip_metadata` |
| Approximate / precise location | No | No Core Location / no IP geolocation in repo |
| Advertising ID | No | |
| Crash logs / analytics | No SDK in repo | Railway/server logs exist; they are not a Play app-analytics SDK (**qualification**) |

Purposes: App functionality, Account management, Developer communications (transactional mail / push). Not advertising, not personalization ads, not fraud-unrelated analytics SDK.

Data shared: **qualification, fill after reading Google’s “share” vs “service provider” definitions**.

- OpenAI: processing of observation text, transcription audio, and structured signal title/summary/issue_focus for analytics classification, all behind openai-v1. If Google still treats service providers as “not shared”, mark not shared and disclose in the Privacy Policy (already done). If they require listing AI processors as shared, list OpenAI for App functionality.
- FCM / APNs: push delivery; typically service provider.
- Railway / Postgres / Redis / Resend: hosting and mail; typically service provider.
- Do not list Analytics Measurement: not in the linked binary (**fait repo**).

Encrypted in transit: production API is HTTPS at **build-time URL**, not a runtime ATS lock beyond Capacitor defaults (**fait repo**). Users can delete account in-app (**fait repo**).

## Remaining console-only checks

- Merge Privacy Report in Xcode after an archive and reconcile any SDK types not listed here.
- Re-read OpenAI, Firebase, and Railway DPAs the day of submission.
- `allowBackup=true` on Android is unchanged (security decision, out of this privacy worksheet).
