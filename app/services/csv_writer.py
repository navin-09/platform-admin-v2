"""Streaming csv writer: a metadata block followed by the data table, atomic replace."""

import csv
import json
import os
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any


def _cell(value: Any) -> Any:
    """Coerce a model value into a csv-safe cell value."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict | list):
        return json.dumps(value, default=str)
    return value


async def write_export_csv(
    path: Path,
    *,
    metadata: dict[str, Any],
    headers: list[str],
    rows: AsyncIterator[list[Any]],
) -> int:
    """Stream ``rows`` into ``path`` as a metadata block + data table; return row count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex[:8]}.tmp")

    count = 0
    with tmp_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Field", "Value"])
        for key, value in metadata.items():
            writer.writerow([key, _cell(value)])
        writer.writerow([])
        writer.writerow(headers)
        async for row in rows:
            writer.writerow([_cell(value) for value in row])
            count += 1

    os.replace(tmp_path, path)
    return count
