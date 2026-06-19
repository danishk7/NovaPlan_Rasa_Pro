"""
hf_proxy.py — Internal FastAPI Rasa proxy
Runs on port 8080 (internal only — nginx handles public port 8501).
"""
from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config.settings import (
    ACTION_SERVER_URL,
    CLIMATIQ_ESTIMATE_URL,
    CLIMATIQ_API_KEY,
    ALLOWED_ORIGINS,
    DIAGNOSTIC_ENV_KEYS,
    ENABLE_API_DOCS,
    GEOAPIFY_API_KEY,
    NOMINATIM_SEARCH_URL,
    NOVAPLAN_USER_AGENT,
    RASA_URL,
    RESTCOUNTRIES_NAME_URL,
    TRAVELPAYOUTS_FLIGHT_URL,
    TRAVELPAYOUTS_API_TOKEN,
    WIKIPEDIA_SUMMARY_URL,
    config_value,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="NovaPlan Backend API + Rasa Proxy",
    lifespan=lifespan,
    docs_url="/docs" if ENABLE_API_DOCS else None,
    redoc_url="/redoc" if ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_API_DOCS else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

try:
    from api.services.routes import api_router

    app.include_router(api_router)
except Exception as exc:
    logger.exception("Failed to mount NovaPlan API routes: %s", exc)


def _mask_env(name: str) -> str:
    value = config_value(name)
    if not value:
        return "NOT SET"
    if len(value) <= 8:
        return "SET (hidden)"
    return f"SET ({value[:4]}…{value[-4:]})"


async def _rasa_health_payload() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{RASA_URL}/status")

        ct = r.headers.get("content-type", "")
        body = r.json() if "application/json" in ct else r.text
        if r.status_code < 500:
            return {
                "status": "ok",
                "rasa_status_code": r.status_code,
                "rasa": body,
            }
        return {
            "status": "error",
            "rasa_status_code": r.status_code,
            "rasa": body,
        }
    except (httpx.ConnectError, httpx.TimeoutException):
        return {
            "status": "warming_up",
            "message": "Rasa model is loading, please wait…",
        }
    except httpx.RequestError as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


async def _actions_health_payload() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{ACTION_SERVER_URL}/health")
        if r.status_code < 500:
            return {"status": "ok", "actions": "reachable"}
        return {"status": "error", "actions": r.text[:200]}
    except httpx.RequestError:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{ACTION_SERVER_URL}/webhook")
            reachable = r.status_code in (200, 405, 404)
            return {"status": "ok" if reachable else "error", "actions": "webhook endpoint reachable"}
        except httpx.RequestError as exc:
            return {"status": "error", "message": str(exc)}


async def _integrations_payload() -> dict[str, Any]:
    token = TRAVELPAYOUTS_API_TOKEN
    climatiq_key = CLIMATIQ_API_KEY
    result: dict[str, Any] = {
        "travelpayouts_token_set": bool(token),
        "climatiq_key_set": bool(climatiq_key),
        "travelpayouts_flights_reachable": False,
        "hotel_provider": "geoapify_places" if GEOAPIFY_API_KEY else "openstreetmap_overpass",
        "hotel_open_data_reachable": False,
        "climatiq_reachable": False,
        "wikipedia_reachable": False,
        "restcountries_reachable": False,
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            travel = await client.get(
                TRAVELPAYOUTS_FLIGHT_URL,
                params={"origin": "BER", "destination": "LIS", "currency": "EUR", "token": token or ""},
            )
        result["travelpayouts_flights_reachable"] = travel.status_code < 500
        result["travelpayouts_flights_status_code"] = travel.status_code
    except httpx.RequestError:
        result["travelpayouts_flights_status_code"] = None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            hotels = await client.get(
                NOMINATIM_SEARCH_URL,
                params={"q": "Amsterdam hotel", "format": "json", "limit": 1},
                headers={"User-Agent": NOVAPLAN_USER_AGENT},
            )
        result["hotel_open_data_reachable"] = hotels.status_code < 500
        result["hotel_open_data_status_code"] = hotels.status_code
    except httpx.RequestError:
        result["hotel_open_data_status_code"] = None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            wiki = await client.get(
                f"{WIKIPEDIA_SUMMARY_URL}/Lisbon",
                headers={"User-Agent": NOVAPLAN_USER_AGENT},
            )
        result["wikipedia_reachable"] = wiki.status_code < 500
        result["wikipedia_status_code"] = wiki.status_code
    except httpx.RequestError:
        result["wikipedia_status_code"] = None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            countries = await client.get(
                f"{RESTCOUNTRIES_NAME_URL}/Portugal",
                params={"fields": "name,capital,region,languages,currencies,timezones"},
            )
        result["restcountries_reachable"] = countries.status_code < 500
        result["restcountries_status_code"] = countries.status_code
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
            result["climatiq_reachable"] = climatiq.status_code < 500
            result["climatiq_status_code"] = climatiq.status_code
        except httpx.RequestError:
            result["climatiq_status_code"] = None
    return result


@app.get("/api/rasa/health")
async def rasa_health():
    payload = await _rasa_health_payload()
    if payload.get("status") == "error":
        return JSONResponse(status_code=503, content=payload)
    return payload


@app.get("/api/diag")
async def diagnostics():
    rasa = await _rasa_health_payload()
    actions = await _actions_health_payload()
    integrations = await _integrations_payload()
    model_path = "/app/rasa/models/novaplan.tar.gz"
    return {
        "env_vars": {key: _mask_env(key) for key in DIAGNOSTIC_ENV_KEYS},
        "model_present": os.path.isfile(model_path),
        "mock_mode": not (
            TRAVELPAYOUTS_API_TOKEN and CLIMATIQ_API_KEY
        ),
        "health": {
            "rasa": rasa,
            "actions": actions,
            "integrations": integrations,
        },
    }




def _is_goodbye_message(text: str) -> bool:
    return text.strip().lower() in {"bye", "goodbye", "good bye", "see you", "exit", "quit"}


def _is_human_handoff_message(text: str) -> bool:
    lower = text.strip().lower()
    return any(phrase in lower for phrase in ("human", "agent", "representative", "support person", "speak to someone", "talk to someone"))


async def _tracker_summary(sender_id: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(f"{RASA_URL}/conversations/{sender_id}/tracker")
        if r.status_code >= 400:
            return {"sender_id": sender_id}
        tracker = r.json()
        slots = tracker.get("slots", {}) if isinstance(tracker, dict) else {}
        keys = ("origin", "destination", "travel_dates", "budget_amount", "num_travellers", "eco_level", "transport_mode", "carbon_score", "price_total")
        return {"sender_id": sender_id, **{k: slots.get(k) for k in keys if slots.get(k) not in (None, "")}}
    except Exception:
        return {"sender_id": sender_id}


def _persist_proxy_handoff(sender_id: str, summary: dict[str, Any], ticket_id: str) -> None:
    try:
        from api.services.session_service import SessionService
        SessionService().persist_handoff(sender_id, summary, ticket_id)
    except Exception as exc:
        logger.warning("Failed to persist proxy handoff: %s", exc)


@app.post("/api/rasa/webhook")
async def rasa_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": f"Bad JSON: {exc}"})

    message_text = str(payload.get("message") or "")
    sender_id = str(payload.get("sender") or "guest")
    if _is_goodbye_message(message_text):
        return JSONResponse(status_code=200, content=[{"text": "🌱 Thanks for choosing NovaPlan.ai. Safe and sustainable travels!"}])
    if _is_human_handoff_message(message_text):
        import uuid
        ticket_id = uuid.uuid4().hex[:8].upper()
        summary = await _tracker_summary(sender_id)
        _persist_proxy_handoff(sender_id, summary, ticket_id)
        return JSONResponse(status_code=200, content=[{
            "text": (
                f"👤 I’ve created a human handover request. Reference: **{ticket_id}**. "
                "Your current session details were recorded for the support team."
            ),
            "custom": {
                "type": "escalation_banner",
                "data": {"ticket_id": ticket_id, "severity": "Medium", "context": summary}
            }
        }])

    try:
        timeout = httpx.Timeout(
            connect=10.0,
            read=120.0,
            write=10.0,
            pool=10.0,
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                f"{RASA_URL}/webhooks/rest/webhook",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        if r.status_code >= 400:
            return JSONResponse(status_code=r.status_code, content={"error": r.text})

        responses = r.json()
        try:
            from api.services.itinerary_service import ItineraryService

            responses = ItineraryService().remove_guest_notice(payload, responses)
        except Exception as exc:
            logger.exception("Itinerary post-processing failed: %s", exc)
        return responses
    except httpx.ConnectError:
        return JSONResponse(
            status_code=200,
            content=[{"text": "NovaPlan AI is still starting up — please try again in a few seconds."}],
        )
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={
                "error": "Rasa took too long to respond.",
                "hint": "The request reached Rasa, but the action or LLM response exceeded the proxy timeout.",
            },
        )

    except httpx.RequestError as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})
