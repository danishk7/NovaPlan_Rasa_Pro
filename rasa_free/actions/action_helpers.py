"""Shared mappers for Rasa rich messages."""

from typing import Any


def map_transport_options(options: list[dict]) -> list[dict]:
    return [
        {
            "mode": o.get("mode", "unknown"),
            "duration": f"{o.get('duration_hrs', '?')}h",
            "cost": f"€{o.get('price_eur', '?')}",
            "emissions": o.get("carbon_kg", 0),
            "eco_rating": o.get("co2_colour", "amber"),
            "details": o.get("notes", ""),
        }
        for o in options
    ]


def map_hotels(hotels: list[dict]) -> list[dict]:
    mapped = []
    for h in hotels:
        carbon = h.get("carbon_kg")
        mapped.append({
            "name": h.get("name", "Unknown Hotel"),
            "rating": min(5, round(float(h.get("rating", 4)) / 2)) if h.get("rating") else 4,
            "price": f"€{h.get('price_eur', '?')}",
            "eco_badge": True,
            "description": f"{h.get('eco_cert', 'Eco-certified')} property",
            "amenities": h.get("highlights", [])[:4],
            "carbon_kg": carbon,
        })
    return mapped


def resolve_destination(tracker, text: str, extract_fn) -> str | None:
    dest = tracker.get_slot("destination") or extract_fn(text)
    if not dest or str(dest).strip().lower() in {"unknown", "your destination", ""}:
        return None
    return str(dest).strip().title()
