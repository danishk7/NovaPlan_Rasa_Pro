"""Static cultural tips and offset program payloads."""

import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mock_data import CULTURAL_TIPS, OFFSET_PROGRAMS


def cultural_tips_for(destination: str) -> dict:
    return CULTURAL_TIPS.get(destination.lower(), CULTURAL_TIPS["default"])


def map_offset_programs(carbon_kg: float) -> tuple[list, float]:
    carbon_tonnes = float(carbon_kg) / 1000
    mapped = []
    for program in OFFSET_PROGRAMS:
        mapped.append({
            "name": program.get("name", ""),
            "description": program.get("project", ""),
            "cost_per_tonne": program.get("price_per_tonne_eur", 0),
            "impact": ", ".join(program.get("co_benefits", [])),
        })
    return mapped, carbon_tonnes
