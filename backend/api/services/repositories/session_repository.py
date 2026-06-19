import uuid
from typing import Any

from db.novaplan import get_pool


class SessionRepository:
    def find_by_id(self, ses_id: str) -> dict[str, Any] | None:
        with get_pool().connection() as conn:
            return conn.execute(
                """
                SELECT
                    s.*,
                    u.name AS user_name,
                    latest.text AS last_message
                FROM sessions s
                LEFT JOIN users u ON u.user_id = s.user_id
                LEFT JOIN LATERAL (
                    SELECT text
                    FROM conversations c
                    WHERE c.ses_id = s.ses_id
                    ORDER BY c.timestamp DESC
                    LIMIT 1
                ) latest ON TRUE
                WHERE s.ses_id = %s
                """,
                (ses_id,),
            ).fetchone()

    def find_active_for_user(self, user_id: str) -> dict[str, Any] | None:
        with get_pool().connection() as conn:
            return conn.execute(
                """
                SELECT
                    s.*,
                    u.name AS user_name,
                    latest.text AS last_message
                FROM sessions s
                LEFT JOIN users u ON u.user_id = s.user_id
                LEFT JOIN LATERAL (
                    SELECT text
                    FROM conversations c
                    WHERE c.ses_id = s.ses_id
                    ORDER BY c.timestamp DESC
                    LIMIT 1
                ) latest ON TRUE
                WHERE s.user_id = %s AND s.status = 'active'
                ORDER BY s.updated_at DESC LIMIT 1
                """,
                (user_id,),
            ).fetchone()

    def create(self, ses_id: str, user_id: str) -> dict[str, Any]:
        with get_pool().connection() as conn:
            row = conn.execute(
                """
                INSERT INTO sessions (ses_id, user_id)
                VALUES (%s, %s)
                RETURNING *
                """,
                (ses_id, user_id),
            ).fetchone()
            conn.commit()
        return row

    def list_all(self) -> list[dict[str, Any]]:
        with get_pool().connection() as conn:
            return conn.execute(
                """
                SELECT
                    s.*,
                    u.name AS user_name,
                    latest.text AS last_message
                FROM sessions s
                LEFT JOIN users u ON u.user_id = s.user_id
                LEFT JOIN LATERAL (
                    SELECT text
                    FROM conversations c
                    WHERE c.ses_id = s.ses_id
                    ORDER BY c.timestamp DESC
                    LIMIT 1
                ) latest ON TRUE
                ORDER BY s.updated_at DESC
                """
            ).fetchall()

    def mark_needs_human(self, ses_id: str) -> None:
        with get_pool().connection() as conn:
            conn.execute(
                "UPDATE sessions SET needs_human = TRUE, updated_at = NOW() WHERE ses_id = %s",
                (ses_id,),
            )
            conn.commit()

    def upsert_handoff(self, ses_id: str) -> None:
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
            conn.commit()

    def touch(self, ses_id: str) -> None:
        with get_pool().connection() as conn:
            conn.execute(
                "UPDATE sessions SET updated_at = NOW() WHERE ses_id = %s",
                (ses_id,),
            )
            conn.commit()

    @staticmethod
    def new_session_id() -> str:
        return f"ses_{uuid.uuid4().hex[:9]}"
