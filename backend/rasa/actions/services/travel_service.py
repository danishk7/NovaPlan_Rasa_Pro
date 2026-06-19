import logging
import os
import sys

from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.carbon_service import estimate_distance_km
from action_config import TRAVELPAYOUTS_API_TOKEN, TRAVELPAYOUTS_FLIGHT_URL
from metadata import CITY_TO_IATA
from utils.http_client import get
from utils.transport_builder import build_transport_options

load_dotenv()
logger = logging.getLogger("nova.actions.travel")

async def fetch_transport_options(
    origin: str,
    destination: str,
    travel_date: str,
    eco_level: str = "moderate",
    selected_mode: str | None = None,
) -> dict:
    dist_km = estimate_distance_km(origin, destination)
    options = build_transport_options(origin, destination, dist_km)
    source = "mock"

    selected_mode = (selected_mode or "").strip().lower() or None

    if TRAVELPAYOUTS_API_TOKEN and selected_mode in (None, "flight"):
        try:
            flight_options = await _fetch_travelpayouts_flights(origin, destination, travel_date)
            if flight_options:
                # Replace mock flight entries entirely with live data
                options = [o for o in options if o["mode"] != "flight"] + flight_options
                for f in flight_options:
                    if f.get("carbon_kg") is None:
                        if dist_km:
                            f["carbon_kg"] = round(dist_km * 0.255, 1)
                            f["co2_colour"] = "red"
                        else:
                            f["carbon_kg"] = None
                            f["co2_colour"] = "unknown"
                source = "live" if selected_mode == "flight" else "mixed"
        except Exception as exc:
            logger.warning("Travelpayouts flights error: %s", exc)

    if selected_mode:
        options = [o for o in options if str(o.get("mode", "")).lower() == selected_mode]

    if eco_level == "high":
        green = [o for o in options if o["co2_colour"] in ("green", "amber")]
        options = green if green else options

    options = sorted(options, key=lambda x: x.get("eco_score", 0), reverse=True)
    return {"options": options, "source": source, "distance_km": dist_km}


async def _fetch_travelpayouts_flights(origin: str, destination: str, travel_date: str) -> list:
    from datetime import datetime as _dt, date as _date

    orig_code = CITY_TO_IATA.get(str(origin).lower(), str(origin).upper()[:3])
    dest_code = CITY_TO_IATA.get(str(destination).lower(), str(destination).upper()[:3])

    params = {
        "origin": orig_code,
        "destination": dest_code,
        "currency": "EUR",
        "token": TRAVELPAYOUTS_API_TOKEN,
    }

    requested_dates = _iso_dates(travel_date)
    requested_depart_date = requested_dates[0] if requested_dates else None
    requested_return_date = requested_dates[1] if len(requested_dates) > 1 else None
    if requested_depart_date:
        params["depart_date"] = requested_depart_date
    if requested_return_date:
        params["return_date"] = requested_return_date

    resp = await get(
        TRAVELPAYOUTS_FLIGHT_URL,
        timeout=12.0,
        params=params,
    )
    resp.raise_for_status()
    payload = resp.json()
    raw = payload.get("data", {}) if isinstance(payload, dict) else {}
    if not raw:
        logger.info("Travelpayouts returned empty data for %s→%s", orig_code, dest_code)
        return []

    def _fmt_dt(value: str) -> tuple[str, str]:
        if not value:
            return "?", ""
        try:
            dt = _dt.fromisoformat(str(value).replace("Z", "+00:00"))
            return dt.strftime("%d %b %Y"), dt.strftime("%H:%M")
        except Exception:
            return str(value)[:10], ""

    def _api_date(value: str | None) -> str | None:
        if not value:
            return None
        try:
            return _dt.fromisoformat(str(value).replace("Z", "+00:00")).date().isoformat()
        except Exception:
            return str(value)[:10] if value else None

    flights = []
    for returned_destination, bucket in raw.items():
        # Usually bucket is {"0": {...}}, but handle single objects defensively.
        if isinstance(bucket, dict) and any(isinstance(v, dict) for v in bucket.values()):
            items = bucket.values()
        elif isinstance(bucket, dict):
            items = [bucket]
        elif isinstance(bucket, list):
            items = bucket
        else:
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            api_depart_date = _api_date(item.get("departure_at"))
            api_return_date = _api_date(item.get("return_at"))
            if api_depart_date:
                try:
                    if _dt.strptime(api_depart_date, "%Y-%m-%d").date() <= _date.today():
                        continue
                except Exception:
                    pass
            if requested_depart_date and api_depart_date != requested_depart_date:
                continue
            if requested_return_date and api_return_date != requested_return_date:
                continue
            try:
                price = float(item.get("price"))
            except (TypeError, ValueError):
                continue

            duration_total = item.get("duration") or 0
            duration_to = item.get("duration_to") or 0
            duration_back = item.get("duration_back") or 0
            dep_date, dep_time = _fmt_dt(item.get("departure_at", ""))
            ret_date, ret_time = _fmt_dt(item.get("return_at", ""))
            airline = item.get("airline") or "Unknown airline"
            flight_number = item.get("flight_number")
            returned_dest = returned_destination or dest_code

            duration_hrs = round(float(duration_total) / 60, 1) if duration_total else "?"
            duration_to_hrs = round(float(duration_to) / 60, 1) if duration_to else "?"
            duration_back_hrs = round(float(duration_back) / 60, 1) if duration_back else "?"

            route_display = f"{orig_code} → {returned_dest}"
            notes = (
                f"✈️ {route_display} · Airline {airline}"
                f"{f' #{flight_number}' if flight_number else ''} · "
                f"Outbound: {dep_date}{f' {dep_time}' if dep_time else ''}"
            )
            if item.get("return_at"):
                notes += f" · Return: {ret_date}{f' {ret_time}' if ret_time else ''}"
            notes += (
                f" · Total fare: €{price:.0f}"
                f" · Duration: outbound {duration_to_hrs}h, return {duration_back_hrs}h"
            )

            flights.append({
                "mode": "flight",
                "operator": airline,
                "duration_hrs": duration_hrs,
                "duration_to_hrs": duration_to_hrs,
                "duration_back_hrs": duration_back_hrs,
                "price_eur": price,
                "currency": payload.get("currency", "EUR"),
                "carbon_kg": None,
                "co2_colour": "red",
                "eco_score": 0.20,
                "source": "live",
                "origin_code": orig_code,
                "destination_code": returned_dest,
                "requested_destination_code": dest_code,
                "departure_at": item.get("departure_at"),
                "return_at": item.get("return_at"),
                "departure_display": f"{dep_date}{f' {dep_time}' if dep_time else ''}",
                "return_display": f"{ret_date}{f' {ret_time}' if ret_time else ''}" if item.get("return_at") else "—",
                "airline": airline,
                "flight_number": flight_number,
                "notes": notes,
            })

    flights.sort(key=lambda f: f.get("price_eur", 999999))
    return flights

def _iso_dates(value: str | None) -> list[str]:
    import re

    if not value:
        return []

    return re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", str(value))
