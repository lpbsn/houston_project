Charte minimale recommandée
# Houston Authentication Charter

## 1. Purpose

This document defines the mandatory authentication and session rules for Houston.

Authentication is security-critical. Any change touching login, logout, tokens, sessions, bootstrap, permissions, memberships, or frontend auth state must follow this charter.

## 2. Architecture decision

Houston uses API-first token-based authentication.

The current MVP auth model is:

- short-lived opaque bearer access token
- access token stored only in frontend memory
- rotating opaque refresh token
- refresh token stored in an HttpOnly cookie for web clients
- refresh token returned explicitly and persisted through a secure-store port for native clients
- refresh token stored as a digest in the database
- backend `UserSession` as the source of truth
- backend-owned permissions and visibility

Houston does not use Django template-based login pages for product UI.

## 3. Forbidden

Never:

- store access tokens in localStorage
- store refresh tokens in localStorage
- store tokens in sessionStorage
- store raw access or refresh tokens in the database
- use JWT for MVP auth
- put permissions or memberships as frontend authority
- use Zustand for auth or server state
- expose whether an email or username exists during login failure
- compare passwords manually
- bypass Django password hashing
- implement product UI login with Django templates
- expose password hashes, token digests, session internals, or internal security metadata in API responses

## 4. Token rules

Access token:

- opaque random token
- short-lived
- TTL: 15 minutes
- returned in login and refresh JSON responses
- sent as `Authorization: Bearer <access_token>`
- stored only in React memory
- persisted only as `AccessToken.token_digest`

Refresh token:

- opaque high-entropy random token
- stored raw only in the browser HttpOnly cookie (Web) or the injected secure native store (Native)
- stored as `SessionRefreshToken.token_digest` in the database
- rotated on every refresh
- previous refresh token invalidated immediately
- reuse of an old refresh token revokes the token family and session
- `refresh_token_transport` (`cookie` or `body`) describes credential transport only; it is never runtime proof, a trust level, or an authorization input

Refresh token cookie:

- name: `houston_refresh_token`
- HttpOnly: true
- Secure: true in production
- SameSite: `Lax`
- Path: `/api/v1/auth/`
- never readable by JavaScript

## 5. Backend persistence model

The backend must track auth state with:

- `UserSession`
- `AccessToken`
- `SessionRefreshToken`

Required concepts:

- user
- refresh token family id
- token digests only
- explicit status and revoked timestamps
- last used timestamp
- access expiry
- refresh expiry
- absolute session expiry
- selected establishment for the current auth session
- light user-agent metadata
- minimal optional IP metadata

Expiration is timestamp-first:

- access token validity comes from `AccessToken.expires_at`
- refresh token validity comes from `SessionRefreshToken.expires_at`
- session validity comes from `UserSession.refresh_expires_at` and `UserSession.absolute_expires_at`
- status may be updated opportunistically, but runtime auth checks must not rely only on status

## 6. Required endpoints

Required MVP endpoints:

- `GET /api/v1/auth/csrf/` — sets the CSRF cookie and returns `csrf_token` in JSON
- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/refresh/`
- `POST /api/v1/auth/logout/`
- `GET /api/v1/auth/bootstrap/`
- `POST /api/v1/auth/switch_establishment/`

Login must:

- accept email or username identifier
- return access token
- return access token expiry
- return bootstrap payload
- require an explicit refresh transport
- enforce CSRF and set only an HttpOnly refresh cookie for `cookie`
- omit cookies and return refresh token + expiry in JSON for `body`

Refresh must:

- use only the explicitly selected refresh transport
- for `cookie`: require CSRF, read and rotate only the refresh cookie
- for `body`: require the refresh in JSON, omit CSRF, never read or modify cookies
- validate refresh token digest and timestamps
- rotate refresh token
- return new access token
- revoke token family on reuse

Logout must:

- prefer a valid bearer token to identify the current session
- for `cookie`: require CSRF, fall back only to the cookie, and clear that cookie
- for `body`: fall back only to an explicit JSON refresh token and never read, set, or clear cookies
- remain safe and idempotent

Bootstrap must return:

- authenticated boolean
- public user fields
- `memberships`
- `active_membership` from the current auth session selected establishment when valid

Switch establishment must:

- require bearer auth
- store selected establishment on `UserSession`
- validate active user, active membership, active establishment, and active organization
- fail closed for invalid, foreign, or inactive establishments
- return bootstrap payload for the updated auth session

Bootstrap is authenticated-only:

- unauthenticated requests return `401`
- authenticated requests return `BootstrapResponse`

## 7. CSRF rules

Cookie-transport auth mutation endpoints must enforce CSRF:

- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/refresh/`
- `POST /api/v1/auth/logout/`

`SameSite=Lax` is defense in depth, not the primary CSRF control.

The Web transport must:

- call `GET /api/v1/auth/csrf/` before login when needed
- read `csrf_token` from the JSON response (do not read `document.cookie`)
- send `X-CSRFToken` on login, refresh, and logout
- keep the refresh token in the HttpOnly cookie only

The body transport must:

- send `credentials: omit` (or an equivalent that actively excludes cookies)
- never depend on the CSRF cookie or header
- persist a rotated refresh before installing access token or authenticated state
- fail closed and clear/revoke best-effort if refresh persistence fails
- never persist refresh in localStorage or sessionStorage

Frontend session replacement must:

- serialize cookie-backed session creation so `Set-Cookie` responses cannot overtake one another
- reject stale body responses before writing their refresh token
- treat any stale cookie response after logout as fail-closed and clear it best-effort
- never restore a previous refresh cookie in JavaScript

Local Docker + Vite development:

- `VITE_API_BASE_URL` is the explicit API host. When empty, relative `/api` paths plus the Vite proxy remain valid
- in Web runtime only, when both the page and configured API hostnames are local loopbacks (`localhost` or `127.0.0.1`), the API hostname is aligned with the page hostname so `SameSite=Lax` cookies remain same-site; protocol and port stay configured
- when using the Vite `/api` proxy, preserve the browser host instead of rewriting it to the internal container hostname
- configure `HOUSTON_CLIENT_ORIGINS` explicitly for local frontend origins such as `http://localhost:5173` and `http://127.0.0.1:5173`
- origin allowlisting permits CORS and CSRF origin checks but does not cause browsers to attach cross-site cookies
- Django `CSRF_TRUSTED_ORIGINS` is derived from the http(s) entries of that list; do not set it separately
- do not use wildcard client origins for local convenience

## 8. Frontend rules

React is a thin client.

Allowed:

- keep access token in memory
- use TanStack Query for bootstrap and auth-related server state
- retry once after 401 by calling refresh
- redirect unauthenticated users to `/login`
- display user and membership data from bootstrap

Forbidden:

- storing auth tokens in localStorage or sessionStorage
- storing auth authority in Zustand
- storing selected establishment in localStorage, sessionStorage, or Zustand
- trusting frontend permissions for backend access
- decoding tokens for permissions
- hardcoding role or domain access rules as security logic

## 9. Authorization boundary

Frontend visibility is UX only.

Backend must enforce:

- identity
- active user status
- active session
- active membership
- role permissions
- operational domain visibility
- establishment scoping

Tokens never grant business permissions by themselves.

## 10. Error handling

Login-like failures must return the generic error contract defined in [`api_error_contract.md`](api_error_contract.md) (see `{ code, detail }`).

```json
{
  "code": "not_authenticated",
  "detail": "Invalid credentials."
}
```

Do not reveal:

- whether identifier exists
- whether password was wrong
- whether account is inactive
- whether membership is missing

Detailed reasons may be logged internally with safe metadata only.

## 11. Tests required

Any auth change must include tests for:

- valid login
- invalid login generic error
- access token authentication
- CSRF enforcement on login, refresh, and logout
- refresh token rotation
- old refresh token reuse detection
- logout revocation
- bootstrap unauthenticated returns `401`
- bootstrap authenticated
- switch establishment success
- switch establishment invalid/foreign/inactive fails closed
- inactive or suspended user rejection
- inactive memberships excluded
- no sensitive fields leaked

## 12. OpenAPI

All auth endpoints must be documented through DRF and drf-spectacular.

After auth API changes, run:

- `make schema`
- `cd apps/web && npm run api:generate`

Generated frontend OpenAPI types must not be edited manually.

## 13. Auth throttling (Batch 3) + Security TODOs

Auth throttling for public auth mutation endpoints is implemented via DRF `ScopedRateThrottle` when `HOUSTON_AUTH_THROTTLE_ENABLED=true` (default).

### Protected endpoints

- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/refresh/`
- `POST /api/v1/auth/register/`
- `POST /api/v1/auth/register/validate-owner/`
- `POST /api/v1/invitations/{token}/accept/`

### Throttling response contract (429)

```json
{
  "code": "throttled",
  "detail": "Request was throttled. Expected available in N seconds."
}
```

### Cache / storage strategy

- Dedicated Redis DB for throttle counters: DB `/3` in prod / non-DEBUG (derived from `REDIS_URL`).
- Optional override: `HOUSTON_CACHE_REDIS_URL` to point to a dedicated Redis DB.
- DEBUG fallback: `LocMemCache` when no explicit Redis URL is provided.

### Configuration (override quotas)

- `HOUSTON_AUTH_THROTTLE_ENABLED`
- `HOUSTON_CACHE_REDIS_URL`
- `HOUSTON_THROTTLE_AUTH_LOGIN`
- `HOUSTON_THROTTLE_AUTH_REFRESH`
- `HOUSTON_THROTTLE_AUTH_REGISTER`
- `HOUSTON_THROTTLE_AUTH_REGISTER_VALIDATE`
- `HOUSTON_THROTTLE_AUTH_INVITATION_ACCEPT`

### Known intentional debts (post-MVP)

- throttling is IP-only
- no fingerprint per identifier
- no throttling by refresh-cookie hash
- Redis shared requirement in prod multi-worker

### Remaining security TODOs

- add suspicious token reuse monitoring and alerting

## 14. WebSocket authentication (Chat V1)

Chat V1 is the first WebSocket surface. It uses a **different auth path** from REST bearer tokens.

### Architecture rules

- **Do not use `AuthMiddlewareStack`** or Django session auth for Chat WebSocket.
- Product WebSocket auth must not depend on session cookies or implicit `scope["user"]` from Django auth middleware.
- Use `OriginValidator` against `HOUSTON_CLIENT_ORIGINS` before the consumer.
- `ALLOWED_HOSTS` validates the HTTP `Host` header only; it is not a browser-origin allowlist.
- Native origins such as `capacitor://localhost` are added in Lot 5, not here.

### Ticket-based WebSocket auth (mandatory for Chat V1)

1. Client obtains a short-lived ticket through authenticated REST :

```
POST /api/v1/establishments/{establishment_id}/chat/ws-ticket/
Authorization: Bearer <access_token>
```

2. Response :

```json
{
  "ticket": "<opaque-one-time-token>",
  "expires_in": 60
}
```

3. Client opens WebSocket **without** token in the URL :

```
/ws/v1/establishments/{establishment_id}/chat/
```

4. First message must be :

```json
{
  "type": "auth",
  "ticket": "<opaque-one-time-token>"
}
```

5. Consumer validates ticket, marks it used, loads user/session/membership/establishment, then responds `auth.ok` or closes with an auth error.

### Ticket properties

- opaque random token
- TTL about 60 seconds
- one-time use (atomic consume in Redis)
- scoped to `user_id`, `session_id` (when available), `establishment_id`, and `membership_id`
- stored in Redis (or dedicated cache) as digest/metadata only — not business truth
- invalidated immediately after successful use

### Forbidden for WebSocket auth

- long-lived access or refresh tokens in the WebSocket URL
- refresh token flow over WebSocket
- storing WebSocket tickets in `localStorage` or `sessionStorage`
- bypassing REST membership/establishment/`chat_enabled` checks at ticket issuance
- `AuthMiddlewareStack` as the primary Chat auth mechanism

### Ticket issuance checks (fail closed)

- user active (not suspended)
- active membership in the establishment
- active establishment and organization
- `chat_enabled=True`
- URL `establishment_id` matches session-selected active membership context

### Consumer auth timeout

- If no valid `auth` message within a short window (about 5 seconds), close the connection (code `4408`).

### Tests required for WebSocket auth changes

- valid ticket auth
- expired ticket rejected
- reused ticket rejected
- wrong establishment rejected
- inactive membership / suspended user / chat disabled rejected
- missing or late auth message closes connection
- origin/host rejection when invalid
- live session revocation via `chat_session_{session_id}` group after auth (`access.revoked` + close)

### Live session revocation (post-auth)

- After successful WS auth, the consumer joins `chat_session_{session_id}` where `session_id` comes from the ws-ticket payload (same `UserSession` as the REST access token).
- `revoke_session` and `switch_selected_establishment` schedule `access.revoked` to that session group only (establishment switch does **not** use membership-wide groups).
- This is transport-only (Channels/Redis) ; `UserSession` in PostgreSQL remains the auth source of truth.
