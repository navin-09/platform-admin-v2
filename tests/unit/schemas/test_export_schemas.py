"""Export schema unit tests — every success and failure validation case."""

import pytest
from pydantic import ValidationError

from app.models.enums import StatusFilter
from app.schemas.export import AuditExportFilters, ExportCreate, UsersExportFilters

REASON_501 = "x" * 501
ACTOR_256 = "a" * 256


# --------------------------------------------------------------------------- #
# module
# --------------------------------------------------------------------------- #


async def test_module_success_accepts_audit_and_users() -> None:
    assert ExportCreate(module="audit", reason="r").module == "audit"
    assert ExportCreate(module="users", reason="r").module == "users"


async def test_module_failure_unknown_value() -> None:
    with pytest.raises(ValidationError):
        ExportCreate(module="mmv", reason="r")


# --------------------------------------------------------------------------- #
# reason (mandatory)
# --------------------------------------------------------------------------- #


async def test_reason_success_strips_surrounding_whitespace() -> None:
    data = ExportCreate(module="audit", reason="  compliance review  ")
    assert data.reason == "compliance review"


async def test_reason_failure_blank() -> None:
    with pytest.raises(ValidationError):
        ExportCreate(module="audit", reason="")


async def test_reason_failure_whitespace_only() -> None:
    """Three spaces are not a reason — the export reason is mandatory."""
    with pytest.raises(ValidationError):
        ExportCreate(module="audit", reason="   ")


async def test_reason_failure_too_long() -> None:
    with pytest.raises(ValidationError):
        ExportCreate(module="audit", reason=REASON_501)


# --------------------------------------------------------------------------- #
# format
# --------------------------------------------------------------------------- #


async def test_format_success_defaults_to_xlsx() -> None:
    assert ExportCreate(module="audit", reason="r").format == "xlsx"


async def test_format_failure_unsupported() -> None:
    with pytest.raises(ValidationError):
        ExportCreate(module="audit", reason="r", format="csv")


# --------------------------------------------------------------------------- #
# filters — omitted defaults
# --------------------------------------------------------------------------- #


async def test_filters_success_omitted_parses_as_none() -> None:
    # The service resolves the per-module default; None means "export everything".
    assert ExportCreate(module="audit", reason="r").filters is None


# --------------------------------------------------------------------------- #
# filters — audit shape
# --------------------------------------------------------------------------- #


async def test_audit_filters_success_all_fields() -> None:
    data = ExportCreate.model_validate(
        {
            "module": "audit",
            "reason": "r",
            "filters": {
                "actor": "admin@example.com",
                "action": "auth.login.success",
                "resource_type": "audit",
                "actor_type": "admin",
            },
        }
    )
    assert isinstance(data.filters, AuditExportFilters)
    assert data.filters.actor == "admin@example.com"
    assert data.filters.action == "auth.login.success"


async def test_audit_filters_success_omitted_fields_default_to_all() -> None:
    data = ExportCreate.model_validate(
        {"module": "audit", "reason": "r", "filters": {"actor": None}}
    )
    assert data.filters.action == "All"
    assert data.filters.resource_type == "All"
    assert data.filters.actor_type == "All"


async def test_audit_filters_failure_actor_too_long() -> None:
    with pytest.raises(ValidationError):
        ExportCreate.model_validate(
            {"module": "audit", "reason": "r", "filters": {"actor": ACTOR_256}}
        )


async def test_audit_filters_failure_invalid_enum_value() -> None:
    with pytest.raises(ValidationError):
        ExportCreate.model_validate(
            {"module": "audit", "reason": "r", "filters": {"action": "not-an-action"}}
        )


async def test_audit_filters_failure_unknown_field() -> None:
    """extra=forbid: a field belonging to NEITHER shape must 422."""
    with pytest.raises(ValidationError):
        ExportCreate.model_validate(
            {"module": "audit", "reason": "r", "filters": {"actor": "x", "bogus": 1}}
        )


# --------------------------------------------------------------------------- #
# filters — users shape
# --------------------------------------------------------------------------- #


async def test_users_filters_success_all_fields() -> None:
    data = ExportCreate.model_validate(
        {
            "module": "users",
            "reason": "r",
            "filters": {"search": "admin", "status": "active"},
        }
    )
    assert isinstance(data.filters, UsersExportFilters)
    assert data.filters.search == "admin"
    assert data.filters.status == StatusFilter.ACTIVE


async def test_users_filters_success_search_only() -> None:
    data = ExportCreate.model_validate(
        {"module": "users", "reason": "r", "filters": {"search": "admin"}}
    )
    assert data.filters.status == StatusFilter.ALL


async def test_users_filters_failure_search_too_long() -> None:
    with pytest.raises(ValidationError):
        ExportCreate.model_validate(
            {"module": "users", "reason": "r", "filters": {"search": ACTOR_256}}
        )


async def test_users_filters_failure_invalid_status() -> None:
    with pytest.raises(ValidationError):
        ExportCreate.model_validate(
            {"module": "users", "reason": "r", "filters": {"status": "bogus"}}
        )


# --------------------------------------------------------------------------- #
# filters — shape/module integrity (invariant ③: no silent degradation)
# --------------------------------------------------------------------------- #


async def test_filters_failure_mixed_shape_rejected_at_schema() -> None:
    """A payload mixing audit + users fields fits neither shape — 422."""
    with pytest.raises(ValidationError):
        ExportCreate.model_validate(
            {"module": "users", "reason": "r", "filters": {"actor": "x", "status": "active"}}
        )


async def test_filters_failure_cross_module_shape_parses_but_is_service_rejected() -> None:
    """A purely wrong-module shape parses (the union cannot see module); the service rejects it."""
    parsed = ExportCreate.model_validate(
        {"module": "audit", "reason": "r", "filters": {"search": "x"}}
    )
    assert isinstance(parsed.filters, UsersExportFilters)
