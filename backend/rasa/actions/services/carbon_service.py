import json
import logging
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from action_config import CLIMATIQ_API_KEY, CLIMATIQ_DATA_VERSION as CONFIG_CLIMATIQ_DATA_VERSION, CLIMATIQ_ESTIMATE_URL
from metadata import (
    CITY_COORDS,
    FALLBACK_FACTORS_KG_PER_KM,
    TRANSPORT_MODE_ALIASES,
    ZERO_CARBON_MODES,
)

logger = logging.getLogger(__name__)

ACTIVITY_ID_FILE = Path(__file__).parent / "climatiq_activity_ids.json"

def _impact_colour(kg_co2e: float) -> str:
    if kg_co2e <= 50:
        return "green"
    if kg_co2e <= 200:
        return "amber"
    return "red"


def _normalised_carbon_result(
    *,
    origin: str,
    destination: str,
    mode: str,
    distance_km: float,
    kg_co2e: float,
    source: str,
    reason: str | None = None,
    raw: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    kg = round(float(kg_co2e), 2)
    result = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "distance_km": float(distance_km),
        "kg_co2e": kg,
        "co2e": kg,
        "co2e_unit": "kg",
        "colour": _impact_colour(kg),
        "api_source": source,
        "source": source,
        "disclaimer": "Carbon values are estimates and may vary by operator, routing, and occupancy.",
    }
    if reason:
        result["reason"] = reason
    if raw is not None:
        result["raw"] = raw
    return result


class ClimatiqConfigurationError(RuntimeError):
    pass


def _load_climatiq_activity_config() -> Dict[str, Any]:
    if not ACTIVITY_ID_FILE.exists():
        logger.warning("Missing Climatiq activity ID file: %s", ACTIVITY_ID_FILE)
        return {"data_version": "34", "transport_modes": {}}

    with ACTIVITY_ID_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


CLIMATIQ_ACTIVITY_CONFIG = _load_climatiq_activity_config()
CLIMATIQ_DATA_VERSION = str(
    CONFIG_CLIMATIQ_DATA_VERSION or CLIMATIQ_ACTIVITY_CONFIG.get("data_version", "34")
)


def _normalise_mode(transport_mode: Optional[str]) -> str:
    mode = (transport_mode or "flight").strip().lower()

    return TRANSPORT_MODE_ALIASES.get(mode, mode)


def _zero_carbon_result(mode: str, distance_km: Optional[float] = None) -> Dict[str, Any]:
    return _normalised_carbon_result(
        origin="",
        destination="",
        mode=mode,
        distance_km=float(distance_km or 0),
        kg_co2e=0.0,
        source="zero_carbon_mode",
        reason=f"{mode.title()} is treated as a zero-carbon travel mode.",
    )


def _fallback_result(
    origin: str,
    destination: str,
    mode: str,
    distance_km: float,
    reason: str,
) -> Dict[str, Any]:
    factor = FALLBACK_FACTORS_KG_PER_KM.get(mode, 0.15)
    co2e = float(distance_km) * factor
    return _normalised_carbon_result(
        origin=origin,
        destination=destination,
        mode=mode,
        distance_km=float(distance_km),
        kg_co2e=co2e,
        source="fallback_estimate",
        reason=reason,
    )


def _get_activity_id(mode: str) -> Optional[str]:
    mode_config = CLIMATIQ_ACTIVITY_CONFIG.get("transport_modes", {}).get(mode)
    if not mode_config:
        return None

    return mode_config.get("default_activity_id") or None


def build_climatiq_payload(mode: str, distance_km: float) -> Dict[str, Any]:
    activity_id = _get_activity_id(mode)

    if not activity_id:
        raise ClimatiqConfigurationError(
            f"No Climatiq activity_id configured for mode '{mode}'."
        )

    return {
        "emission_factor": {
            "activity_id": activity_id,
            "data_version": CLIMATIQ_DATA_VERSION,
        },
        "parameters": {
            "distance": float(distance_km),
            "distance_unit": "km",
        },
    }


def estimate_distance_km(origin: str, destination: str) -> Optional[float]:
    origin_key = (origin or "").strip().lower()
    destination_key = (destination or "").strip().lower()

    if origin_key not in CITY_COORDS or destination_key not in CITY_COORDS:
        return None

    lat1, lon1 = CITY_COORDS[origin_key]
    lat2, lon2 = CITY_COORDS[destination_key]

    radius_km = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(radius_km * c, 2)


async def _call_climatiq_api(
    origin: str,
    destination: str,
    transport_mode: str,
    distance_km: Optional[float],
) -> Dict[str, Any]:
    mode = _normalise_mode(transport_mode)

    if distance_km is None or float(distance_km) <= 0:
        distance_km = estimate_distance_km(origin, destination)

    if distance_km is None or float(distance_km) <= 0:
        distance_km = 500.0

    if mode in ZERO_CARBON_MODES:
        return _zero_carbon_result(mode, float(distance_km))

    if not CLIMATIQ_API_KEY:
        return _fallback_result(
            origin,
            destination,
            mode,
            float(distance_km),
            "Missing CLIMATIQ_API_KEY.",
        )

    try:
        payload = build_climatiq_payload(mode, float(distance_km))
    except Exception as exc:
        logger.warning("Climatiq payload build failed: %s", exc)
        return _fallback_result(
            origin,
            destination,
            mode,
            float(distance_km),
            str(exc),
        )

    logger.info("Climatiq estimate payload: %s", json.dumps(payload, indent=2))

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                CLIMATIQ_ESTIMATE_URL,
                headers={
                    "Authorization": f"Bearer {CLIMATIQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        response.raise_for_status()
        data = response.json()

        kg_co2e = float(data.get("co2e") or 0.0)
        result = _normalised_carbon_result(
            origin=origin,
            destination=destination,
            mode=mode,
            distance_km=float(distance_km),
            kg_co2e=kg_co2e,
            source="climatiq",
            raw=data,
        )
        result["activity_id"] = payload["emission_factor"]["activity_id"]
        result["data_version"] = CLIMATIQ_DATA_VERSION
        return result

    except Exception as exc:
        logger.warning("Climatiq API failed: %s — using fallback estimate", exc)
        return _fallback_result(
            origin,
            destination,
            mode,
            float(distance_km),
            str(exc),
        )


async def calculate_carbon(
    origin: str,
    destination: str,
    transport_mode: str,
    distance_km: Optional[float] = None,
) -> Dict[str, Any]:
    return await _call_climatiq_api(
        origin=origin,
        destination=destination,
        transport_mode=transport_mode,
        distance_km=distance_km,
    )
