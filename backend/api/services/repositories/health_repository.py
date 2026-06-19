from db.novaplan import get_pool


class HealthRepository:
    def ping(self) -> dict:
        with get_pool().connection() as conn:
            row = conn.execute("SELECT NOW() AS now").fetchone()
        return {"database": "postgres", "now": row["now"]}
