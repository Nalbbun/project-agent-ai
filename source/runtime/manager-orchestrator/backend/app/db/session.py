from __future__ import annotations

import time
from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, create_engine

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def wait_for_db(max_attempts: int = 30, sleep_seconds: float = 2.0) -> None:
    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(sleep_seconds)
    raise RuntimeError(f"database is not ready: {last_error}")
