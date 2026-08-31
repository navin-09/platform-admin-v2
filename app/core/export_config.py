"""Per-module export specs: authorized fields, labels, classification."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExportSpec:
    module: str
    label: str
    classification: str
    filename_prefix: str
    sheet_name: str
    # (model field name, header label) — the authorized-field allow-list.
    columns: tuple[tuple[str, str], ...]


# Audit exports are Restricted; details are included as JSON (already redacted at write time).
AUDIT_EXPORT_SPEC = ExportSpec(
    module="audit",
    label="Audit Logs",
    classification="Restricted",
    filename_prefix="audit_export",
    sheet_name="Audit Events",
    columns=(
        ("id", "Event ID"),
        ("created_at", "Created At (UTC)"),
        ("actor", "Actor"),
        ("actor_type", "Actor Type"),
        ("action", "Action"),
        ("resource_type", "Resource Type"),
        ("resource_id", "Resource ID"),
        ("details", "Details"),
        ("payload", "Payload"),
        ("response", "Response"),
        ("url", "URL"),
        ("request_id", "Request ID"),
        ("ip_address", "IP Address"),
        ("user_agent", "User Agent"),
    ),
)


# Users are Confidential; credentials and session state are never in the allow-list.
USERS_EXPORT_SPEC = ExportSpec(
    module="users",
    label="Users",
    classification="Confidential",
    filename_prefix="users_export",
    sheet_name="Users",
    columns=(
        ("id", "User ID"),
        ("username", "Name"),
        ("email", "Email"),
        ("status", "Status"),
        ("created_at", "Created At (UTC)"),
        ("updated_at", "Updated At (UTC)"),
    ),
)

EXPORT_SPECS: dict[str, ExportSpec] = {
    spec.module: spec for spec in (AUDIT_EXPORT_SPEC, USERS_EXPORT_SPEC)
}
