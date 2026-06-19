import logging
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mock_data import CULTURAL_TIPS
from action_config import NOVAPLAN_USER_AGENT, RESTCOUNTRIES_NAME_URL, WIKIPEDIA_SUMMARY_URL
from metadata import CITY_COUNTRY, IATA_TO_CITY
from utils.http_client import get

logger = logging.getLogger("nova.actions.cultural")

def _normalise_destination(destination: str | None) -> str:
    value = (destination or "").strip()
    if not value:
        return ""
    return IATA_TO_CITY.get(value.upper(), value.title())


async def fetch_cultural_profile(destination: str) -> dict:
    city = _normalise_destination(destination)
    if not city or city.lower() in {"unknown", "your destination"}:
        return {"source": "none", "destination": destination, "tips": CULTURAL_TIPS["default"]}

    mock_tips = CULTURAL_TIPS.get(city.lower(), CULTURAL_TIPS["default"])
    tips = dict(mock_tips)
    sources = []

    try:
        resp = await get(
            f"{WIKIPEDIA_SUMMARY_URL}/{city.replace(' ', '%20')}",
            timeout=8.0,
            headers={"User-Agent": NOVAPLAN_USER_AGENT},
        )
        if resp.status_code == 200:
            wiki = resp.json()
            country_facts = []
            if wiki.get("description"):
                country_facts.append(wiki["description"])
            extract = (wiki.get("extract") or "")[:480]
            if extract:
                country_facts.append(extract)

            tips["wiki"] = {
                "title": wiki.get("title") or city,
                "description": wiki.get("description") or "",
                "extract": wiki.get("extract") or "",
                "extract_html": wiki.get("extract_html") or wiki.get("extract") or "",
                "thumbnail": (wiki.get("thumbnail") or {}).get("source"),
                "url": (wiki.get("content_urls") or {}).get("desktop", {}).get("page"),
            }

            if country_facts:
                tips["country_overview"] = country_facts
                sources.append("wikipedia")
            tips["sustainability_rating"] = (
                tips.get("sustainability_rating")
                or f"Live overview from Wikipedia for {city}"
            )
    except Exception as exc:
        logger.warning("Wikipedia cultural fetch failed for %s: %s", city, exc)

    country = CITY_COUNTRY.get(city.lower())
    if country:
        try:
            resp = await get(
                f"{RESTCOUNTRIES_NAME_URL}/{country.replace(' ', '%20')}",
                timeout=8.0,
                params={
                    "fields": "name,capital,region,subregion,languages,currencies,timezones"
                },
            )
            if resp.status_code == 200:
                country_data = _first_country(resp.json())
                if country_data:
                    facts = _country_facts(country_data, country)
                    tips["country_overview"] = facts + tips.get("country_overview", [])
                    sources.append("restcountries")
        except Exception as exc:
            logger.warning("Rest Countries fetch failed for %s: %s", country, exc)

    if sources:
        return {
            "source": "+".join(sources),
            "destination": city,
            "tips": tips,
        }

    return {
        "source": "mock_data",
        "destination": city,
        "tips": mock_tips,
    }


def _first_country(payload) -> dict | None:
    if isinstance(payload, list):
        return payload[0] if payload and isinstance(payload[0], dict) else None
    if isinstance(payload, dict):
        if "name" in payload:
            return payload
        for value in payload.values():
            if isinstance(value, dict) and "name" in value:
                return value
    return None


def _country_facts(data: dict, fallback_name: str) -> list[str]:
    name = data.get("name", {}).get("common", fallback_name)
    capital = ", ".join(data.get("capital", []) or ["N/A"])
    languages = ", ".join((data.get("languages") or {}).values()) or "N/A"
    currencies = ", ".join((data.get("currencies") or {}).keys()) or "N/A"
    timezone = ", ".join(data.get("timezones", [])[:2]) or "N/A"
    region = data.get("region", "N/A")
    return [
        f"Country: {name}",
        f"Capital: {capital}",
        f"Region: {region}",
        f"Languages: {languages}",
        f"Currencies: {currencies}",
        f"Time zones: {timezone}",
    ]
