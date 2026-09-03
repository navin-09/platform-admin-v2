# API Standards

The contract every endpoint in this repo follows. `AGENTS.md` carries the short version; this file
is the full reference. `docs/api.md` shows the same rules applied end-to-end on the Users resource.

## 1. The envelope

Every response — every method, success or error — is the same three fields (schema `ApiResponse`
in `app/schemas/common.py`):

```json
{
  "code": "S_201_USR_CREATED",
  "message": "User created successfully",
  "data": { "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "name": "Arun Kumar" }
}
```

| Field | Type | Rule |
|-------|------|------|
| `code` | string | Machine-readable result code (§2). Always present. |
| `message` | string | Human-readable; safe for logs or (translated) UI. Never null. |
| `data` | object / array / null | The payload. `null` when there is nothing to return (e.g. DELETE). Always send the key — never omit it. |

`data` shape by method:

| Method | `data` shape |
|--------|--------------|
| GET (list) | `ListData`: `{ "data": [...], "pagination": {...} }` (§7) |
| GET (single) | the resource object |
| POST | the created resource object |
| PUT / PATCH | the updated resource object |
| DELETE | `null` |

## 2. Result codes

`code` packs the status, the HTTP status, and the business meaning into one string:

```
S   _   201   _   USR_CREATED
↑        ↑          ↑
status   http       business code
```

| Segment | Values | Notes |
|---------|--------|-------|
| Status prefix | `S` success, `W` warning, `E` error | Always one letter, first segment. |
| HTTP code | `200`, `201`, `400`, `404`, `409`, `422`, `500`, ... | Mirrors the actual HTTP response status. |
| Business code | `USR_CREATED`, `USR_NOT_FOUND`, `VALIDATION_FAILED`, ... | Everything after the second underscore. Distinguishes same-HTTP outcomes (`USR_NOT_FOUND` vs `ROL_NOT_FOUND` — both 404). |

Business codes are `RESOURCE_OUTCOME` in upper snake case. Each resource owns a prefix —
`USR_`, `ROL_`, `SCR_`, `AUTH_`, `AUDIT_`, `EXPORT_`, `HEALTH_` — so codes never collide.

**Where codes live** (rule 6 in `docs/standards.md`):

- Success codes: `CODE_*` / `MSG_*` constants in the schema module of the resource that returns
  them (`app/schemas/user.py`, `app/schemas/role.py`, ...).
- Error codes: declared on their `AppError` subclasses in `app/exceptions/exceptions.py`.

**Codes are a public contract.** Never rename or reuse one once clients depend on it — add a new
class / constant instead.

Standard error codes (all in `app/exceptions/exceptions.py`):

| `code` | HTTP | When |
|--------|------|------|
| `E_401_NOT_AUTHENTICATED` | 401 | Missing/invalid auth token |
| `E_401_AUTH_INVALID_CREDENTIALS` | 401 | Bad credentials at login |
| `E_403_FORBIDDEN` | 403 | Authenticated but lacks the permission |
| `E_404_{RES}_NOT_FOUND` | 404 | Resource doesn't exist (`E_404_USR_NOT_FOUND`, `E_404_ROL_NOT_FOUND`, ...) |
| `E_409_CONFLICT` / `E_409_{RES}_...` | 409 | Uniqueness or state conflict (`E_409_USR_EMAIL_EXISTS`, `E_409_USR_LAST_ADMIN`, `E_409_PROTECTED_RESOURCE`) |
| `E_422_VALIDATION_FAILED` | 422 | Well-formed request that breaks business/validation rules |
| `E_429_AUTH_OTP_THROTTLED` | 429 | Rate limit exceeded |
| `E_500_INTERNAL_ERROR` | 500 | Unhandled server error |
| `E_503_HEALTH_DOWN` | 503 | A dependency is down |

## 3. Warnings — the `W_` prefix

`W_` marks a request that **succeeded** but whose side effect failed — the client should still
flag something to the user:

```json
{
  "code": "W_201_USR_CREATED_EMAIL_FAILED",
  "message": "User created, but the welcome email could not be sent",
  "data": { "id": "3fa85f64-...", "name": "Arun Kumar" }
}
```

No current endpoint emits `W_`; reach for it the moment a success can carry a failed side effect.

## 4. Errors

Services raise typed `AppError` subclasses; the global handlers
(`app/exceptions/exception_handlers.py`) shape them into the envelope. Handlers never build error responses by hand and
never try/except what the global layer already covers. **Raise, don't return** — a lookup that
finds nothing raises; callers never check for `None`.

Field-level detail rides in `data.errors`, built with `field_errors([("field", "issue")])`:

```json
{
  "code": "E_422_VALIDATION_FAILED",
  "message": "Validation failed",
  "data": {
    "errors": [ { "field": "email", "issue": "Email is already registered" } ]
  }
}
```

## 5. URLs and naming

- **Versioned prefix**: every route mounts under `/api/v1` (`app/api/router.py`).
- **Plural nouns, no verbs**: `/users`, never `/getUsers`.
- **kebab-case** for multi-word path segments: `/order-items`.
- **snake_case JSON fields**: the DTO field names *are* the wire names — `created_at`,
  `total_items` (this repo's convention; it keeps Python and wire names identical).
- **Path `id` params are UUIDs**: `/users/{id}` with a `uuid.UUID`.

## 6. Standard method set per resource

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/resource` | List — paginated, filterable |
| POST | `/resource` | Create |
| GET | `/resource/{id}` | Read one |
| PUT | `/resource/{id}` | Full replace (complete body required) |
| PATCH | `/resource/{id}` | Partial update (only provided fields change) |
| DELETE | `/resource/{id}` | Soft delete — sets `status = inactive`, never removes rows |

## 7. Pagination

List endpoints take `page` and `limit` query params, bounded by the shared constants in
`app/core/constants.py` (`MIN_PAGE`, `DEFAULT_PAGE = 1`; `DEFAULT_PAGE_SIZE = 20`,
`MAX_PAGE_SIZE = 100`), and wrap items with `ListData` via `build_list_data(...)`:

```json
"data": {
  "data": [ ... ],
  "pagination": { "page": 1, "limit": 20, "total_items": 134, "total_pages": 7 }
}
```

The inner `data` array sits inside the envelope's `data` — that nesting is intentional.

## 8. Auth and headers

All endpoints require a Bearer JWT unless explicitly public, and business endpoints declare the
permission that guards them (`require_permission(PermissionName.USERS_READ)` etc.):

| Header | Direction | Notes |
|--------|-----------|-------|
| `Authorization: Bearer <token>` | Request | Required unless public |
| `Content-Type: application/json` | Request/Response | Required on bodies |
| `X-Request-ID` | Request/Response | Correlation ID (`HEADER_REQUEST_ID`); the request-context middleware records it — echo it back |

## 9. Where each piece lives in code

| Contract piece | Code |
|----------------|------|
| Envelope | `ApiResponse` — `app/schemas/common.py` |
| List wrapper + pagination | `ListData`, `build_list_data` — `app/schemas/common.py` |
| Success codes/messages | `CODE_*` / `MSG_*` — `app/schemas/{resource}.py` |
| Error codes | `AppError` subclasses — `app/exceptions/exceptions.py` |
| Pagination bounds | `app/core/constants.py` |
| Auth / permission gate | `require_permission` — `app/api/deps.py` |
| Field bounds | `app/utils/limits.py` (see AGENTS.md, "bounded fields") |

`response_model=ApiResponse[...]` on every route keeps the auto-generated OpenAPI spec
(`/docs`, `/openapi.json`) truthful — FastAPI generates it; there is no hand-maintained YAML.

## 10. Adding or changing an endpoint — checklist

1. **DTOs + codes** in `app/schemas/{thing}.py`: request/response models (bounds from
   `app/utils/limits.py`), `CODE_*`/`MSG_*` for each new success outcome.
2. **Service function** in `app/services/{thing}_service.py`: the business rules; raises
   `AppError` subclasses instead of returning nulls/sentinels.
3. **Thin handler** in `app/api/v1/{thing}.py`: parse → one service call → `ApiResponse`, with
   `response_model=ApiResponse[...]` and `require_permission(...)`.
4. **List endpoints**: paginate with `build_list_data` and the constants from
   `app/core/constants.py`.
5. **Tests**: service unit tests (repository faked) + API tests (`create_app()` + `TestClient`,
   `get_db` overridden) — 95% gate on services + repositories.
6. **Before committing**: `uv run ruff check . && uv run ruff format --check . && uv run mypy app
   && uv run pytest`.
