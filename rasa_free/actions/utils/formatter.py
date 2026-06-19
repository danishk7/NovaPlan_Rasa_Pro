from rasa_sdk import Tracker


def latest_text(tracker: Tracker) -> str:
    return (tracker.latest_message or {}).get("text", "") or ""


def custom_message(msg_type: str, data: dict) -> dict:
    """Wrap rich payload for frontend: { custom: { type, data } } via json_message."""
    return {"type": msg_type, "data": data}


def format_travel_dates(dates_str: str) -> str:
    """Parse natural language date strings into a clean start–end display.

    Examples:
        "15 june for 5 days"   → "15 Jun – 20 Jun"
        "15-20 June"           → "15 Jun – 20 Jun"
        "July 10-17"           → "10 Jul – 17 Jul"
        "next weekend"         → "next weekend"  (unchanged)
        "—"                    → "—"
    """
    import re as _re
    from datetime import datetime, timedelta

    if not dates_str or not isinstance(dates_str, str):
        return dates_str or "—"
    raw = dates_str.strip()
    if raw in ("—", "", "flexible", "Flexible"):
        return raw

    MONTHS = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10,
        "november": 11, "december": 12,
    }
    lower = raw.lower()
    now_year = datetime.now().year

    # Pattern: "15 june for 5 days" or "15 june for 3 nights"
    m = _re.search(
        r"(\d{1,2})\s+([a-z]+)\s+for\s+(\d+)\s*(days?|nights?)",
        lower,
    )
    if m:
        day   = int(m.group(1))
        month = MONTHS.get(m.group(2)[:3])
        count = int(m.group(3))
        if month:
            try:
                start = datetime(now_year, month, day)
                end   = start + timedelta(days=count)
                return f"{start.strftime('%-d %b')} – {end.strftime('%-d %b')}"
            except ValueError:
                pass

    # Pattern: "15-20 june" or "june 15-20" or "15 – 20 june"
    m = _re.search(
        r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([a-z]+)",
        lower,
    )
    if m:
        d1    = int(m.group(1))
        d2    = int(m.group(2))
        month = MONTHS.get(m.group(3)[:3])
        if month:
            try:
                start = datetime(now_year, month, d1)
                end   = datetime(now_year, month, d2)
                return f"{start.strftime('%-d %b')} – {end.strftime('%-d %b')}"
            except ValueError:
                pass

    # Pattern: "july 10-17"
    m = _re.search(
        r"([a-z]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2})",
        lower,
    )
    if m:
        month = MONTHS.get(m.group(1)[:3])
        d1    = int(m.group(2))
        d2    = int(m.group(3))
        if month:
            try:
                start = datetime(now_year, month, d1)
                end   = datetime(now_year, month, d2)
                return f"{start.strftime('%-d %b')} – {end.strftime('%-d %b')}"
            except ValueError:
                pass

    # Pattern: single date "15 june" — no range, return as-is capitalised
    m = _re.search(r"(\d{1,2})\s+([a-z]+)", lower)
    if m:
        day   = int(m.group(1))
        month = MONTHS.get(m.group(2)[:3])
        if month:
            try:
                start = datetime(now_year, month, day)
                return start.strftime("%-d %b")
            except ValueError:
                pass

    # Fallback: return capitalised original
    return raw.capitalize()

def safe_float(value, default=0.0):
    try:
        return float(str(value).replace("€", "").replace(",", "").strip())
    except (TypeError, ValueError, AttributeError):
        return default