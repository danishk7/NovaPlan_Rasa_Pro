import pytest

from conftest import DummyTracker, event_value
import actions


@pytest.mark.asyncio
async def test_session_start_sets_metadata_slots(dispatcher, domain):
    tracker = DummyTracker(slots={"user_id": "user-1", "conversation_id": "ses_123"}, text="", sender_id="ses_123")

    events = await actions.ActionSessionStart().run(dispatcher, tracker, domain)

    assert event_value(events, "user_id") == "user-1"
    assert event_value(events, "conversation_id") == "ses_123"


@pytest.mark.asyncio
async def test_validate_travel_date_rejects_same_day_or_past(dispatcher, domain):
    tracker = DummyTracker(slots={"travel_dates": "2024-01-01"}, text="travel yesterday")

    events = await actions.ActionValidateTravelDate().run(dispatcher, tracker, domain)

    assert event_value(events, "travel_dates") is None
    assert dispatcher.texts


@pytest.mark.asyncio
async def test_fetch_travel_options_requires_route(dispatcher, domain):
    tracker = DummyTracker(slots={"origin": "Berlin"}, text="")

    events = await actions.ActionFetchTravelOptions().run(dispatcher, tracker, domain)

    assert "both cities" in dispatcher.texts[0]
    assert events == []


@pytest.mark.asyncio
async def test_fetch_travel_options_sets_best_option(monkeypatch, dispatcher, domain):
    async def fake_fetch(*args, **kwargs):
        return {
            "source": "mock",
            "options": [{"mode": "train", "price_eur": 55, "eco_score": 0.9, "carbon_kg": 12}],
        }

    monkeypatch.setattr(actions, "fetch_transport_options", fake_fetch)
    tracker = DummyTracker(
        slots={"origin": "Berlin", "destination": "Amsterdam", "transport_mode": "train", "travel_dates": "2026-08-01"}
    )

    events = await actions.ActionFetchTravelOptions().run(dispatcher, tracker, domain)

    assert event_value(events, "transport_mode") == "train"
    assert event_value(events, "price_total") == 55
    assert event_value(events, "transport_options")[0]["mode"] == "train"


@pytest.mark.asyncio
async def test_fetch_travel_options_handles_service_exception(monkeypatch, dispatcher, domain):
    async def boom(*args, **kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr(actions, "fetch_transport_options", boom)
    tracker = DummyTracker(slots={"origin": "Berlin", "destination": "Amsterdam", "transport_mode": "train"})

    events = await actions.ActionFetchTravelOptions().run(dispatcher, tracker, domain)

    assert "Could not fetch" in dispatcher.texts[-1]
    assert events == []


@pytest.mark.asyncio
async def test_calculate_carbon_dispatches_card(monkeypatch, dispatcher, domain):
    monkeypatch.setattr(actions, "estimate_distance_km", lambda *_: 100)

    async def fake_calculate(*args, **kwargs):
        return {"kg_co2e": 120, "colour": "amber", "api_source": "test", "disclaimer": "estimate"}

    monkeypatch.setattr(actions, "calculate_carbon", fake_calculate)
    tracker = DummyTracker(
        slots={"origin": "Berlin", "destination": "Paris", "transport_mode": "flight", "num_travellers": 2}
    )

    events = await actions.ActionCalculateCarbon().run(dispatcher, tracker, domain)

    assert event_value(events, "carbon_score") == 120
    assert dispatcher.json_messages[0]["type"] == "carbon_card"
    assert dispatcher.json_messages[0]["data"]["per_person"] == 60


@pytest.mark.asyncio
async def test_calculate_carbon_missing_route(dispatcher, domain):
    events = await actions.ActionCalculateCarbon().run(dispatcher, DummyTracker(slots={}), domain)

    assert "both cities" in dispatcher.texts[0]
    assert events == []


@pytest.mark.asyncio
async def test_fetch_eco_hotels_sets_best_hotel(monkeypatch, dispatcher, domain):
    async def fake_hotels(*args, **kwargs):
        return {"source": "test", "hotels": [{"name": "Eco Stay", "price_eur": 100}]}

    monkeypatch.setattr(actions, "fetch_eco_hotels", fake_hotels)
    tracker = DummyTracker(slots={"destination": "Lisbon", "budget_amount": 500})

    events = await actions.ActionFetchEcoHotels().run(dispatcher, tracker, domain)

    assert event_value(events, "destination") == "Lisbon"
    assert event_value(events, "hotel_options")[0]["name"] == "Eco Stay"


@pytest.mark.asyncio
async def test_fetch_eco_hotels_asks_for_destination(dispatcher, domain):
    events = await actions.ActionFetchEcoHotels().run(dispatcher, DummyTracker(slots={}), domain)

    assert events == []
    assert "city" in dispatcher.texts[0]


@pytest.mark.asyncio
async def test_information_actions_dispatch_payloads(monkeypatch, dispatcher, domain):
    async def fake_profile(destination):
        return {
            "source": "mock_data",
            "tips": {
                "country_overview": ["Overview"],
                "eco_activities": ["Walk"],
                "responsible_tips": ["Respect locals"],
                "sustainability_rating": "Good",
            },
        }

    monkeypatch.setattr(actions, "fetch_cultural_profile", fake_profile)
    tracker = DummyTracker(slots={"destination": "Rome"}, text="activities in Rome")

    await actions.ActionGetEcoTips().run(dispatcher, tracker, domain)
    await actions.ActionGetActivities().run(dispatcher, tracker, domain)
    await actions.ActionGetCulturalInfo().run(dispatcher, tracker, domain)

    assert any("Eco travel tips" in text for text in dispatcher.texts)
    assert [msg["type"] for msg in dispatcher.json_messages].count("cultural_tips") == 2


@pytest.mark.asyncio
async def test_offset_programs_estimates_when_carbon_missing(monkeypatch, dispatcher, domain):
    monkeypatch.setattr(actions, "estimate_distance_km", lambda *_: 100)

    async def fake_carbon(*args, **kwargs):
        return {"kg_co2e": 80}

    monkeypatch.setattr(actions, "calculate_carbon", fake_carbon)
    tracker = DummyTracker(slots={"origin": "Berlin", "destination": "Paris", "transport_mode": "train"})

    events = await actions.ActionGetOffsetPrograms().run(dispatcher, tracker, domain)

    assert event_value(events, "carbon_score") == 80
    assert dispatcher.json_messages[0]["type"] == "offset_programs"


@pytest.mark.asyncio
async def test_review_trip_details_resets_review_slots(dispatcher, domain):
    tracker = DummyTracker(
        slots={
            "origin": "Berlin",
            "destination": "Paris",
            "travel_dates": "2026-08-01",
            "budget_amount": 700,
            "num_travellers": 2,
            "eco_level": "high",
            "transport_mode": "train",
        }
    )

    events = await actions.ActionReviewTripDetails().run(dispatcher, tracker, domain)

    assert event_value(events, "awaiting_review") is None
    assert event_value(events, "itinerary_draft") is True


@pytest.mark.asyncio
async def test_destination_info_handles_service_exception(monkeypatch, dispatcher, domain):
    async def boom(*args, **kwargs):
        raise RuntimeError("wiki down")

    monkeypatch.setattr(actions, "fetch_cultural_profile", boom)
    tracker = DummyTracker(slots={"destination": "Paris"})

    events = await actions.ActionFetchDestinationInfo().run(dispatcher, tracker, domain)

    assert event_value(events, "destination_info")


@pytest.mark.asyncio
async def test_build_itinerary_package_validates_route(dispatcher, domain):
    same_city_events = await actions.ActionBuildItineraryPackage().run(
        dispatcher,
        DummyTracker(slots={"origin": "Paris", "destination": "Paris"}),
        domain,
    )
    valid_events = await actions.ActionBuildItineraryPackage().run(
        dispatcher,
        DummyTracker(slots={"origin": "Paris", "destination": "Rome"}),
        domain,
    )

    assert same_city_events == []
    assert valid_events[0]["name"] == "action_display_itinerary_summary"


@pytest.mark.asyncio
async def test_complete_itinerary_persists_and_returns_reference(monkeypatch, dispatcher, domain):
    created = {}

    class FakeRepo:
        @staticmethod
        def new_itinerary_id():
            return "3108FE77"

    class FakeService:
        def create(self, payload):
            created["payload"] = payload
            return {"success": True, "itnId": payload.itnId}

    monkeypatch.setattr(actions, "ItineraryRepository", FakeRepo)
    monkeypatch.setattr(actions, "ItineraryService", FakeService)
    tracker = DummyTracker(
        slots={
            "user_id": "user-1",
            "origin": "Berlin",
            "destination": "Paris",
            "travel_dates": "2026-08-01",
            "budget_amount": 500,
            "num_travellers": 1,
            "eco_level": "moderate",
            "transport_mode": "train",
            "carbon_score": 40,
        }
    )

    events = await actions.ActionCompleteItinerary().run(dispatcher, tracker, domain)

    assert created["payload"].itnId == "3108FE77"
    assert event_value(events, "booking_reference") == "3108FE77"
    assert event_value(events, "itinerary_confirmed") is True


@pytest.mark.asyncio
async def test_complete_itinerary_handles_db_error(monkeypatch, dispatcher, domain):
    class FakeRepo:
        @staticmethod
        def new_itinerary_id():
            return "3108FE77"

    class FailingService:
        def create(self, payload):
            raise RuntimeError("db down")

    monkeypatch.setattr(actions, "ItineraryRepository", FakeRepo)
    monkeypatch.setattr(actions, "ItineraryService", FailingService)
    tracker = DummyTracker(slots={"user_id": "user-1", "origin": "Berlin", "destination": "Paris"})

    events = await actions.ActionCompleteItinerary().run(dispatcher, tracker, domain)

    assert any("could not save" in text for text in dispatcher.texts)
    assert event_value(events, "booking_reference") == "3108FE77"


@pytest.mark.asyncio
async def test_cancel_and_restart_actions(dispatcher, domain):
    cancel_events = await actions.ActionCancelBooking().run(dispatcher, DummyTracker(), domain)
    restart_events = await actions.ActionRestart().run(dispatcher, DummyTracker(), domain)

    assert event_value(cancel_events, "origin") is None
    assert any(event.get("event") == "reset_slots" for event in restart_events)


@pytest.mark.asyncio
async def test_human_handover_dispatches_banner_and_escalates(monkeypatch, dispatcher, domain):
    calls = []
    monkeypatch.setattr(actions, "_persist_human_handoff", lambda *args: calls.append(args))
    tracker = DummyTracker(slots={"carbon_score": 250, "origin": "Berlin"}, sender_id="ses_1")

    events = await actions.ActionHumanHandover().run(dispatcher, tracker, domain)

    assert calls
    assert dispatcher.json_messages[0]["type"] == "escalation_banner"
    assert dispatcher.json_messages[0]["data"]["severity"] == "High"
    assert event_value(events, "escalated") is True


@pytest.mark.asyncio
async def test_fallback_first_miss_shows_quick_replies(dispatcher, domain):
    tracker = DummyTracker(slots={"fallback_count": 0}, text="@@@")

    events = await actions.ActionHandleFallback().run(dispatcher, tracker, domain)

    assert event_value(events, "fallback_count") == 1
    assert dispatcher.json_messages[0]["type"] == "quick_reply"


@pytest.mark.asyncio
async def test_fallback_second_miss_escalates(dispatcher, domain):
    tracker = DummyTracker(slots={"fallback_count": 1}, text="@@@")

    events = await actions.ActionDefaultFallback().run(dispatcher, tracker, domain)

    assert dispatcher.responses == ["utter_default_fallback"]
    assert any(event.get("name") == "action_human_handover" for event in events)
