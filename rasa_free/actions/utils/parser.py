import re
from typing import Optional

KNOWN_CITIES = [
    "amsterdam", "lisbon", "barcelona", "paris", "rome", "berlin", "london",
    "vienna", "madrid", "copenhagen", "stockholm", "prague", "budapest",
    "munich", "brussels", "new york", "tokyo", "dubai", "edinburgh",
    "dublin", "warsaw", "zurich", "reykjavik", "tallinn", "florence",
]


def title_city(value: Optional[str]) -> Optional[str]:
    return value.strip().title() if value and value.strip() else None


def extract_route(text: str) -> tuple[Optional[str], Optional[str]]:
    lower = text.lower()
    match = re.search(
        r"\bfrom\s+([a-zA-Z ]+?)\s+to\s+([a-zA-Z ]+?)(?:[?.!,]|$|\s+(?:by|on|under|for|next|in)\b)",
        lower,
    )
    if match:
        return title_city(match.group(1)), title_city(match.group(2))

    from_match = re.search(
        r"\bfrom\s+([a-zA-Z ]+?)(?:[?.!,]|$|\s+(?:to|by|on|under|for|next|in)\b)",
        lower,
    )
    to_match = re.search(
        r"\bto\s+([a-zA-Z ]+?)(?:[?.!,]|$|\s+(?:from|by|on|under|for|next|in)\b)",
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
    lower = text.lower()
    match = re.search(r"\b(?:in|for|to)\s+([a-zA-Z ]+?)(?:\s+under|[?.!,]|$)", lower)
    if match:
        candidate = match.group(1).strip()
        for city in KNOWN_CITIES:
            if re.search(rf"\b{re.escape(city)}\b", candidate):
                return title_city(city)

    _, destination = extract_route(text)
    if destination:
        return destination

    for city in KNOWN_CITIES:
        if re.search(rf"\b{re.escape(city)}\b", lower):
            return title_city(city)
    return None


def extract_budget(text: str) -> Optional[float]:
    match = re.search(
        r"(?:under|below|budget|maximum|max|about|around)?\s*(?:€|eur|euros)?\s*(\d{2,6})",
        text.lower(),
    )
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def extract_transport_mode(text: str) -> Optional[str]:
    lower = text.lower()
    aliases = {
        "flight": ("flight", "fly", "flying", "plane", "airplane"),
        "train": ("train", "rail"),
        "bus": ("bus", "coach"),
        "car": ("car", "driving", "drive"),
        "electric_car": ("electric car", "ev"),
        "ferry": ("ferry", "boat"),
        "walking": ("walking", "walk", "on foot", "by foot", "travel via foot"),
    }
    for mode, terms in aliases.items():
        if any(re.search(rf"\b{re.escape(term)}\b", lower) for term in terms):
            return mode
    return None
