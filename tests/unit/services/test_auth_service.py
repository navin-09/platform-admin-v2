"""Auth service unit tests — collaborators faked (see tests/unit/fakes.py).

Architecture: the ``auth`` fixture wires Fake* repositories + stubbed token/
password helpers onto ``auth_service``. Tests configure only what they need
(e.g. ``fakes.repo.admin = None`` for the unknown-admin path) and assert on
state + recorder lists. Sections group one service function's success/failure
cases.
"""

import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from jose import JWTError

from app.exceptions.exceptions import (
    AccountInactiveError,
    AccountLockedError,
    AuthenticationError,
    InvalidCredentialsError,
    InvalidOtpError,
    OtpThrottledError,
    PasswordResetFailedError,
    PasswordReuseError,
)
from app.models.enums import Status
from app.models.password_history import PasswordHistory
from app.models.password_reset_otp import PasswordResetOtp
from app.schemas.auth import (
    GenerateOtpRequest,
    LoginRequest,
    RefreshRequest,
    UpdatePasswordRequest,
    VerifyOtpRequest,
)
from app.services import auth_service
from app.utils.time import utcnow
from tests.unit.fakes import (
    FakeAuthRepository,
    FakeOtpRepository,
    FakePasswordHistoryRepository,
    FakeRbacService,
    active_admin,
)


@pytest.fixture()
def fakes(monkeypatch) -> SimpleNamespace:
    """Wire fakes + stubs onto the service; tests mutate ``fakes`` to steer."""
    fakes = SimpleNamespace(
        repo=FakeAuthRepository(admin=active_admin()),
        otp=FakeOtpRepository(),
        history=FakePasswordHistoryRepository(),
        rbac=FakeRbacService(permissions={"S1.R", "S2.R"}, roles={"super_admin"}),
        password_ok=True,  # verify_password result
    )
    monkeypatch.setattr(auth_service, "auth_repository", fakes.repo)
    monkeypatch.setattr(auth_service, "otp_repository", fakes.otp)
    monkeypatch.setattr(auth_service, "password_history_repository", fakes.history)
    monkeypatch.setattr(auth_service, "rbac_service", fakes.rbac)
    monkeypatch.setattr(auth_service, "verify_password", lambda *_a, **_k: fakes.password_ok)
    monkeypatch.setattr(auth_service, "hash_password", lambda _plain: "hashed")
    monkeypatch.setattr(auth_service, "create_access_token", lambda *a, **k: "access")
    monkeypatch.setattr(auth_service, "create_refresh_token", lambda *a, **k: "refresh")
    monkeypatch.setattr(
        auth_service,
        "decode_token",
        lambda *a, **k: {
            "type": "access",
            "user_id": str(fakes.repo.admin.id),
            "jti": "r1",
        },
    )
    return fakes


def _otp(*, verified: bool = False, expired: bool = False) -> PasswordResetOtp:
    return PasswordResetOtp(
        email="admin@example.com",
        expires_at=utcnow() - timedelta(minutes=1) if expired else utcnow() + timedelta(minutes=5),
        request_count=1,
        window_started_at=utcnow(),
        verified=verified,
    )


# --------------------------------------------------------------------------- #
# login
# --------------------------------------------------------------------------- #


async def test_login_success(fakes) -> None:
    token = await auth_service.login(LoginRequest(email="admin@example.com", password="pw"))

    assert token.access_token == "access"
    assert token.refresh_token == "refresh"
    assert fakes.repo.admin.current_refresh_jti == "r1"
    assert fakes.repo.saved == [fakes.repo.admin]


async def test_login_success_resets_failed_attempts(fakes) -> None:
    fakes.repo.admin.failed_login_attempts = 3
    fakes.repo.admin.locked_until = None

    await auth_service.login(LoginRequest(email="admin@example.com", password="pw"))

    assert fakes.repo.admin.failed_login_attempts == 0
    assert fakes.repo.admin.locked_until is None


async def test_login_failure_unknown_admin(fakes) -> None:
    fakes.repo.admin = None

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(LoginRequest(email="nope@example.com", password="pw"))


async def test_login_failure_wrong_password_increments_counter(fakes) -> None:
    fakes.password_ok = False

    with pytest.raises(InvalidCredentialsError) as exc_info:
        await auth_service.login(LoginRequest(email="admin@example.com", password="pw"))

    assert exc_info.value.code == "E_401_AUTH_INVALID_CREDENTIALS"
    assert fakes.repo.admin.failed_login_attempts == 1


async def test_login_failure_locks_account_at_max_attempts(fakes) -> None:
    fakes.password_ok = False
    fakes.repo.admin.failed_login_attempts = 4

    with pytest.raises(AccountLockedError):
        await auth_service.login(LoginRequest(email="admin@example.com", password="pw"))

    assert fakes.repo.admin.locked_until is not None
    assert fakes.repo.admin.failed_login_attempts == 0


async def test_login_failure_locked_account_skips_password_check(fakes, monkeypatch) -> None:
    fakes.repo.admin.locked_until = utcnow() + timedelta(minutes=10)
    verify = Mock()
    monkeypatch.setattr(auth_service, "verify_password", verify)

    with pytest.raises(AccountLockedError):
        await auth_service.login(LoginRequest(email="admin@example.com", password="pw"))

    verify.assert_not_called()


async def test_login_failure_expired_lockout_is_cleared(fakes) -> None:
    fakes.repo.admin.failed_login_attempts = 5
    fakes.repo.admin.locked_until = utcnow() - timedelta(minutes=1)

    await auth_service.login(LoginRequest(email="admin@example.com", password="pw"))

    assert fakes.repo.admin.locked_until is None
    assert fakes.repo.admin.failed_login_attempts == 0


async def test_login_failure_inactive_account(fakes) -> None:
    fakes.repo.admin = active_admin(status=Status.INACTIVE)

    with pytest.raises(AccountInactiveError):
        await auth_service.login(LoginRequest(email="admin@example.com", password="pw"))


# --------------------------------------------------------------------------- #
# get_admin_by_id / get_admin_from_payload
# --------------------------------------------------------------------------- #


async def test_get_admin_by_id_success(fakes) -> None:
    result = await auth_service.get_admin_by_id(fakes.repo.admin.id)
    assert result is fakes.repo.admin


async def test_get_admin_by_id_failure_unknown(fakes) -> None:
    fakes.repo.admin = None

    with pytest.raises(AuthenticationError):
        await auth_service.get_admin_by_id(uuid.uuid4())


async def test_get_admin_by_id_failure_inactive(fakes) -> None:
    fakes.repo.admin = active_admin(status=Status.INACTIVE)

    with pytest.raises(AccountInactiveError):
        await auth_service.get_admin_by_id(fakes.repo.admin.id)


async def test_get_admin_from_payload_success_current_access(fakes) -> None:
    fakes.repo.admin.current_refresh_jti = "r1"
    payload = {"type": "access", "user_id": str(fakes.repo.admin.id), "jti": "a1", "rjti": "r1"}

    result = await auth_service.get_admin_from_payload(payload)

    assert result is fakes.repo.admin


async def test_get_admin_from_payload_failure_stale_access_session(fakes) -> None:
    fakes.repo.admin.current_refresh_jti = "r2"
    payload = {"type": "access", "user_id": str(fakes.repo.admin.id), "jti": "a1", "rjti": "r1"}

    with pytest.raises(AuthenticationError):
        await auth_service.get_admin_from_payload(payload)


async def test_get_admin_from_payload_failure_missing_session(fakes) -> None:
    fakes.repo.admin.current_refresh_jti = None
    payload = {"type": "refresh", "user_id": str(fakes.repo.admin.id), "jti": "r1"}

    with pytest.raises(AuthenticationError):
        await auth_service.get_admin_from_payload(payload)


# --------------------------------------------------------------------------- #
# refresh
# --------------------------------------------------------------------------- #


async def test_refresh_success_rotates_session(fakes, monkeypatch) -> None:
    admin = fakes.repo.admin
    admin.current_refresh_jti = "r1"
    monkeypatch.setattr(
        auth_service,
        "decode_token",
        Mock(
            side_effect=[
                {"type": "refresh", "user_id": str(admin.id), "jti": "r1"},
                {"jti": "r2"},
            ]
        ),
    )

    token = await auth_service.refresh(RefreshRequest(refresh_token="r"))

    assert token.access_token == "access"
    assert token.refresh_token == "refresh"
    assert admin.current_refresh_jti == "r2"


async def test_refresh_failure_malformed_subject(fakes, monkeypatch) -> None:
    monkeypatch.setattr(
        auth_service,
        "decode_token",
        Mock(return_value={"type": "refresh", "user_id": "not-a-uuid"}),
    )

    with pytest.raises(AuthenticationError):
        await auth_service.refresh(RefreshRequest(refresh_token="r"))


async def test_refresh_failure_wrong_token_type(fakes, monkeypatch) -> None:
    monkeypatch.setattr(
        auth_service,
        "decode_token",
        Mock(return_value={"type": "access", "user_id": str(uuid.uuid4())}),
    )

    with pytest.raises(AuthenticationError):
        await auth_service.refresh(RefreshRequest(refresh_token="r"))


async def test_refresh_failure_invalid_token(fakes, monkeypatch) -> None:
    monkeypatch.setattr(auth_service, "decode_token", Mock(side_effect=JWTError("bad token")))

    with pytest.raises(AuthenticationError):
        await auth_service.refresh(RefreshRequest(refresh_token="r"))


async def test_refresh_failure_unknown_admin(fakes, monkeypatch) -> None:
    fakes.repo.admin = None
    monkeypatch.setattr(
        auth_service,
        "decode_token",
        Mock(return_value={"type": "refresh", "user_id": str(uuid.uuid4())}),
    )

    with pytest.raises(AuthenticationError):
        await auth_service.refresh(RefreshRequest(refresh_token="r"))


# --------------------------------------------------------------------------- #
# logout
# --------------------------------------------------------------------------- #


async def test_logout_success_clears_session_pointer(fakes) -> None:
    fakes.repo.admin.current_refresh_jti = "r1"

    await auth_service.logout(access_token="access-token")

    assert fakes.repo.admin.current_refresh_jti is None


async def test_logout_failure_invalid_token(fakes, monkeypatch) -> None:
    monkeypatch.setattr(auth_service, "decode_token", Mock(side_effect=JWTError("bad token")))

    with pytest.raises(AuthenticationError):
        await auth_service.logout(access_token="bad-token")


async def test_logout_failure_non_access_token(fakes, monkeypatch) -> None:
    monkeypatch.setattr(auth_service, "decode_token", Mock(return_value={"type": "refresh"}))

    with pytest.raises(AuthenticationError):
        await auth_service.logout(access_token="refresh-token")


async def test_logout_failure_malformed_user_id(fakes, monkeypatch) -> None:
    monkeypatch.setattr(
        auth_service, "decode_token", Mock(return_value={"type": "access", "user_id": "not-a-uuid"})
    )

    with pytest.raises(AuthenticationError):
        await auth_service.logout(access_token="access-token")


async def test_logout_failure_unknown_admin(fakes, monkeypatch) -> None:
    fakes.repo.admin = None
    monkeypatch.setattr(
        auth_service,
        "decode_token",
        Mock(return_value={"type": "access", "user_id": str(uuid.uuid4())}),
    )

    with pytest.raises(AuthenticationError):
        await auth_service.logout(access_token="access-token")


# --------------------------------------------------------------------------- #
# generate_otp (opaque: unknown/inactive admin still "succeeds")
# --------------------------------------------------------------------------- #


async def test_generate_otp_success_creates_row(fakes) -> None:
    await auth_service.generate_otp(GenerateOtpRequest(email="admin@example.com"))

    created = fakes.otp.saved[0]
    assert isinstance(created, PasswordResetOtp)
    assert created.request_count == 1


async def test_generate_otp_success_increments_within_window(fakes) -> None:
    fakes.otp.row = _otp()
    fakes.otp.row.request_count = 1

    await auth_service.generate_otp(GenerateOtpRequest(email="admin@example.com"))

    assert fakes.otp.row.request_count == 2
    assert fakes.otp.saved == [fakes.otp.row]


async def test_generate_otp_success_resets_window_after_expiry(fakes) -> None:
    fakes.otp.row = PasswordResetOtp(
        email="admin@example.com",
        expires_at=utcnow(),
        request_count=3,
        window_started_at=utcnow() - timedelta(minutes=20),
    )

    await auth_service.generate_otp(GenerateOtpRequest(email="admin@example.com"))

    assert fakes.otp.row.request_count == 1
    assert fakes.otp.saved == [fakes.otp.row]


async def test_generate_otp_failure_throttled_at_limit(fakes) -> None:
    fakes.otp.row = PasswordResetOtp(
        email="admin@example.com",
        expires_at=utcnow(),
        request_count=3,
        window_started_at=utcnow(),
    )

    with pytest.raises(OtpThrottledError):
        await auth_service.generate_otp(GenerateOtpRequest(email="admin@example.com"))


async def test_generate_otp_opaque_success_for_unknown_admin(fakes) -> None:
    fakes.repo.admin = None

    await auth_service.generate_otp(GenerateOtpRequest(email="nope@example.com"))


async def test_generate_otp_opaque_success_for_inactive_admin(fakes) -> None:
    fakes.repo.admin = active_admin(status=Status.INACTIVE)

    await auth_service.generate_otp(GenerateOtpRequest(email="admin@example.com"))


# --------------------------------------------------------------------------- #
# verify_otp
# --------------------------------------------------------------------------- #


async def test_verify_otp_success_marks_verified(fakes) -> None:
    fakes.otp.row = _otp()

    await auth_service.verify_otp(VerifyOtpRequest(email="admin@example.com", otp="12345"))

    assert fakes.otp.row.verified is True
    assert fakes.otp.saved == [fakes.otp.row]


async def test_verify_otp_failure_wrong_otp(fakes) -> None:
    fakes.otp.row = _otp()

    with pytest.raises(InvalidOtpError) as exc_info:
        await auth_service.verify_otp(VerifyOtpRequest(email="admin@example.com", otp="wrong"))

    assert exc_info.value.code == "E_400_AUTH_INVALID_OTP"


async def test_verify_otp_failure_unknown_admin_opaque(fakes) -> None:
    fakes.repo.admin = None

    with pytest.raises(InvalidOtpError) as exc_info:
        await auth_service.verify_otp(VerifyOtpRequest(email="nope@example.com", otp="12345"))

    assert exc_info.value.code == "E_400_AUTH_INVALID_OTP"


async def test_verify_otp_failure_expired(fakes) -> None:
    fakes.otp.row = _otp(expired=True)

    with pytest.raises(InvalidOtpError):
        await auth_service.verify_otp(VerifyOtpRequest(email="admin@example.com", otp="12345"))


async def test_verify_otp_failure_missing_row(fakes) -> None:
    with pytest.raises(InvalidOtpError):
        await auth_service.verify_otp(VerifyOtpRequest(email="admin@example.com", otp="12345"))


# --------------------------------------------------------------------------- #
# update_password
# --------------------------------------------------------------------------- #


async def test_update_password_success_clears_lockout_and_session(fakes) -> None:
    admin = fakes.repo.admin
    admin.failed_login_attempts = 4
    admin.locked_until = utcnow()
    admin.current_refresh_jti = "r1"
    fakes.otp.row = _otp(verified=True)
    fakes.password_ok = False  # the new password must NOT match history

    result = await auth_service.update_password(
        UpdatePasswordRequest(
            email="admin@example.com", new_password="S3cureP@ss", confirm_password="S3cureP@ss"
        )
    )

    assert result is admin
    assert admin.failed_login_attempts == 0
    assert admin.locked_until is None
    assert admin.current_refresh_jti is None
    assert fakes.repo.password_updates == [(admin, "hashed")]
    assert fakes.otp.deleted == ["admin@example.com"]


async def test_update_password_failure_reused_password(fakes) -> None:
    admin = fakes.repo.admin
    fakes.otp.row = _otp(verified=True)
    fakes.history.recent = [
        PasswordHistory(platform_admin_id=admin.id, hashed_password="oldhash", created_at=utcnow())
    ]
    fakes.password_ok = True  # new password matches a previous one

    with pytest.raises(PasswordReuseError):
        await auth_service.update_password(
            UpdatePasswordRequest(
                email="admin@example.com", new_password="S3cureP@ss", confirm_password="S3cureP@ss"
            )
        )


async def test_update_password_failure_unverified_otp(fakes) -> None:
    fakes.otp.row = _otp(verified=False)

    with pytest.raises(PasswordResetFailedError) as exc_info:
        await auth_service.update_password(
            UpdatePasswordRequest(
                email="admin@example.com", new_password="S3cureP@ss", confirm_password="S3cureP@ss"
            )
        )

    assert exc_info.value.code == "E_400_AUTH_PASSWORD_RESET_FAILED"


async def test_update_password_failure_expired_otp(fakes) -> None:
    fakes.otp.row = _otp(verified=True, expired=True)

    with pytest.raises(PasswordResetFailedError) as exc_info:
        await auth_service.update_password(
            UpdatePasswordRequest(
                email="admin@example.com", new_password="S3cureP@ss", confirm_password="S3cureP@ss"
            )
        )

    assert exc_info.value.code == "E_400_AUTH_PASSWORD_RESET_FAILED"


async def test_update_password_failure_unknown_admin_opaque(fakes) -> None:
    fakes.repo.admin = None

    with pytest.raises(PasswordResetFailedError) as exc_info:
        await auth_service.update_password(
            UpdatePasswordRequest(
                email="nope@example.com", new_password="S3cureP@ss", confirm_password="S3cureP@ss"
            )
        )

    assert exc_info.value.code == "E_400_AUTH_PASSWORD_RESET_FAILED"
