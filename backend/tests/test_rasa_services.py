import pytest

from services import carbon_service, cultural_service, hotel_service, itinerary_service, travel_service


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.mark.asyncio
async def test_calculate_carbon_uses_zero_carbon_shortcut():
    result = await carbon_service.calculate_carbon("Berlin", "Paris", "walking", 10)

    assert result["kg_co2e"] == 0
    assert result["source"] == "zero_carbon_mode"


@pytest.mark.asyncio
async def test_calculate_carbon_falls_back_without_api_key(monkeypatch):
    monkeypatch.setattr(carbon_service, "CLIMATIQ_API_KEY", "")

    result = await carbon_service.calculate_carbon("Berlin", "Paris", "flight", 100)

    assert result["source"] == "fallback_estimate"
    assert result["kg_co2e"] > 0


def test_build_climatiq_payload_requires_activity_id(monkeypatch):
    monkeypatch.setattr(carbon_service, "CLIMATIQ_ACTIVITY_CONFIG", {"transport_modes": {}})

    with pytest.raises(carbon_service.ClimatiqConfigurationError):
        carbon_service.build_climatiq_payload("flight", 100)


@pytest.mark.asyncio
async def test_fetch_transport_options_uses_mock_when_token_missing(monkeypatch):
    monkeypatch.setattr(travel_service, "TRAVELPAYOUTS_API_TOKEN", "")
    monkeypatch.setattr(travel_service, "estimate_distance_km", lambda *_: 500)

    result = await travel_service.fetch_transport_options("Berlin", "Amsterdam", "2026-08-01", selected_mode="train")

    assert result["source"] == "mock"
    assert result["options"]
    assert {option["mode"] for option in result["options"]} == {"train"}


@pytest.mark.asyncio
async def test_fetch_transport_options_handles_travelpayouts_failure(monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("api down")

    monkeypatch.setattr(travel_service, "TRAVELPAYOUTS_API_TOKEN", "token")
    monkeypatch.setattr(travel_service, "_fetch_travelpayouts_flights", boom)
    monkeypatch.setattr(travel_service, "estimate_distance_km", lambda *_: 500)

    result = await travel_service.fetch_transport_options("Berlin", "Amsterdam", "2026-08-01", selected_mode="flight")

    assert result["source"] == "mock"
    assert result["options"]


@pytest.mark.asyncio
async def test_fetch_eco_hotels_uses_curated_fallback(monkeypatch):
    monkeypatch.setattr(hotel_service, "GEOAPIFY_API_KEY", "")
    monkeypatch.setattr(hotel_service, "OSM_HOTEL_LOOKUP_ENABLED", False)

    result = await hotel_service.fetch_eco_hotels("Amsterdam", "2026-08-01", "2026-08-03", 200)

    assert result["source"] == "curated_eco_hotels"
    assert result["hotels"]


@pytest.mark.asyncio
async def test_fetch_eco_hotels_falls_back_after_geoapify_error(monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("geoapify down")

    monkeypatch.setattr(hotel_service, "GEOAPIFY_API_KEY", "key")
    monkeypatch.setattr(hotel_service, "OSM_HOTEL_LOOKUP_ENABLED", False)
    monkeypatch.setattr(hotel_service, "_fetch_geoapify_hotels", boom)

    result = await hotel_service.fetch_eco_hotels("Lisbon", "2026-08-01", "2026-08-03", 200)

    assert result["source"] == "curated_eco_hotels"
    assert result["hotels"][0]["name"]


@pytest.mark.asyncio
async def test_fetch_cultural_profile_uses_wikipedia_and_restcountries(monkeypatch):
    async def fake_get(url, **kwargs):
        if "wikipedia" in url:
            return FakeResponse(
                {
                    "title": "Amsterdam",
                    "description": "Capital city",
                    "extract": "Amsterdam is known for canals.",
                    "content_urls": {"desktop": {"page": "https://example.test/wiki"}},
                }
            )
        return FakeResponse(
            [
                {
                    "name": {"common": "Netherlands"},
                    "capital": ["Amsterdam"],
                    "region": "Europe",
                    "languages": {"nld": "Dutch"},
                    "currencies": {"EUR": {}},
                    "timezones": ["UTC+01:00"],
                }
            ]
        )

    monkeypatch.setattr(cultural_service, "get", fake_get)

    result = await cultural_service.fetch_cultural_profile("Amsterdam")

    assert "wikipedia" in result["source"]
    assert "restcountries" in result["source"]
    assert result["tips"]["wiki"]["title"] == "Amsterdam"


@pytest.mark.asyncio
async def test_fetch_cultural_profile_handles_restcountries_redirect_payload(monkeypatch):
    async def fake_get(url, **kwargs):
        if "wikipedia" in url:
            return FakeResponse({"title": "London", "description": "Capital city", "extract": "London overview."})
        return FakeResponse(
            {
                "GBR": {
                    "name": {"common": "United Kingdom"},
                    "capital": ["London"],
                    "region": "Europe",
                    "languages": {"eng": "English"},
                    "currencies": {"GBP": {}},
                    "timezones": ["UTC+00:00"],
                }
            }
        )

    monkeypatch.setattr(cultural_service, "get", fake_get)

    result = await cultural_service.fetch_cultural_profile("London")

    assert "restcountries" in result["source"]
    assert "Country: United Kingdom" in result["tips"]["country_overview"]


@pytest.mark.asyncio
async def test_fetch_cultural_profile_returns_default_for_missing_destination():
    result = await cultural_service.fetch_cultural_profile("")

    assert result["source"] == "none"
    assert result["tips"]


def test_map_offset_programs_converts_kg_to_tonnes():
    programs, tonnes = itinerary_service.map_offset_programs(250)

    assert tonnes == 0.25
    assert programs
    assert {"name", "description", "cost_per_tonne", "impact"} <= set(programs[0])
