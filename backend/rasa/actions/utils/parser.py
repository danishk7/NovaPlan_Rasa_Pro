import re
from datetime import date, datetime, timedelta
from typing import Optional

from metadata import KNOWN_CITIES, MONTHS, PARSER_TRANSPORT_ALIASES

STOP_WORDS = (
    "by", "on", "under", "for", "next", "in", "with", "budget", "from", "to",
    "tomorrow", "today", "weekend", "people", "person", "traveller", "traveler",
)

CITY_PREFIX_RE = re.compile(
    r"^(?:to|from|travelling to|traveling to|going to|go to|destination is|origin is|i want to travel to|i want to go to)\s+(.+)$",
    re.IGNORECASE,
)


def title_city(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = CITY_PREFIX_RE.sub(r"\1", value.strip())
    value = re.sub(r"[^a-zA-Z\s-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return None
    # Prefer known city if phrase contains one, e.g. "travelling to paris next week".
    low = value.lower()
    for city in KNOWN_CITIES:
        if re.search(rf"\b{re.escape(city)}\b", low):
            return city.title()
    # Trim at common stop words.
    parts = []
    for token in value.split():
        if token.lower() in STOP_WORDS:
            break
        parts.append(token)
    return " ".join(parts).title() if parts else None


def clean_city_phrase(value: Optional[str]) -> Optional[str]:
    return title_city(value)


def extract_route(text: str) -> tuple[Optional[str], Optional[str]]:
    lower = (text or "").lower().strip()
    if not lower:
        return None, None

    match = re.search(
        r"\bfrom\s+([a-zA-Z ]+?)\s+to\s+([a-zA-Z ]+?)(?:[?.!,]|$|\s+(?:by|on|under|for|next|in|with)\b)",
        lower,
    )
    if match:
        return title_city(match.group(1)), title_city(match.group(2))

    from_match = re.search(
        r"\bfrom\s+([a-zA-Z ]+?)(?:[?.!,]|$|\s+(?:to|by|on|under|for|next|in|with)\b)",
        lower,
    )
    to_match = re.search(
        r"\b(?:to|travelling to|traveling to|going to|destination is)\s+([a-zA-Z ]+?)(?:[?.!,]|$|\s+(?:from|by|on|under|for|next|in|with)\b)",
        lower,
    )
    if from_match and not to_match:
        return title_city(from_match.group(1)), None
    if to_match and not from_match:
        return None, title_city(to_match.group(1))

    found = [city for city in KNOWN_CITIES if re.search(rf"\b{re.escape(city)}\b", lower)]
    if len(found) >= 2:
        return title_city(found[0]), title_city(found[1])
    if len(found) == 1:
        return None, title_city(found[0])
    return None, None


def extract_destination(text: str) -> Optional[str]:
    lower = (text or "").lower().strip()
    if not lower:
        return None

    patterns = [
        r"\b(?:to|travelling to|traveling to|going to|go to|destination is)\s+([a-zA-Z ]+?)(?:\s+(?:under|by|on|for|next|in|with)\b|[?.!,]|$)",
        r"\b(?:cultural tips for|culture tips for|cultural information for|cultural info for|tips for|about)\s+([a-zA-Z ]+?)(?:[?.!,]|$)",
        r"\b(?:hotels in|hotel in|activities in|things to do in)\s+([a-zA-Z ]+?)(?:\s+(?:under|below|budget|for)\b|[?.!,]|$)",
        r"^([a-zA-Z ]+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            candidate = title_city(match.group(1))
            if candidate:
                return candidate

    _, destination = extract_route(text)
    return destination


def extract_origin(text: str) -> Optional[str]:
    origin, _ = extract_route(text)
    if origin:
        return origin
    lower = (text or "").lower().strip()
    match = re.search(r"\b(?:from|origin is)\s+([a-zA-Z ]+?)(?:[?.!,]|$|\s+(?:to|by|on|under|for|next|in|with)\b)", lower)
    return title_city(match.group(1)) if match else None


def extract_budget(text: str) -> Optional[float]:
    match = re.search(
        r"(?:under|below|budget|maximum|max|about|around)?\s*(?:€|eur|euros)?\s*(\d{2,6})",
        (text or "").lower(),
    )
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def extract_transport_mode(text: str) -> Optional[str]:
    lower = (text or "").lower()
    for mode, terms in PARSER_TRANSPORT_ALIASES.items():
        if any(re.search(rf"\b{re.escape(term)}\b", lower) for term in terms):
            return mode
    return None


def extract_review_choice(text: str) -> Optional[str]:
    lower = (text or "").lower().strip()
    if re.search(r"\b(confirm|book|yes|looks good|go ahead|okay|ok)\b", lower):
        return "confirm"
    if re.search(r"\b(modify|change|edit|update|different)\b", lower):
        return "modify"
    if re.search(r"\b(cancel|stop|abort|nevermind|never mind)\b", lower):
        return "cancel"
    return None



def _parse_explicit_travel_dates(text: str) -> list[date]:
    lower = (text or "").lower().strip()
    today = date.today()
    parsed: list[date] = []

    # ISO dates: 2026-06-24
    for value in re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", lower):
        try:
            parsed.append(datetime.strptime(value, "%Y-%m-%d").date())
        except ValueError:
            pass

    # EU numeric dates: 24/06/2026, 24-06-2026, 24.06.2026
    for value in re.findall(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b", lower):
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                parsed.append(datetime.strptime(value, fmt).date())
                break
            except ValueError:
                continue

    for day_s, month_s, year_s in re.findall(r"\b(\d{1,2})\s+([a-z]+)(?:\s+(20\d{2}))?\b", lower):
        month = MONTHS.get(month_s) or MONTHS.get(month_s[:3])
        if not month:
            continue
        year = int(year_s) if year_s else today.year
        try:
            parsed.append(date(year, month, int(day_s)))
        except ValueError:
            pass
    return parsed


def _duration_days(text: str) -> Optional[int]:
    lower = (text or "").lower()
    m = re.search(r"\bfor\s+(\d{1,2})\s+days?\b", lower)
    if not m:
        return None
    try:
        days = int(m.group(1))
        return days if days > 0 else None
    except ValueError:
        return None


def extract_travel_date(text: str) -> Optional[str]:
    lower = (text or "").lower().strip()
    today = date.today()

    if "tomorrow" in lower:
        start = today + timedelta(days=1)
        days = _duration_days(lower)
        if days:
            return f"{start.isoformat()} to {(start + timedelta(days=days)).isoformat()}"
        return start.isoformat()
    if "today" in lower:
        start = today
        days = _duration_days(lower)
        if days:
            return f"{start.isoformat()} to {(start + timedelta(days=days)).isoformat()}"
        return start.isoformat()

    explicit_dates = _parse_explicit_travel_dates(lower)
    if len(explicit_dates) >= 2:
        return f"{explicit_dates[0].isoformat()} to {explicit_dates[1].isoformat()}"
    if len(explicit_dates) == 1:
        start = explicit_dates[0]
        days = _duration_days(lower)
        if days:
            return f"{start.isoformat()} to {(start + timedelta(days=days)).isoformat()}"
        return start.isoformat()

    # Keep natural relative dates for the LLM/business layer.
    rel = re.search(r"\b(next\s+(?:weekend|week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b", lower)
    if rel:
        return rel.group(1)
    return None


def is_past_travel_date(value: Optional[str]) -> bool:
    if not value:
        return False
    value = str(value).strip().lower()
    today = date.today()

    # Validate the first explicit date in normalized ranges and raw user text.
    explicit_dates = _parse_explicit_travel_dates(value)
    if explicit_dates:
        return explicit_dates[0] <= today
    return False

def infer_slot_updates(text: str, current_slots: dict) -> dict:
    updates: dict = {}
    origin, destination = extract_route(text)

    if not current_slots.get("origin") and origin:
        updates["origin"] = origin

    if not current_slots.get("destination"):
        dest = destination or extract_destination(text)
        if dest and dest.lower() != str(current_slots.get("origin") or "").lower():
            updates["destination"] = dest

    if not current_slots.get("travel_dates"):
        travel_date = extract_travel_date(text)
        if travel_date:
            updates["travel_dates"] = travel_date

    if not current_slots.get("transport_mode"):
        mode = extract_transport_mode(text)
        if mode:
            updates["transport_mode"] = mode

    if not current_slots.get("budget_amount"):
        budget = extract_budget(text)
        if budget:
            updates["budget_amount"] = budget

    if not current_slots.get("awaiting_review"):
        choice = extract_review_choice(text)
        if choice:
            updates["awaiting_review"] = choice

    return updates
