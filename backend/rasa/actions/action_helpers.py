from typing import Any


def map_transport_options(options: list[dict]) -> list[dict]:
    mapped: list[dict[str, Any]] = []

    for option in options or []:
        mode = option.get("mode", "unknown")
        price = option.get("price_eur", option.get("price"))
        cost = f"€{price}" if price not in (None, "") else "Price unavailable"
        duration = f"{option.get('duration_hrs', '?')}h"

        if mode == "flight" and option.get("source") == "live":
            airline = option.get("airline") or option.get("operator") or "Unknown airline"
            flight_number = option.get("flight_number")
            flight_suffix = f" #{flight_number}" if flight_number else ""
            origin_code = option.get("origin_code", "")
            destination_code = option.get("destination_code", "")
            route = f"{origin_code} → {destination_code}" if origin_code or destination_code else "Flight route"

            details = (
                f"{route} | Airline: {airline}{flight_suffix}\n\n"
                f"Outbound: {option.get('departure_display', '—')}\n\n"
                f"Return: {option.get('return_display', '—')}\n\n"
                f"Total fare shown by API: {cost}\n\n"
                f"Duration: outbound {option.get('duration_to_hrs', '?')}h, "
                f"return {option.get('duration_back_hrs', '?')}h"
            )
        else:
            details = option.get("notes") or "No details available"

        mapped.append(
            {
                "mode": mode,
                "duration": duration,
                "cost": cost,
                "emissions": option.get("carbon_kg", 0),
                "eco_rating": option.get("co2_colour", "amber"),
                "details": details,
                "departure": option.get("departure_display"),
                "return": option.get("return_display"),
                "airline": option.get("airline") or option.get("operator"),
                "origin_code": option.get("origin_code"),
                "destination_code": option.get("destination_code"),
                "price_eur": price,
                "duration_hrs": option.get("duration_hrs"),
            }
        )

    return mapped


def map_hotels(hotels: list[dict]) -> list[dict]:
    mapped = []
    for hotel in hotels or []:
        carbon = hotel.get("carbon_kg")
        mapped.append(
            {
                "name": hotel.get("name", "Unknown Hotel"),
                "rating": min(5, round(float(hotel.get("rating", 4)) / 2)) if hotel.get("rating") else 4,
                "price": f"€{hotel.get('price_eur', '?')}",
                "price_eur": hotel.get("price_eur"),
                "eco_badge": True,
                "description": f"{hotel.get('eco_cert', 'Eco-certified')} property",
                "amenities": hotel.get("highlights", [])[:4],
                "address": hotel.get("address"),
                "source": hotel.get("source"),
                "carbon_kg": carbon,
            }
        )
    return mapped


def resolve_destination(tracker, text: str, extract_fn) -> str | None:
    destination = tracker.get_slot("destination") or extract_fn(text)
    if not destination or str(destination).strip().lower() in {"unknown", "your destination", ""}:
        return None
    return str(destination).strip().title()
