import os
from typing import Any

import httpx

from config.settings import (
    ACTION_SERVER_URL,
    CLIMATIQ_ESTIMATE_URL,
    NOMINATIM_SEARCH_URL,
    NOVAPLAN_USER_AGENT,
    RASA_URL,
    RESTCOUNTRIES_NAME_URL,
    TRAVELPAYOUTS_FLIGHT_URL,
    WIKIPEDIA_SUMMARY_URL,
    CLIMATIQ_API_KEY,
    GEOAPIFY_API_KEY,
    TRAVELPAYOUTS_API_TOKEN,
)
from ..http_client import get_json
from .repositories.health_repository import HealthRepository


class HealthService:
    def __init__(self) -> None:
        self.health_repo = HealthRepository()

    def database(self) -> dict[str, Any]:
        row = self.health_repo.ping()
        return {"status": "ok", **row}

    async def rasa(self) -> dict[str, Any]:
        try:
            response = await get_json(f"{RASA_URL}/status", timeout=5.0)
            ct = response.headers.get("content-type", "")
            if response.status_code == 404:
                return {"status": "ok", "rasa": "server reachable; /status unavailable"}
            body = response.json() if "application/json" in ct else response.text
            status = "ok" if response.status_code < 500 else "error"
            return {"status": status, "rasa": body}
        except (httpx.ConnectError, httpx.TimeoutException):
            return {"status": "warming_up", "message": "Rasa model is loading"}
        except httpx.RequestError as exc:
            return {"status": "error", "message": str(exc)}

    async def actions(self) -> dict[str, Any]:
        try:
            response = await get_json(f"{ACTION_SERVER_URL}/health", timeout=5.0)
            if response.status_code < 500:
                return {"status": "ok", "actions": "reachable"}
            return {"status": "error", "actions": response.text[:200]}
        except httpx.RequestError:
            # Action server may not expose /health — TCP reachability via webhook path
            try:
                response = await get_json(f"{ACTION_SERVER_URL}/webhook", timeout=3.0)
                reachable = response.status_code in (200, 405, 404)
                return {"status": "ok" if reachable else "error", "actions": "webhook endpoint reachable"}
            except httpx.RequestError as exc:
                return {"status": "error", "message": str(exc)}

    async def integrations(self) -> dict[str, Any]:
        travel_token = TRAVELPAYOUTS_API_TOKEN
        climatiq_key = CLIMATIQ_API_KEY
        result: dict[str, Any] = {
            "travelpayouts_token_set": bool(travel_token),
            "climatiq_key_set": bool(climatiq_key),
            "travelpayouts_flights_reachable": False,
            "hotel_provider": "geoapify_places" if GEOAPIFY_API_KEY else "openstreetmap_overpass",
            "hotel_open_data_reachable": False,
            "climatiq_reachable": False,
            "wikipedia_reachable": False,
            "restcountries_reachable": False,
        }
        try:
            travel = await get_json(
                TRAVELPAYOUTS_FLIGHT_URL,
                timeout=8.0,
                params={"origin": "BER", "destination": "LIS", "currency": "EUR", "token": travel_token or ""},
            )
            result["travelpayouts_flights_status_code"] = travel.status_code
            result["travelpayouts_flights_reachable"] = travel.status_code < 500
        except httpx.RequestError:
            result["travelpayouts_flights_status_code"] = None

        try:
            hotels = await get_json(
                NOMINATIM_SEARCH_URL,
                timeout=8.0,
                params={"q": "Amsterdam hotel", "format": "json", "limit": 1},
                headers={"User-Agent": NOVAPLAN_USER_AGENT},
            )
            result["hotel_open_data_status_code"] = hotels.status_code
            result["hotel_open_data_reachable"] = hotels.status_code < 500
        except httpx.RequestError:
            result["hotel_open_data_status_code"] = None

        try:
            wiki = await get_json(
                f"{WIKIPEDIA_SUMMARY_URL}/Lisbon",
                timeout=8.0,
                headers={"User-Agent": NOVAPLAN_USER_AGENT},
            )
            result["wikipedia_status_code"] = wiki.status_code
            result["wikipedia_reachable"] = wiki.status_code < 500
        except httpx.RequestError:
            result["wikipedia_status_code"] = None

        try:
            countries = await get_json(
                f"{RESTCOUNTRIES_NAME_URL}/Portugal",
                timeout=8.0,
                params={"fields": "name,capital,region,languages,currencies,timezones"},
            )
            result["restcountries_status_code"] = countries.status_code
            result["restcountries_reachable"] = countries.status_code < 500
        except httpx.RequestError:
            result["restcountries_status_code"] = None

        if climatiq_key:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    climatiq = await client.post(
                        CLIMATIQ_ESTIMATE_URL,
                        headers={"Authorization": f"Bearer {climatiq_key}", "Content-Type": "application/json"},
                        json={
                            "emission_factor": {
                                "activity_id": "passenger_flight-route_type_domestic-aircraft_type_na-distance_na-class_na-rf_included-distance_uplift_included",
                                "data_version": "34",
                            },
                            "parameters": {"distance": 100, "distance_unit": "km"},
                        },
                    )
                result["climatiq_status_code"] = climatiq.status_code
                result["climatiq_reachable"] = climatiq.status_code < 500
            except httpx.RequestError:
                result["climatiq_status_code"] = None
        result["live_data_possible"] = bool(travel_token) and bool(climatiq_key)
        result["status"] = "ok" if result["live_data_possible"] else "missing_secret"
        return result

    async def aggregate(self) -> dict[str, Any]:
        checks: dict[str, Any] = {}
        critical_ok = True

        try:
            checks["database"] = self.database()
        except Exception as exc:
            checks["database"] = {"status": "error", "message": str(exc)}
            critical_ok = False

        checks["rasa"] = await self.rasa()
        if checks["rasa"].get("status") == "error":
            critical_ok = False

        checks["actions"] = await self.actions()
        if checks["actions"].get("status") == "error":
            critical_ok = False

        checks["integrations"] = await self.integrations()

        return {
            "status": "ok" if critical_ok else "degraded",
            "checks": checks,
        }
