from datetime import date, datetime, time, timedelta, timezone, tzinfo

# India Standard Time: the zone of the first city, Hyderabad. A date without a
# time of day is a whole day in its city's zone (packages/cities).
IST = timezone(timedelta(hours=5, minutes=30))


def utc_now() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """Return `value` as timezone-aware UTC; naive values are taken to be UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def start_of_day(day: date, zone: tzinfo = IST) -> datetime:
    return datetime.combine(day, time.min, tzinfo=zone)


def end_of_day(day: date, zone: tzinfo = IST) -> datetime:
    return datetime.combine(day, time(23, 59, 59), tzinfo=zone)


def start_of_day_ist(day: date) -> datetime:
    return start_of_day(day, IST)


def end_of_day_ist(day: date) -> datetime:
    return end_of_day(day, IST)
