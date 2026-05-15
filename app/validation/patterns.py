import re

# Common reusable regex patterns
PERMISSION_CODE_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
SLUG_RE = re.compile(r"^[a-z0-9_]+$")
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
PHONE_RE = re.compile(r"^\+?[0-9()\-\s]{7,20}$")
TOTP_CODE_RE = re.compile(r"^\d{6}$")

# Typical payload signatures for XSS / SQLi attempts
DANGEROUS_INPUT_RE = re.compile(
	r"(<\s*/?\s*script\b|javascript:|on\w+\s*=|--|/\*|\*/|;\s*(drop|alter|truncate|delete|update|insert)\b|union\s+select)",
	re.IGNORECASE,
)
