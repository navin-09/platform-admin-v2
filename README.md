# platform-admin-v2

FastAPI backend where **Platform Admins** log in and manage platform **Users**, with an append-only audit log.

## Architecture

Requests flow one way, through four layers (rule 1). Each layer only talks to the one below it:

```text
HTTP request
   │
   ▼
api/          parse the request, check auth, call ONE service, shape the response
   │
   ▼
services/     business rules (validation, uniqueness, password hashing, tokens)
   │
   ▼
repositories/ the ONLY layer that writes SQL — one repository per model
   │
   ▼
models/       SQLModel tables (User, PlatformAdmin, AuditLog) + enums
```

Supporting modules around that core:

- **schemas/** — Pydantic DTOs. Requests/responses are always DTOs; a table model never crosses the API boundary.
- **core/** — config, security (bcrypt + JWT), constants, structured logging, tracing.
- **exceptions/** — typed `ApiError`s + handlers that turn them into the response envelope.
- **middleware/** — sets a `request_id` per request, logs one access line, adds `X-Process-Time`.
- **utils/** — shared pure helpers.

### Example: creating a user

```text
POST /api/v1/users  {"name", "email", "password", "status"}
        │
        ▼
api/v1/users.py        parse body → UserCreate DTO · verify admin token (deps.py)
        │  await user_service.create_user(db, data)
        ▼
services/user_service  email already taken? → raise · hash password (core/security)
        │  await user_repository.create_user(db, user)
        ▼
repositories/user      db.add(user) → db.commit() → db.refresh(user)
        │
        ▼
models/user.py         "users" table (SQLModel)
        │
        ▼
api/v1/users.py        entity → UserRead DTO → ApiResponse {code, message, data}
```

## Stack

Python 3.12 · FastAPI · SQLModel (tables) + Pydantic v2 (DTOs) · SQLAlchemy 2 async · asyncpg · PostgreSQL · Alembic · python-jose · bcrypt · OpenTelemetry · stdlib JSON logging.

## Structure

Every file and folder has a single responsibility. Keep this map updated (rule 18).

```text
platform-admin-v2/
├── .github/workflows/ci.yml    # CI: lint, types, security scan, tests
├── .pre-commit-config.yaml     # git hooks (whitespace, ruff)
├── .python-version             # pinned Python 3.12
├── .gitignore                  # files git must not track
├── .env.example                # env var template (committed)
├── alembic.ini                 # Alembic config
├── alembic/
│   ├── env.py                  # async migration runner (reads model metadata)
│   └── versions/               # migration scripts (0001_initial_schema, ...)
├── app/
│   ├── main.py                 # FastAPI entrypoint; wires routers + middleware + tracing
│   ├── database/
│   │   ├── database.py         # async engine, session factory, get_db dependency
│   │   ├── session.py          # request-scoped session holder (get_session)
│   │   └── scripts/
│   │       └── seed_admin.py   # create/reset a Platform Admin manually
│   ├── api/
│   │   ├── deps.py             # get_current_admin auth dependency
│   │   ├── audit.py            # request → audit-context helper
│   │   └── v1/
│   │       ├── health.py       # GET /health
│   │       ├── auth.py         # POST /api/v1/auth/login + /refresh
│   │       ├── users.py        # user CRUD routes
│   │       └── audit_logs.py   # GET /api/v1/audit-logs
│   ├── core/
│   │   ├── config.py           # Settings (from env)
│   │   ├── constants.py        # pagination + header constants
│   │   ├── security.py         # bcrypt hashing + JWT
│   │   ├── logging.py          # structured JSON logging + request_id
│   │   └── tracing.py          # OpenTelemetry setup
│   ├── exceptions/
│   │   ├── errors.py           # ApiError + error catalog
│   │   └── handlers.py         # exception → envelope handlers
│   ├── middleware/
│   │   ├── request_context.py  # sets request_id per request
│   │   └── logging.py          # one access-log line per request
│   ├── models/
│   │   ├── __init__.py         # re-exports models (registers tables for Alembic)
│   │   ├── enums.py            # UserStatus, AuditAction, AuditResourceType
│   │   ├── user.py             # users table
│   │   ├── platform_admin.py   # platform_admins table
│   │   └── audit_log.py        # audit_logs table
│   ├── repositories/
│   │   ├── auth_repository.py  # admin lookup
│   │   ├── health_repository.py # DB liveness probe (SELECT 1)
│   │   ├── user_repository.py  # all user SQL
│   │   └── audit_repository.py # audit SQL (insert + list only — append-only)
│   ├── schemas/
│   │   ├── common.py           # ApiResponse envelope + Pagination
│   │   ├── auth.py             # auth DTOs + result codes
│   │   ├── user.py             # user DTOs + password policy + result codes
│   │   ├── audit.py            # audit DTOs + result codes
│   │   └── health.py           # health result codes
│   ├── services/
│   │   ├── auth_service.py     # login business logic
│   │   ├── health_service.py   # service health check
│   │   ├── user_service.py     # user business rules
│   │   └── audit_service.py    # audit recording (best-effort)
│   └── utils/
│       ├── pagination.py       # total_pages helper
│       ├── time.py             # utcnow helper
│       └── validate.py         # shared request-field format validators
├── docs/
│   ├── standards.md            # the coding rules
│   ├── testing-standards.md    # enterprise testing rules (all test types)
│   ├── api.md                  # API reference
│   └── adr/                    # architecture decision records
├── tests/
│   ├── conftest.py             # env setup (no DB connection)
│   └── unit/
│       ├── services/           # pure unit tests (repositories mocked)
│       └── repositories/       # pure unit tests (mocked AsyncSession)
├── CONTEXT.md                  # domain glossary
├── README.md                   # this file
└── pyproject.toml              # project + tooling config
```

> `docs/` and `CONTEXT.md` are currently git-ignored (local notes, not pushed yet).

## Run

```bash
uv sync
uv run python -m alembic upgrade head
uv run python app/database/scripts/seed_admin.py --username admin --email admin@example.com --password '<password>'
uv run app
```

See `docs/api.md` for the full walkthrough.

## Checks before committing

Run all of these from `platform-admin-v2/` before you commit. CI runs the same checks on every push/PR.

```bash
# 1. Format (rewrites files to match the style)
uv run ruff format .

# 2. Lint (--fix repairs what it can)
uv run ruff check --fix .

# 3. Type check
uv run mypy app

# 4. Security scan
uv run bandit -c pyproject.toml -r app

# 5. Tests
uv run pytest
```

All five must pass before you commit. To verify *without* rewriting files, CI uses the check-only forms:

```bash
uv run ruff format --check .
uv run ruff check .
```

Your git hooks already run ruff on `git commit`. If you haven't installed them yet, do it once:

```bash
uv run pre-commit install
```
