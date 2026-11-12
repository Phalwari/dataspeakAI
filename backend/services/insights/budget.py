"""Small helpers for enforcing planner deadlines where a driver supports cancellation."""

from __future__ import annotations

from contextlib import contextmanager
import time
from typing import Callable, Iterator

from sqlalchemy.engine import Connection


@contextmanager
def sqlite_deadline(connection: Connection, deadline: float | None) -> Iterator[Callable[[], bool]]:
    """Install SQLite's progress handler for one operation and always remove it."""
    timed_out = {"value": False}
    raw = None
    if deadline is not None and connection.dialect.name == "sqlite":
        try:
            raw = connection.connection.driver_connection
            def progress_handler() -> int:
                expired = time.monotonic() >= deadline
                timed_out["value"] = timed_out["value"] or expired
                return 1 if expired else 0
            raw.set_progress_handler(progress_handler, 1_000)
        except (AttributeError, TypeError):
            raw = None
    try:
        yield lambda: timed_out["value"] or (deadline is not None and time.monotonic() >= deadline)
    finally:
        if raw is not None:
            try:
                raw.set_progress_handler(None, 0)
            except (AttributeError, TypeError):
                pass
