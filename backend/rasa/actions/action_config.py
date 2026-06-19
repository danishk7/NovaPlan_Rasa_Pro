import os


NOVAPLAN_USER_AGENT = "NovaPlan.ai/1.0 (sustainable travel assistant; contact: support@novaplan.ai)"
TRAVELPAYOUTS_API_TOKEN = os.getenv("TRAVELPAYOUTS_API_TOKEN", "")
CLIMATIQ_API_KEY = os.getenv("CLIMATIQ_API_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY", "").strip()
ENABLE_GUEST_ITINERARY_PERSISTENCE = os.getenv("ENABLE_GUEST_ITINERARY_PERSISTENCE", "false").strip().lower() == "true"
OSM_HOTEL_LOOKUP_ENABLED = True
CLIMATIQ_DATA_VERSION = "34"

TRAVELPAYOUTS_FLIGHT_URL = "https://api.travelpayouts.com/v1/prices/cheap"
CLIMATIQ_ESTIMATE_URL = "https://api.climatiq.io/data/v1/estimate"
GEOAPIFY_GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
GEOAPIFY_PLACES_URL = "https://api.geoapify.com/v2/places"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_INTERPRETER_URL = "https://overpass-api.de/api/interpreter"
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary"
RESTCOUNTRIES_NAME_URL = "https://restcountries.com/v3.1/name"
