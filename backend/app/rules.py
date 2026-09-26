"""
Booking rules for the spaceport.

These rules are kept separate from FastAPI and the database so they're easier
to test. Booking times use UTC internally, but operating hours are based on
Central Time.

The database handles booking conflicts and the 30-minute refueling buffer.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


CENTRAL = ZoneInfo("America/Chicago")

# Spaceport operating hours
OPENING_TIME = time(6, 0)
CLOSING_TIME = time(22, 0)

# Time needed between bookings for refueling
REFUEL_BUFFER = timedelta(minutes=30)

# Booking screen is divided into 30-minute slots
SLOT_LENGTH = timedelta(minutes=30)


class BookingRuleError(ValueError):
    """Raised when a booking doesn't follow the booking rules."""


def operating_window(day: date) -> tuple[datetime, datetime]:
    """Return the opening and closing time for the day in UTC."""

    opens = datetime.combine(day, OPENING_TIME, tzinfo=CENTRAL)
    closes = datetime.combine(day, CLOSING_TIME, tzinfo=CENTRAL)

    return opens.astimezone(UTC), closes.astimezone(UTC)


def central_midnight(day: date) -> datetime:
    """Return midnight in Central Time for the given day."""

    return datetime.combine(day, time(0), tzinfo=CENTRAL)


def validate_booking_times(start: datetime, end: datetime, now: datetime) -> None:
    """Check that the requested booking times are valid."""

    if start.tzinfo is None or end.tzinfo is None:
        raise BookingRuleError("Times must include a timezone offset.")

    if end <= start:
        raise BookingRuleError("End time must be after start time.")

    if start < now:
        raise BookingRuleError("Cannot book a time in the past.")

    # Check the booking against the operating hours for that Central Time day
    opens, closes = operating_window(start.astimezone(CENTRAL).date())

    if start < opens or end > closes:
        raise BookingRuleError(
            "Bookings must fall within operating hours, 6:00 AM to 10:00 PM Central Time."
        )


def overlaps(
    start: datetime,
    end: datetime,
    other_start: datetime,
    other_end: datetime,
) -> bool:
    """Check whether two time ranges overlap."""

    return start < other_end and other_start < end


def within_refuel_buffer(
    start: datetime,
    end: datetime,
    other_start: datetime,
    other_end: datetime,
) -> bool:
    """Check whether two bookings overlap or are too close for refueling."""

    return overlaps(
        start,
        end + REFUEL_BUFFER,
        other_start,
        other_end + REFUEL_BUFFER,
    )


@dataclass
class Slot:
    start: datetime
    end: datetime
    status: str  # available, booked, refueling, or past


def day_slots(
    day: date,
    bookings: list[tuple[datetime, datetime]],
    now: datetime,
) -> list[Slot]:
    """Build the 30-minute booking slots for a day."""

    opens, closes = operating_window(day)
    slots = []

    # Work in UTC here so daylight-saving changes don't affect slot calculations
    cursor = opens

    while cursor < closes:
        slot_end = cursor + SLOT_LENGTH

        if any(overlaps(cursor, slot_end, s, e) for s, e in bookings):
            status = "booked"

        elif cursor < now:
            status = "past"

        elif any(
            within_refuel_buffer(cursor, slot_end, s, e)
            for s, e in bookings
        ):
            status = "refueling"

        else:
            status = "available"

        slots.append(Slot(cursor, slot_end, status))
        cursor = slot_end

    return slots