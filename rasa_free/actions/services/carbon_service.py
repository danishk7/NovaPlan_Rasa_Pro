"""Climatiq carbon estimates with mock fallback."""

import logging
import math
import os
import sys
from typing import Optional

from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mock_data import CARBON_DATA, EMISSION_FACTORS
from utils.http_client import post

load_dotenv()
logger = logging.getLogger("nova.actions.carbon")

CLIMATIQ_API_KEY  = os.getenv("CLIMATIQ_API_KEY", "")
CLIMATIQ_BASE_URL = "https://api.climatiq.io"

CLIMATIQ_ACTIVITY_IDS = {
    "flight":       "passenger_flight-route_type_na-aircraft_type_na-distance_na-class_na-rf_included",
    "train":        "passenger_train-route_type_national-fuel_source_na",
    "bus":          "passenger_vehicle-vehicle_type_coach-fuel_source_diesel-distance_na-engine_size_na",
    "car":          "passenger_vehicle-vehicle_type_car-fuel_source_petrol-distance_na-engine_size_medium",
    "electric_car": "passenger_vehicle-vehicle_type_car-fuel_source_electric-distance_na-engine_size_medium",
    "ferry":        "passenger_ferry-route_type_na-fuel_source_na",
}


async def calculate_carbon(
    origin: str,
    destination: str,
    transport_mode: str,
    distance_km: Optional[float] = None,
) -> dict:
    use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

    if not CLIMATIQ_API_KEY or use_mock:
        result = _mock_carbon(origin, destination, transport_mode, distance_km)
        result["api_source"] = "mock_data"
        return result

    try:
        result = await _call_climatiq_api(origin, destination, transport_mode, distance_km)
        result["api_source"] = "climatiq"
        return result
    except Exception as exc:
        logger.warning("Climatiq API failed (%s) — mock fallback", exc)
        result = _mock_carbon(origin, destination, transport_mode, distance_km)
        result["api_source"] = "mock_data"
        return result


async def _call_climatiq_api(
    origin: str,
    destination: str,
    transport_mode: str,
    distance_km: Optional[float],
) -> dict:
    activity_id = CLIMATIQ_ACTIVITY_IDS.get(
        transport_mode.lower(), CLIMATIQ_ACTIVITY_IDS["flight"]
    )
    parameters = {"distance": distance_km, "distance_unit": "km", "passengers": 1} \
        if distance_km else {"origin": origin, "destination": destination, "passengers": 1}

    # Note: data_version must NOT be sent — it causes a 400 from Climatiq.
    # Omitting it uses the latest stable version automatically.
    payload = {
        "emission_factor": {"activity_id": activity_id},
        "parameters": parameters,
    }

    response = await post(
        f"{CLIMATIQ_BASE_URL}/data/v1/estimate",
        json=payload,
        timeout=8.0,
        headers={"Authorization": f"Bearer {CLIMATIQ_API_KEY}"},
    )
    response.raise_for_status()
    data = response.json()
    kg_co2e = data.get("co2e", 0)
    return {
        "kg_co2e": round(kg_co2e, 2),
        "colour": _co2_colour(kg_co2e),
        "source": "Climatiq API",
        "disclaimer": (
            "Emission estimates sourced from Climatiq (IPCC AR6 factors). "
            "Figures are per-passenger estimates."
        ),
        "activity_id": activity_id,
    }


def _mock_carbon(
    origin: str,
    destination: str,
    transport_mode: str,
    distance_km: Optional[float],
) -> dict:
    key = (origin.lower(), destination.lower(), transport_mode.lower())
    reverse_key = (destination.lower(), origin.lower(), transport_mode.lower())

    if key in CARBON_DATA:
        kg_co2e = CARBON_DATA[key]
    elif reverse_key in CARBON_DATA:
        kg_co2e = CARBON_DATA[reverse_key]
    elif distance_km:
        factor = EMISSION_FACTORS.get(transport_mode.lower(), 0.2)
        kg_co2e = distance_km * factor
    else:
        factor = EMISSION_FACTORS.get(transport_mode.lower(), 0.2)
        kg_co2e = 1000 * factor

    kg_co2e = round(kg_co2e, 2)
    return {
        "kg_co2e": kg_co2e,
        "colour": _co2_colour(kg_co2e),
        "source": "mock_data",
        "disclaimer": "Estimated figure. Connect CLIMATIQ_API_KEY for live data.",
    }


def _co2_colour(kg_co2e: float) -> str:
    if kg_co2e < 50:
        return "green"
    if kg_co2e < 200:
        return "amber"
    return "red"


def estimate_distance_km(origin: str, destination: str) -> float:
    city_coords = {
        "berlin": (52.52, 13.41),
        "amsterdam": (52.37, 4.90),
        "london": (51.51, -0.13),
        "paris": (48.85, 2.35),
        "barcelona": (41.39, 2.17),
        "lisbon": (38.72, -9.14),
        "rome": (41.90, 12.50),
        "vienna": (48.21, 16.37),
        "madrid": (40.42, -3.70),
        "copenhagen": (55.68, 12.57),
        "stockholm": (59.33, 18.07),
        "prague": (50.08, 14.44),
        "budapest": (47.50, 19.04),
        "warsaw": (52.23, 21.01),
        "munich": (48.14, 11.58),
    }
    o = city_coords.get(origin.lower())
    d = city_coords.get(destination.lower())
    if not (o and d):
        return 1000.0
    lat1, lon1 = math.radians(o[0]), math.radians(o[1])
    lat2, lon2 = math.radians(d[0]), math.radians(d[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(a)), 1)
