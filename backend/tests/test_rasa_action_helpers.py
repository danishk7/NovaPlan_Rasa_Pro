from datetime import date, timedelta

import pytest

from conftest import DummyDispatcher, DummyTracker, event_value

import actions
from action_helpers import map_hotels, map_transport_options, resolve_destination
from utils import parser
from utils.eco_level import normalize_eco_level
from utils.formatter import custom_message, format_travel_dates, safe_float
from utils.transport_builder import build_transport_options


def test_validate_trip_slots_rejects_same_origin_destination():
    dispatcher = DummyDispatcher()

    valid, events = actions._validate_trip_slots(
        dispatcher,
        {"origin": "Berlin", "destination": "berlin", "travel_dates": "2026-07-24"},
    )

    assert valid is False
    assert event_value(events, "destination") is None
    assert "cannot be the same" in dispatcher.texts[0]


def test_validate_trip_slots_rejects_past_date():
    dispatcher = DummyDispatcher()

    valid, events = actions._validate_trip_slots(
        dispatcher,
        {"origin": "Berlin", "destination": "Paris", "travel_dates": "2024-01-01"},
    )

    assert valid is False
    assert event_value(events, "travel_dates") is None


def test_normalise_core_slots_extracts_route_budget_and_mode():
    tracker = DummyTracker(
        text="I want to travel from Berlin to Amsterdam by train with budget 900 euros for 2 people",
        slots={},
    )

    values = actions._normalise_core_slots(tracker)

    assert values["origin"] == "Berlin"
    assert values["destination"] == "Amsterdam"
    assert values["budget_amount"] == 900
    assert values["transport_mode"] == "train"


def test_trip_price_uses_travellers_and_nights():
    price = actions._calculate_trip_price(
        num_travellers=2,
        ticket_option={"price_eur": 80},
        hotel_option={"price_eur": 120},
        travel_dates="2026-08-01 to 2026-08-04",
    )

    assert price["ticket_total"] == 160
    assert price["hotel_total"] == 720
    assert price["total"] == 880


def test_parser_extracts_route_budget_transport_and_future_date():
    future = (date.today() + timedelta(days=20)).isoformat()
    text = f"book from London to Paris with budget 500 by bus on {future}"

    assert parser.extract_route(text) == ("London", "Paris")
    assert parser.extract_budget(text) == 500
    assert parser.extract_transport_mode(text) == "bus"
    assert parser.extract_travel_date(text) == future


def test_parser_flags_past_travel_date():
    assert parser.is_past_travel_date("2024-01-01") is True


def test_formatters_and_normalizers():
    assert custom_message("carbon_card", {"kg": 10}) == {"type": "carbon_card", "data": {"kg": 10}}
    assert format_travel_dates("2026-08-01 to 2026-08-03")
    assert safe_float("12.5") == 12.5
    assert normalize_eco_level("maximum sustainability") == "high"


def test_mapping_helpers_shape_transport_and_hotels():
    mapped = map_transport_options(
        [{"mode": "train", "price_eur": 40, "duration_hrs": 2, "carbon_kg": 8, "notes": "direct"}]
    )
    hotels = map_hotels(
        [{"name": "Eco Stay", "price_eur": 100, "rating": 8.5, "eco_cert": "Green", "highlights": ["solar"]}]
    )

    assert mapped[0]["mode"] == "train"
    assert mapped[0]["cost"] == "€40"
    assert hotels[0]["name"] == "Eco Stay"
    assert "solar" in hotels[0]["amenities"]


def test_resolve_destination_prefers_slot_then_text():
    tracker = DummyTracker(slots={"destination": "Lisbon"}, text="hotels in Rome")

    assert resolve_destination(tracker, "hotels in Rome", parser.extract_destination) == "Lisbon"
    assert resolve_destination(DummyTracker(), "hotels in Rome", parser.extract_destination) == "Rome"


def test_transport_builder_returns_expected_modes():
    options = build_transport_options("Berlin", "Amsterdam", 600)

    assert {option["mode"] for option in options} >= {"flight", "train", "bus", "car"}
    assert all("eco_score" in option for option in options)
