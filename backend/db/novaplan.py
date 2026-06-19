from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from config.settings import (
    DATABASE_URL,
    DB_POOL_MAX_IDLE,
    DB_POOL_MAX_LIFETIME,
    DB_POOL_MAX_SIZE,
    DB_POOL_MIN_SIZE,
    DB_POOL_TIMEOUT,
)

load_dotenv()

pool: ConnectionPool | None = None


def get_database_url() -> str:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    return DATABASE_URL


def get_pool() -> ConnectionPool:
    global pool
    if pool is None:
        pool = ConnectionPool(
            conninfo=get_database_url(),
            min_size=DB_POOL_MIN_SIZE,
            max_size=DB_POOL_MAX_SIZE,
            timeout=DB_POOL_TIMEOUT,
            max_idle=DB_POOL_MAX_IDLE,
            max_lifetime=DB_POOL_MAX_LIFETIME,
            check=ConnectionPool.check_connection,
            kwargs={"row_factory": dict_row},
        )
    return pool
