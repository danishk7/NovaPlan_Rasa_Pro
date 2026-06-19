import os
import sys
import types
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ACTIONS_ROOT = BACKEND_ROOT / "rasa" / "actions"

for path in (BACKEND_ROOT, ACTIONS_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

os.environ.setdefault("TRAVELPAYOUTS_API_TOKEN", "")
os.environ.setdefault("CLIMATIQ_API_KEY", "")
os.environ.setdefault("GEOAPIFY_API_KEY", "")
os.environ.setdefault("DATABASE_URL", "postgresql://unit-test/not-used")
os.environ.setdefault("RASA_LICENSE", "test-license")
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
os.environ.setdefault("LLM_MODEL_NAME", "openai/gpt-4o-mini")

try:
    import psycopg_pool  # noqa: F401
except ModuleNotFoundError:
    psycopg_pool_stub = types.ModuleType("psycopg_pool")

    class ConnectionPool:
        @staticmethod
        def check_connection(*args, **kwargs):
            return None

        def __init__(self, *args, **kwargs):
            raise RuntimeError("ConnectionPool is disabled in unit tests")

    psycopg_pool_stub.ConnectionPool = ConnectionPool
    sys.modules["psycopg_pool"] = psycopg_pool_stub


class DummyDispatcher:
    def __init__(self):
        self.messages = []

    def utter_message(self, *args, **kwargs):
        self.messages.append({"args": args, **kwargs})

    @property
    def texts(self):
        return [m.get("text") for m in self.messages if m.get("text")]

    @property
    def json_messages(self):
        return [m.get("json_message") for m in self.messages if m.get("json_message") is not None]

    @property
    def responses(self):
        return [m.get("response") for m in self.messages if m.get("response")]


class DummyTracker:
    def __init__(self, slots=None, text="", sender_id="test-sender"):
        self.slots = slots or {}
        self.sender_id = sender_id
        self.latest_message = {"text": text}

    def get_slot(self, key):
        return self.slots.get(key)


@pytest.fixture
def dispatcher():
    return DummyDispatcher()


@pytest.fixture
def domain():
    return {
        "slots": {
            "itinerary_draft": {},
            "itinerary_confirmed": {},
            "escalated": {},
        }
    }


def event_value(events, key):
    for event in events:
        if isinstance(event, dict):
            if event.get("name") == key or event.get("key") == key:
                return event.get("value")
            continue
        if getattr(event, "key", None) == key:
            return getattr(event, "value", None)
    raise AssertionError(f"SlotSet for {key!r} not found in {events!r}")
