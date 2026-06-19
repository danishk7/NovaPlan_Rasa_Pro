import logging
import os
import sys
from typing import Any

import httpx
from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mock_data import ECO_HOTELS
from metadata import ECO_KEYWORDS, IATA_TO_CITY
from action_config import (
    GEOAPIFY_API_KEY,
    GEOAPIFY_GEOCODE_URL,
    GEOAPIFY_PLACES_URL,
    NOMINATIM_SEARCH_URL,
    NOVAPLAN_USER_AGENT,
    OSM_HOTEL_LOOKUP_ENABLED,
    OVERPASS_INTERPRETER_URL,
)

load_dotenv()
logger = logging.getLogger("nova.actions.hotel")

HTTP_HEADERS = {
    "User-Agent": NOVAPLAN_USER_AGENT
}

def _normalise_destination(destination: str | None) -> str:
    value = (destination or "").strip()
    if not value:
        return "Unknown"
    upper = value.upper()
    if upper in IATA_TO_CITY:
        return IATA_TO_CITY[upper]
    return value.title()


async def fetch_eco_hotels(
    destination: str,
    check_in: str,
    check_out: str,
    max_price: float,
    eco_level: str = "moderate",
) -> dict:

    if GEOAPIFY_API_KEY:
        try:
            hotels = await _fetch_geoapify_hotels(destination, max_price)
            if hotels:
                return {
                    "hotels": _rank_hotels(hotels),
                    "source": "geoapify_places",
                }
        except Exception as exc:
            logger.warning("Geoapify hotel lookup failed; trying OSM fallback: %s", exc)

    if OSM_HOTEL_LOOKUP_ENABLED:
        try:
            hotels = await _fetch_osm_hotels(destination, max_price)
            if hotels:
                return {
                    "hotels": _rank_hotels(hotels),
                    "source": "openstreetmap_overpass",
                }
        except Exception as exc:
            logger.warning("OSM/Overpass hotel lookup failed; using curated fallback: %s", exc)

    return {
        "hotels": _mock_hotels(destination, max_price, eco_level),
        "source": "curated_eco_hotels",
    }


async def _fetch_geoapify_hotels(destination: str, max_price: float) -> list[dict[str, Any]]:
    geocode_url = GEOAPIFY_GEOCODE_URL
    places_url = GEOAPIFY_PLACES_URL
    async with httpx.AsyncClient(timeout=12.0, headers=HTTP_HEADERS) as client:
        geo = await client.get(geocode_url, params={"text": destination, "limit": 1, "apiKey": GEOAPIFY_API_KEY})
        geo.raise_for_status()
        features = geo.json().get("features", [])
        if not features:
            return []
        lon, lat = features[0]["geometry"]["coordinates"]
        resp = await client.get(
            places_url,
            params={
                "categories": "accommodation.hotel,accommodation.hostel,accommodation.guest_house,accommodation.apartment",
                "filter": f"circle:{lon},{lat},8000",
                "bias": f"proximity:{lon},{lat}",
                "limit": 12,
                "apiKey": GEOAPIFY_API_KEY,
            },
        )
        resp.raise_for_status()
        results = resp.json().get("features", [])

    hotels = []
    for idx, item in enumerate(results):
        props = item.get("properties", {})
        name = props.get("name") or f"{destination} Stay {idx + 1}"
        address = props.get("formatted") or props.get("address_line2") or destination
        hotels.append(_hotel_from_place(name=name, address=address, destination=destination, max_price=max_price, idx=idx))
    return hotels


async def _fetch_osm_hotels(destination: str, max_price: float) -> list[dict[str, Any]]:
    lat, lon = await _geocode_city(destination)
    if lat is None or lon is None:
        return []

    query = f"""
    [out:json][timeout:20];
    (
      node["tourism"~"hotel|hostel|guest_house|apartment"](around:8000,{lat},{lon});
      way["tourism"~"hotel|hostel|guest_house|apartment"](around:8000,{lat},{lon});
      relation["tourism"~"hotel|hostel|guest_house|apartment"](around:8000,{lat},{lon});
    );
    out center tags 20;
    """
    async with httpx.AsyncClient(timeout=25.0, headers=HTTP_HEADERS) as client:
        resp = await client.post(OVERPASS_INTERPRETER_URL, data={"data": query})
        resp.raise_for_status()
        elements = resp.json().get("elements", [])

    hotels = []
    seen: set[str] = set()
    for idx, elem in enumerate(elements):
        tags = elem.get("tags", {}) or {}
        name = tags.get("name")
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        address = _address_from_osm_tags(tags, destination)
        hotels.append(_hotel_from_place(name=name, address=address, destination=destination, max_price=max_price, idx=idx, tags=tags))
        if len(hotels) >= 10:
            break
    return hotels


async def _geocode_city(destination: str) -> tuple[float | None, float | None]:
    async with httpx.AsyncClient(timeout=12.0, headers=HTTP_HEADERS) as client:
        resp = await client.get(
            NOMINATIM_SEARCH_URL,
            params={"q": destination, "format": "json", "limit": 1},
        )
        resp.raise_for_status()
        data = resp.json()
    if not data:
        return None, None
    try:
        return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None, None


def _hotel_from_place(
    *,
    name: str,
    address: str,
    destination: str,
    max_price: float,
    idx: int,
    tags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tags = tags or {}
    lower_blob = " ".join([name, address, " ".join(f"{k}:{v}" for k, v in tags.items())]).lower()
    eco_score = 0.68
    eco_cert = "Eco-conscious planning option"
    for kw in ECO_KEYWORDS:
        if kw in lower_blob:
            eco_score = 0.82
            eco_cert = f"Eco signal: {kw.title()}"
            break

    base_prices = [95, 115, 135, 155, 180, 210]
    estimated = base_prices[idx % len(base_prices)]
    if max_price and estimated > max_price:
        estimated = max(70, min(float(max_price), estimated * 0.8))

    rating = tags.get("stars") or tags.get("rating") or round(7.8 + (idx % 4) * 0.3, 1)
    try:
        rating = float(rating)
    except Exception:
        rating = 8.0

    return {
        "name": name,
        "eco_cert": eco_cert,
        "rating": rating,
        "price_eur": round(float(estimated), 0),
        "eco_score": eco_score,
        "carbon_kg": _estimate_hotel_carbon(eco_score, rating),
        "highlights": ["Public transport nearby", "Lower-impact stay", "Locally mapped hotel"],
        "address": address or destination,
        "booking_url": "#",
        "source": "open_data",
    }


def _address_from_osm_tags(tags: dict[str, Any], city: str) -> str:
    parts = []
    street = tags.get("addr:street")
    housenumber = tags.get("addr:housenumber")
    postcode = tags.get("addr:postcode")
    if street:
        parts.append(f"{street} {housenumber}".strip())
    if postcode:
        parts.append(str(postcode))
    parts.append(tags.get("addr:city") or city)
    return ", ".join([p for p in parts if p])


def _mock_hotels(destination: str, max_price: float, eco_level: str) -> list:
    city = _normalise_destination(destination)
    key = city.lower()
    hotels = ECO_HOTELS.get(key)
    if not hotels:
        hotels = _city_fallback_hotels(city)
    filtered = [h for h in hotels if float(h.get("price_eur", 999999)) <= float(max_price or 999999)] or hotels
    if eco_level == "high":
        certified = [h for h in filtered if "No cert" not in h.get("eco_cert", "")]
        filtered = certified if certified else filtered
    return _rank_hotels([dict(h) for h in filtered])


def _city_fallback_hotels(city: str) -> list:
    city = city if city and city != "Unknown" else "Destination"
    return [
        {
            "name": f"{city} Eco Central Hotel",
            "eco_cert": "Curated eco-friendly option",
            "rating": 8.2,
            "price_eur": 135,
            "eco_score": 0.78,
            "highlights": ["Public transport nearby", "Low-waste operations", "Energy-efficient rooms"],
            "address": f"Central {city}",
            "booking_url": "#",
        },
        {
            "name": f"{city} Green Stay",
            "eco_cert": "Sustainable property practices",
            "rating": 8.0,
            "price_eur": 115,
            "eco_score": 0.74,
            "highlights": ["Reusable amenities", "Local breakfast", "Water-saving programme"],
            "address": f"{city} city area",
            "booking_url": "#",
        },
        {
            "name": f"{city} Responsible Travel Lodge",
            "eco_cert": "Eco-conscious accommodation",
            "rating": 7.9,
            "price_eur": 95,
            "eco_score": 0.70,
            "highlights": ["Bike-friendly", "Community suppliers", "Recycling programme"],
            "address": f"Greater {city}",
            "booking_url": "#",
        },
    ]


def _rank_hotels(hotels: list) -> list:
    if not hotels:
        return hotels
    for h in hotels:
        h["carbon_kg"] = h.get("carbon_kg") or _estimate_hotel_carbon(
            float(h.get("eco_score", 0.5)), float(h.get("rating", 3) or 3)
        )
    prices = [float(h.get("price_eur", 999)) for h in hotels]
    ratings = [float(h.get("rating", 3) or 3) for h in hotels]
    max_p, min_p = max(prices), min(prices)
    max_r, min_r = max(ratings), min(ratings)
    for h in hotels:
        h["weighted_score"] = (
            0.5 * float(h.get("eco_score", 0.5))
            + 0.3 * (1 - (float(h.get("price_eur", 999)) - min_p) / (max_p - min_p + 1e-9))
            + 0.2 * ((float(h.get("rating", 3) or 3) - min_r) / (max_r - min_r + 1e-9))
        )
    return sorted(hotels, key=lambda x: x["weighted_score"], reverse=True)[:3]


def _estimate_hotel_carbon(eco_score: float, rating: float) -> float:
    baseline = 28 + max(rating - 3, 0) * 4
    reduction = min(max(eco_score, 0), 1) * 14
    return round(max(8, baseline - reduction), 1)
