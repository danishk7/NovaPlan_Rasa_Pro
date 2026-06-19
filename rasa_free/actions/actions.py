"""NovaPlan custom Rasa actions — single consolidated file."""

import logging
import os
import re
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Text

from dotenv import load_dotenv
from rasa_sdk import Action, FormValidationAction, Tracker
from rasa_sdk.events import ActionExecuted, AllSlotsReset, FollowupAction, SessionStarted, SlotSet
from rasa_sdk.executor import CollectingDispatcher

_ACTIONS_DIR = os.path.dirname(os.path.abspath(__file__))
if _ACTIONS_DIR not in sys.path:
    sys.path.insert(0, _ACTIONS_DIR)
_ROOT_DIR = os.path.dirname(os.path.dirname(_ACTIONS_DIR))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from action_helpers import map_hotels, map_transport_options, resolve_destination
from services.carbon_service import calculate_carbon, estimate_distance_km
from services.cultural_service import fetch_cultural_profile
from services.hotel_service import fetch_eco_hotels
from services.itinerary_service import map_offset_programs
from services.travel_service import fetch_transport_options
from api.services.itinerary_service import ItineraryService
from api.schemas.itinerary import ItineraryRequest
from utils.formatter import custom_message, format_travel_dates, latest_text, safe_float
from utils.eco_level import normalize_eco_level
from utils.parser import (
    extract_budget,
    extract_destination,
    extract_route,
    extract_transport_mode,
)

load_dotenv()
logger = logging.getLogger("nova.actions")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────────────────────────────────────

class ActionSessionStart(Action):
    def name(self) -> Text:
        return "action_session_start"

    async def run(self, dispatcher, tracker, domain):
        events = [SessionStarted()]
        for slot in ("user_id", "conversation_id"):
            val = tracker.get_slot(slot)
            if val:
                events.append(SlotSet(slot, val))
        events.append(ActionExecuted("action_listen"))
        return events


# ─────────────────────────────────────────────────────────────────────────────
# TRAVEL INFORMATION
# ─────────────────────────────────────────────────────────────────────────────

class ActionFetchTravelOptions(Action):
    def name(self) -> Text:
        return "action_fetch_travel_options"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        text = latest_text(tracker)
        extracted_origin, extracted_destination = extract_route(text)
        origin_slot = tracker.get_slot("origin")
        destination_slot = tracker.get_slot("destination")
        origin = origin_slot or extracted_origin or "Unknown"
        destination = (
            destination_slot
            or extracted_destination
            or extract_destination(text)
            or "Unknown"
        )
        if origin_slot and not destination_slot and destination.lower() == origin_slot.lower():
            destination = "Unknown"
        travel_dates = tracker.get_slot("travel_dates") or "flexible"
        eco_level = tracker.get_slot("eco_level") or "moderate"

        if origin == "Unknown" or destination == "Unknown":
            dispatcher.utter_message(
                text="Please tell me both cities for the route, for example: from Berlin to Amsterdam."
            )
            return []

        dispatcher.utter_message(
            text=f"🔍 Finding travel options from **{origin}** to **{destination}**..."
        )
        try:
            payload = await fetch_transport_options(origin, destination, travel_dates, eco_level)
            options = payload.get("options", [])
            api_source = payload.get("source", "mock")
        except Exception as exc:
            logger.error("fetch_transport_options failed: %s", exc)
            options = []
            api_source = "error"

        if not options:
            dispatcher.utter_message(text="No transport options found for this route.")
            return []

        dispatcher.utter_message(
            text=(
                f"🚆 Transport options ({api_source} data): flight, train, bus, car, "
                f"ferry, and walking — ranked by eco-score."
            )
        )
        mapped = map_transport_options(options)
        dispatcher.utter_message(
            json_message=custom_message(
                "transport_options",
                {
                    "origin": origin,
                    "destination": destination,
                    "options": mapped,
                    "api_source": api_source,
                },
            )
        )
        best = options[0]
        return [
            SlotSet("origin", origin if origin != "Unknown" else None),
            SlotSet("destination", destination if destination != "Unknown" else None),
            SlotSet("transport_mode", best["mode"]),
        ]


class ActionCalculateCarbon(Action):
    def name(self) -> Text:
        return "action_calculate_carbon"

    async def run(self, dispatcher, tracker, domain):
        text = latest_text(tracker)
        extracted_origin, extracted_destination = extract_route(text)
        origin_slot = tracker.get_slot("origin")
        destination_slot = tracker.get_slot("destination")
        origin = origin_slot or extracted_origin or "Unknown"
        destination = (
            destination_slot
            or extracted_destination
            or extract_destination(text)
            or "Unknown"
        )
        if origin_slot and not destination_slot and destination.lower() == origin_slot.lower():
            destination = "Unknown"
        mode = tracker.get_slot("transport_mode") or extract_transport_mode(text) or "flight"

        if origin == "Unknown" or destination == "Unknown":
            dispatcher.utter_message(
                text="Please tell me both cities before I calculate emissions, "
                     "for example: carbon for train from London to Paris."
            )
            return []

        dispatcher.utter_message(
            text=f"♻️ Calculating carbon for **{mode}** from {origin} to {destination}..."
        )
        try:
            dist_km = estimate_distance_km(origin, destination)
            result = await calculate_carbon(origin, destination, mode, dist_km)
        except Exception as exc:
            logger.error("calculate_carbon failed: %s", exc)
            dispatcher.utter_message(text="⚠️ Carbon calculation failed. Please try again.")
            return []

        colour = result["colour"]
        label = {
            "green": "Low impact ✅",
            "amber": "Moderate impact ⚠️",
            "red": "High impact ❌",
        }.get(colour, "")
        api_source = result.get("api_source", result.get("source", "estimate"))

        dispatcher.utter_message(
            text=f"♻️ Carbon estimate: **{result['kg_co2e']} kg CO₂e** ({api_source})"
        )
        dispatcher.utter_message(
            json_message=custom_message(
                "carbon_card",
                {
                    "colour": colour,
                    "kg_co2e": result["kg_co2e"],
                    "mode": mode,
                    "label": label,
                    "source": api_source,
                    "disclaimer": result.get("disclaimer", ""),
                },
            )
        )
        if colour == "red":
            dispatcher.utter_message(
                json_message=custom_message(
                    "quick_reply",
                    {
                        "replies": [
                            "🚆 Show train options",
                            "♻️ Offset this journey",
                            "Continue with flight",
                        ]
                    },
                )
            )
        return [
            SlotSet("origin", origin if origin != "Unknown" else None),
            SlotSet("destination", destination if destination != "Unknown" else None),
            SlotSet("transport_mode", mode),
            SlotSet("carbon_score", result["kg_co2e"]),
            SlotSet("carbon_colour", colour),
        ]


class ActionFetchEcoHotels(Action):
    def name(self) -> Text:
        return "action_fetch_eco_hotels"

    async def run(self, dispatcher, tracker, domain):
        text = latest_text(tracker)
        destination = resolve_destination(tracker, text, extract_destination)
        if not destination:
            dispatcher.utter_message(
                text="🌍 Which **city** should I search eco hotels in? (e.g. Amsterdam, Lisbon)"
            )
            return []

        budget = safe_float(tracker.get_slot("budget_amount"), 1000) or extract_budget(text) or 1000
        eco_level = tracker.get_slot("eco_level") or "moderate"

        dispatcher.utter_message(text=f"🏨 Searching eco-certified hotels in **{destination}**...")
        try:
            result = await fetch_eco_hotels(
                destination,
                check_in=datetime.now().strftime("%Y-%m-%d"),
                check_out=datetime.now().strftime("%Y-%m-%d"),
                max_price=float(budget),
                eco_level=eco_level,
            )
            hotels = result.get("hotels", [])
            api_source = result.get("source", "mock_data")
        except Exception as exc:
            logger.error("fetch_eco_hotels failed: %s", exc)
            dispatcher.utter_message(text="⚠️ Hotel search failed. Please try again.")
            return []

        if not hotels:
            dispatcher.utter_message(
                text=f"No eco-certified hotels found in {destination} within budget."
            )
            return []

        dispatcher.utter_message(
            text=f"🏨 Found {len(hotels)} options ({api_source} data) with prices and eco ratings."
        )
        dispatcher.utter_message(
            json_message=custom_message(
                "hotel_carousel",
                {
                    "destination": destination,
                    "hotels": map_hotels(hotels),
                    "api_source": api_source,
                },
            )
        )
        return [
            SlotSet("destination", destination),
            SlotSet("budget_amount", float(budget)),
        ]


class ActionGetEcoTips(Action):
    def name(self) -> Text:
        return "action_get_eco_tips"

    async def run(self, dispatcher, tracker, domain):
        text = latest_text(tracker)
        destination = resolve_destination(tracker, text, extract_destination)
        dest_label = f" for **{destination}**" if destination else ""
        dispatcher.utter_message(
            text=f"🌿 Eco travel tips{dest_label}:\n\n"
                 "• Choose trains over flights where possible\n"
                 "• Stay in certified eco hotels\n"
                 "• Offset unavoidable emissions\n"
                 "• Pack light to reduce fuel consumption\n"
                 "• Use public transport at your destination"
        )
        return []


class ActionGetActivities(Action):
    def name(self) -> Text:
        return "action_get_activities"

    async def run(self, dispatcher, tracker, domain):
        text = latest_text(tracker)
        destination = resolve_destination(tracker, text, extract_destination)
        if not destination:
            dispatcher.utter_message(
                text="🌍 Please tell me the **destination city** for activity suggestions (e.g. Barcelona)."
            )
            return []

        profile = await fetch_cultural_profile(destination)
        tips = profile.get("tips", {})
        api_source = profile.get("source", "mock_data")

        data_payload: dict = {}
        if "country_overview" in tips:
            data_payload["country_overview"] = {"category": "Country overview", "tips": tips["country_overview"]}
        if "eco_activities" in tips:
            data_payload["eco_activities"] = {"category": "Eco Activities", "tips": tips["eco_activities"]}
        if "responsible_tips" in tips:
            data_payload["responsible_tips"] = {"category": "Responsible Travel Tips", "tips": tips["responsible_tips"]}

        dispatcher.utter_message(text=f"🌍 Cultural profile for **{destination}** ({api_source} data).")
        dispatcher.utter_message(
            json_message=custom_message(
                "cultural_tips",
                {
                    "destination": destination,
                    "data": data_payload,
                    "sustainability_rating": tips.get("sustainability_rating", "N/A"),
                    "api_source": api_source,
                },
            )
        )
        return [SlotSet("destination", destination)]


class ActionGetCulturalInfo(Action):
    def name(self) -> Text:
        return "action_get_cultural_info"

    async def run(self, dispatcher, tracker, domain):
        destination = tracker.get_slot("destination")
        if not destination:
            dispatcher.utter_message(
                text="🌍 Please tell me a destination first (e.g. Tokyo, Barcelona)."
            )
            return []

        profile = await fetch_cultural_profile(destination)
        tips = profile.get("tips", {})
        source = profile.get("source", "mock_data")

        dispatcher.utter_message(text=f"🌍 Cultural insights for {destination} ({source})")
        dispatcher.utter_message(
            json_message=custom_message(
                "cultural_tips",
                {
                    "destination": destination,
                    "country_overview": tips.get("country_overview", []),
                    "eco_activities": tips.get("eco_activities", []),
                    "responsible_tips": tips.get("responsible_tips", []),
                    "sustainability_rating": tips.get("sustainability_rating", "N/A"),
                    "source": source,
                },
            )
        )
        return []


class ActionGetOffsetPrograms(Action):
    def name(self) -> Text:
        return "action_get_offset_programs"

    async def run(self, dispatcher, tracker, domain):
        text = latest_text(tracker)
        carbon_kg = float(tracker.get_slot("carbon_score") or 0)
        if carbon_kg <= 0:
            extracted_origin, extracted_destination = extract_route(text)
            origin_slot = tracker.get_slot("origin")
            destination_slot = tracker.get_slot("destination")
            origin = origin_slot or extracted_origin or "Berlin"
            dest = (
                destination_slot
                or extracted_destination
                or extract_destination(text)
                or "Amsterdam"
            )
            if origin_slot and not destination_slot and dest.lower() == origin_slot.lower():
                dest = "Amsterdam"
            mode = tracker.get_slot("transport_mode") or extract_transport_mode(text) or "flight"
            dist = estimate_distance_km(origin, dest)
            est = await calculate_carbon(origin, dest, mode, dist)
            carbon_kg = float(est.get("kg_co2e", 120))
            dispatcher.utter_message(
                text=f"Using estimated journey emissions **{carbon_kg:.1f} kg CO₂e** for offset options."
            )

        programs, carbon_tonnes = map_offset_programs(carbon_kg)
        lines = [f"• {p['name']} — €{p['cost_per_tonne']:.2f}/tonne" for p in programs[:4]]
        dispatcher.utter_message(
            text="🌱 **Carbon offset programs** (verified schemes):\n" + "\n".join(lines)
        )
        dispatcher.utter_message(
            json_message=custom_message(
                "offset_programs",
                {
                    "programs": programs,
                    "carbon_tonnes": carbon_tonnes,
                    "api_source": "mock_data",
                },
            )
        )
        return [SlotSet("carbon_score", carbon_kg)]


# ─────────────────────────────────────────────────────────────────────────────
# ITINERARY SUMMARY & REVIEW
# ─────────────────────────────────────────────────────────────────────────────

class ActionDisplayItinerarySummary(Action):
    """Called after form completes. transport_mode is the last collected slot,
    so we fetch results for that specific mode only — no all-options carousel.
    Shows targeted travel + carbon data, then asks Book / Modify / Cancel.
    Nothing is persisted until the user explicitly confirms."""

    def name(self) -> Text:
        return "action_display_itinerary_summary"

    async def run(self, dispatcher, tracker, domain):
        origin         = tracker.get_slot("origin") or "Unknown"
        destination    = tracker.get_slot("destination") or "Unknown"
        travel_dates   = tracker.get_slot("travel_dates") or "Flexible"
        budget         = tracker.get_slot("budget_amount") or "Not specified"
        eco_level      = tracker.get_slot("eco_level") or "moderate"
        transport_mode = tracker.get_slot("transport_mode") or "flight"
        num_travellers = int(tracker.get_slot("num_travellers") or 1)

        # ── 1. Trip overview header ───────────────────────────────────────────
        dispatcher.utter_message(
            text=(
                f"📋 **Your Trip Plan**\n\n"
                f"🏠 **From:** {origin}\n"
                f"🌍 **To:** {destination}\n"
                f"📅 **Dates:** {travel_dates}\n"
                f"👥 **Travellers:** {num_travellers}\n"
                f"💰 **Budget:** €{budget}\n"
                f"🌱 **Eco Level:** {eco_level}\n"
                f"🚗 **Transport:** {transport_mode.title()}"
            )
        )

        # ── 2. Fetch options filtered to the user-selected mode ───────────────
        dispatcher.utter_message(
            text=(
                f"🔍 Fetching **{transport_mode}** options "
                f"from **{origin}** → **{destination}**..."
            )
        )
        selected_option = None
        try:
            payload      = await fetch_transport_options(origin, destination, travel_dates, eco_level)
            all_options  = payload.get("options", [])
            api_source   = payload.get("source", "mock")
            mode_options = [o for o in all_options
                            if o.get("mode", "").lower() == transport_mode.lower()]
            display_options = mode_options if mode_options else all_options
            if display_options:
                selected_option = display_options[0]
                dispatcher.utter_message(
                    json_message=custom_message(
                        "transport_options",
                        {
                            "origin":        origin,
                            "destination":   destination,
                            "options":       map_transport_options(display_options),
                            "api_source":    api_source,
                            "selected_mode": transport_mode,
                        },
                    )
                )
            else:
                dispatcher.utter_message(
                    text=(
                        f"⚠️ No **{transport_mode}** options found. "
                        f"You can modify your transport choice below."
                    )
                )
        except Exception as exc:
            logger.error("fetch_transport_options in summary failed: %s", exc)
            dispatcher.utter_message(text="⚠️ Could not fetch live transport data right now.")

        # ── 3. Carbon estimate for the selected mode ──────────────────────────
        carbon_kg = None
        try:
            from services.carbon_service import estimate_distance_km
            dist_km       = estimate_distance_km(origin, destination)
            carbon_result = await calculate_carbon(origin, destination, transport_mode, dist_km)
            carbon_kg     = carbon_result.get("kg_co2e")
            colour        = carbon_result.get("colour", "amber")
            label         = {"green": "Low ✅", "amber": "Moderate ⚠️", "red": "High ❌"}.get(colour, "")
            per_person    = round(carbon_kg / num_travellers, 1) if carbon_kg and num_travellers > 1 else None
            carbon_text   = f"♻️ **{transport_mode.title()} emissions:** {carbon_kg} kg CO₂e total"
            if per_person:
                carbon_text += f" ({per_person} kg per person)"
            dispatcher.utter_message(text=carbon_text)
            dispatcher.utter_message(
                json_message=custom_message(
                    "carbon_card",
                    {
                        "colour":     colour,
                        "kg_co2e":    carbon_kg,
                        "per_person": per_person,
                        "mode":       transport_mode,
                        "label":      label,
                        "source":     carbon_result.get("api_source", "estimate"),
                        "disclaimer": carbon_result.get("disclaimer", ""),
                    },
                )
            )
            if colour == "red":
                dispatcher.utter_message(
                    text=(
                        "🌿 High-emission option. Use **Change transport mode** below "
                        "to compare a greener alternative."
                    )
                )
        except Exception as exc:
            logger.error("carbon calc in summary failed: %s", exc)

        # ── 4. Confirm / change mode / modify / cancel ────────────────────────
        price_hint = ""
        if selected_option and selected_option.get("price_eur"):
            price_hint = f"\n💳 Est. cost: **€{selected_option['price_eur']}**"
        dispatcher.utter_message(
            text=f"✅ **Ready to confirm your {transport_mode.title()} trip?**{price_hint}",
            buttons=[
                {"title": "✅ Confirm & Book",        "payload": "/confirm_itinerary"},
                {"title": "🔄 Change transport mode", "payload": "/modify_transport_mode"},
                {"title": "✏️ Modify other details",  "payload": "/modify_itinerary"},
                {"title": "❌ Cancel",                 "payload": "/booking_cancelled"},
            ],
        )

        return [
            SlotSet("awaiting_review",    True),
            SlotSet("modification_count", 0),
            SlotSet("carbon_score",       carbon_kg),
        ]



class ActionBuildItineraryPackage(Action):
    """Legacy action kept for backward compatibility — the new flow uses
    ActionDisplayItinerarySummary instead. Safe to call but does nothing
    that can loop."""

    def name(self) -> Text:
        return "action_build_itinerary_package"

    async def run(self, dispatcher, tracker, domain):
        origin      = tracker.get_slot("origin")
        destination = tracker.get_slot("destination")
        if not origin or not destination:
            dispatcher.utter_message(
                text="Please tell me your departure and destination cities first."
            )
            return []   # stop — do NOT re-trigger booking_form here

        if str(origin).strip().lower() == str(destination).strip().lower():
            dispatcher.utter_message(
                text="Your departure and destination city are the same. Please start a new trip."
            )
            return []

        # Delegate to the summary action which handles the full flow
        return [FollowupAction("action_display_itinerary_summary")]


class ActionCompleteItinerary(Action):
    """Only called after the user explicitly confirms booking from the summary screen.
    This is the point at which the itinerary is saved/persisted."""

    def name(self) -> Text:
        return "action_complete_itinerary"

    async def run(self, dispatcher, tracker, domain):
        # Guard: must have seen the summary first
        if not tracker.get_slot("awaiting_review"):
            dispatcher.utter_message(
                text="Please complete the trip details first before confirming a booking."
            )
            return []

        origin = tracker.get_slot("origin") or "—"
        destination = tracker.get_slot("destination") or "—"
        dates = tracker.get_slot("travel_dates") or "—"
        budget = tracker.get_slot("budget_amount") or "—"
        num_travellers = tracker.get_slot("num_travellers") or "—"
        eco = tracker.get_slot("eco_level") or "—"
        carbon = tracker.get_slot("carbon_score") or "—"
        mode = tracker.get_slot("transport_mode") or "—"
        ref = str(uuid.uuid4())[:8].upper()
        dates = format_travel_dates(dates)

        summary = (
            f"🎉 **Itinerary created** — reference `#{ref}`\n\n"
            f"• Route: {origin} → {destination}\n"
            f"• Dates: {dates}\n"
            f"• Budget: €{budget}\n"
            f"• Travellers: {num_travellers}\n"
            f"• Sustainability: {eco}\n"
            f"• Preferred transport: {mode}\n"
            f"• Est. emissions: {carbon} kg CO₂e\n\n"
            f"A PDF/email export can be added in the web app. Your plan is saved in this session."
        )
        dispatcher.utter_message(text=summary)

        user_id = tracker.get_slot("user_id") or tracker.get_slot("conversation_id") or "guest"
        title = f"{origin} → {destination} | {mode} | €{budget}"
        note = (
            f"Reference: #{ref} | Dates: {dates} | Eco level: {eco} | "
            f"Estimated emissions: {carbon} kg CO₂e"
        )
        try:
            ItineraryService().create(
                ItineraryRequest(
                    userId=user_id,
                    time=dates if dates != "—" else None,
                    title=title,
                    note=note,
                    status="confirmed",
                    order=0,
                )
            )
            dispatcher.utter_message(text="✅ Your confirmed itinerary has been saved to the database.")
        except Exception as exc:
            logger.error("failed persisting itinerary: %s", exc)
            dispatcher.utter_message(
                text=(
                    "⚠️ Your itinerary is ready, but I could not save it to the database right now. "
                    "Please try again later."
                )
            )

        dispatcher.utter_message(
            json_message=custom_message(
                "itinerary_summary",
                {
                    "reference": ref,
                    "origin": origin,
                    "destination": destination,
                    "travel_dates": dates,
                    "budget_eur": budget,
                    "num_travellers": num_travellers,
                    "eco_level": eco,
                    "transport_mode": mode,
                    "carbon_kg": carbon,
                    "status": "confirmed",
                },
            )
        )
        return [SlotSet("itinerary_draft", False), SlotSet("itinerary_confirmed", True)]


# ─────────────────────────────────────────────────────────────────────────────
# SLOT RESET ACTIONS (modification flow)
# ─────────────────────────────────────────────────────────────────────────────

class ActionResetOrigin(Action):
    def name(self) -> Text:
        return "action_reset_origin"

    async def run(self, dispatcher, tracker, domain):
        mod_count = tracker.get_slot("modification_count") or 0
        return [SlotSet("origin", None), SlotSet("modification_count", mod_count + 1)]


class ActionResetDestination(Action):
    def name(self) -> Text:
        return "action_reset_destination"

    async def run(self, dispatcher, tracker, domain):
        mod_count = tracker.get_slot("modification_count") or 0
        return [SlotSet("destination", None), SlotSet("modification_count", mod_count + 1)]


class ActionResetDates(Action):
    def name(self) -> Text:
        return "action_reset_dates"

    async def run(self, dispatcher, tracker, domain):
        mod_count = tracker.get_slot("modification_count") or 0
        return [SlotSet("travel_dates", None), SlotSet("modification_count", mod_count + 1)]


class ActionResetBudget(Action):
    def name(self) -> Text:
        return "action_reset_budget"

    async def run(self, dispatcher, tracker, domain):
        mod_count = tracker.get_slot("modification_count") or 0
        return [SlotSet("budget_amount", None), SlotSet("modification_count", mod_count + 1)]


class ActionResetEcoLevel(Action):
    def name(self) -> Text:
        return "action_reset_eco_level"

    async def run(self, dispatcher, tracker, domain):
        mod_count = tracker.get_slot("modification_count") or 0
        return [SlotSet("eco_level", None), SlotSet("modification_count", mod_count + 1)]


class ActionResetTransportMode(Action):
    def name(self) -> Text:
        return "action_reset_transport_mode"

    async def run(self, dispatcher, tracker, domain):
        mod_count = tracker.get_slot("modification_count") or 0
        return [SlotSet("transport_mode", None), SlotSet("modification_count", mod_count + 1)]


class ActionResetNumTravellers(Action):
    def name(self) -> Text:
        return "action_reset_num_travellers"

    async def run(self, dispatcher, tracker, domain):
        mod_count = tracker.get_slot("modification_count") or 0
        return [SlotSet("num_travellers", None), SlotSet("modification_count", mod_count + 1)]


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING CANCEL / RESTART
# ─────────────────────────────────────────────────────────────────────────────

class ActionCancelBooking(Action):
    """Cancel the current itinerary draft (pre-payment cancellation)."""

    def name(self) -> Text:
        return "action_cancel_booking"

    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(
            text="❌ Booking cancelled. Your trip details have been cleared. Let me know if you'd like to start a new search!"
        )
        return [
            SlotSet("origin", None),
            SlotSet("destination", None),
            SlotSet("travel_dates", None),
            SlotSet("budget_amount", None),
            SlotSet("eco_level", None),
            SlotSet("transport_mode", None),
            SlotSet("num_travellers", None),
            SlotSet("awaiting_review", False),
            SlotSet("itinerary_draft", False),
        ]


class ActionCancelItinerary(Action):
    """Cancel inside an active form (triggered by deny intent during form)."""

    def name(self) -> Text:
        return "action_cancel_itinerary"

    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(
            text="No problem — I've cancelled the current booking. Feel free to start again whenever you're ready!"
        )
        return [
            SlotSet("origin", None),
            SlotSet("destination", None),
            SlotSet("travel_dates", None),
            SlotSet("budget_amount", None),
            SlotSet("eco_level", None),
            SlotSet("transport_mode", None),
            SlotSet("num_travellers", None),
            SlotSet("awaiting_review", False),
            SlotSet("itinerary_draft", False),
        ]


class ActionRestart(Action):
    """Full conversation restart triggered by start_over intent."""

    def name(self) -> Text:
        return "action_restart"

    async def run(self, dispatcher, tracker, domain):
        return [AllSlotsReset()]


# ─────────────────────────────────────────────────────────────────────────────
# ESCALATION & FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

class ActionHumanHandover(Action):
    def name(self) -> Text:
        return "action_human_handover"

    async def run(self, dispatcher, tracker, domain):
        destination = tracker.get_slot("destination") or "Not specified"
        origin = tracker.get_slot("origin") or "Not specified"
        travel_dates = tracker.get_slot("travel_dates") or "Not specified"
        ticket_id = str(uuid.uuid4())[:8].upper()
        severity = "Medium"
        carbon = tracker.get_slot("carbon_score")
        if carbon and float(carbon) > 200:
            severity = "High"

        dispatcher.utter_message(
            json_message=custom_message(
                "escalation_banner",
                {
                    "ticket_id": ticket_id,
                    "severity": severity,
                    "context": {
                        "origin": origin,
                        "destination": destination,
                        "travel_dates": travel_dates,
                    },
                },
            )
        )
        dispatcher.utter_message(
            text=(
                f"👤 **Connecting you to a travel specialist...**\n\n"
                f"Your reference: **#{ticket_id}** | Priority: **{severity}**\n\n"
                f"A specialist will review your trip ({origin} → {destination}) "
                f"and follow up shortly."
            )
        )
        return [SlotSet("escalated", True)]


class ActionHandleFallback(Action):
    def name(self) -> Text:
        return "action_handle_fallback"

    async def run(self, dispatcher, tracker, domain):
        # ROOT CAUSE EXPLANATION (kept here for future maintainers):
        # utter_default_fallback CANNOT appear as a step in the fallback rule
        # after this action, because the two recovery stories
        # ('fallback then recovery with greet' and 'fallback then recovery with
        # book trip') continue with a new user intent after this action — Rasa
        # inserts an implicit action_listen between this action and that intent.
        # A rule that chains utter_default_fallback here predicts a bot action
        # next; the stories predict action_listen next. That is the
        # InvalidRule contradiction. It cannot be resolved in YAML.
        #
        # SOLUTION: the rule is a single step (nlu_fallback → this action).
        # All messages are sent here via dispatcher. The validator warning
        # "utter_default_fallback not used in any story/rule" is suppressed by
        # listing it in domain.yml actions: as well as responses: — that tells
        # Rasa it is intentionally called from custom action code.
        count = int(tracker.get_slot("fallback_count") or 0) + 1

        if count >= 2:
            # Second consecutive miss — tell the user and escalate.
            dispatcher.utter_message(response="utter_default_fallback")
            return [
                SlotSet("fallback_count", 0),
                FollowupAction("action_human_handover"),
            ]

        # First miss — show a helpful menu.
        dispatcher.utter_message(text="🤔 I didn't quite understand that. Here's what I can help with:")
        dispatcher.utter_message(
            json_message=custom_message(
                "quick_reply",
                {
                    "replies": [
                        {"title": "🗺️ Plan a trip", "payload": "book_trip"},
                        {"title": "📊 Carbon footprint", "payload": "request_carbon_info"},
                        {"title": "🏨 Eco hotels", "payload": "request_eco_hotels"},
                        {"title": "🌍 Cultural tips", "payload": "request_cultural_info"},
                        {"title": "👤 Speak to a human", "payload": "escalate_to_human"},
                    ]
                },
            )
        )
        return [SlotSet("fallback_count", count)]


class ActionDefaultFallback(Action):
    """Compatibility wrapper so Rasa's built-in action_default_fallback is handled."""

    def name(self) -> Text:
        return "action_default_fallback"

    async def run(self, dispatcher, tracker, domain):
        return await ActionHandleFallback().run(dispatcher, tracker, domain)


# ─────────────────────────────────────────────────────────────────────────────
# FORM VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

class ValidateTripIntakeForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_booking_form"

    async def validate_destination(self, slot_value, dispatcher, tracker, domain):
        if not slot_value or len(str(slot_value).strip()) < 2:
            dispatcher.utter_message(
                text="Please enter a valid destination city (e.g. Amsterdam, Lisbon)."
            )
            return {"destination": None}

        clean_dest = str(slot_value).strip().title()
        current_origin = tracker.get_slot("origin")

        # Guard: slot_value is the stale origin being fed back by the entity
        # extractor (e.g. user said "to paris" but NLU tagged paris as origin).
        # In this case slot_value == current_origin even though user typed a
        # different city — we must clear and re-ask rather than blame the user.
        if current_origin and current_origin.strip().title() == clean_dest:
            # Check whether the user's raw text actually contains a different city.
            # If the text contains the origin city we assume it was mis-extracted;
            # if it only contains the origin name we ask them to be more specific.
            dispatcher.utter_message(
                text=(
                    f"I see **{clean_dest}** as your departure city. "
                    f"Please tell me where you want to **travel to** — a different city."
                )
            )
            return {"destination": None}

        return {"destination": clean_dest}

    async def validate_origin(self, slot_value, dispatcher, tracker, domain):
        if not slot_value or len(str(slot_value).strip()) < 2:
            dispatcher.utter_message(
                text="Please enter a valid departure city (e.g. Berlin, London)."
            )
            return {"origin": None}

        clean_origin = str(slot_value).strip().title()
        current_destination = tracker.get_slot("destination")

        # If destination was already set and equals the new origin, clear
        # destination so the form re-asks for it rather than silently looping.
        if current_destination and current_destination.strip().title() == clean_origin:
            logger.info(
                "Origin '%s' matches existing destination — clearing destination to re-ask.",
                clean_origin,
            )
            return {"origin": clean_origin, "destination": None}

        return {"origin": clean_origin}

    async def validate_travel_dates(self, slot_value, dispatcher, tracker, domain):
        if not slot_value:
            dispatcher.utter_message(text="Please enter your travel dates (e.g. 15-20 June, next weekend, July 2025).")
            return {"travel_dates": None}

        raw = str(slot_value).strip()

        # Reject if it looks like a city, transport request, or intent phrase
        # rather than an actual date — heuristic: contains known intent keywords
        # or is longer than 60 chars with no digit or month word.
        MONTH_WORDS = (
            "jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec",
            "january","february","march","april","june","july","august","september",
            "october","november","december","weekend","week","next","tonight","today",
            "tomorrow","monday","tuesday","wednesday","thursday","friday","saturday","sunday",
        )
        REJECT_PHRASES = (
            "cultural tips","transport options","show me","give me","tell me",
            "book","cancel","from","to","travelling","planning",
        )
        lower = raw.lower()
        has_date_signal = (
            any(re.search(rf"\b{m}\b", lower) for m in MONTH_WORDS)
            or bool(re.search(r"\d", raw))
        )
        has_reject_phrase = any(p in lower for p in REJECT_PHRASES)

        if has_reject_phrase or not has_date_signal:
            dispatcher.utter_message(
                text=(
                    "That doesn't look like travel dates. "
                    "Please enter when you'd like to travel — e.g. **15-20 June**, "
                    "**next weekend**, **July 10-17**."
                )
            )
            return {"travel_dates": None}

        return {"travel_dates": raw}

    async def validate_num_travellers(self, slot_value, dispatcher, tracker, domain):
        # Reject anything that isn't a plain number between 1 and 50
        REJECT_PHRASES = (
            "transport", "show me", "give me", "cultural", "options", "from", "to",
            "berlin", "paris", "flight", "train", "book", "cancel",
        )
        raw = str(slot_value or "").strip().lower()
        if any(p in raw for p in REJECT_PHRASES):
            dispatcher.utter_message(
                text="Please enter the **number of travellers** — e.g. 1, 2, or 4."
            )
            return {"num_travellers": None}
        try:
            n = float(str(slot_value).replace(",", ".").strip())
            if n < 1 or n > 50 or n != int(n):
                raise ValueError
            return {"num_travellers": int(n)}
        except (ValueError, TypeError):
            dispatcher.utter_message(
                text="Please enter a whole number of travellers between 1 and 50.",
                buttons=[
                    {"title": "1 person", "payload": "1 traveller"},
                    {"title": "2 people", "payload": "2 travellers"},
                    {"title": "3–4 people", "payload": "3 travellers"},
                    {"title": "5+ people", "payload": "5 travellers"},
                ],
            )
            return {"num_travellers": None}

    async def validate_budget_amount(self, slot_value, dispatcher, tracker, domain):
        REJECT_PHRASES = (
            "transport", "show me", "give me", "cultural", "options", "from", "to",
            "flight", "train", "book", "cancel", "berlin", "paris",
        )
        raw = str(slot_value or "").strip().lower()
        if any(p in raw for p in REJECT_PHRASES):
            dispatcher.utter_message(
                text="Please enter your **budget in euros** — e.g. 1000 or €1500."
            )
            return {"budget_amount": None}
        try:
            amount = float(str(slot_value).replace("€", "").replace(",", "").strip())
            if amount <= 0:
                raise ValueError
            return {"budget_amount": amount}
        except (ValueError, TypeError):
            dispatcher.utter_message(
                text="Please enter a numeric budget in EUR (e.g. 1000).",
                buttons=[
                    {"title": "Under €500", "payload": "My budget is about 400 euros"},
                    {"title": "€500 – €1,500", "payload": "My budget is about 1000 euros"},
                    {"title": "€1,500 – €3,000", "payload": "My budget is about 2000 euros"},
                    {"title": "€3,000+", "payload": "My budget is about 4000 euros"},
                ],
            )
            return {"budget_amount": None}

    async def validate_eco_level(self, slot_value, dispatcher, tracker, domain):
        normalized = normalize_eco_level(
            str(slot_value) if slot_value is not None else latest_text(tracker)
        )
        if not normalized:
            dispatcher.utter_message(
                text="Please choose a sustainability level:",
                buttons=[
                    {"title": "🌿 Just a little greener", "payload": "low eco level please"},
                    {"title": "♻️ Actively eco-friendly", "payload": "moderate eco level please"},
                    {"title": "🌍 Maximum sustainability", "payload": "high eco level please"},
                ],
            )
            return {"eco_level": None}
        return {"eco_level": normalized}

    async def validate_transport_mode(self, slot_value, dispatcher, tracker, domain):
        raw_value = str(slot_value or "").strip()
        normalized = extract_transport_mode(raw_value) or extract_transport_mode(latest_text(tracker))
        if not normalized:
            dispatcher.utter_message(
                text="Please choose how you'd like to travel:",
                buttons=[
                    {"title": "✈️ Flight", "payload": "flight"},
                    {"title": "🚆 Train", "payload": "train"},
                    {"title": "🚌 Bus", "payload": "bus"},
                    {"title": "🚗 Car", "payload": "car"},
                    {"title": "⛴️ Ferry", "payload": "ferry"},
                ],
            )
            return {"transport_mode": None}
        return {"transport_mode": normalized}
