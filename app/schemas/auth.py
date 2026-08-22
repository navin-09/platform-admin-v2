from pydantic import BaseModel, EmailStr, Field

CODE_LOGIN_OK = "S_200_AUTH_LOGIN_OK"
MSG_LOGIN_OK = "Login successful"
CODE_REFRESH_OK = "S_200_AUTH_REFRESH_OK"
MSG_REFRESH_OK = "Token refreshed"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, description="Admin account password (must not be empty)")


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105  ("bearer" is an OAuth token type, not a secret)
