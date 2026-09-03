# Store review — Spore (P1.11)

Status: operator runbook + console templates  
Last reviewed: 2026-09-03

Secrets (passwords, invite codes) stay **out of git**. This file uses placeholders only.

Related: [`store_listing.md`](store_listing.md) · [`store_compliance.md`](store_compliance.md) · [`store_privacy_declarations.md`](store_privacy_declarations.md)

## Constraints (product, not optional)

The store binary talks to `https://app.spore-os.com`.

- Owner registration needs a valid `HOUSTON_REGISTRATION_INVITE_CODES` value on Railway. Empty list → registration rejected.
- After register, the owner must finish draft onboarding and invite a **director** (distinct person) before the establishment can activate.
- Operational data is establishment-scoped. A reviewer with no active membership on an active establishment cannot exercise the core loop.
- Publishing observations / comments / chat requires CGU `cgu-v1`. Transcription and the AI observation pipeline require in-app consent `openai-v1`.
- The observation → signal path needs a running Celery worker and the production AI configuration. An empty signal feed is a review risk, not a store-metadata problem.
- There is **no** in-app demo mode and **no** production seed command. Do not run `provision_konoha_*` on a non-local host. KONOHA is local/dev only.

Apple 2.1 and Play App access: the reviewer must sign in without waiting on the developer during review.

## Reviewer path (recommended)

Give reviewers a **staff** login on an already **activated** establishment with a few fictional workplace items visible (observation, signal, action plan). They should **not** register, complete onboarding, or use personal data.

Optional second login (manager or director) only if you want them to see a higher-privilege surface. One staff account is enough for the core loop.

## Operator checklist (before first submission)

Do this once on production. Store credentials in your private notes, not in this repo.

1. Confirm Railway: invite codes set, Celery worker running, OpenAI configured if you want transcription/AI reviewed.
2. Register an owner with the invite code. Use fictional identity and a mailbox you control.
3. Complete the onboarding wizard (activity description, units, subjects, team).
4. Invite a director at a second mailbox you control; accept the invite; activate the establishment.
5. Create one or two staff/manager seats (fictional workplace names). Accept CGU and OpenAI consent on **every** account you will hand to stores.
6. As staff, submit a few observations and leave at least one signal and one action plan visible so the feed is not empty. Use workplace wording, not KONOHA / anime names.
7. Sign out, sign in on a clean session with the **staff** credentials you will paste in the consoles. Walk observation → signal → plan without help.
8. Confirm account deletion remains reachable from Profil (reviewers must not need it, but stores ask).

If step 7 fails, do not submit. Fix production or the sandbox, then retry.

## App Review Information (Apple) — paste

```
Spore is a workplace operations app for a single establishment, not a public social network.

Sign in with the demo staff account below. Do not create a new account (owner signup is invite-gated and requires completing onboarding plus a director invite).

Username / email: [REDACTED — operator]
Password: [REDACTED — operator]

After login you should see the establishment feed. Core loop: capture an observation (text is enough; microphone is for optional transcription), then open the resulting signal and action plan.

UGC: observations, comments, chat. Users can report content and block a colleague for new DMs and new mentions. There is no moderation back-office and no public graph.

Permissions: microphone (transcription), camera (WKWebView photo picker), notifications (optional). No location, no tracking ATT, no Sign in with Apple.

Support: https://spore-os.com/support/
Privacy: https://spore-os.com/politique-de-confidentialite/
```

## App access (Play Console) — paste

Same facts. Restricted features: **all operational screens** are behind login.

```
All operational features require sign-in.

Use this demo staff account (do not register):
Username / email: [REDACTED — operator]
Password: [REDACTED — operator]

The establishment is already active with sample workplace data. Accept any in-app terms / AI consent prompts if they appear (they should already be accepted on this account).

Support: https://spore-os.com/support/
```

## What not to do

- Commit passwords or invite codes.
- Hand reviewers a raw invite code and expect them to finish onboarding unaided.
- Point reviewers at KONOHA or `@konoha` accounts.
- Claim 24/7 human moderation (see [`store_compliance.md`](store_compliance.md)).
