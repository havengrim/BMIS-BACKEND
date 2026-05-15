from app.validation.patterns import DANGEROUS_INPUT_RE, PHONE_RE, TOTP_CODE_RE, USERNAME_RE


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def validate_safe_text(
    value: str,
    *,
    field_label: str = "Field",
    min_length: int = 1,
    max_length: int | None = None,
) -> str:
    value = _normalize_text(value)
    if len(value) < min_length:
        raise ValueError(f"{field_label} must not be empty")
    if max_length is not None and len(value) > max_length:
        raise ValueError(f"{field_label} must be at most {max_length} characters")
    if DANGEROUS_INPUT_RE.search(value):
        raise ValueError(f"{field_label} contains potentially unsafe content")
    return value


def validate_optional_safe_text(
    value: str | None,
    *,
    field_label: str = "Field",
    max_length: int | None = None,
) -> str | None:
    if value is None:
        return None
    return validate_safe_text(
        value,
        field_label=field_label,
        min_length=1,
        max_length=max_length,
    )


def validate_username(value: str) -> str:
    value = value.strip()
    if not USERNAME_RE.match(value):
        raise ValueError(
            "Username must be 3-32 chars and contain only letters, numbers, underscores, dots, or hyphens"
        )
    return value


def validate_phone_number(value: str | None) -> str | None:
    if value is None:
        return None
    value = _normalize_text(value)
    if not PHONE_RE.match(value):
        raise ValueError("Invalid contact number format")
    return value


def validate_totp_code(value: str) -> str:
    value = value.strip()
    if not TOTP_CODE_RE.match(value):
        raise ValueError("TOTP code must be exactly 6 digits")
    return value


def validate_password_input(value: str, *, min_length: int = 8, max_length: int = 128) -> str:
    value = value.strip()
    if len(value) < min_length:
        raise ValueError(f"Password must be at least {min_length} characters")
    if len(value) > max_length:
        raise ValueError(f"Password must be at most {max_length} characters")
    return value
