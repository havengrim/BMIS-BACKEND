from app.validation.patterns import PERMISSION_CODE_RE, SLUG_RE


def validate_permission_code(value: str) -> str:
    value = value.strip().lower()
    if not PERMISSION_CODE_RE.match(value):
        raise ValueError(
            "Permission code must be lowercase module.action format (e.g. users.read)"
        )
    return value


def validate_slug(
    value: str,
    *,
    field_label: str = "Value",
    error_message: str | None = None,
) -> str:
    value = value.strip().lower()
    if not SLUG_RE.match(value):
        if error_message:
            raise ValueError(error_message)
        raise ValueError(f"{field_label} must be lowercase letters, numbers, or underscores only")
    return value


def validate_non_empty_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("name must not be empty")
    return value
