# Unit Testing Guide

This is the *short, plain-English* version of `docs/testing-standards.md`. Read this
first if you've never written a test here before. The other document is the full rulebook —
come back to it once this one makes sense.

---

## 1. The one-sentence picture

Every `.py` file in `app/` has a matching test file in `tests/`. We test **business rules**
(`app/services/`) and **database code** (`app/repositories/`) in isolation, with no real
database and no network. 218 tests run in ~7 seconds.

```
app/services/user_service.py          →  tests/unit/services/test_user_service.py
app/repositories/user_repository.py   →  tests/unit/repositories/test_user_repository.py
app/schemas/user.py                   →  tests/unit/schemas/test_field_limits.py
```

One tested file = one test file. That's the whole map.

---

## 2. The three kinds of tests in this repo

| Layer | What it asks | Uses a real DB? | Test doubles used |
|-------|-------------|-----------------|-------------------|
| **Schemas** (`tests/unit/schemas/`) | "Is this input valid / too long / empty?" | No | **None** — plain Python |
| **Services** (`tests/unit/services/`) | "Is the business rule right?" | No | **Fakes** + `monkeypatch` |
| **Repositories** (`tests/unit/repositories/`) | "Does it talk to the database correctly?" | No | **Mocks** for the DB session |

There are **no** API/integration/real-database tests yet — that's a deliberate v1 decision
(see `docs/testing-standards.md` §1). If your test needs a real database, you're writing the
wrong kind of test.

---

## 3. Test doubles — the part everyone trips on

A *test double* is a stand-in for something the code you're testing depends on. We use
**four tools**, and each has one job. They are not interchangeable — that's why the code
mixes them and why it looks confusing at first.

### 3.1 The four tools

| Tool | What it is (plain English) | Use it when… |
|------|---------------------------|--------------|
| **Fake** (`FakeUserRepository`, etc. in `tests/unit/fakes.py`) | A real class you write that has the same methods as the real thing, but **remembers calls in a list** instead of hitting a database. | A service depends on a **repository or another service**. Set a field, call the service, read the recorder list. |
| **`monkeypatch.setattr`** (pytest fixture) | Temporarily **swap one name on a module** with something else; pytest puts it back after the test. | The service imported a **helper function** you don't want to run for real — `hash_password`, `verify_password`, `create_access_token`, `decode_token`. |
| **`AsyncMock` / `MagicMock`** (`unittest.mock`) | A **robot object**: call any method on it, set `.return_value` or `.side_effect`, then later ask "were you called? with what?". | Replace the **database session** in repository tests (`db.add`, `db.commit`, `db.execute`). `AsyncMock` for things you `await`, `MagicMock` for things you call normally. |
| **`patch.object`** (`unittest.mock`) | The **older way** to swap a name or build an inline mock. | Mostly **legacy** in service tests. Still used in repository tests to inject the mocked session (`get_session`). Prefer a fake or `monkeypatch` when writing new service tests. |

### 3.2 The rule in one line

> **Fakes for collaborators (repositories/services). `monkeypatch` for helper functions.
> Mocks for the database session.**

### 3.3 Why the repository tests look different from the service tests

Service tests swap in a whole **Fake** (`FakeUserRepository`) because a service's
collaborator is another repository. Repository tests are the bottom of the stack — their
only collaborator is the database **session**, so there's nothing to fake; you mock the
session with `MagicMock`/`AsyncMock` and inject it with `patch.object(user_repository,
"get_session", return_value=db)`.

So the "different styles" are mostly *correct layering*, not chaos:

```
services    →  Fakes + monkeypatch        (business rules)
repositories →  MagicMock/AsyncMock session (DB glue)
schemas     →  nothing                     (pure validation)
```

**Known inconsistency to clean up:** a couple of service tests use `patch.object` inline
(e.g. `tests/unit/services/test_user_service.py::test_list_users_with_date_filters`) where
every sibling test uses the `fakes` fixture. That's a leftover, not a pattern to copy.

---

## 4. How to run the tests

```bash
uv run pytest                 # run everything (coverage runs automatically)
uv run pytest -k "login"      # run only tests whose name contains "login"
uv run pytest -v              # one line per test
uv run pytest tests/unit/services/test_user_service.py   # one file only
uv run pytest --lf            # re-run only the tests that failed last time
```

The full pre-commit gate (run this before you push):

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest
```

---

## 5. Anatomy of a test (the shape every test follows)

Every test is three comments: **Given → When → Then** (setup → act → assert).

```python
async def test_login_failure_inactive_account(fakes) -> None:
    # GIVEN an inactive admin with a correct password
    fakes.repo.admin = active_admin(status=Status.INACTIVE)

    # WHEN / THEN — the attempt is rejected
    with pytest.raises(AccountInactiveError):
        await auth_service.login(LoginRequest(email="admin@example.com", password="pw"))
```

Rules that come from this shape:

- **Name the test for behaviour**, not implementation: `test_login_failure_inactive_account`,
  not `test_login_2`.
- Use **plain `assert`**. For expected errors use `pytest.raises(ErrorType)` (add
  `match="..."` when the message matters).
- **One behaviour per test.** Don't act-assert-act-assert. One cause → one failure.
- Assertions go at the **end**.

---

## 6. How to add a new unit test — step by step

### Step 0 — pick the layer

The logic lives in `app/services/` and `app/repositories/`. Ask "where does the code I'm
changing live?" and put the test in the matching `tests/unit/...` folder.

### Step 1 — service test (the most common one)

Say you added a new rule to `user_service.update_user`. Copy the existing pattern:

```python
# tests/unit/services/test_user_service.py

async def test_update_user_failure_email_taken_by_self(fakes) -> None:
    # GIVEN the new email is already used by a *different* admin
    fakes.email_owner = _user(email="other@example.com")

    # WHEN / THEN the update is rejected
    with pytest.raises(EmailExistsError):
        await user_service.update_user(
            user_id=fakes.user.id, data=UserUpdate(email="other@example.com")
        )
```

What's going on:

1. The `fakes` fixture (already in the file) wired a `FakeUserRepository` onto
   `user_service.user_repository`, and an `AsyncMock` onto `user_service.audit_service.record`.
2. You **steer** the fake by setting fields: `fakes.email_owner = ...` tells the fake what
   `get_user_by_email` should return.
3. You **call** the real service function.
4. You **assert** either the raised error, the return value, or the recorder list
   (`fakes.created`, `fakes.deleted`, `fakes.updated`).

If your function calls a helper like `hash_password`, stub it in the fixture with
`monkeypatch.setattr(user_service, "hash_password", lambda _plain: "hashed")` — you're not
testing `hash_password`, you're controlling its result.

### Step 2 — repository test

Say you add a new query to `user_repository`. Copy this pattern:

```python
# tests/unit/repositories/test_user_repository.py

async def test_list_users_returns_total_and_rows() -> None:
    db = MagicMock()                                    # a fake DB session
    db.scalar = AsyncMock(return_value=42)              # the COUNT(*) result
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = ["u1", "u2"]

    with patch.object(user_repository, "get_session", return_value=db):
        users, total = await user_repository.list_users(page=1, limit=20)

    assert users == ["u1", "u2"]
    assert total == 42
```

What's going on:

1. `db` is a `MagicMock` standing in for the SQLAlchemy `AsyncSession`. Chain `.return_value`
   to make `db.execute(...)` return a result whose `.scalars().all()` gives the rows.
2. `patch.object(user_repository, "get_session", return_value=db)` makes the repository use
   *your* session.
3. Assert the **outcome**, or — because for data access the only observable outcome is "did
   it talk to the session correctly" — assert the calls:

```python
db.add.assert_called_once_with(user)
db.commit.assert_awaited_once()
db.refresh.assert_awaited_once_with(user)
```

### Step 3 — schema test (easiest)

```python
# tests/unit/schemas/test_field_limits.py

def test_name_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        UserCreate(name="", email="a@b.com", password="S3cureP@ss")
```

No mocks, no fixtures — just construct the DTO and assert.

---

## 7. Gotchas (common mistakes)

1. **`async` code needs `async def test_...` and `await`.** The repo sets
   `asyncio_mode = "auto"`, so you don't need decorators — just make the test `async` and
   `await` the call.
2. **If you `await` it, mock it with `AsyncMock`; if you call it, `MagicMock`.** An
   `await db.commit()` where `commit` is a plain `MagicMock` fails in confusing ways.
3. **Assert async calls with `assert_awaited_once_with`, not `assert_called_once_with`.**
4. **Never import `app.main` or touch a real DB/network/filesystem** in a unit test. (The
   one exception: `test_xlsx_writer.py` and the export tests write real files into `tmp_path`
   — that's fine because `tmp_path` is a per-test temporary directory.)
5. **Don't mock the function you're testing.** If the test only passes because you mocked
   `user_service.update_user`, you've tested the mock, not the code.
6. **Fakes record, don't lie silently.** `FakeUserRepository.get_user` returns
   `self.user` (which may be `None`); the recorder lists (`created`, `updated`, `deleted`)
   are how you check what the service *did*.
7. **Passwords/tokens in test data are fine** — ruff ignores `S105`/`S106` in `tests/`.
8. **Read the section banners.** Service test files group tests under comments like
   `# update_user`. Put your new test under the matching banner so the file stays navigable.

---

## 8. Where to copy from

These files are the cleanest examples — open one and imitate it:

- **Service + fakes:** `tests/unit/services/test_user_service.py` (and `tests/unit/fakes.py`)
- **Service + monkeypatch helpers:** `tests/unit/services/test_auth_service.py`
- **Repository + mocked session:** `tests/unit/repositories/test_user_repository.py`
- **Schema validation:** `tests/unit/schemas/test_field_limits.py`

If a rule in this guide and `docs/testing-standards.md` disagree, the standards doc wins —
flag the disagreement to a senior so we can fix whichever one is stale.
