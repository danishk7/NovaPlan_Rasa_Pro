import logging
import os
import sys

from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mock_data import ECO_HOTELS
from utils.http_client import get

load_dotenv()
logger = logging.getLogger("nova.actions.hotel")

TRAVELPAYOUTS_API_TOKEN = os.getenv("TRAVELPAYOUTS_API_TOKEN", "")

ECO_KEYWORDS = {
    "green key", "earthcheck", "leed", "iso 14001",
    "biosphere", "travelife", "rainforest alliance",
    "eco", "sustainable", "green",
}

CITY_TO_IATA = {
    "amsterdam": "AMS", "lisbon": "LIS", "barcelona": "BCN",
    "paris": "PAR", "rome": "ROM", "berlin": "BER",
    "london": "LON", "vienna": "VIE", "madrid": "MAD",
    "copenhagen": "CPH", "stockholm": "STO", "prague": "PRG",
    "budapest": "BUD", "munich": "MUC", "brussels": "BRU",
    "new york": "NYC", "tokyo": "TYO", "dubai": "DXB",
    "edinburgh": "EDI", "dublin": "DUB", "warsaw": "WAW",
}


async def fetch_eco_hotels(
    destination: str,
    check_in: str,
    check_out: str,
    max_price: float,
    eco_level: str = "moderate",
) -> dict:
    use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

    if TRAVELPAYOUTS_API_TOKEN and not use_mock:
        try:
            result = await _fetch_travelpayouts_hotels(
                destination, check_in, check_out, max_price, eco_level
            )
            if result:
                return {"hotels": result, "source": "live"}
        except Exception as exc:
            logger.warning("Travelpayouts hotels error: %s", exc)

    return {"hotels": _mock_hotels(destination, max_price, eco_level), "source": "mock_data"}


async def _fetch_travelpayouts_hotels(
    destination: str,
    check_in: str,
    check_out: str,
    max_price: float,
    eco_level: str,
) -> list:
    city_code = CITY_TO_IATA.get(destination.lower(), destination.upper()[:3])
    resp = await get(
        "https://engine.hotellook.com/api/v2/lookup.json",
        timeout=12.0,
        params={
            "query": city_code,
            "lang": "en",
            "lookFor": "hotel",
            "limit": 15,
            "token": TRAVELPAYOUTS_API_TOKEN,
        },
    )
    resp.raise_for_status()
    hotel_list = resp.json().get("results", {}).get("hotels", [])

    hotels = []
    for item in hotel_list[:15]:
        price = float(item.get("price", item.get("priceFrom", 999)) or 999)
        if price > max_price:
            continue
        name = item.get("hotelName", item.get("label", "Unknown Hotel"))
        eco_score = 0.35
        eco_cert = "Standard property"
        for kw in ECO_KEYWORDS:
            if kw in name.lower():
                eco_score = 0.80
                eco_cert = kw.title()
                break
        hotels.append({
            "name": name,
            "eco_cert": eco_cert,
            "rating": float(item.get("stars", 3) or 3),
            "price_eur": price,
            "eco_score": eco_score,
            "carbon_kg": _estimate_hotel_carbon(eco_score, float(item.get("stars", 3) or 3)),
            "highlights": ["WiFi", "Eco-friendly", "Breakfast"],
            "address": item.get("locationName", destination),
            "booking_url": "#",
        })
    return _rank_hotels(hotels)


def _mock_hotels(destination: str, max_price: float, eco_level: str) -> list:
    hotels = ECO_HOTELS.get(destination.lower(), ECO_HOTELS["default"])
    filtered = [h for h in hotels if h["price_eur"] <= max_price] or hotels
    if eco_level == "high":
        certified = [h for h in filtered if "No cert" not in h.get("eco_cert", "")]
        filtered = certified if certified else filtered
    return _rank_hotels(filtered)


def _rank_hotels(hotels: list) -> list:
    if not hotels:
        return hotels
    for h in hotels:
        h["carbon_kg"] = h.get("carbon_kg") or _estimate_hotel_carbon(
            float(h.get("eco_score", 0.5)), float(h.get("rating", 3) or 3)
        )
    prices = [h["price_eur"] for h in hotels]
    ratings = [h["rating"] for h in hotels]
    max_p, min_p = max(prices), min(prices)
    max_r, min_r = max(ratings), min(ratings)
    for h in hotels:
        h["weighted_score"] = (
            0.5 * h["eco_score"]
            + 0.3 * (1 - (h["price_eur"] - min_p) / (max_p - min_p + 1e-9))
            + 0.2 * ((h["rating"] - min_r) / (max_r - min_r + 1e-9))
        )
    return sorted(hotels, key=lambda x: x["weighted_score"], reverse=True)[:3]


def _estimate_hotel_carbon(eco_score: float, rating: float) -> float:
    baseline = 28 + max(rating - 3, 0) * 4
    reduction = min(max(eco_score, 0), 1) * 14
    return round(max(8, baseline - reduction), 1)
