"""Shared request-field format validators."""

import re

SLUG_PATTERN = re.compile(r"^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$")
PERMISSION_PATTERN = re.compile(r"^[A-Za-z0-9]+(-[A-Za-z0-9]+)*\.(R|W)$")


def validate_slug_format(value: str, field_label: str = "Value") -> str:
    """Enforce alphanumeric-with-hyphens format (hyphens only in the middle)."""
    if not SLUG_PATTERN.fullmatch(value):
        raise ValueError(f"{field_label} must follow the valid format")
    return value


def validate_permission_format(value: str, field_label: str = "Permission") -> str:
    """Enforce ``<screen-code>.<R|W>`` — a slug screen code plus an uppercase ``R`` or ``W``."""
    if not PERMISSION_PATTERN.fullmatch(value):
        raise ValueError(f"{field_label} must follow the format <screen-code>.<R|W>")
    return value
