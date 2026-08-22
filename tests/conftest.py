"""Pytest configuration and shared fixtures.

Environment variables are set here *before* any ``app.*`` import. This matters
because ``app.core.config`` instantiates ``Settings()`` at import time, and
``database_url`` / ``secret_key`` are required (no defaults). Injecting test
values here keeps the suite independent of a developer's local ``.env`` and of
CI secrets.
"""

import os

# ``setdefault`` avoids clobbering values already present in the environment.
# The URL value is irrelevant to the unit tests (all DB access is mocked), but
# it must exist for ``Settings()`` to build.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
