"""Reusable validated field types shared across request DTOs."""

import re
from functools import partial
from typing import Annotated

from pydantic import AfterValidator, Field
from pydantic import EmailStr as PydanticEmailStr

from app.utils.limits import EMAIL_MAX_LENGTH, NAME_MAX_LENGTH, SCREEN_CODE_MAX_LENGTH
from app.utils.validate import validate_permission_format, validate_slug_format

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


# Pydantic's EmailStr validates the *format* but imposes no length limit, so the
# shared max length is added here so the DTO rejects over-long emails before the
# database's VARCHAR(255) column would (ADR-0021).
EmailStr = Annotated[PydanticEmailStr, Field(max_length=EMAIL_MAX_LENGTH)]

NameStr = Annotated[
    str,
    Field(min_length=1, max_length=NAME_MAX_LENGTH, examples=["john-doe"]),
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

ScreenCodeStr = Annotated[
    str,
    Field(min_length=1, max_length=SCREEN_CODE_MAX_LENGTH, examples=["S5"]),
    AfterValidator(partial(validate_slug_format, field_label="Code")),
]

PermissionStr = Annotated[
    str,
    Field(min_length=3, max_length=SCREEN_CODE_MAX_LENGTH + 2, examples=["S1.W"]),
    AfterValidator(partial(validate_permission_format, field_label="Permission")),
]
