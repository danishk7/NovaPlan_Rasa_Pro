import logging
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mock_data import CULTURAL_TIPS
from utils.http_client import get

logger = logging.getLogger("nova.actions.cultural")

CITY_COUNTRY = {
    "amsterdam": "Netherlands",
    "lisbon": "Portugal",
    "barcelona": "Spain",
    "paris": "France",
    "rome": "Italy",
    "berlin": "Germany",
    "london": "United Kingdom",
    "vienna": "Austria",
    "madrid": "Spain",
    "copenhagen": "Denmark",
    "stockholm": "Sweden",
    "prague": "Czech Republic",
    "budapest": "Hungary",
    "munich": "Germany",
    "brussels": "Belgium",
    "new york": "United States",
    "tokyo": "Japan",
    "dubai": "United Arab Emirates",
    "edinburgh": "United Kingdom",
    "dublin": "Ireland",
    "warsaw": "Poland",
}


async def fetch_cultural_profile(destination: str) -> dict:
    city = (destination or "").strip().title()
    if not city or city.lower() in {"unknown", "your destination"}:
        return {"source": "none", "destination": destination, "tips": CULTURAL_TIPS["default"]}

    mock_tips = CULTURAL_TIPS.get(city.lower(), CULTURAL_TIPS["default"])
    tips = dict(mock_tips)
    sources = []

    try:
        resp = await get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{city.replace(' ', '%20')}",
            timeout=8.0,
        )
        if resp.status_code == 200:
            wiki = resp.json()
            country_facts = []
            if wiki.get("description"):
                country_facts.append(wiki["description"])
            extract = (wiki.get("extract") or "")[:480]
            if extract:
                country_facts.append(extract)

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
                f"https://restcountries.com/v3.1/name/{country.replace(' ', '%20')}",
                timeout=8.0,
                params={
                    "fields": "name,capital,region,subregion,languages,currencies,timezones"
                },
            )
            if resp.status_code == 200:
                facts = _country_facts(resp.json()[0], country)
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
