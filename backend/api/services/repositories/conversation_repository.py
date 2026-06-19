from typing import Any

from db.novaplan import get_pool


class ConversationRepository:
    def list_for_session(self, ses_id: str) -> list[dict[str, Any]]:
        with get_pool().connection() as conn:
            return conn.execute(
                """
                SELECT c.*, u.name AS user_name, u.role AS user_role
                FROM conversations c
                LEFT JOIN users u ON u.user_id = c.user_id
                WHERE c.ses_id = %s
                ORDER BY c.timestamp ASC
                """,
                (ses_id,),
            ).fetchall()

    def create(
        self,
        ses_id: str,
        user_id: str | None,
        text: str,
    ) -> None:
        with get_pool().connection() as conn:
            conn.execute(
                """
                INSERT INTO conversations (ses_id, user_id, text)
                VALUES (%s, %s, %s)
                """,
                (ses_id, user_id, text),
            )
            conn.commit()
