from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import PlainSerializer

BAHRAIN = ZoneInfo("Asia/Bahrain")
BAHRAIN_UTC_OFFSET_HOURS = 3  # Asia/Bahrain has no DST


def now_bahrain() -> datetime:
    return datetime.now(BAHRAIN)


def to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def bahrain_day_start_utc(d: date) -> datetime:
    start = datetime(d.year, d.month, d.day, tzinfo=BAHRAIN)
    return to_naive_utc(start)


def bahrain_range_utc(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    """Inclusive calendar dates in Asia/Bahrain → naive UTC half-open [start, end)."""
    if date_to < date_from:
        date_from, date_to = date_to, date_from
    start = bahrain_day_start_utc(date_from)
    end = bahrain_day_start_utc(date_to + timedelta(days=1))
    return start, end


def as_bahrain(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BAHRAIN)


def iso_utc(dt: datetime) -> str:
    """Serialize as ISO 8601 with an explicit ``Z``.

    Timestamps are stored naive-UTC. Without the marker, ``new Date(iso)`` in a
    browser follows the ECMAScript rule for date-times lacking an offset and
    reads the value as *local* time, so every UTC timestamp renders three hours
    early in Bahrain. The ``Z`` is what makes the instant unambiguous.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UtcDateTime = Annotated[
    datetime,
    PlainSerializer(iso_utc, return_type=str, when_used="json"),
]
"""A stored-UTC datetime that goes over JSON with an explicit ``Z`` marker."""


def period_bounds_utc(period: str) -> tuple[datetime, datetime]:
    now_bh = now_bahrain()
    end = to_naive_utc(now_bh)
    if period == "today":
        start = bahrain_day_start_utc(now_bh.date())
    elif period == "week":
        start = to_naive_utc(now_bh - timedelta(days=7))
    else:
        start = bahrain_day_start_utc(date(now_bh.year, now_bh.month, 1))
    return start, end


def period_chart_dates(period: str) -> tuple[date, date]:
    """Bahrain calendar dates (inclusive) for the dashboard sales chart."""
    now_bh = now_bahrain()
    today = now_bh.date()
    if period == "today":
        return today, today
    if period == "week":
        return (now_bh - timedelta(days=6)).date(), today
    return date(now_bh.year, now_bh.month, 1), today
