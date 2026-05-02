from dataclasses import dataclass

import psycopg

from platform_api.config import Settings


@dataclass(frozen=True)
class DatabaseStatus:
    ok: bool
    detail: str


def check_database(settings: Settings) -> DatabaseStatus:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("select 1")
                cur.fetchone()
    except Exception as exc:  # pragma: no cover - driver details vary by environment
        return DatabaseStatus(ok=False, detail=str(exc))

    return DatabaseStatus(ok=True, detail="ok")
