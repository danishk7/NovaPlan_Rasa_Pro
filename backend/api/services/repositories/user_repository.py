import uuid
from typing import Any

from db.novaplan import get_pool


class UserRepository:
    def find_by_email(self, email: str) -> dict[str, Any] | None:
        with get_pool().connection() as conn:
            return conn.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()

    def find_by_login(self, identifier: str) -> dict[str, Any] | None:
        with get_pool().connection() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE email = %s OR name = %s OR user_id = %s",
                (identifier, identifier, identifier),
            ).fetchone()

    def find_by_id(self, user_id: str) -> dict[str, Any] | None:
        with get_pool().connection() as conn:
            return conn.execute("SELECT * FROM users WHERE user_id = %s", (user_id,)).fetchone()

    def create(
        self,
        user_id: str,
        name: str,
        email: str,
        password_hash: str,
        *,
        role: str = "user",
        auth_provider: str = "local",
    ) -> dict[str, Any]:
        with get_pool().connection() as conn:
            row = conn.execute(
                """
                INSERT INTO users (user_id, name, email, password_hash, role, auth_provider)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, name, email, password_hash, role, auth_provider),
            ).fetchone()
            conn.commit()
        return row

    def list_public(self) -> list[dict[str, Any]]:
        with get_pool().connection() as conn:
            return conn.execute(
                "SELECT user_id, name, email, role FROM users ORDER BY created_at DESC"
            ).fetchall()

    def update_role(self, user_id: str, role: str) -> dict[str, Any] | None:
        with get_pool().connection() as conn:
            row = conn.execute(
                "UPDATE users SET role = %s, updated_at = NOW() WHERE user_id = %s "
                "RETURNING user_id, name, email, role",
                (role, user_id),
            ).fetchone()
            conn.commit()
        return row

    def delete(self, user_id: str) -> dict[str, Any] | None:
        with get_pool().connection() as conn:
            row = conn.execute(
                "DELETE FROM users WHERE user_id = %s RETURNING user_id", (user_id,)
            ).fetchone()
            conn.commit()
        return row

    def update_profile(self, user_id: str, fields: list[tuple[str, Any]]) -> None:
        assignments = ", ".join(f"{column} = %s" for _, column, _ in fields)
        values = [value for _, _, value in fields]
        values.append(user_id)
        with get_pool().connection() as conn:
            conn.execute(
                f"UPDATE users SET {assignments}, updated_at = NOW() WHERE user_id = %s",
                values,
            )
            conn.commit()

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex
