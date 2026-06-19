"""Transport options via Travelpayouts flights + mock land routes."""

import logging
import os
import sys

from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mock_data import TRANSPORT_OPTIONS
from services.carbon_service import estimate_distance_km
from utils.http_client import get
from utils.transport_builder import build_transport_options

CITY_TO_IATA = {
    "amsterdam": "AMS", "lisbon": "LIS", "barcelona": "BCN",
    "paris": "PAR", "rome": "ROM", "berlin": "BER",
    "london": "LON", "vienna": "VIE", "madrid": "MAD",
    "copenhagen": "CPH", "stockholm": "STO", "prague": "PRG",
    "budapest": "BUD", "munich": "MUC", "brussels": "BRU",
    "new york": "NYC", "tokyo": "TYO", "dubai": "DXB",
    "edinburgh": "EDI", "dublin": "DUB", "warsaw": "WAW",
}

load_dotenv()
logger = logging.getLogger("nova.actions.travel")

TRAVELPAYOUTS_API_TOKEN = os.getenv("TRAVELPAYOUTS_API_TOKEN", "")


async def fetch_transport_options(
    origin: str,
    destination: str,
    travel_date: str,
    eco_level: str = "moderate",
) -> dict:
    """Returns {options: list, source: 'live'|'mock'|'mixed'}."""
    use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
    dist_km = estimate_distance_km(origin, destination)
    options = build_transport_options(origin, destination, dist_km)
    source = "mock"

    if TRAVELPAYOUTS_API_TOKEN and not use_mock:
        try:
            flight_options = await _fetch_travelpayouts_flights(origin, destination, travel_date)
            if flight_options:
                # Replace mock flight entries entirely with live data
                options = [o for o in options if o["mode"] != "flight"] + flight_options
                for f in flight_options:
                    if f.get("carbon_kg") is None:
                        f["carbon_kg"] = round(dist_km * 0.255, 1)
                        f["co2_colour"] = "red"
                source = "live"   # all flights are now live; land modes are still estimated
        except Exception as exc:
            logger.warning("Travelpayouts flights error: %s", exc)

    if eco_level == "high":
        green = [o for o in options if o["co2_colour"] in ("green", "amber")]
        options = green if green else options

    options = sorted(options, key=lambda x: x.get("eco_score", 0), reverse=True)
    return {"options": options, "source": source, "distance_km": dist_km}


async def _fetch_travelpayouts_flights(origin: str, destination: str, travel_date: str) -> list:
    orig_code = CITY_TO_IATA.get(origin.lower(), origin.upper()[:3])
    dest_code = CITY_TO_IATA.get(destination.lower(), destination.upper()[:3])
    resp = await get(
        "https://api.travelpayouts.com/v1/prices/cheap",
        timeout=12.0,
        params={
            "origin": orig_code,
            "destination": dest_code,
            "currency": "EUR",
            "token": TRAVELPAYOUTS_API_TOKEN,
        },
    )
    resp.raise_for_status()
    raw = resp.json().get("data", {})
    if not raw:
        logger.info("Travelpayouts returned empty data for %s→%s", orig_code, dest_code)
        return []
    flights = []
    for _, item in raw.items():
        price   = float(item.get("price", 999))
        dur     = item.get("duration", 150)
        dep_raw = item.get("departure_at", "")
        try:
            from datetime import datetime as _dt
            dep_str = _dt.fromisoformat(dep_raw).strftime("%-d %b %H:%M")
        except Exception:
            dep_str = dep_raw[:10] if dep_raw else "?"
        flights.append({
            "mode":         "flight",
            "operator":     item.get("airline", "Unknown airline"),
            "duration_hrs": round(dur / 60, 1) if dur else 2.5,
            "price_eur":    price,
            "carbon_kg":    None,
            "co2_colour":   "red",
            "eco_score":    0.20,
            "source":       "live",
            "notes":        f"✈️ Live fare · Departs {dep_str}",
        })
    return flights


def _mock_transport(origin: str, destination: str) -> list:
    key = (origin.lower(), destination.lower())
    rev_key = (destination.lower(), origin.lower())
    return list(
        TRANSPORT_OPTIONS.get(key)
        or TRANSPORT_OPTIONS.get(rev_key)
        or TRANSPORT_OPTIONS["default"]
    )
