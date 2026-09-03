# AGENTS.md — Platform Admin v2

Repo guardrails for AI agents. Self-contained coding standards; `docs/standards.md` is the
canonical deep reference (same rules, more prose).

## Architecture & layering

Requests flow one way:

`api → services → repositories → models`

- **api** (`app/api/`): routing, request parsing, dependency injection, response shaping. No business logic, no SQL.
- **services** (`app/services/`): business rules. Call repositories. Return entities.
- **repositories** (`app/repositories/`): the *only* layer that writes SQLAlchemy/SQLModel queries. One repository per model.
- **models** (`app/models/`): table definitions. Import *nothing* from `app` except sibling model modules and pure, dependency-free helpers from `app/utils/`.

Hard rules:
- The API layer never calls a repository directly — always through a service.
- Services never return Pydantic DTOs — they return entities; the API layer converts to DTOs.
- Models never import schemas, services, repositories, or config.
- **API handlers are thin**: parse → call one service function → shape the response (target 2–3 line bodies). No business logic, loops, or multi-step orchestration in routers. Success uses the shared `ApiResponse` envelope; errors raise typed `AppError`s shaped by the global handlers — never a parallel raw dict. Audit recording may add a couple of lines; the test is "no business logic", not a literal line count.

## Table models and API schemas are separate

Table models (SQLModel) and API schemas (Pydantic) are *different classes*. A table model never crosses the API boundary. Requests/responses are always DTOs.

## Imports

- No single-letter module aliases — `from app.schemas import user as u` is banned. Import the module (`from app.schemas import user`) or specific names (`from app.schemas.user import UserCreate`).
- No duplicate imports. ruff enforces ordering and unused imports.

## Naming

- Files/modules: `snake_case`. Repositories: `{thing}_repository.py`. Services: `{thing}_service.py`.
- Functions/variables: `snake_case`. Classes: `PascalCase`. PEP 8.

## Enums and constants

- Any field with a fixed set of values is a `StrEnum`, stored as a DB enum. No bare `"active"`/`"inactive"` literals in logic.
- Result codes/messages (`CODE_*`, `MSG_*`) live in the **schema module** of the resource that returns them. Shared infra constants (pagination, header names) live in `app/core/constants.py`.

## Errors

- Every domain error is a class in `app/exceptions/exceptions.py` subclassing `AppError`, declaring `status_code`, `code` (stable Result Code), and `message` as class attributes. Global handlers convert any raised `AppError` to the envelope.
- **Raise, don't return.** A lookup that finds nothing raises its error class; callers never check for `None`.
- **Codes are a public contract.** Never rename or reuse a code once clients depend on it — add a new class instead.
- To add an error: subclass `AppError` (or a matching category such as `ConflictError`), set `status_code`, `code`, `message`. Field-level detail via `field_errors([("field", "issue")])` into `data`.

## Types, async, style

- Everything is type-hinted. `mypy --strict` passes on `app/`. Avoid `Any`; comment why if unavoidable.
- All I/O is async (`async def` + `await`). No blocking calls in the request path.
- **Small functions**: target ≤15 lines; extract a `_helper()` when longer. Readability over the number.
- **No hardcoded values**: name constants or enums. Obvious literals (`0`, `1`, `""`, `"bearer"`) are fine.
- **Keyword args at call sites** when passing more than one argument. No `*` keyword-only marker.
- **Readable and simple**: the plainest code that solves the problem; cleverness is a cost, not a virtue.

## Tests

- Unit tests cover `app/services/` and `app/repositories/` — one test file per module. Repositories mock `AsyncSession`; services mock the repository layer.
- API tests allowed: fresh `create_app()` + `TestClient`, override `get_db` (no real DB).
- **95% coverage gate** on `app/services/` + `app/repositories/` (CI fails below it).
- Deterministic: no network, no real DB, no sleeps.
- Full rules: `docs/testing-standards.md`.

## Secrets, git, suppressions

- `.env` is gitignored; only `.env.example` is committed. Secrets via `pydantic-settings`; never scattered `os.getenv`. Passwords never logged or returned.
- Trunk-based git: short-lived branches, PR review before merge. Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- No `# noqa` / `type: ignore` without a deliberate, documented reason. The `# noqa: E402` import-order hack is banned — fix the structure.

## DRY and docstrings

- A helper used in 2+ places goes in `app/utils/`. Single-use code stays local (or becomes a `_helper`).
- Every `.py` module starts with a one-line docstring stating its responsibility.
- **One-line docstrings only** — module, class, function, method. No `Args:`/`Returns:`/`Raises:` blocks, no examples. Detail belongs in an ADR, `docs/api.md`, or the README.
- Every file/folder (at every level) appears in the `README.md` structure map with a one-line description — update the map when you add, move, or remove anything.

## Keep it simple (no over-engineering)

Solve the problem with the simplest design that is still secure and DRY. No speculative abstraction, configuration, or "reusable" machinery for needs the spec doesn't have. A missing abstraction is cheap to add later; a wrong abstraction is expensive to remove.

## Soft delete

DELETE endpoints mark `status = inactive`; rows are never removed. Unique values stay globally unique across active and inactive rows. List returns all statuses by default; `GET /{id}` returns any existing row. Join tables are never deleted. `super_admin` and screens `S1`–`S4` reject both DELETE and `PATCH status=inactive`.

## Every user-supplied field is explicitly bounded

- **Required string fields** reject empty and declare a maximum length. **Optional string fields** declare a maximum length.
- A bound may come from `Field(min_length=…, max_length=…)`, a format validator (`EmailStr`, password policy), or an enum.
- **Numeric fields** are bounded by range (`ge`/`le`) rather than length.
- Length/range values are **shared constants in `app/utils/limits.py`**, referenced by both the DTO and the SQLModel table, so server and database never drift.
- Bounded strings use `VARCHAR(n)`; `TEXT` is never used for a bounded field.
- Validation happens **only** in Pydantic schemas (single server gate). No service-layer re-validation; no DB `CHECK` for min-length or format. The DB backstops max-length and `NOT NULL`/uniqueness.
- Applies to **every** user-supplied input — query params included, not just request bodies.

## Schema changes and data

Generate every migration with Alembic autogenerate:

```bash
uv run alembic revision --autogenerate -m "add foo column"
uv run alembic upgrade head
```

Review the generated file in `alembic/versions/`; edit it only if autogenerate missed a change. Do not create or hand-write a version file — the revision id, `down_revision`, and DDL come from Alembic.

Data changes (seeds, backfills) live in idempotent scripts under `app/database/scripts/`, never in a migration.

If `alembic` fails with `Can't locate revision`, the database predates the squashed history — reset it (drop & recreate, then `upgrade head` + seed) rather than editing version files.

## Before committing

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```
