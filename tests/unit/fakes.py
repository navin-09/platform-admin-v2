"""Shared fake repositories for service unit tests (configure attributes, read recorders)."""

import uuid
from datetime import datetime
from typing import Any

from app.models.enums import Status
from app.models.password_history import PasswordHistory
from app.models.password_reset_otp import PasswordResetOtp
from app.models.platform_admin import PlatformAdmin
from app.models.role import Role
from app.models.screen import Screen


class FakeAuthRepository:
    """Fake for ``app.repositories.auth_repository`` (admin lookup/save)."""

    def __init__(self, *, admin: PlatformAdmin | None = None) -> None:
        self.admin = admin  # returned by get_admin_by_email / get_admin_by_id
        self.saved: list[PlatformAdmin] = []
        self.password_updates: list[tuple[PlatformAdmin, str]] = []

    async def get_admin_by_email(self, email: str) -> PlatformAdmin | None:
        return self.admin

    async def get_admin_by_id(self, admin_id: uuid.UUID) -> PlatformAdmin | None:
        return self.admin

    async def save_admin(self, admin: PlatformAdmin) -> PlatformAdmin:
        self.saved.append(admin)
        return admin

    async def update_admin_password(
        self, admin: PlatformAdmin, hashed_password: str
    ) -> PlatformAdmin:
        self.password_updates.append((admin, hashed_password))
        return admin


class FakeOtpRepository:
    """Fake for ``app.repositories.otp_repository``."""

    def __init__(self, *, row: PasswordResetOtp | None = None) -> None:
        self.row = row  # returned by get
        self.saved: list[PasswordResetOtp] = []
        self.deleted: list[str] = []

    async def get(self, email: str) -> PasswordResetOtp | None:
        return self.row

    async def save(self, row: PasswordResetOtp) -> PasswordResetOtp:
        self.saved.append(row)
        return row

    async def delete(self, email: str) -> None:
        self.deleted.append(email)


class FakePasswordHistoryRepository:
    """Fake for ``app.repositories.password_history_repository``."""

    def __init__(self, *, recent: list[PasswordHistory] | None = None) -> None:
        self.recent = recent or []  # returned by recent_for_admin
        self.added: list[PasswordHistory] = []
        self.trimmed: list[uuid.UUID] = []

    async def recent_for_admin(self, admin_id: uuid.UUID, limit: int) -> list[PasswordHistory]:
        return self.recent

    async def add(
        self, admin_id: uuid.UUID, hashed_password: str, created_at: datetime
    ) -> PasswordHistory:
        entry = PasswordHistory(
            platform_admin_id=admin_id, hashed_password=hashed_password, created_at=created_at
        )
        self.added.append(entry)
        return entry

    async def trim(self, admin_id: uuid.UUID, keep: int) -> None:
        self.trimmed.append(admin_id)


class FakeRbacService:
    """Whole-service double for ``app.services.rbac_service`` (used by auth tests)."""

    def __init__(
        self, *, permissions: set[str] | None = None, roles: set[str] | None = None
    ) -> None:
        self.permissions = permissions or set()
        self.roles = roles or set()

    async def permissions_for_admin(self, admin_id: uuid.UUID) -> set[str]:
        return self.permissions

    async def roles_for_admin(self, admin_id: uuid.UUID) -> set[str]:
        return self.roles


class FakeRbacRepository:
    """Fake for ``app.repositories.rbac_repository``."""

    def __init__(
        self,
        *,
        screen_perms: set[tuple[str, bool, bool]] | None = None,
        role_names: set[str] | None = None,
    ) -> None:
        self.screen_perms = screen_perms or set()
        self.role_names = role_names or set()
        self.assigned: list[uuid.UUID] = []

    async def screen_permissions_for_admin(
        self, admin_id: uuid.UUID
    ) -> set[tuple[str, bool, bool]]:
        return self.screen_perms

    async def role_names_for_admin(self, admin_id: uuid.UUID) -> set[str]:
        return self.role_names

    async def assign_super_admin(self, admin_id: uuid.UUID) -> None:
        self.assigned.append(admin_id)


class FakeUserRepository:
    """Fake for ``app.repositories.user_repository`` (mapped onto PlatformAdmin)."""

    def __init__(
        self,
        *,
        user: PlatformAdmin | None = None,
        email_owner: PlatformAdmin | None = None,
    ) -> None:
        self.user = user  # returned by get_user
        self.email_owner = email_owner  # returned by get_user_by_email
        self.users: list[PlatformAdmin] = []  # returned by list_users
        self.active_count = 1  # returned by count_active_admins
        self.created: list[PlatformAdmin] = []
        self.updated: list[tuple[PlatformAdmin, dict[str, Any]]] = []
        self.deleted: list[PlatformAdmin] = []

    async def get_user(self, user_id: uuid.UUID) -> PlatformAdmin | None:
        return self.user

    async def get_user_by_email(self, email: str) -> PlatformAdmin | None:
        return self.email_owner

    async def create_user(self, user: PlatformAdmin) -> PlatformAdmin:
        self.created.append(user)
        return user

    async def list_users(self, **kwargs: Any) -> tuple[list[PlatformAdmin], int]:
        return (self.users, len(self.users))

    async def update_user(self, user: PlatformAdmin, data: dict[str, Any]) -> PlatformAdmin:
        for key, value in data.items():
            setattr(user, key, value)
        self.updated.append((user, data))
        return user

    async def count_active_admins(self, exclude_id: uuid.UUID | None = None) -> int:
        return self.active_count

    async def delete_user(self, user: PlatformAdmin) -> None:
        self.deleted.append(user)


class FakeRoleRepository:
    """Fake for ``app.repositories.role_repository``."""

    def __init__(
        self,
        *,
        role: Role | None = None,
        role_by_name: Role | None = None,
    ) -> None:
        self.role = role  # returned by get_role
        self.role_by_name = role_by_name  # returned by get_role_by_name
        self.roles: list[Role] = []  # returned by list_roles
        self.permission_rows: list[tuple[str, int, bool, bool]] = []  # permissions_for_role
        self.permission_rows_by_role: dict[uuid.UUID, list[tuple[str, int, bool, bool]]] = {}
        self.created: list[Role] = []
        self.updated: list[tuple[Role, dict[str, Any]]] = []
        self.last_permissions: list[Any] | None = None  # permissions passed to update_role
        self.deleted: list[Role] = []

    async def get_role(self, role_id: uuid.UUID) -> Role | None:
        return self.role

    async def get_role_by_name(self, name: str) -> Role | None:
        return self.role_by_name

    async def create_role(self, role: Role, permissions: list[Any]) -> Role:
        self.created.append(role)
        return role

    async def list_roles(self, **kwargs: Any) -> tuple[list[Role], int]:
        return (self.roles, len(self.roles))

    async def permissions_for_role(self, role_id: uuid.UUID) -> list[tuple[str, int, bool, bool]]:
        return self.permission_rows

    async def permissions_for_roles(
        self, role_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[tuple[str, int, bool, bool]]]:
        return self.permission_rows_by_role

    async def update_role(
        self, role: Role, data: dict[str, Any], permissions: list[Any] | None = None
    ) -> Role:
        for key, value in data.items():
            setattr(role, key, value)
        self.updated.append((role, data))
        self.last_permissions = permissions
        return role

    async def delete_role(self, role: Role) -> None:
        self.deleted.append(role)


class FakeScreenRepository:
    """Fake for ``app.repositories.screen_repository``."""

    def __init__(
        self,
        *,
        screen: Screen | None = None,
        screen_by_code: Screen | None = None,
        next_code: str | None = None,
    ) -> None:
        self.screen = screen  # returned by get_screen
        self.screen_by_code = screen_by_code  # returned by get_screen_by_code
        self.next_code = next_code  # returned by next_screen_code
        self.screens: list[Screen] = []  # returned by list_screens
        self.created: list[Screen] = []
        self.created_kwargs: dict[str, Any] = {}
        self.updated: list[Screen] = []
        self.deleted: list[Screen] = []

    async def get_screen(self, screen_id: uuid.UUID) -> Screen | None:
        return self.screen

    async def get_screen_by_code(self, code: str) -> Screen | None:
        return self.screen_by_code

    async def next_screen_code(self) -> str:
        return self.next_code or "S1"

    async def list_screens(self, **kwargs: Any) -> tuple[list[Screen], int]:
        return (self.screens, len(self.screens))

    async def create_screen(self, screen: Screen, **kwargs: Any) -> Screen:
        self.created.append(screen)
        self.created_kwargs = kwargs
        return screen

    async def update_screen(self, screen: Screen, data: dict[str, Any]) -> Screen:
        for key, value in data.items():
            setattr(screen, key, value)
        self.updated.append(screen)
        return screen

    async def delete_screen(self, screen: Screen) -> None:
        self.deleted.append(screen)


class FakeHealthRepository:
    """Fake for ``app.repositories.health_repository``."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error

    async def ping(self) -> None:
        if self.error is not None:
            raise self.error


class FakeAuditRepository:
    """Fake for ``app.repositories.audit_repository``."""

    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.entries: list[Any] = []  # returned by list_audit_logs

    async def create_audit_log(self, **kwargs: Any) -> None:
        self.created.append(kwargs)

    async def list_audit_logs(self, **kwargs: Any) -> tuple[list[Any], int]:
        return (self.entries, len(self.entries))


def active_admin(**overrides: object) -> PlatformAdmin:
    """Build a PlatformAdmin row with sensible defaults for tests."""
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": "hash",
        "status": Status.ACTIVE,
    }
    fields.update(overrides)
    return PlatformAdmin(**fields)  # type: ignore[arg-type]
