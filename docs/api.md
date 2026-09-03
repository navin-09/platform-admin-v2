# API Reference — Users

**Base URL:** `http://127.0.0.1:8000/api/v1`
Every endpoint requires `Authorization: Bearer <token>` and the stated permission. All responses
use the standard envelope `{ "code", "message", "data" }` — the contract is defined in
`docs/api-standards.md`; this file is the worked example.

Ids are UUIDs; JSON fields are snake_case; timestamps are ISO 8601 UTC.

---

## 1. Create User — `POST /users`

Permission: `USERS_WRITE`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name |
| `email` | string | Yes | Valid, globally unique email |
| `password` | string | Yes | Password policy applies |
| `status` | string | No | `active` (default) or `inactive` |

```http
POST /api/v1/users HTTP/1.1
Authorization: Bearer eyJhbGciOi...
Content-Type: application/json

{ "name": "Arun Kumar", "email": "arun.kumar@example.com", "password": "S3cureP@ss" }
```

**`201 Created`**

```json
{
  "code": "S_201_USR_CREATED",
  "message": "User created successfully",
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Arun Kumar",
    "email": "arun.kumar@example.com",
    "status": "active",
    "created_at": "2026-01-15T09:30:00Z",
    "updated_at": "2026-01-15T09:30:00Z"
  }
}
```

**Errors:** `E_422_VALIDATION_FAILED` (422, field detail in `data.errors`) ·
`E_409_USR_EMAIL_EXISTS` (409) · `E_401_NOT_AUTHENTICATED` (401) · `E_403_FORBIDDEN` (403) ·
`E_500_INTERNAL_ERROR` (500)

---

## 2. List Users — `GET /users`

Permission: `USERS_READ`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | integer | `1` | Page number (≥ 1) |
| `limit` | integer | `20` | Items per page (1–100) |
| `search` | string | — | Free-text search on name or email |
| `status` | string | `all` | `all`, `active`, or `inactive` |
| `from_date` | date | — | Created on/after this date (`YYYY-MM-DD`) |
| `to_date` | date | — | Created on/before this date (`YYYY-MM-DD`) |

```http
GET /api/v1/users?page=1&limit=20&search=arun HTTP/1.1
Authorization: Bearer eyJhbGciOi...
```

**`200 OK`** — the inner `data` array sits inside the envelope's `data`:

```json
{
  "code": "S_200_USR_LIST_OK",
  "message": "Users fetched successfully",
  "data": {
    "data": [
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "Arun Kumar",
        "email": "arun.kumar@example.com",
        "status": "active",
        "created_at": "2026-01-15T09:30:00Z",
        "updated_at": "2026-01-15T09:30:00Z"
      }
    ],
    "pagination": { "page": 1, "limit": 20, "total_items": 1, "total_pages": 1 }
  }
}
```

**Errors:** `E_401_NOT_AUTHENTICATED` (401) · `E_403_FORBIDDEN` (403) · `E_500_INTERNAL_ERROR` (500)

---

## 3. Get User — `GET /users/{id}`

Permission: `USERS_READ`

```http
GET /api/v1/users/3fa85f64-5717-4562-b3fc-2c963f66afa6 HTTP/1.1
Authorization: Bearer eyJhbGciOi...
```

**`200 OK`**

```json
{
  "code": "S_200_USR_FETCH_OK",
  "message": "User fetched successfully",
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Arun Kumar",
    "email": "arun.kumar@example.com",
    "status": "active",
    "created_at": "2026-01-15T09:30:00Z",
    "updated_at": "2026-01-15T09:30:00Z"
  }
}
```

**Errors:** `E_404_USR_NOT_FOUND` (404) · `E_401_NOT_AUTHENTICATED` (401) · `E_403_FORBIDDEN` (403) · `E_500_INTERNAL_ERROR` (500)

---

## 4. Replace User — `PUT /users/{id}`

Permission: `USERS_WRITE`. Full representation required — `name`, `email`, `password` all
mandatory; `status` is unchanged by PUT.

```http
PUT /api/v1/users/3fa85f64-5717-4562-b3fc-2c963f66afa6 HTTP/1.1
Authorization: Bearer eyJhbGciOi...
Content-Type: application/json

{ "name": "Arun Kumar", "email": "arun.k@example.com", "password": "S3cureP@ss" }
```

**`200 OK`**

```json
{
  "code": "S_200_USR_UPDATED",
  "message": "User updated successfully",
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Arun Kumar",
    "email": "arun.k@example.com",
    "status": "active",
    "created_at": "2026-01-15T09:30:00Z",
    "updated_at": "2026-01-16T11:05:00Z"
  }
}
```

**Errors:** `E_422_VALIDATION_FAILED` (422) · `E_409_USR_EMAIL_EXISTS` (409) ·
`E_404_USR_NOT_FOUND` (404) · `E_401_NOT_AUTHENTICATED` (401) · `E_403_FORBIDDEN` (403) ·
`E_500_INTERNAL_ERROR` (500)

---

## 5. Partially Update User — `PATCH /users/{id}`

Permission: `USERS_WRITE`. Any subset of `name`, `email`, `status`; omitted fields stay as-is.

```http
PATCH /api/v1/users/3fa85f64-5717-4562-b3fc-2c963f66afa6 HTTP/1.1
Authorization: Bearer eyJhbGciOi...
Content-Type: application/json

{ "status": "inactive" }
```

**`200 OK`** — same shape as PUT, with `S_200_USR_UPDATED` and the new field values.

**Errors:** `E_422_VALIDATION_FAILED` (422) · `E_409_USR_LAST_ADMIN` (409 — cannot deactivate the
last admin) · `E_404_USR_NOT_FOUND` (404) · `E_401_NOT_AUTHENTICATED` (401) ·
`E_403_FORBIDDEN` (403) · `E_500_INTERNAL_ERROR` (500)

---

## 6. Delete User — `DELETE /users/{id}`

Permission: `USERS_WRITE`. Soft delete: the row's `status` becomes `inactive`; nothing is removed.

```http
DELETE /api/v1/users/3fa85f64-5717-4562-b3fc-2c963f66afa6 HTTP/1.1
Authorization: Bearer eyJhbGciOi...
```

**`200 OK`**

```json
{
  "code": "S_200_USR_DELETED",
  "message": "User deleted successfully",
  "data": null
}
```

**Errors:** `E_409_USR_LAST_ADMIN` (409) · `E_404_USR_NOT_FOUND` (404) ·
`E_401_NOT_AUTHENTICATED` (401) · `E_403_FORBIDDEN` (403) · `E_500_INTERNAL_ERROR` (500)

---

## Summary

| # | Method | Path | Payload | Success code |
|---|--------|------|---------|--------------|
| 1 | POST | `/users` | `name`, `email`, `password`, `status?` | `S_201_USR_CREATED` |
| 2 | GET | `/users` | query params only | `S_200_USR_LIST_OK` |
| 3 | GET | `/users/{id}` | none | `S_200_USR_FETCH_OK` |
| 4 | PUT | `/users/{id}` | full: `name`, `email`, `password` | `S_200_USR_UPDATED` |
| 5 | PATCH | `/users/{id}` | any of `name`, `email`, `status` | `S_200_USR_UPDATED` |
| 6 | DELETE | `/users/{id}` | none | `S_200_USR_DELETED` (`data: null`) |

The generated spec lives at `/docs` (Swagger UI) and `/openapi.json` — it always mirrors the code.
