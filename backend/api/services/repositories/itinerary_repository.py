from typing import Any
import secrets

from psycopg.types.json import Jsonb

from db.novaplan import get_pool


class ItineraryRepository:
    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with get_pool().connection() as conn:
            return conn.execute(
                "SELECT * FROM itineraries WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()

    def create(
        self,
        user_id: str,
        time: str | None,
        title: str,
        summary: dict[str, Any],
        status: str,
        itn_id: str | None = None,
    ) -> str:
        with get_pool().connection() as conn:
            itn_id = itn_id or self.new_itinerary_id()
            conn.execute(
                """
                INSERT INTO itineraries (itn_id, user_id, time, title, summary, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (itn_id, user_id, time, title, Jsonb(summary), status),
            )
            conn.commit()
        return itn_id

    @staticmethod
    def new_itinerary_id() -> str:
        return secrets.token_hex(4).upper()
