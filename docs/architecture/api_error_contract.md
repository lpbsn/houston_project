# API Error Contract (standardized error envelope)

Status: authoritative
Last reviewed: 2026-06-02

## Purpose

This document defines the mandatory error response shapes emitted by the global DRF exception handler:

- [`apps/api/houston/core/api/exceptions.py`](apps/api/houston/core/api/exceptions.py) (`api_exception_handler`)

The contract is used for framework-level errors (auth, permissions, not-found, throttling, validation) and is intentionally stable so that the frontend can render predictable user-facing and developer-facing states.

## Canonical response shapes

### 1) Framework errors (most cases)

```json
{
  "code": "not_authenticated",
  "detail": "Invalid credentials."
}
```

Notes:
- `code` is a short snake_case string identifying the error category.
- `detail` is a user-safe string.
- `errors` is not present unless this is a validation envelope (next section).

### 2) Validation errors

```json
{
  "code": "validation_error",
  "detail": "Request validation failed.",
  "errors": {}
}
```

Notes:
- `errors` is a dictionary (possibly nested) containing the field-level details.
- The handler normalizes DRF validation error payloads into the `errors` object.

## Supported `code` values (current implementation)

- `validation_error`: request validation failed (includes `errors`).
- `not_authenticated`: request requires authentication (e.g. login/refresh failures with generic messaging).
- `authentication_failed`: authentication credentials were provided but invalid (e.g. malformed or expired access token).
- `permission_denied`: authenticated user is not allowed to perform the action.
- `not_found`: resource not visible / outside scope.
- `throttled`: rate limited (429).
- `internal_error`: unexpected server failure (safe generic message).
- `api_error`: fallback category for other DRF/API exceptions.

## Throttling (429) shape

When DRF throttling is triggered, the response must match:

```json
{
  "code": "throttled",
  "detail": "Request was throttled. Expected available in N seconds."
}
```

## Security invariants (especially for login)

For login-like failures:
- the `detail` must be generic (e.g. “Invalid credentials.”)
- the response must not reveal whether an identifier exists, whether the password was wrong, whether the account is inactive, or whether membership is missing

This is enforced by product policy and validated by backend tests.

## Documentation debt / OpenAPI drift (explicit)

Some endpoints may still be annotated in OpenAPI using only a plain `detail` schema (historical `DetailResponse`).
At runtime, the global handler still normalizes framework exceptions into the standardized `{ code, detail }` / validation envelope shapes.

Frontend integration should rely on `code` + `detail` when present, and treat `detail` as the user-safe message.

