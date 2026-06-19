import json
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

from action_config import ENABLE_GUEST_ITINERARY_PERSISTENCE
from action_helpers import map_hotels, map_transport_options, resolve_destination
from metadata import IATA_TO_CITY
from services.carbon_service import calculate_carbon, estimate_distance_km
from services.cultural_service import fetch_cultural_profile
from services.hotel_service import fetch_eco_hotels
from services.itinerary_service import map_offset_programs
from services.travel_service import fetch_transport_options
from api.services.itinerary_service import ItineraryService
from api.services.repositories.itinerary_repository import ItineraryRepository
from api.services.schemas.itinerary import ItineraryRequest
from utils.formatter import custom_message, format_travel_dates, latest_text, safe_float
from utils.eco_level import normalize_eco_level
from utils.parser import (
    clean_city_phrase,
    extract_budget,
    extract_destination,
    extract_origin,
    extract_review_choice,
    extract_route,
    extract_transport_mode,
    extract_travel_date,
    infer_slot_updates,
    is_past_travel_date,
)

load_dotenv()
logger = logging.getLogger("nova.actions")


MANDATORY_TRIP_SLOTS = ("origin", "destination", "travel_dates")

def _normalise_city_code(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return IATA_TO_CITY.get(value.strip().upper(), value)



def _slot_snapshot(tracker: Tracker) -> Dict[str, Any]:
    return {key: tracker.get_slot(key) for key in [
        "origin", "destination", "travel_dates", "budget_amount", "num_travellers",
        "eco_level", "transport_mode", "trip_type", "awaiting_review", "fetch_travel_options_confirmed",
        "hotel_options", "destination_info", "modification_choice", "final_booking_decision",
    ]}


def _normalise_core_slots(tracker: Tracker) -> Dict[str, Any]:
    text = latest_text(tracker)
    slots = _slot_snapshot(tracker)
    updates = infer_slot_updates(text, slots)
    merged = {**slots, **updates}

    if merged.get("origin"):
        merged["origin"] = clean_city_phrase(str(_normalise_city_code(merged["origin"])))
    if merged.get("destination"):
        merged["destination"] = clean_city_phrase(str(_normalise_city_code(merged["destination"])))
    parsed_date = extract_travel_date(text)
    if parsed_date and re.search(r"\b(?:today|tomorrow|next|\d{1,2}[./-]\d{1,2}|\d{1,2}\s+[a-zA-Z]+|for\s+\d+\s+days?)\b", text or "", re.IGNORECASE):
        merged["travel_dates"] = parsed_date
    elif not merged.get("travel_dates") and parsed_date:
        merged["travel_dates"] = parsed_date
    if not merged.get("awaiting_review"):
        choice = extract_review_choice(text)
        if choice:
            merged["awaiting_review"] = choice
    return merged


def _slotset_changed(tracker: Tracker, values: Dict[str, Any]) -> List[SlotSet]:
    events: List[SlotSet] = []
    for key, value in values.items():
        if value is not None and tracker.get_slot(key) != value:
            events.append(SlotSet(key, value))
    return events


def _validate_trip_slots(dispatcher: CollectingDispatcher, values: Dict[str, Any]) -> tuple[bool, List[SlotSet]]:
    events: List[SlotSet] = []
    origin = values.get("origin")
    destination = values.get("destination")
    travel_dates = values.get("travel_dates")

    if origin and destination and str(origin).strip().lower() == str(destination).strip().lower():
        dispatcher.utter_message(
            text="⚠️ Your origin and destination cannot be the same. Please enter a different destination."
        )
        events.append(SlotSet("destination", None))
        return False, events

    if is_past_travel_date(str(travel_dates)):
        dispatcher.utter_message(
            text="📅 We do not support same-day or past travel bookings. Please choose a departure date after today, for example 24 June 2026 for 5 days."
        )
        events.append(SlotSet("travel_dates", None))
        return False, events

    return True, events


def _safe_int(value: Any, default: int = 1) -> int:
    try:
        return max(1, int(float(value)))
    except (TypeError, ValueError):
        return default


def _safe_float_or_none(value: Any) -> float | None:
    try:
        if value in (None, "", "—"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None



def _travel_date_range_for_hotels(travel_dates: Any) -> tuple[str, str]:
    import re
    from datetime import date, timedelta
    raw = str(travel_dates or "")
    matches = re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", raw)
    if len(matches) >= 2:
        return matches[0], matches[1]
    if len(matches) == 1:
        start = matches[0]
        try:
            dt = datetime.strptime(start, "%Y-%m-%d").date()
            return start, (dt + timedelta(days=3)).isoformat()
        except Exception:
            pass
    start = date.today() + timedelta(days=14)
    return start.isoformat(), (start + timedelta(days=3)).isoformat()



def _extract_first_number(value: Any) -> float | None:
    if value in (None, "", "—"):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group(0)) if match else None


def _trip_nights(travel_dates: Any) -> int:
    raw = str(travel_dates or "")
    dates = re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", raw)
    if len(dates) >= 2:
        try:
            start = datetime.strptime(dates[0], "%Y-%m-%d").date()
            end = datetime.strptime(dates[1], "%Y-%m-%d").date()
            return max(1, (end - start).days)
        except Exception:
            return 1
    # Best effort for phrases still containing "for N days".
    match = re.search(r"\bfor\s+(\d{1,2})\s+days?\b", raw, re.IGNORECASE)
    if match:
        try:
            return max(1, int(match.group(1)))
        except Exception:
            pass
    return 1


def _calculate_trip_price(
    *,
    num_travellers: Any,
    ticket_option: dict | None,
    hotel_option: dict | None,
    travel_dates: Any,
) -> dict[str, Any]:
    travellers = _safe_int(num_travellers, 1)
    nights = _trip_nights(travel_dates)
    ticket_price = _extract_first_number((ticket_option or {}).get("price_eur"))
    if ticket_price is None:
        ticket_price = _extract_first_number((ticket_option or {}).get("cost"))
    hotel_per_night = _extract_first_number((hotel_option or {}).get("price_eur"))
    if hotel_per_night is None:
        hotel_per_night = _extract_first_number((hotel_option or {}).get("price"))

    ticket_total = travellers * float(ticket_price or 0)
    hotel_total = travellers * nights * float(hotel_per_night or 0)
    total = ticket_total + hotel_total
    return {
        "num_travellers": travellers,
        "nights": nights,
        "ticket_price_per_traveller": round(float(ticket_price or 0), 2),
        "ticket_total": round(ticket_total, 2),
        "hotel_price_per_night": round(float(hotel_per_night or 0), 2),
        "hotel_total": round(hotel_total, 2),
        "total": round(total, 2),
        "formula": "Total = (travellers × ticket price) + (travellers × hotel per night × trip nights)",
    }


def _slot_allowed(domain: Dict[str, Any], slot_name: str) -> bool:
    return slot_name in (domain or {}).get("slots", {})


def _slotset_if_defined(domain: Dict[str, Any], slot_name: str, value: Any) -> list[SlotSet]:
    return [SlotSet(slot_name, value)] if _slot_allowed(domain, slot_name) else []


def _guest_persistence_enabled() -> bool:
    return ENABLE_GUEST_ITINERARY_PERSISTENCE

# SESSION
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


class ActionValidateTravelDate(Action):
    def name(self) -> Text:
        return "action_validate_travel_date"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        values = _normalise_core_slots(tracker)
        travel_dates = values.get("travel_dates")
        raw_text = latest_text(tracker)
        if not travel_dates:
            return _slotset_changed(tracker, values)
        if is_past_travel_date(str(travel_dates)) or is_past_travel_date(raw_text):
            dispatcher.utter_message(text="📅 We do not support same-day or past travel bookings. Please choose a departure date after today, for example 24 June 2026 for 5 days.")
            return [SlotSet("travel_dates", None)]
        return _slotset_changed(tracker, values)


# TRAVEL INFORMATION
class ActionFetchTravelOptions(Action):
    def name(self) -> Text:
        return "action_fetch_travel_options"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        values = _normalise_core_slots(tracker)
        origin = values.get("origin")
        destination = values.get("destination")
        travel_dates = values.get("travel_dates") or "flexible"
        eco_level = values.get("eco_level") or "moderate"
        selected_mode = (values.get("transport_mode") or "flight").lower()

        if not origin or not destination:
            dispatcher.utter_message(
                text="Please tell me both cities for the route, for example: from Berlin to Amsterdam."
            )
            return _slotset_changed(tracker, values)

        dispatcher.utter_message(
            text=f"🔍 Searching sustainable **{selected_mode.title()}** and hotel options for your trip from **{origin}** to **{destination}**..."
        )

        try:
            payload = await fetch_transport_options(origin, destination, travel_dates, eco_level, selected_mode=selected_mode)
            all_options = payload.get("options", [])
            api_source = payload.get("source", "mock")
        except Exception as exc:
            logger.error("fetch_transport_options failed: %s", exc)
            dispatcher.utter_message(text="⚠️ Could not fetch travel options right now. I’ll continue with the summary.")
            return _slotset_changed(tracker, values)

        mode_options = [
            option for option in all_options
            if str(option.get("mode", "")).lower() == selected_mode
        ]

        if not mode_options:
            dispatcher.utter_message(
                text=f"⚠️ I could not find **{selected_mode}** options for this route. I’ll keep your selected mode and continue with the summary."
            )
            events = _slotset_changed(tracker, values)
            events.append(SlotSet("transport_options", []))
            return events

        best_option = mode_options[0]
        dispatcher.utter_message(
            text=f"✅ Found {len(mode_options)} **{selected_mode}** option(s). I selected the best option for your summary."
        )
        events = _slotset_changed(tracker, values)
        events.extend([
            SlotSet("transport_mode", selected_mode),
            SlotSet("price_total", best_option.get("price_eur")),
            SlotSet("transport_options", [best_option]),
        ])
        return events

class ActionCalculateCarbon(Action):
    def name(self) -> Text:
        return "action_calculate_carbon"

    async def run(self, dispatcher, tracker, domain):
        values = _normalise_core_slots(tracker)
        origin = values.get("origin")
        destination = values.get("destination")
        mode = (values.get("transport_mode") or "flight").lower()
        num_travellers = _safe_int(values.get("num_travellers"), 1)

        if not origin or not destination:
            dispatcher.utter_message(
                text="Please tell me both cities before I calculate emissions, for example: carbon for train from London to Paris."
            )
            return _slotset_changed(tracker, values)

        dispatcher.utter_message(
            text=f"♻️ Calculating carbon for **{mode}** from **{origin}** to **{destination}**..."
        )

        try:
            dist_km = estimate_distance_km(origin, destination)
            result = await calculate_carbon(origin, destination, mode, dist_km)
        except Exception as exc:
            logger.error("calculate_carbon failed: %s", exc)
            dispatcher.utter_message(text="⚠️ Carbon calculation failed. I’ll continue with a fallback summary.")
            return _slotset_changed(tracker, values)

        kg_co2e = float(result.get("kg_co2e") or result.get("co2e") or 0)
        colour = result.get("colour", "amber")
        label = {
            "green": "Low impact ✅",
            "amber": "Moderate impact ⚠️",
            "red": "High impact ❌",
        }.get(colour, "")
        api_source = result.get("api_source", result.get("source", "estimate"))
        per_person = round(kg_co2e / num_travellers, 1) if num_travellers > 1 else None

        carbon_text = f"♻️ Carbon estimate: **{kg_co2e:.1f} kg CO₂e total** ({api_source})."
        if per_person is not None:
            carbon_text += f" That is about **{per_person} kg CO₂e per traveller**."
        dispatcher.utter_message(text=carbon_text)
        dispatcher.utter_message(
            json_message=custom_message(
                "carbon_card",
                {
                    "colour": colour,
                    "kg_co2e": kg_co2e,
                    "per_person": per_person,
                    "mode": mode,
                    "label": label,
                    "source": api_source,
                    "disclaimer": result.get("disclaimer", "Carbon values are estimates."),
                },
            )
        )
        if colour == "red":
            dispatcher.utter_message(
                text="🌿 This is a higher-impact option. You can still continue, or modify the transport mode later if you prefer a greener alternative."
            )

        events = _slotset_changed(tracker, values)
        events.extend([
            SlotSet("origin", origin),
            SlotSet("destination", destination),
            SlotSet("transport_mode", mode),
            SlotSet("carbon_score", kg_co2e),
        ])
        return events

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

        
        try:
            check_in, check_out = _travel_date_range_for_hotels(tracker.get_slot("travel_dates"))
            result = await fetch_eco_hotels(
                destination,
                check_in=check_in,
                check_out=check_out,
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

        best_hotel = hotels[0]
        dispatcher.utter_message(
            text=f"✅ Found {len(hotels)} hotel option(s). I selected the best hotel option for your summary."
        )
        # Store only the best hotel option for the final Trip Summary.
        return [
            SlotSet("destination", destination),
            SlotSet("budget_amount", float(budget)),
            SlotSet("hotel_options", [best_hotel]),
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
        text = latest_text(tracker)
        destination = resolve_destination(tracker, text, extract_destination)
        if not destination:
            dispatcher.utter_message(
                text="🌍 Please tell me a destination first (e.g. Tokyo, Barcelona)."
            )
            return []

        profile = await fetch_cultural_profile(destination)
        tips = profile.get("tips", {})
        source = profile.get("source", "mock_data")

        country_overview = tips.get("country_overview", [])
        eco_activities = tips.get("eco_activities", [])
        responsible_tips = tips.get("responsible_tips", [])
        overview_text = "\n".join(f"• {x}" for x in country_overview[:4]) if isinstance(country_overview, list) else str(country_overview)
        eco_text = "\n".join(f"• {x}" for x in eco_activities[:4]) if isinstance(eco_activities, list) else str(eco_activities)
        responsible_text = "\n".join(f"• {x}" for x in responsible_tips[:4]) if isinstance(responsible_tips, list) else str(responsible_tips)

        dispatcher.utter_message(
            text=(
                f"🌍 **Cultural insights for {destination}** ({source})\n\n"
                f"**Overview**\n{overview_text or 'No overview available.'}\n\n"
                f"**Eco-friendly activities**\n{eco_text or 'No activities available.'}\n\n"
                f"**Responsible travel tips**\n{responsible_text or 'No responsible travel tips available.'}"
            )
        )
        dispatcher.utter_message(
            json_message=custom_message(
                "cultural_tips",
                {
                    "destination": destination,
                    "country_overview": country_overview,
                    "eco_activities": eco_activities,
                    "responsible_tips": responsible_tips,
                    "sustainability_rating": tips.get("sustainability_rating", "N/A"),
                    "source": source,
                },
            )
        )
        destination_info = overview_text or f"{destination} is your selected destination."
        return [SlotSet("destination", destination), SlotSet("destination_info", destination_info)]


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


# ITINERARY SUMMARY & REVIEW
class ActionReviewTripDetails(Action):
    def name(self) -> Text:
        return "action_review_trip_details"

    async def run(self, dispatcher, tracker, domain):
        values = _normalise_core_slots(tracker)
        valid, validation_events = _validate_trip_slots(dispatcher, values)
        if not valid:
            return validation_events

        origin = values.get("origin") or "—"
        destination = values.get("destination") or "—"
        travel_dates = format_travel_dates(values.get("travel_dates") or "—")
        budget = values.get("budget_amount") or "Not specified"
        travellers = _safe_int(values.get("num_travellers"), 1)
        eco_level = values.get("eco_level") or "moderate"
        transport_mode = values.get("transport_mode") or "flight"
        carbon_kg = _safe_float_or_none(tracker.get_slot("carbon_score"))
        carbon_line = (
            f"{carbon_kg:.1f} kg CO₂e total"
            if carbon_kg is not None
            else "Not available yet"
        )

        dispatcher.utter_message(
            text=(
                "📋 **Review your trip details before I search live booking options**\n\n"
                f"1. **Route:** {origin} → {destination}\n"
                f"2. **Dates:** {travel_dates}\n"
                f"3. **Travellers:** {travellers}\n"
                f"4. **Budget:** €{budget}\n"
                f"5. **Eco preference:** {eco_level}\n"
                f"6. **Transport:** {str(transport_mode).title()}\n"
                f"7. **Carbon estimate:** {carbon_line}\n\n"
                "Do you want to continue with booking/searching this trip, or modify something first?"
            )
        )
        events = _slotset_changed(tracker, values)
        # Reset review slots so a previous modify/confirm choice cannot loop.
        events.extend([
            SlotSet("awaiting_review", None),
            SlotSet("modification_choice", None),
            SlotSet("transport_options", None),
            SlotSet("hotel_options", None),
            SlotSet("destination_info", None),
            SlotSet("price_total", None),
            SlotSet("final_booking_decision", None),
        ])
        events.extend(_slotset_if_defined(domain, "itinerary_draft", True))
        events.extend(_slotset_if_defined(domain, "itinerary_confirmed", False))
        return events


class ActionFetchDestinationInfo(Action):
    def name(self) -> Text:
        return "action_fetch_destination_info"

    async def run(self, dispatcher, tracker, domain):
        values = _normalise_core_slots(tracker)
        destination = values.get("destination") or resolve_destination(tracker, latest_text(tracker), extract_destination)
        if not destination:
            return _slotset_changed(tracker, values)

        try:
            profile = await fetch_cultural_profile(destination)
            tips = profile.get("tips", {}) if isinstance(profile, dict) else {}
            source = profile.get("source", "mock_data") if isinstance(profile, dict) else "mock_data"
            overview = tips.get("country_overview") or []
            responsible = tips.get("responsible_tips") or []
            eco_activities = tips.get("eco_activities") or []
            wiki = tips.get("wiki") or {}

            overview_lines = overview if isinstance(overview, list) else [str(overview)]
            responsible_lines = responsible if isinstance(responsible, list) else [str(responsible)]
            activity_lines = eco_activities if isinstance(eco_activities, list) else [str(eco_activities)]

            description_parts = []
            description_parts.extend([x for x in overview_lines if x][:5])
            if activity_lines:
                description_parts.append("Eco activities: " + "; ".join([x for x in activity_lines if x][:3]))
            if responsible_lines:
                description_parts.append("Responsible tips: " + "; ".join([x for x in responsible_lines if x][:3]))

            fallback_description = "\n".join(f"• {x}" for x in description_parts if x)
            if not fallback_description:
                fallback_description = f"{destination} is your selected destination. NovaPlan will include practical, lower-impact travel guidance."

            # Facts column: prefer structured country facts from RestCountries.
            facts = []
            for item in overview_lines[:8]:
                if isinstance(item, str) and ":" in item:
                    field, value = item.split(":", 1)
                    facts.append({"field": field.strip(), "value": value.strip()})

            destination_payload = {
                "city": destination,
                "source": source,
                "description": wiki.get("extract") or fallback_description,
                "wiki_html": wiki.get("extract_html") or wiki.get("extract") or fallback_description,
                "wiki_title": wiki.get("title") or destination,
                "wiki_url": wiki.get("url"),
                "thumbnail": wiki.get("thumbnail"),
                "facts": facts,
                "country_overview": overview_lines,
                "responsible_tips": responsible_lines[:4],
                "eco_activities": activity_lines[:4],
            }

            return [
                *_slotset_changed(tracker, values),
                SlotSet("destination", destination),
                SlotSet("destination_info", destination_payload),
            ]
        except Exception as exc:
            logger.warning("destination info fetch failed for %s: %s", destination, exc)
            return [
                *_slotset_changed(tracker, values),
                SlotSet("destination_info", {"city": destination, "description": f"{destination} is your selected destination. Destination details were unavailable, so I used a safe fallback summary.", "wiki_html": f"{destination} is your selected destination. Destination details were unavailable, so I used a safe fallback summary.", "facts": []}),
            ]


class ActionDisplayItinerarySummary(Action):

    def name(self) -> Text:
        return "action_display_itinerary_summary"

    async def run(self, dispatcher, tracker, domain):
        values = _normalise_core_slots(tracker)
        valid, validation_events = _validate_trip_slots(dispatcher, values)
        if not valid:
            return validation_events

        origin = values.get("origin") or "Unknown"
        destination = values.get("destination") or "Unknown"
        travel_dates = format_travel_dates(values.get("travel_dates") or "Flexible")
        budget = values.get("budget_amount") or "Not specified"
        eco_level = values.get("eco_level") or "moderate"
        transport_mode = values.get("transport_mode") or "flight"
        num_travellers = _safe_int(values.get("num_travellers"), 1)
        carbon_kg = _safe_float_or_none(tracker.get_slot("carbon_score"))
        transport_options = tracker.get_slot("transport_options") or []
        hotel_options = tracker.get_slot("hotel_options") or []
        destination_payload = tracker.get_slot("destination_info") or {}
        if isinstance(destination_payload, dict):
            destination_description = destination_payload.get("description") or destination_payload.get("wiki_html") or f"{destination} is your selected destination."
        else:
            destination_description = str(destination_payload or f"{destination} is your selected destination.")
            destination_payload = {"city": destination, "description": destination_description, "wiki_html": destination_description, "facts": []}

        # The product promise is to select the best option. Keep only the top
        # ranked ticket and hotel in the final user-facing summary.
        mapped_transport = (map_transport_options(transport_options) if isinstance(transport_options, list) else [])[:1]
        mapped_hotels = (map_hotels(hotel_options) if isinstance(hotel_options, list) else [])[:1]

        ticket_lines = []
        if mapped_transport:
            for idx, opt in enumerate(mapped_transport[:1], start=1):
                details = (opt.get("details") or "No details available").replace("\n", "<br>")
                option_label = "Flight Option" if str(opt.get("mode", transport_mode)).lower() == "flight" else "Travel Option"
                ticket_lines.append(
                    f"**{option_label} {idx}**\n"
                    f"| Field | Details |\n|---|---|\n"
                    f"| Mode | {str(opt.get('mode', transport_mode)).title()} |\n"
                    f"| Cost | {opt.get('cost', 'Price unavailable')} |\n"
                    f"| Duration | {opt.get('duration', '—')} |\n"
                    f"| Emissions | {opt.get('emissions', '—')} kg CO₂e |\n"
                    f"| Details | {details} |"
                )
        else:
            ticket_lines.append("No matching ticket option was returned for this route/mode. You can still keep the draft and search again later.")

        hotel_lines = []
        if mapped_hotels:
            for idx, hotel in enumerate(mapped_hotels[:1], start=1):
                amenities = hotel.get("amenities") or []
                amenity_text = ", ".join(amenities) if isinstance(amenities, list) else str(amenities)
                hotel_lines.append(
                    f"**Hotel Option {idx}**\n"
                    f"| Field | Details |\n|---|---|\n"
                    f"| Name | {hotel.get('name', 'Eco hotel')} |\n"
                    f"| Price | {hotel.get('price', '—')} |\n"
                    f"| Rating | {hotel.get('rating', '—')} |\n"
                    f"| Address | {hotel.get('address') or destination} |\n"
                    f"| Sustainability | {hotel.get('description', 'Eco-friendly property')} |\n"
                    f"| Highlights | {amenity_text or '—'} |\n"
                    f"| Hotel carbon | {hotel.get('carbon_kg', '—')} kg CO₂/night |"
                )
        else:
            hotel_lines.append("No hotel options were returned. NovaPlan can still confirm the travel draft and hotels can be searched later.")

        best_transport_for_price = mapped_transport[0] if mapped_transport else None
        best_hotel_for_price = mapped_hotels[0] if mapped_hotels else None
        price_breakdown = _calculate_trip_price(
            num_travellers=num_travellers,
            ticket_option=best_transport_for_price,
            hotel_option=best_hotel_for_price,
            travel_dates=travel_dates,
        )
        carbon_line = f"{carbon_kg:.1f} kg CO₂e total" if carbon_kg is not None else "Not available"

        summary_text = (
            f"# 🌍 Trip Summary\n\n"
            f"## Booking Summary\n"
            f"| Field | Details |\n|---|---|\n"
            f"| Route | {origin} → {destination} |\n"
            f"| Dates | {travel_dates} |\n"
            f"| Travellers | {num_travellers} |\n"
            f"| Budget | €{budget} |\n"
            f"| Eco preference | {eco_level} |\n"
            f"| Transport | {str(transport_mode).title()} |\n\n"
            f"## About Destination\n"
            f"### About {destination}\n{destination_description}\n\n"
            f"## Ticket Options\n" + "\n\n".join(ticket_lines) + "\n\n"
            f"## Hotel Options\n" + "\n\n".join(hotel_lines) + "\n\n"
            f"## Carbon Footprint\n"
            f"| Field | Details |\n|---|---|\n"
            f"| Estimated journey emissions | {carbon_line} |\n"
            f"| Note | Values are estimates and depend on route, vehicle type, load factor, and data availability. |\n\n"
            f"Please choose an option below: **Confirm Trip**, **Modify Trip**, **Cancel Trip**, or **Start Again**."
        )
        dispatcher.utter_message(text="✅ Selecting the best flight and hotel option")
        dispatcher.utter_message(text="✅ Preparing your Trip")

        dispatcher.utter_message(
            json_message=custom_message(
                "itinerary_summary",
                {
                    "status": "draft",
                    "booking": {
                        "origin": origin,
                        "destination": destination,
                        "travel_dates": travel_dates,
                        "budget_eur": budget,
                        "num_travellers": num_travellers,
                        "eco_level": eco_level,
                        "transport_mode": transport_mode,
                    },
                    "origin": origin,
                    "destination": destination,
                    "travel_dates": travel_dates,
                    "budget_eur": budget,
                    "num_travellers": num_travellers,
                    "eco_level": eco_level,
                    "transport_mode": transport_mode,
                    "carbon": {
                        "kg_co2e": carbon_kg,
                        "label": carbon_line,
                    },
                    "carbon_kg": carbon_kg,
                    "price_total": price_breakdown.get("total"),
                    "trip_price": price_breakdown,
                    "transport_options": mapped_transport,
                    "hotel_options": mapped_hotels,
                    "destination_info": destination_payload,
                    "destination_description": destination_description,
                    "sections": {
                        "booking_summary": "booking",
                        "about_destination": "destination_info",
                        "ticket_options": "transport_options",
                        "hotel_options": "hotel_options",
                        "carbon_footprint": "carbon",
                    },
                    "actions": ["confirm", "modify", "cancel", "restart"],
                },
            )
        )
        events = _slotset_changed(tracker, values)
        events.extend([SlotSet("final_booking_decision", None), SlotSet("price_total", price_breakdown.get("total"))])
        events.extend(_slotset_if_defined(domain, "itinerary_draft", True))
        return events


class ActionBuildItineraryPackage(Action):
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
    def name(self) -> Text:
        return "action_complete_itinerary"

    async def run(self, dispatcher, tracker, domain):
        values = _normalise_core_slots(tracker)
        valid, validation_events = _validate_trip_slots(dispatcher, values)
        if not valid:
            return validation_events

        origin = values.get("origin") or "—"
        destination = values.get("destination") or "—"
        dates = format_travel_dates(values.get("travel_dates") or "—")
        budget = values.get("budget_amount") or tracker.get_slot("budget_amount") or "—"
        eco = values.get("eco_level") or tracker.get_slot("eco_level") or "—"
        mode = values.get("transport_mode") or tracker.get_slot("transport_mode") or "—"
        carbon = tracker.get_slot("carbon_score")
        transport_options_for_price = tracker.get_slot("transport_options") or []
        hotel_options_for_price = tracker.get_slot("hotel_options") or []

        if not transport_options_for_price:
            try:
                transport_result = await fetch_transport_options(
                    origin,
                    destination,
                    values.get("travel_dates") or tracker.get_slot("travel_dates") or dates,
                    eco,
                    selected_mode=mode,
                )
                transport_options_for_price = transport_result.get("options", [])[:1]
            except Exception as exc:
                logger.warning("confirm transport fallback failed for %s to %s: %s", origin, destination, exc)

        if carbon in (None, "", "—"):
            try:
                distance_km = estimate_distance_km(origin, destination)
                carbon_result = await calculate_carbon(origin, destination, mode, distance_km)
                carbon = carbon_result.get("kg_co2e")
            except Exception as exc:
                logger.warning("confirm carbon fallback failed for %s to %s: %s", origin, destination, exc)

        if not hotel_options_for_price:
            try:
                check_in, check_out = _travel_date_range_for_hotels(values.get("travel_dates") or tracker.get_slot("travel_dates"))
                hotel_result = await fetch_eco_hotels(
                    destination,
                    check_in=check_in,
                    check_out=check_out,
                    max_price=float(safe_float(budget, 1000) or 1000),
                    eco_level=eco,
                )
                hotel_options_for_price = hotel_result.get("hotels", [])[:1]
            except Exception as exc:
                logger.warning("confirm hotel fallback failed for %s: %s", destination, exc)

        mapped_transport = map_transport_options(transport_options_for_price)
        mapped_hotels = map_hotels(hotel_options_for_price)
        destination_payload = tracker.get_slot("destination_info") or {}
        if isinstance(destination_payload, dict):
            destination_description = destination_payload.get("description") or destination_payload.get("wiki_html") or f"{destination} is your selected destination."
        else:
            destination_description = str(destination_payload or f"{destination} is your selected destination.")
            destination_payload = {"city": destination, "description": destination_description, "wiki_html": destination_description, "facts": []}
        price_breakdown = _calculate_trip_price(
            num_travellers=values.get("num_travellers") or tracker.get_slot("num_travellers"),
            ticket_option=mapped_transport[0] if mapped_transport else None,
            hotel_option=mapped_hotels[0] if mapped_hotels else None,
            travel_dates=values.get("travel_dates") or tracker.get_slot("travel_dates"),
        )
        price = price_breakdown.get("total") or tracker.get_slot("price_total") or budget or 0
        ref = ItineraryRepository.new_itinerary_id()

        sender_id = getattr(tracker, "sender_id", None)
        user_id = tracker.get_slot("user_id") or tracker.get_slot("conversation_id") or sender_id
        if user_id == "guest" or str(user_id or "").startswith("novaplan-web-user"):
            user_id = None
        title = f"{origin} → {destination} | {mode} | €{budget}"
        summary = {
            "status": "confirmed",
            "reference": ref,
            "booking_reference": ref,
            "origin": origin,
            "destination": destination,
            "travel_dates": dates,
            "budget_eur": budget,
            "num_travellers": _safe_int(values.get("num_travellers") or tracker.get_slot("num_travellers"), 1),
            "eco_level": eco,
            "transport_mode": mode,
            "carbon": {
                "kg_co2e": _safe_float_or_none(carbon),
                "label": f"{_safe_float_or_none(carbon):.1f} kg CO₂e" if _safe_float_or_none(carbon) is not None else "Not available",
            },
            "carbon_kg": _safe_float_or_none(carbon),
            "price_total": price_breakdown.get("total"),
            "trip_price": price_breakdown,
            "transport_options": mapped_transport,
            "hotel_options": mapped_hotels,
            "destination_info": destination_payload,
            "destination_description": destination_description,
            "sections": {
                "booking_summary": "booking",
                "about_destination": "destination_info",
                "ticket_options": "transport_options",
                "hotel_options": "hotel_options",
                "carbon_footprint": "carbon",
            },
        }

        if user_id or _guest_persistence_enabled():
            try:
                ItineraryService().create(
                    ItineraryRequest(
                        itnId=ref,
                        userId=user_id or "guest",
                        time=dates if dates != "—" else None,
                        title=title,
                        summary=summary,
                        status="confirmed",
                    )
                )
                dispatcher.utter_message(text="✅ Your confirmed itinerary has been saved to the database.")
            except Exception as exc:
                logger.error("failed persisting itinerary: %s", exc)
                dispatcher.utter_message(
                    text=(
                        "⚠️ Your itinerary is confirmed for this chat, but I could not save it to the database. "
                        "Please sign in or try again later to persist it."
                    )
                )
        else:
            dispatcher.utter_message(text="ℹ️ You are using a guest chat, so I kept the itinerary in this session only.")

        dispatcher.utter_message(
            text=(
                "✅ Booking Confirmed!\n\n"
                f"Please find the booking reference **{ref}** for your trip "
                f"from **{origin}** to **{destination}** from **{dates}** "
                f"with **{_safe_int(values.get('num_travellers') or tracker.get_slot('num_travellers'), 1)} traveller(s)** "
                f"for the total price of **€{float(price_breakdown.get('total') or 0):.2f}**.\n\n"
                "The confirmed itinerary will be sent to your e-mail shortly.\n\n"
                "Have a wonderful, sustainable trip! 🌍\n\n"
                "Thank you for using NovaPlan.ai chatbot."
            )
        )
        dispatcher.utter_message(
            custom={
                "type": "itinerary_summary",
                "data": summary,
            }
        )
        events = [
            SlotSet("booking_reference", ref),
            SlotSet("price_total", _safe_float_or_none(price) or 0),
            SlotSet("transport_options", transport_options_for_price),
            SlotSet("hotel_options", hotel_options_for_price),
            SlotSet("carbon_score", _safe_float_or_none(carbon)),
        ]
        events.extend(_slotset_if_defined(domain, "itinerary_draft", False))
        events.extend(_slotset_if_defined(domain, "itinerary_confirmed", True))
        return events


# SLOT RESET ACTIONS
class ActionCancelBooking(Action):
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
            SlotSet("num_travellers", None),
            SlotSet("eco_level", None),
            SlotSet("transport_mode", None),
            SlotSet("awaiting_review", None),
            SlotSet("fetch_travel_options_confirmed", None),
            SlotSet("modification_choice", None),
            SlotSet("transport_options", None),
            SlotSet("price_total", None),
            SlotSet("carbon_score", None),
            SlotSet("hotel_options", None),
            SlotSet("destination_info", None),
            SlotSet("final_booking_decision", None),
            *_slotset_if_defined(domain, "itinerary_draft", False),
            *_slotset_if_defined(domain, "itinerary_confirmed", False),
        ]


class ActionRestart(Action):
    def name(self) -> Text:
        return "action_restart"

    async def run(self, dispatcher, tracker, domain):
        return [AllSlotsReset()]


# ESCALATION & FALLBACK
def _persist_human_handoff(sender_id: str, summary: dict[str, Any], ticket_id: str) -> None:
    try:
        from db.novaplan import get_pool
        ses_id = sender_id or f"ses_{ticket_id.lower()}"
        text = json.dumps({"ticket_id": ticket_id, "handover_summary": summary}, ensure_ascii=False)
        with get_pool().connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (ses_id, user_id, status, needs_human)
                VALUES (%s, NULL, 'active', TRUE)
                ON CONFLICT (ses_id) DO UPDATE
                SET needs_human = TRUE, updated_at = NOW()
                """,
                (ses_id,),
            )
            conn.execute(
                """
                INSERT INTO conversations (ses_id, user_id, text)
                VALUES (%s, %s, %s)
                """,
                (ses_id, None, text),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("failed persisting human handoff: %s", exc)


class ActionHumanHandover(Action):
    def name(self) -> Text:
        return "action_human_handover"

    async def run(self, dispatcher, tracker, domain):
        sender_id = getattr(tracker, "sender_id", None) or tracker.get_slot("conversation_id") or "guest"
        ticket_id = str(uuid.uuid4())[:8].upper()
        summary = {
            "origin": tracker.get_slot("origin") or "Not specified",
            "destination": tracker.get_slot("destination") or "Not specified",
            "travel_dates": tracker.get_slot("travel_dates") or "Not specified",
            "budget_amount": tracker.get_slot("budget_amount") or "Not specified",
            "num_travellers": tracker.get_slot("num_travellers") or "Not specified",
            "eco_level": tracker.get_slot("eco_level") or "Not specified",
            "transport_mode": tracker.get_slot("transport_mode") or "Not specified",
            "carbon_score": tracker.get_slot("carbon_score") or "Not available",
            "price_total": tracker.get_slot("price_total") or "Not available",
        }
        try:
            carbon = float(summary.get("carbon_score") or 0)
        except Exception:
            carbon = 0
        severity = "High" if carbon > 200 else "Medium"
        _persist_human_handoff(str(sender_id), {**summary, "severity": severity}, ticket_id)

        dispatcher.utter_message(
            json_message=custom_message(
                "escalation_banner",
                {
                    "ticket_id": ticket_id,
                    "severity": severity,
                    "context": summary,
                    "message": "Human handover request has been recorded for the support console.",
                },
            )
        )
        dispatcher.utter_message(
            text=(
                "👤 I’ve created a human handover request for our support team.\n\n"
                f"Reference: **{ticket_id}** | Priority: **{severity}**\n\n"
                "I included the current session details so a support person can continue from the React support UI."
            )
        )
        return _slotset_if_defined(domain, "escalated", True)


class ActionHandleFallback(Action):
    def name(self) -> Text:
        return "action_handle_fallback"

    async def run(self, dispatcher, tracker, domain):
        text = latest_text(tracker)
        updates = infer_slot_updates(text, _slot_snapshot(tracker))
        if updates:
            cleaned = {}
            for key, value in updates.items():
                if key in {"origin", "destination"}:
                    cleaned[key] = clean_city_phrase(str(value))
                else:
                    cleaned[key] = value
            valid, validation_events = _validate_trip_slots(dispatcher, {**_slot_snapshot(tracker), **cleaned})
            if not valid:
                return validation_events
            human_summary = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in cleaned.items())
            dispatcher.utter_message(text=f"✅ Got it — {human_summary}.")
            return [SlotSet(k, v) for k, v in cleaned.items()]

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

    def name(self) -> Text:
        return "action_default_fallback"

    async def run(self, dispatcher, tracker, domain):
        return await ActionHandleFallback().run(dispatcher, tracker, domain)
