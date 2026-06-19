from __future__ import annotations


def normalize_eco_level(value: str | None) -> str | None:
    if value is None:
        return None

    v = str(value).lower().strip()
    if v in {"low", "moderate", "high"}:
        return v

    if any(
        phrase in v
        for phrase in (
            "maximum",
            "very sustainable",
            "as green as possible",
            "high eco",
            "high sustainability",
            "very eco",
        )
    ):
        return "high"

    if any(
        phrase in v
        for phrase in (
            "moderate",
            "actively",
            "eco-friendly",
            "somewhat",
            "mostly eco",
        )
    ):
        return "moderate"

    if any(
        phrase in v
        for phrase in (
            "low",
            "little greener",
            "a bit",
            "flexible",
            "green",
            "greener",
        )
    ):
        return "low"

    return None
