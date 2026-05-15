from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

from app.validation.common_validators import (
    validate_optional_safe_text,
    validate_password_input,
    validate_phone_number,
    validate_safe_text,
    validate_totp_code,
    validate_username,
)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None   # required when TOTP is enabled

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_input(v)

    @field_validator("totp_code")
    @classmethod
    def validate_login_totp_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validate_totp_code(v)


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    contact_number: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_register_username(cls, v: str) -> str:
        return validate_username(v)

    @field_validator("password")
    @classmethod
    def validate_register_password(cls, v: str) -> str:
        return validate_password_input(v)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_required_names(cls, v: str) -> str:
        return validate_safe_text(v, field_label="Name", min_length=1, max_length=100)

    @field_validator("middle_name")
    @classmethod
    def validate_middle_name(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Middle name", max_length=100)

    @field_validator("contact_number")
    @classmethod
    def validate_register_contact(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number(v)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    mfa_required: bool = False        # True → frontend must ask for TOTP code


class RefreshRequest(BaseModel):
    refresh_token: str


class GoogleTokenRequest(BaseModel):
    """For SPA/mobile: send Google id_token, receive BMIS JWT tokens."""
    id_token: str


# ─── TOTP ────────────────────────────────────────────────────────────────────

class TOTPSetupResponse(BaseModel):
    """Returned when a user initiates TOTP setup."""
    provisioning_uri: str             # otpauth:// URI → encode as QR code on frontend
    secret: str                       # raw base32 secret (show as backup code)


class TOTPVerifyRequest(BaseModel):
    """Used to confirm TOTP setup or to verify during login."""
    code: str                         # 6-digit code from authenticator app

    @field_validator("code")
    @classmethod
    def validate_verify_code(cls, v: str) -> str:
        return validate_totp_code(v)


class TOTPDisableRequest(BaseModel):
    """Requires the current TOTP code to disable MFA."""
    code: str

    @field_validator("code")
    @classmethod
    def validate_disable_code(cls, v: str) -> str:
        return validate_totp_code(v)
