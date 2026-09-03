# Testing Standards

Enterprise rules for writing, organizing, and reviewing tests. Distilled from
*Python Testing with pytest, Second Edition* (Brian Okken, Pragmatic Bookshelf, 2022) and
adapted to this codebase and its NBFC constraints.

Companion to `docs/standards.md` rule 10 (which is the short version). This is the full version.

---

## 1. Test types — know which level you're testing

| Level | What it tests | Collaborators | In this repo (v1) |
|-------|---------------|---------------|-------------------|
| **Unit** | One function/class in isolation | Mocked | ✅ `app/services/`, `app/repositories/` |
| **Subsystem / integration** | A layer against a real collaborator (e.g. repository + real test DB) | Real (test DB) | ❌ deferred — no DB in v1 |
| **System / API** | Behaviour through the public API/endpoints | Real app, mocked DB | ✅ allowed — `create_app()` + `TestClient`, DB overridden |
| **End-to-end / UI** | Full user journey | Everything real | ❌ frontend/QA owns it |
| **Smoke** | Critical path only, fastest possible | Minimal | ✅ implicit: CI runs the unit suite as the gate |
| **Regression** | A bug pinned as a failing test first | Mocked | ✅ always for bug fixes |

**Rule:** test at the layer where the logic lives. Thin routers and thin DB glue mean the logic is in
services and repositories — so that's where the unit tests go.

---

## 2. Deciding *what* to test

### 2.1 Prioritise features (Okken, ch. 7)

Order test effort by:

1. **Recent** — new / repaired / refactored code.
2. **Core** — the product's essential functions (for us: login, user CRUD, audit trail).
3. **Risk** — customer-critical, rarely-exercised, or third-party-dependent code.
4. **Problematic** — code with a history of defects.
5. **Expertise** — algorithms understood by only a few people.

### 2.2 Generate test cases methodically

For each function, start with a **non-trivial happy path**, then add cases for:

- **interesting inputs** (empty, boundary, malformed, duplicates),
- **interesting starting states** (empty / one / many),
- **interesting end states** (did the action change state correctly),
- **all error states** (not-found, conflict, invalid token, inactive account, etc.).

Every BRD acceptance criterion (AC) maps to at least one test. An AC you can't turn into a test
is vague — go back and clarify it.

### 2.3 Write the strategy down

Decisions like "unit tests on services + repositories only, no DB" are strategy. They live in
`docs/standards.md` rule 10 and in this document — never only in someone's head.

---

## 3. Unit test rules

1. **Scope:** `app/services/` and `app/repositories/` only. One test file per tested module.
2. **No external I/O:** no real DB, no network, no filesystem. API tests use `create_app()` + `TestClient` with `get_db` overridden; no `app.main` import.
3. **Structure:** Given-When-Then (Arrange-Act-Assert). Assertions go at the *end* of the test.
4. **One behaviour per test.** Avoid Act-Assert-Act-Assert chains — a failing test should have one
   obvious cause.
5. **Use plain `assert`.** For expected exceptions use `pytest.raises(ErrorType, match="...")`.
6. **Name for behaviour, not implementation:** `test_login_inactive_account`, not `test_login_2`.
7. **Deterministic:** no sleeps, no wall-clock, no random data, no shared mutable state between tests.
8. **Fake collaborators, not patch chains:** service tests wire the shared fakes from
   `tests/unit/fakes.py` (one fake per repository) via a per-file fixture, then configure
   attributes and read recorder lists. Avoid long `patch.object(...)` context chains — a test
   should set a fake field, call the service, and assert. Files follow the export suite's
   layout: section banners per service function, success/failure pairs (`test_<unit>_success`,
   `test_<unit>_failure_<condition>`).

### Structure example

```python
@pytest.fixture()
def fakes(monkeypatch) -> SimpleNamespace:
    """Wire the shared fake + helper stubs onto the service under test."""
    fakes = SimpleNamespace(
        repo=FakeAuthRepository(admin=active_admin()),
        password_ok=True,
    )
    monkeypatch.setattr(auth_service, "auth_repository", fakes.repo)
    monkeypatch.setattr(auth_service, "verify_password", lambda *_a, **_k: fakes.password_ok)
    return fakes


async def test_login_failure_inactive_account(fakes) -> None:
    # GIVEN an inactive admin with a correct password
    fakes.repo.admin = active_admin(status=Status.INACTIVE)

    # WHEN we attempt login, THEN it is rejected
    with pytest.raises(AccountInactiveError):
        await auth_service.login(LoginRequest(email="admin@example.com", password="pw"))
```

---

## 4. Mocking rules

### 4.1 What a mock is (and is not)

A mock is a stand-in for a **collaborator** — the repository under a service, or the `AsyncSession`
under a repository. It is **not** a fake database. No SQLite, no in-memory DB, no test database, no
connection. If a test needs a real database, it is an integration test and out of v1 scope.

### 4.2 The mechanics

Two kinds of stand-in, one per layer:

**Service tests** wire the shared fakes from `tests/unit/fakes.py` and stub helper functions with
`monkeypatch.setattr` (a pytest fixture that swaps a name on the module under test and restores it
after the test):

  ```python
  monkeypatch.setattr(user_service, "user_repository", FakeUserRepository(user=admin))
  monkeypatch.setattr(user_service, "hash_password", lambda _plain: "hashed")
  ```

  Services import the repository module (`from app.repositories import user_repository`), so the
  name `user_repository` lives on the service module and is what you replace — not the function it
  points to.

**Repository tests** replace the database session with a mock. `MagicMock` fakes **sync** calls
(`db.add(...)`); `AsyncMock` fakes **async** calls — anything you `await` must be an `AsyncMock`.
Inject the session with `patch.object`:

  ```python
  db = MagicMock()
  db.commit = AsyncMock()
  with patch.object(user_repository, "get_session", return_value=db):
      ...
  ```

- **Prefer `autospec=True`** when the mocked object is a real class — it catches typos and parameter
  changes ("mock drift"). Skip it only when the object is genuinely dynamic.
- **Assert calls** when there's no return value to check:

  ```python
  db.commit.assert_awaited_once()
  db.add.assert_called_once_with(user)
  ```

- **Simulate errors** with `side_effect`:

  ```python
  AsyncMock(side_effect=JWTError("bad token"))
  ```

### 4.3 The golden rule: mock behaviour, not implementation

Tests that mock internals become **change-detector tests** — they break on harmless refactors and
teach the team to ignore failing tests. Mock at the boundary of the unit under test, and assert the
outcome, not the call, wherever the outcome is observable.

> For the repository layer we *do* assert calls (`commit`, `add`, `refresh`) because the only
> observable outcome is "it talked to the session correctly" — that's the boundary, and it's the
> accepted limit of unit-testing data access without a database.

---

## 5. Fixtures

1. Keep **one `conftest.py`** at `tests/` so fixtures are easy to find.
2. Default scope is **function**. Use `scope="module"`/`"session"` only for expensive, side-effect-free
   setup — and we have none in v1.
3. Avoid `autouse=True` unless *every* test genuinely needs it.
4. Fixtures are for **setup/teardown and shared collaborators**, not for asserting behaviour.

---

## 6. Parametrization

- Use `@pytest.mark.parametrize` to turn one test into many — for the dimension that actually
  matters (statuses, error types, invalid inputs).
- Parametrize **one thing** per test; hard-code the rest. Keep the generated IDs readable
  (`test_login[INACTIVE]`, not `test_login[admin1-pw2]`).

---

## 7. Markers

| Marker | Use | Rule |
|--------|-----|------|
| `@pytest.mark.skip(reason=...)` | Feature not implemented yet | Always a reason |
| `@pytest.mark.skipif(cond, reason=...)` | OS/version/feature-flag conditional | Keep the condition small |
| `@pytest.mark.xfail(reason=...)` | Known bug, expected to fail | Track it; fix and remove |
| Custom (`smoke`, `unit`, `integration`) | Select subsets | Register every marker in config |

**Always run with `--strict-markers`** (put it in `addopts`). A typo'd marker must fail at
collection, not silently pass as a warning.

---

## 8. Coverage

1. Gate with `--cov-fail-under=95` on the **tested layers** (`app/services`, `app/repositories`).
2. Coverage is a **floor, not a target.** Adding tests only to hit 100% on dead code is worse than
   leaving it uncovered (Okken: "Beware of Coverage-Driven Development").
3. `# pragma: no cover` is allowed only for documented glue such as `if __name__ == "__main__":`.
4. Run coverage on the tests too (`--cov=tests`) to catch **duplicate test names** — a copy-pasted
   test that overwrites another is silently lost otherwise.

---

## 9. Configuration & CI

- One config in `pyproject.toml` → `[tool.pytest.ini_options]`: `testpaths`, `addopts`
  (coverage scope + gate + `--strict-markers`), `asyncio_mode = "auto"`.
- CI runs the same five checks as local: `ruff check`, `ruff format --check`, `mypy`, `bandit`,
  `pytest`.
- A test that needs a database, network, or sleep does not belong in the unit suite.

---

## 10. Debugging failing tests (quick commands)

| Flag | Purpose |
|------|---------|
| `-v` | One line per test, full names |
| `--tb=short` | Just the failing line + assertion |
| `-ra` | Report reasons for skip/xfail/fail |
| `-k "login"` | Run only tests matching keyword |
| `--lf` / `--ff` | Re-run last-failed / failed-first |

---

## Appendix — where each rule comes from in the book

| Rule | Book chapter |
|------|--------------|
| Test types & pyramid, feature prioritisation, test-case generation, write the strategy down | ch. 7 Strategy |
| Arrange-Act-Assert / Given-When-Then, plain `assert`, `pytest.raises(match=...)` | ch. 2 Writing Test Functions |
| Fixtures: scope, one `conftest.py`, autouse | ch. 3 Fixtures |
| Parametrization: parametrize one dimension, readable IDs | ch. 5 Parametrization |
| Markers: skip/skipif/xfail/custom + `--strict-markers` | ch. 6 Markers |
| Configuration: `rootdir`, `testpaths`, test-name collision | ch. 8 Configuration Files |
| Coverage: gate, `# pragma: no cover`, beware coverage-driven development, `--cov=tests` | ch. 9 Coverage |
| Mocking: `autospec`, `assert_called_*`, `side_effect`, behaviour-vs-implementation, multi-layer testing | ch. 10 Mocking |
| CI + minimum coverage gate | ch. 11 tox and CI |
| Debugging failures | ch. 13 Debugging Test Failures |
