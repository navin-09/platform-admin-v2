from enum import Enum, StrEnum


class Status(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ExportStatus(StrEnum):
    """Lifecycle of an export record (BRD: pending → ready; expired after 24h)."""

    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


class AuditAction(StrEnum):
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGIN_LOCKOUT = "auth.login.lockout"
    REFRESH_SUCCESS = "auth.refresh.success"
    REFRESH_FAILURE = "auth.refresh.failure"
    LOGOUT = "auth.logout"
    OTP_REQUESTED = "auth.password_reset.otp_requested"  # noqa: S105
    OTP_THROTTLED = "auth.password_reset.otp_throttled"  # noqa: S105
    OTP_VERIFY_SUCCESS = "auth.password_reset.otp_verify_success"  # noqa: S105
    OTP_VERIFY_FAILURE = "auth.password_reset.otp_verify_failure"  # noqa: S105
    PASSWORD_RESET_SUCCESS = "auth.password_reset.success"  # noqa: S105  # nosec B105
    PASSWORD_RESET_FAILURE = "auth.password_reset.failure"  # noqa: S105  # nosec B105
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_REPLACE = "user.replace"
    USER_DELETE = "user.delete"
    ROLE_CREATE = "role.create"
    ROLE_UPDATE = "role.update"
    ROLE_DELETE = "role.delete"
    SCREEN_CREATE = "screen.create"
    SCREEN_UPDATE = "screen.update"
    SCREEN_DELETE = "screen.delete"
    AUDIT_READ = "audit.read"
    ACCESS_DENIED = "access.denied"
    EXPORT_GENERATED = "export.generated"
    EXPORT_DOWNLOADED = "export.downloaded"


class AuditResourceType(StrEnum):
    AUTH = "auth"
    USER = "user"
    ROLE = "role"
    SCREEN = "screen"
    AUDIT = "audit"
    EXPORT = "export"


class ActorType(StrEnum):
    ADMIN = "admin"
    SYSTEM = "system"


class PermissionName(StrEnum):
    """The fixed set of permissions routes can require (written ``<screen>.<R|W>``)."""

    USERS_READ = "S1.R"
    USERS_WRITE = "S1.W"
    AUDIT_READ = "S2.R"
    ROLES_READ = "S3.R"
    ROLES_WRITE = "S3.W"
    SCREENS_READ = "S4.R"
    SCREENS_WRITE = "S4.W"


def enum_values(enum_cls: type[Enum]) -> list[str]:
    """Return the stored values for an enum (used by SQLAlchemy's SAEnum)."""
    return [str(member.value) for member in enum_cls]


# List-endpoint filter enums: each mirrors a base enum plus an ALL sentinel.
# Kept separate from the base enum so "All" never leaks into persisted data
# (e.g. a real resource's status, or a recorded audit action).


class StatusFilter(StrEnum):
    ALL = "All"
    ACTIVE = Status.ACTIVE.value
    INACTIVE = Status.INACTIVE.value


class AuditActionFilter(StrEnum):
    ALL = "All"
    LOGIN_SUCCESS = AuditAction.LOGIN_SUCCESS.value
    LOGIN_FAILURE = AuditAction.LOGIN_FAILURE.value
    LOGIN_LOCKOUT = AuditAction.LOGIN_LOCKOUT.value
    REFRESH_SUCCESS = AuditAction.REFRESH_SUCCESS.value
    REFRESH_FAILURE = AuditAction.REFRESH_FAILURE.value
    LOGOUT = AuditAction.LOGOUT.value
    OTP_REQUESTED = AuditAction.OTP_REQUESTED.value
    OTP_THROTTLED = AuditAction.OTP_THROTTLED.value
    OTP_VERIFY_SUCCESS = AuditAction.OTP_VERIFY_SUCCESS.value
    OTP_VERIFY_FAILURE = AuditAction.OTP_VERIFY_FAILURE.value
    PASSWORD_RESET_SUCCESS = AuditAction.PASSWORD_RESET_SUCCESS.value
    PASSWORD_RESET_FAILURE = AuditAction.PASSWORD_RESET_FAILURE.value
    USER_CREATE = AuditAction.USER_CREATE.value
    USER_UPDATE = AuditAction.USER_UPDATE.value
    USER_REPLACE = AuditAction.USER_REPLACE.value
    USER_DELETE = AuditAction.USER_DELETE.value
    ROLE_CREATE = AuditAction.ROLE_CREATE.value
    ROLE_UPDATE = AuditAction.ROLE_UPDATE.value
    ROLE_DELETE = AuditAction.ROLE_DELETE.value
    SCREEN_CREATE = AuditAction.SCREEN_CREATE.value
    SCREEN_UPDATE = AuditAction.SCREEN_UPDATE.value
    SCREEN_DELETE = AuditAction.SCREEN_DELETE.value
    AUDIT_READ = AuditAction.AUDIT_READ.value
    ACCESS_DENIED = AuditAction.ACCESS_DENIED.value
    EXPORT_GENERATED = AuditAction.EXPORT_GENERATED.value
    EXPORT_DOWNLOADED = AuditAction.EXPORT_DOWNLOADED.value


class AuditResourceTypeFilter(StrEnum):
    ALL = "All"
    AUTH = AuditResourceType.AUTH.value
    USER = AuditResourceType.USER.value
    ROLE = AuditResourceType.ROLE.value
    SCREEN = AuditResourceType.SCREEN.value
    AUDIT = AuditResourceType.AUDIT.value
    EXPORT = AuditResourceType.EXPORT.value


class AuditActorTypeFilter(StrEnum):
    ALL = "All"
    ADMIN = ActorType.ADMIN.value
    SYSTEM = ActorType.SYSTEM.value


def resolve_filter[T: StrEnum](value: StrEnum, base: type[T]) -> T | None:
    """Map a filter member to its base-enum member, or None for the ALL sentinel."""
    return None if value.name == "ALL" else base(value.value)
