# Data inventory — Spore

Status: authoritative for store privacy work (P1.1 / PR2)
Last reviewed: 2026-09-02

This document describes **what the product actually collects and retains**, what account deletion does, and remaining uncertainties. It is the source of truth for Privacy Policy and store declarations (PR2). It is not a legal opinion.

## Roles

- The client establishment is controller of **operational workplace records**.
- FloorPower / Spore is processor of that operational processing, and controller of **platform account, session, and security** data.

## Categories collected

### Account and session

- Email or username, password (hashed), first/last name, user UUID, membership role/status.
- Sessions: refresh/access token digests, user agent, IP (`ip_metadata`), establishment selection.
- Web: HttpOnly refresh cookie + CSRF. Native: refresh token in Capacitor secure storage. Access token in memory only.
- Client leftovers: in-memory observation drafts; `localStorage` observation processing tracker (UX, not the observation body).

### Membership and invitations

- Establishment membership, scopes, invitations (email via Resend when enabled).

### Operational content

- Observation `raw_text`, private photos (`ObservationMedia` / `TemporaryUpload`).
- Comments and mention links.
- Chat messages (7-day hard purge of message rows; conversations may remain empty).
- Signals (title, structured summary from AI), action plans and executions, analytics patterns, gamification ledger (append-only).
- In-app notifications (generic copy; chat titles may include actor display name until rewritten).

### Device

- Microphone: transcription audio is request-scoped and deleted after the request; only text is kept. Native strings: `NSMicrophoneUsageDescription`; Android `RECORD_AUDIO`. Android also declares `POST_NOTIFICATIONS`.
- Photos: private storage, authorized reads, signed preview TTL. Photo UI is `<input type="file" accept="image/...">` without `capture`. iOS WKWebView can still offer Take Photo; `NSCameraUsageDescription` was added as a crash-avoidance qualification.
- Native push: FCM token (`PushDevice`), membership `push_enabled`. Native iOS SPM links **FirebaseCore + FirebaseMessaging only**. Android Gradle: `firebase-messaging` only. The JS `firebase` npm package is present but unused; no `firebase/analytics`. FCM auto-init is disabled on iOS and Android. `GoogleAppMeasurement` appears in iOS `Package.resolved` but is **not linked** and was not in the inspected `.app` binary.
- No geolocation, contacts, biometric, advertising ID, or product analytics SDK.

### Third parties

- **OpenAI** (verified production paths in this repo): observation pipeline (`HOUSTON_AI_OBSERVATION_PROVIDER`), transcription (`HOUSTON_AI_TRANSCRIPTION_PROVIDER`), analytics pattern classifier (`HOUSTON_AI_ANALYTICS_PATTERN_PROVIDER`). Usage metadata in `AIUsageLog` (no prompt/raw output stored locally). Provider retention is **not** controlled in this repo.
- **openai-v1 user consent** (product, PR2): gates observation text pipeline, request-scoped transcription audio, and the analytics pattern classifier (structured signal title / summary / issue_focus, plus duplicate-guard follow-up). Photos and chat are not sent. OpenAI pattern classification is skipped when any source-observation author lacks current consent.
- **Resend**: invitation emails when enabled; content-report operator mail uses the same client and sends **identifiers only** (no UGC body).
- **Firebase Cloud Messaging / APNs**: push delivery. Not Analytics in the current native link set.
- **PostgreSQL, Redis, Railway**: hosting. Railway legal entity US; execution region currently EU West (Amsterdam) as stated on mentions légales.
- No Sentry, no marketing analytics.

### Legal records (PR2)

- `User.terms_version` / `terms_accepted_at` (`cgu-v1`).
- `User.ai_consent_version` / `ai_processing_consented_at` (`openai-v1`).
- `MembershipBlock` (establishment-scoped, symmetric effect on new DMs and new mentions).
- `ContentReport` (persisted; operator e-mail with IDs only).

### Public legal URLs

- Privacy Policy: `https://spore-os.com/politique-de-confidentialite/`
- Terms: `https://spore-os.com/conditions-d-utilisation/`
- Legal notice: `https://spore-os.com/mentions-legales/`
- Account deletion: `https://spore-os.com/supprimer-compte/`

### Logging

- Structured logs with allowlisted extras (IDs, counts). Policy: no raw observation text, comment/chat bodies, media, tokens, full AI prompts.
- Infra log retention (Railway) is **not specified in the repo**.

## Retention already automated (not account deletion)

- Chat messages older than 7 days.
- Orphan `TemporaryUpload` after 24 hours.
- Observation media when the last active CREATED_FROM signal disappears.
- Transcription temp files at end of request.

## Account deletion (implemented)

Initiation: in-app Profil (`/general`) and this public page: `https://spore-os.com/supprimer-compte/`. Email fallback uses the editor address on mentions légales. Target handling time for email requests: **30 days**.

Not a hard `User.delete()` (operational FKs use `PROTECT` on membership).

**Removed or broken**

- Email, names, usable password, login.
- Sessions (including IP / user agent) and push devices.
- Unlinked temporary uploads.
- Recipient notification inbox for that membership.
- Chat messages still present that the user authored (in addition to membership DM teardown).
- Observation text they submitted (replaced by `[contenu retiré]`) and photos on those observations.
- Comment bodies they authored (replaced by `[commentaire retiré]`).
- Chat notification titles that baked their display name (rewritten to the generic actor label).

**User row**

- `status=anonymized`, `is_active=false`, email null, internal unique username not used as public display.
- Public display name: **Compte supprimé**. Membership rows stay for referential integrity (**pseudonymisation**, not anonymity: activity remains joinable by membership id in the database).

**Kept as establishment work**

- Signal and action-plan records, lifecycle events.
- `AIUsageLog` metadata.
- Gamification ledger (append-only; not rewritten).
- Comment/observation **rows** (content tombstoned as above).

**Last owner:** must confirm closing the organization (`archived`) and deactivating its draft/active establishments. Other members lose access via existing org/establishment status checks.

**Last director who is not last owner:** deletion **completes**. Team management still cannot remove the last director. Onboarding activation still requires a director (`missing_active_or_invited_director`).

## Residuals (must be disclosed)

- Names or personal details inside **other people’s** comments or remaining signal AI summaries.
- OpenAI copies of prompts already sent.
- Possible orphan media files if worker and api-web volumes diverge (known deploy limitation).
- Infra logs.

## Absences useful for stores

No advertising, tracking, IDFA/ATT, Web Push, geolocation, or Sign in with Apple.

## Uncertainties (still not facts)

- OpenAI and Railway log retention policies (read current vendor terms at console fill time).
- Exact FCM/SDK device-data practices beyond what this repo links: follow current Firebase documentation when filling Data Safety.
- Whether a given iOS WKWebView build actually presents Take Photo for `<input type="file">` (usage string added as qualification, not as proof that the camera API is always used).
- Session IP: stored as `ip_metadata`. Apple has no dedicated “IP address” collected-data type; see store worksheets. Not used in this repo to infer location.
