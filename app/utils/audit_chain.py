"""SHA-256 chaining for audit entries (tamper-evident evidence, ASVS 7.3.3)."""

import hashlib
import json
from typing import Any


def entry_digest(prev_hash: str | None, fields: dict[str, Any]) -> str:
    """Hash the previous entry's hash together with the canonical entry fields."""
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(f"{prev_hash or ''}|{canonical}".encode()).hexdigest()
