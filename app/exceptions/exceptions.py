"""Domain error hierarchy with stable namespaced result codes."""

from typing import Any


class AppError(Exception):
    """Base for every domain error: status, stable code, message, and data."""

    status_code: int = 500
    code: str = "E_500_INTERNAL_ERROR"
    message: str = "Something went wrong. Please try again later."

    def __init__(self, *, data: dict[str, Any] | None = None) -> None:
        super().__init__(self.message)
        self.data = data


def field_errors(errors: list[tuple[str, str]]) -> dict[str, Any]:
    """Shape (field, issue) pairs into the ``data.errors`` payload."""
    return {"errors": [{"field": field, "issue": issue} for field, issue in errors]}


class AuthenticationError(AppError):
    """Raised when no valid access token authenticates the request."""

    status_code = 401
    code = "E_401_NOT_AUTHENTICATED"
    message = "Your session has expired. Please login again."


class InvalidCredentialsError(AuthenticationError):
    """Raised when the email/password does not match a Platform Admin."""

    code = "E_401_AUTH_INVALID_CREDENTIALS"
    message = "Invalid user credentials."


class AccountLockedError(AuthenticationError):
    """Raised when the account is temporarily locked after repeated failures."""

    code = "E_401_AUTH_ACCOUNT_LOCKED"
    message = "Your account has been temporarily locked. Please try again after 15 minutes"


class PermissionDeniedError(AppError):
    """Raised when the Current Admin lacks the required permission."""

    status_code = 403
    code = "E_403_FORBIDDEN"
    message = "You do not have permission to perform this action"


class AccountInactiveError(PermissionDeniedError):
    """Raised when an otherwise-valid admin's account is inactive."""

    code = "E_403_AUTH_ACCOUNT_INACTIVE"
    message = "User did not authorise to access the Admin Portal."


class UserNotFoundError(AppError):
    """Raised when a User does not exist."""

    status_code = 404
    code = "E_404_USR_NOT_FOUND"
    message = "User not found"


class RoleNotFoundError(AppError):
    """Raised when a Role does not exist."""

    status_code = 404
    code = "E_404_ROL_NOT_FOUND"
    message = "Role not found"


class ScreenNotFoundError(AppError):
    """Raised when a Screen does not exist."""

    status_code = 404
    code = "E_404_SCR_NOT_FOUND"
    message = "Screen not found"


class ConflictError(AppError):
    """Raised when a request violates a data constraint."""

    status_code = 409
    code = "E_409_CONFLICT"
    message = "A conflict occurred"


class EmailExistsError(ConflictError):
    """Raised when the email is already registered."""

    code = "E_409_USR_EMAIL_EXISTS"
    message = "Email is already registered"

    def __init__(self) -> None:
        super().__init__(data=field_errors([("email", self.message)]))


class LastAdminError(ConflictError):
    """Raised when deactivating the last active Platform Admin."""

    code = "E_409_USR_LAST_ADMIN"
    message = "Cannot deactivate the last active platform admin"


class RoleNameExistsError(ConflictError):
    """Raised when a Role with the same name already exists."""

    code = "E_409_ROL_NAME_EXISTS"
    message = "Role name already exists"

    def __init__(self) -> None:
        super().__init__(data=field_errors([("name", self.message)]))


class ScreenCodeExistsError(ConflictError):
    """Raised when a Screen with the same code already exists."""

    code = "E_409_SCR_CODE_EXISTS"
    message = "Screen code already exists"

    def __init__(self) -> None:
        super().__init__(data=field_errors([("code", self.message)]))


class ProtectedResourceError(ConflictError):
    """Raised when a request tries to delete or deactivate a protected resource."""

    code = "E_409_PROTECTED_RESOURCE"
    message = "This resource is protected and cannot be deleted or deactivated"


class ExportNotFoundError(AppError):
    """Raised when an export record does not exist or belongs to someone else."""

    status_code = 404
    code = "E_404_EXPORT_NOT_FOUND"
    message = "Export not found"


class ExportExpiredError(AppError):
    """Raised when the 24h single-user download link has expired (BRD §6.6)."""

    status_code = 410
    code = "E_410_EXPORT_EXPIRED"
    message = "The export link has expired. Please create a new export"


class ExportTooLargeError(AppError):
    """Raised when an export would exceed the 100,000-record per-file cap (BRD §6.6)."""

    status_code = 413
    code = "E_413_EXPORT_TOO_LARGE"
    message = "The export exceeds the maximum of 100,000 records. Narrow the filters and try again"


class InvalidOtpError(AppError):
    """Raised when the password-reset OTP is wrong or expired."""

    status_code = 400
    code = "E_400_AUTH_INVALID_OTP"
    message = "Invalid or expired OTP"


class OtpThrottledError(AppError):
    """Raised when password-reset OTP requests exceed the throttle window."""

    status_code = 429
    code = "E_429_AUTH_OTP_THROTTLED"
    message = "Too many OTP requests. Please try again later."


class PasswordReuseError(AppError):
    """Raised when the new password matches a previously used password."""

    status_code = 400
    code = "E_400_AUTH_PASSWORD_REUSED"
    message = "New password must not match a previous password"


class PasswordResetFailedError(AppError):
    """Raised when a password reset cannot be completed."""

    status_code = 400
    code = "E_400_AUTH_PASSWORD_RESET_FAILED"
    message = "Unable to reset password"


class ValidationError(AppError):
    """Raised when request fields fail validation."""

    status_code = 422
    code = "E_422_VALIDATION_FAILED"
    message = "Validation failed"


class ServiceUnavailableError(AppError):
    """Raised when a downstream dependency (e.g. the database) is down."""

    status_code = 503
    code = "E_503_HEALTH_DOWN"
    message = "Service is unhealthy"
