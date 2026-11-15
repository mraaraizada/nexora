from __future__ import annotations

from datetime import date, datetime, time, timezone

UTC = timezone.utc


def now_utc() -> datetime:
    return datetime.now(UTC)


def split_date_time(dt: datetime) -> tuple[date, time]:
    """Splits a datetime into (date, time) for the response schema's separate fields."""
    return dt.date(), dt.time().replace(microsecond=0)
