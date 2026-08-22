import re
import uuid
from datetime import datetime
from functools import partial
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserStatus
from app.schemas.common import Pagination
from app.utils.validate import validate_slug_format

PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,13}$")
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 13
CREDENTIAL_STRENGTH_RULES = (
    "Password must be 8 to 13 characters and include an uppercase letter, a "
    "lowercase letter, a number, and a special character"
)
PASSWORD_EXAMPLE = "S3cureP@ss"  # noqa: S105  # nosec B105  (example shown in OpenAPI docs, not a real secret)


def validate_password_strength(value: str) -> str:
    if not PASSWORD_PATTERN.fullmatch(value):
        raise ValueError(CREDENTIAL_STRENGTH_RULES)
    return value


NameStr = Annotated[
    str,
    Field(min_length=1, max_length=255, examples=["john-doe"]),
    AfterValidator(partial(validate_slug_format, field_label="Name")),
]

PasswordStr = Annotated[
    str,
    Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        examples=[PASSWORD_EXAMPLE],
        description=CREDENTIAL_STRENGTH_RULES,
    ),
    AfterValidator(validate_password_strength),
]

CODE_CREATED = "S_201_USR_CREATED"
MSG_CREATED = "User created successfully"
CODE_LISTED = "S_200_USR_LIST_OK"
MSG_LISTED = "Users fetched successfully"
CODE_FETCHED = "S_200_USR_FETCH_OK"
MSG_FETCHED = "User fetched successfully"
CODE_UPDATED = "S_200_USR_UPDATED"
MSG_UPDATED = "User updated successfully"
CODE_DELETED = "S_200_USR_DELETED"
MSG_DELETED = "User deleted successfully"


class UserCreate(BaseModel):
    name: NameStr
    email: EmailStr
    password: PasswordStr
    status: UserStatus = UserStatus.ACTIVE


class UserUpdate(BaseModel):
    """Partial update (PATCH) — only provided fields are applied."""

    name: NameStr | None = None
    email: EmailStr | None = None
    status: UserStatus | None = None


class UserReplace(BaseModel):
    """Full replace (PUT) — name/email/password required; status unchanged."""

    name: NameStr
    email: EmailStr
    password: PasswordStr


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    status: UserStatus
    created_at: datetime
    updated_at: datetime


class UserListData(BaseModel):
    data: list[UserRead]
    pagination: Pagination
