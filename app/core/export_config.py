"""Per-module export specifications: authorized fields, labels, classification.

The BRD (§6.6 / §19.2) requires every export to carry only authorized fields,
masking where needed, its classification, and retained filters. Each module that
supports export declares one ``ExportSpec`` here; the engine stays generic.
"""

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


# Audit exports are Restricted (BRD §17.7). Details/payload/response are included
# as JSON text for complete evidence; credentials are already redacted at write
# time by the audit pipeline itself (app/utils/redact.py).
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


# Users (Platform Admins) — Confidential per BRD §4.4 (user screens).
# Credentials and session state (hashed_password, refresh jti, lock state) are
# deliberately NOT in the allow-list — BRD §6.6: credentials never exportable.
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
