import math
from typing import Any


def require_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def finite_float(value: float | int, field: str, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(numeric):
        raise ValueError(f"{field} must be finite")
    if minimum is not None and numeric < minimum:
        raise ValueError(f"{field} must be >= {minimum}, got {value}")
    if maximum is not None and numeric > maximum:
        raise ValueError(f"{field} must be <= {maximum}, got {value}")
    return numeric


def nonnegative_int(value: int, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    try:
        integer = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if integer < 0:
        raise ValueError(f"{field} must be nonnegative")
    return integer


def positive_limit(value: int | None, field: str = "limit") -> int | None:
    if value is None:
        return None
    integer = nonnegative_int(value, field)
    if integer == 0:
        raise ValueError(f"{field} must be positive when provided")
    return integer


def validate_choice(value: str, allowed: set[str], field: str) -> str:
    if value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"Invalid {field}: {value}. Allowed: {allowed_values}")
    return value


def validate_metadata(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("metadata must be an object")
    return value
