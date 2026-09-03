# Coding Standards

Rules for this codebase. Tooling enforces what it can (ruff, mypy, bandit, CI); the rest are review conventions.

## 1. Layering (hard boundary)

Requests flow one way:

`api → services → repositories → models`

- **api** (`app/api/`): routing, request parsing, dependency injection, response shaping. No business logic, no SQL.
- **services** (`app/services/`): business rules. Call repositories. Return model entities.
- **repositories** (`app/repositories/`): the *only* layer that writes SQLAlchemy/SQLModel queries. One repository per model.
- **models** (`app/models/`): table definitions. Import *nothing* from `app` except sibling model modules and pure, dependency-free helpers from `app/utils/` (e.g. `utcnow`).

Hard rules:
- The API layer never calls a repository directly — always through a service.
- Services never return Pydantic DTOs — they return entities; the API layer converts to DTOs.
- Models never import schemas, services, repositories, or config.
- API handlers are thin: parse → call one service function → shape the response (see rule 14).

## 2. Table models and API schemas are separate

Table models (SQLModel) and API schemas (Pydantic) are *different classes*. A table model never crosses the API boundary. Requests/responses are always DTOs.

## 3. Imports

- No single-letter module aliases. `from app.schemas import user as u` is banned.
  Import the module (`from app.schemas import user`) or specific names (`from app.schemas.user import UserCreate`).
- No duplicate imports. ruff enforces ordering and unused imports.

## 4. Naming

- Files/modules: `snake_case`. Repositories: `{thing}_repository.py`. Services: `{thing}_service.py`.
- Functions/variables: `snake_case`. Classes: `PascalCase`. Follow PEP 8.

## 5. Enums over magic strings

Any field with a fixed set of values is a `StrEnum`, stored as a DB enum. No bare `"active"` / `"inactive"` literals scattered in logic.

## 6. Constants live with their domain

Response result codes/messages (`CODE_*`, `MSG_*`) live in the **schema module** of the resource that returns them
(`app/schemas/user.py`, `app/schemas/auth.py`, `app/schemas/audit.py`, `app/schemas/health.py`).
Shared infra constants (pagination, header names) live in `app/core/constants.py`.

## 7. Errors

Every domain error is a class in `app/exceptions/exceptions.py` subclassing `AppError`. Each class declares `status_code`, `code` (the stable Result Code), and `message` as class attributes; the global handlers turn any raised `AppError` into the response envelope. Services and dependencies raise these directly (`raise UserNotFoundError()`) — they never return `None` to mean "not found".

- **Raise, don't return.** A lookup that finds nothing raises its error class; callers never check for `None`.
- **Codes are a public contract.** `E_404_USR_NOT_FOUND`, `E_401_AUTH_INVALID_CREDENTIALS`, etc. are stable and machine-readable. Never rename or reuse a code once clients depend on it — add a new class instead.
- **To add an error:** subclass `AppError` (or a matching category such as `ConflictError`), and set `status_code`, `code`, `message` as class attributes. Field-level detail goes through `field_errors([("field", "issue")])` into `data`.

## 8. Types

Everything is type-hinted. `mypy --strict` must pass on `app/`. Avoid `Any`; if you must use it, say why in a comment.

## 9. Async

All I/O is async (`async def` + `await`). No blocking calls in the request path.

## 10. Tests

- Unit tests cover `app/services/` and `app/repositories/` — one test file per module. Repositories use a mocked `AsyncSession`; services mock the repository layer.
- API tests are allowed: build a fresh app with `create_app()`, drive it with `TestClient`, and override `get_db` so no real DB is touched.
- 95% coverage gate on `app/services/` + `app/repositories/` (CI fails below it).
- Tests are deterministic: no network, no real DB, no sleeps.

Full enterprise testing rules (test types, strategy, mocking, fixtures, parametrization, markers, coverage, CI): see `docs/testing-standards.md`.

## 11. Secrets & config

- `.env` is gitignored; only `.env.example` is committed.
- Secrets are read via `pydantic-settings` into `Settings`; never `os.getenv` scattered in code.
- Passwords are never logged or returned by the API.

## 12. Git

- Trunk-based: short-lived branches off `main`, PR review required before merge.
- Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.

## 13. No unexplained suppressions

No `# noqa` / `type: ignore` unless it is a *deliberate, documented exception with a reason*. The `# noqa: E402` import-order hack is banned — fix the structure instead.

## 14. Thin API layer

API handlers stay tiny — parse input, call **one** service function, return the shaped response. Target **2–3 lines of body**: the handler's purpose is to call the service, not to do work. No business logic, no loops, no multi-step orchestration in the router. If a handler grows, the extra work belongs in a service.

Success responses use the shared `ApiResponse` envelope; errors are raised as typed `AppError`s and shaped by the global exception handlers (`app/exceptions/exception_handlers.py`). `ApiResponse` is the single source of truth for *both* envelopes — the exception handlers build it too, never a parallel raw dict. A handler never builds an error response or writes a try/except for an error the global layer already covers.

_Audit recording may add a couple of lines — that's expected. The test is "no business logic here", not a literal line count._

## 15. Small functions

Functions stay short — target **≤15 lines**. When one grows past that, extract the excess into a `_helper()` in the same module (leading underscore = private to that module).

The goal is readability, not the number: if splitting makes the code *harder* to follow, one clear function is better than fragmented helpers. 15 is a target, not a law.

## 16. No hardcoded values

No magic numbers or hardcoded strings in logic. Extract them to a named constant (module-level, or `app/core/constants.py`) or an enum. Obvious literals (`0`, `1`, `""`, `"bearer"`) are fine — anything whose *meaning* isn't obvious from the value itself needs a name.

## 17. DRY — shared code lives in `app/utils/`

A helper used in **two or more** places goes in `app/utils/`. Single-use code stays local (or becomes a `_helper` in its own module). DRY means "don't duplicate the same logic" — not "force every similar-looking two lines into one function."

## 18. Every file/folder explains itself in one line

Each `.py` module starts with a one-line module docstring stating its single responsibility (e.g. `"""User data access (all SQL)."""`). Every file and folder — **at every level, sub-folders and nested files included** — appears in the `README.md` structure map with a one-line description. When you add, move, or remove a file or folder, update that map so it always matches reality. A dev should be able to read the README structure + a file's docstring and know what that file is for without opening it.

## 19. Keep it simple (no over-engineering)

Solve the problem at hand with the simplest design that is still secure and DRY. Don't add abstraction, configuration, or "reusable" machinery for needs the spec doesn't have — build it when a second real use appears, not before. A missing abstraction is cheap to add later; a wrong abstraction is expensive to remove.

## 20. Keyword arguments at call sites

Use keyword arguments for every parameter when a call passes **more than one** argument; a single obvious argument may stay positional:

```python
list_users(page=1, limit=20, search="a", status=UserStatus.ACTIVE)   # good
list_users(1, 20, "a", UserStatus.ACTIVE)                            # avoid
get_user(user_id)                                                    # fine (one arg)
```

Named arguments are self-documenting and immune to accidental parameter swaps. Don't use the `*` keyword-only marker — it's an extra syntax people trip over; this convention is enforced in review.

## 21. Readable and simple — don't overcomplicate

Write the plainest code that solves the problem. Prefer obvious names, straight-line functions, and the simplest structure a reader can follow in one pass. Cleverness and abstraction are a cost, not a virtue — add them only when a concrete need (not a guess) demands it. Pairs with rule 15 (small functions) and rule 19 (no over-engineering).

## 22. Migrations are autogenerated, data lives in seed scripts

Schema migrations are created with `alembic revision --autogenerate -m "..."` and reviewed — never hand-written. Alembic autogenerates the DDL (tables, columns, constraints); adjust the generated file only if autogenerate misses something. Data changes (seed catalogs, backfills) do not go in the migration — they live in idempotent scripts under `app/database/scripts/` (see `seed_admin.py`).

## 23. One-line docstrings only

Every docstring — module, class, function, method — is a single concise line. No multi-line
docstrings, no `Args:`/`Returns:`/`Raises:` blocks, no usage examples. If the detail matters, it
belongs in an ADR, `docs/api.md`, or the README — not in the code. This extends rule 18 (which
covers module docstrings) to every docstring.

## 24. Soft delete — DELETE marks inactive, never removes rows

DELETE endpoints do not remove rows. They set the resource's `status` to `inactive` and record the
delete Audit Entry. Rows keep their globally-unique values — a soft-deleted `roles.name`,
`users.email`, or `screens.code` is *not* reusable by a new row (uniqueness holds across active and
inactive rows). List endpoints return all statuses by default and `GET /{id}` returns any existing
row; the UI decides what to hide. Join tables (`role_screens`, `platform_admin_roles`) are never
deleted — a soft-deleted Role or Screen simply stops contributing Permissions, and re-activating it
restores them. `super_admin` and screens `S1`–`S4` reject both DELETE and `PATCH status=inactive`.

## 25. Every user-supplied field is explicitly bounded

- **Required string fields** reject empty and declare a maximum length.
- **Optional string fields** declare a maximum length (no minimum).
- A bound may come from `Field(min_length=…, max_length=…)`, a format validator (`EmailStr`, the password policy), or an enum — not only literal `min_length`/`max_length`.
- **Numeric fields** are bounded the same way, by range (`ge`/`le`) rather than length.
- Length/range values are **shared constants in `app/utils/limits.py`**, referenced by both the Pydantic DTO and the SQLModel table, so the server and the database can never drift.
- Bounded strings use `VARCHAR(n)`. `TEXT` is never used for a bounded field.
- Validation happens **only** in Pydantic schemas (the single server gate). No service-layer re-validation of the same field, and no DB `CHECK` for min-length or format — the app is the sole writer; the database backstops max-length (`VARCHAR`) and `NOT NULL`/uniqueness.
- Applies to **every** user-supplied input — query params included, not just request bodies.

## 26. API contract — one envelope, stable result codes

Every endpoint returns the shared envelope `{ "code", "message", "data" }` (the `ApiResponse`
schema in `app/schemas/common.py`); `data` is always present — `null` when there is no payload,
never an omitted key. `code` follows `{S|W|E}_{httpStatus}_{BUSINESS_CODE}` — `S_201_USR_CREATED`,
`E_404_USR_NOT_FOUND` — with `W_` marking a request that succeeded but whose side effect failed.
Success codes/messages live as `CODE_*`/`MSG_*` constants in the resource's schema module
(rule 6); error codes are declared on their `AppError` classes (rule 7). List endpoints wrap
their items with `ListData` (`data` array + `pagination`) built through `build_list_data`.
Routes mount under `/api/v1`; JSON field names are the DTO field names (snake_case).
The full contract — shapes per method, standard error codes, pagination bounds, auth headers,
endpoint checklist — is `docs/api-standards.md`; the Users endpoints apply it end-to-end in
`docs/api.md`.
