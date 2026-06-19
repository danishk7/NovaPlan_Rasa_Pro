"""Build full transport mode list with carbon estimates for any city pair."""

from __future__ import annotations

import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mock_data import EMISSION_FACTORS, TRANSPORT_OPTIONS

# Mode templates for routes without curated mock rows
MODE_TEMPLATES = [
    ("train", "Regional / intercity rail", 0.95),
    ("bus", "Coach / intercity bus", 0.78),
    ("flight", "Short-haul flight", 0.22),
    ("car", "Private car (avg. occupancy)", 0.45),
    ("electric_car", "Electric car", 0.70),
    ("ferry", "Ferry (if coastal)", 0.50),
    ("walking", "Walking / on foot", 1.0),
]


def _colour(kg: float) -> str:
    if kg < 50:
        return "green"
    if kg < 200:
        return "amber"
    return "red"


def build_transport_options(origin: str, destination: str, distance_km: float) -> list[dict]:
    key = (origin.lower(), destination.lower())
    rev = (destination.lower(), origin.lower())
    curated = TRANSPORT_OPTIONS.get(key) or TRANSPORT_OPTIONS.get(rev)

    if curated:
        options = [dict(o) for o in curated]
        modes_present = {o["mode"] for o in options}
    else:
        options = []
        modes_present = set()

    duration_factor = max(distance_km / 80, 1.0)

    for mode, operator, eco_score in MODE_TEMPLATES:
        if mode in modes_present:
            continue
        factor = EMISSION_FACTORS.get(mode, 0.15)
        carbon_kg = round(distance_km * factor, 1) if mode not in ("walking",) else 0.0
        if mode == "walking":
            duration_hrs = round(distance_km / 5, 1)
            price = 0
        elif mode == "flight":
            duration_hrs = round(max(1.2, distance_km / 750), 1)
            price = round(55 + distance_km * 0.09, 0)
        elif mode == "train":
            duration_hrs = round(max(2.0, distance_km / 110), 1)
            price = round(25 + distance_km * 0.12, 0)
        elif mode == "bus":
            duration_hrs = round(max(3.0, distance_km / 70), 1)
            price = round(15 + distance_km * 0.06, 0)
        else:
            duration_hrs = round(max(2.5, duration_factor * 2), 1)
            price = round(30 + distance_km * 0.08, 0)

        options.append({
            "mode": mode,
            "operator": operator,
            "duration_hrs": duration_hrs,
            "price_eur": price,
            "carbon_kg": carbon_kg,
            "co2_colour": _colour(carbon_kg),
            "eco_score": eco_score,
            "notes": "Estimated option (configure APIs for live fares)",
        })

    for opt in options:
        if opt.get("carbon_kg") is None and opt.get("mode") != "flight":
            factor = EMISSION_FACTORS.get(opt["mode"], 0.15)
            opt["carbon_kg"] = round(distance_km * factor, 1)
            opt["co2_colour"] = _colour(opt["carbon_kg"])

    return sorted(options, key=lambda x: x.get("eco_score", 0), reverse=True)
