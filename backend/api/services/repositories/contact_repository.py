from typing import Any

from db.novaplan import get_pool


class ContactRepository:
    def create(self, name: str | None, email: str | None, topic: str | None, message: str | None) -> None:
        with get_pool().connection() as conn:
            conn.execute(
                "INSERT INTO contacts (name, email, topic, message) VALUES (%s, %s, %s, %s)",
                (name, email, topic, message),
            )
            conn.commit()

    def list_all(self) -> list[dict[str, Any]]:
        with get_pool().connection() as conn:
            return conn.execute("SELECT * FROM contacts ORDER BY created_at DESC").fetchall()
