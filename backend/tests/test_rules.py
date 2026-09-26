from datetime import UTC, date, datetime

import pytest

from app.rules import (
    CENTRAL,
    BookingRuleError,
    day_slots,
    operating_window,
    validate_booking_times,
    within_refuel_buffer,
)

# A fixed "now" well before the test dates, so tests don't depend on today's date.
NOW = datetime(2026, 1, 1, tzinfo=UTC)
DAY = date(2026, 9, 28)


def ct(hour, minute=0, day=DAY):
    """A Central Time instant on the test day."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=CENTRAL)


# --- Operating window and daylight saving time ---

def test_operating_window_in_summer_is_utc_minus_5():
    opens, closes = operating_window(DAY)
    assert opens == datetime(2026, 9, 28, 11, 0, tzinfo=UTC)
    assert closes == datetime(2026, 9, 29, 3, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "day, opens_utc_hour",
    [
        (date(2026, 3, 7), 12),   # last day of CST (UTC-6)
        (date(2026, 3, 8), 11),   # DST starts: CDT (UTC-5)
        (date(2026, 10, 31), 11), # last day of CDT
        (date(2026, 11, 1), 12),  # DST ends: back to CST
    ],
)
def test_operating_window_follows_dst(day, opens_utc_hour):
    opens, closes = operating_window(day)
    assert opens.hour == opens_utc_hour
    assert closes - opens == (ct(22, day=day) - ct(6, day=day))


# --- validate_booking_times ---

def test_booking_inside_hours_is_valid():
    validate_booking_times(ct(9), ct(11), NOW)


def test_booking_exactly_filling_the_day_is_valid():
    validate_booking_times(ct(6), ct(22), NOW)


def test_times_given_in_utc_are_judged_in_central():
    # 03:00 UTC on the 29th is 10:00 PM Central on the 28th: exactly closing time.
    validate_booking_times(ct(20), datetime(2026, 9, 29, 3, 0, tzinfo=UTC), NOW)


@pytest.mark.parametrize(
    "start, end",
    [
        (ct(5, 59), ct(7)),    # starts before opening
        (ct(21), ct(22, 1)),   # ends after closing
        (ct(21), ct(23)),      # runs well past closing
        (ct(21), ct(7, day=date(2026, 9, 29))),  # crosses midnight
    ],
)
def test_booking_outside_hours_is_rejected(start, end):
    with pytest.raises(BookingRuleError, match="operating hours"):
        validate_booking_times(start, end, NOW)


def test_end_before_start_is_rejected():
    with pytest.raises(BookingRuleError, match="after start"):
        validate_booking_times(ct(11), ct(9), NOW)


def test_zero_length_booking_is_rejected():
    with pytest.raises(BookingRuleError, match="after start"):
        validate_booking_times(ct(9), ct(9), NOW)


def test_naive_datetimes_are_rejected():
    with pytest.raises(BookingRuleError, match="timezone"):
        validate_booking_times(datetime(2026, 9, 28, 9), datetime(2026, 9, 28, 11), NOW)


def test_booking_in_the_past_is_rejected():
    with pytest.raises(BookingRuleError, match="past"):
        validate_booking_times(ct(9), ct(11), now=ct(10))


# --- Refuel buffer ---

@pytest.mark.parametrize(
    "start, end, expected",
    [
        (ct(11), ct(13), True),         # overlaps existing 10-12
        (ct(12, 29), ct(14), True),     # 29 min after it ends
        (ct(12, 30), ct(14), False),    # exactly 30 min after
        (ct(8), ct(9, 31), True),       # ends 29 min before it starts
        (ct(8), ct(9, 30), False),      # ends exactly 30 min before
    ],
)
def test_refuel_buffer(start, end, expected):
    assert within_refuel_buffer(start, end, ct(10), ct(12)) is expected


# --- Slots for the booking screen ---

def test_empty_day_has_32_available_half_hour_slots():
    slots = day_slots(DAY, [], NOW)
    assert len(slots) == 32
    assert slots[0].start == ct(6)
    assert slots[-1].end == ct(22)
    assert all(s.status == "available" for s in slots)


@pytest.mark.parametrize("day", [date(2026, 3, 8), date(2026, 11, 1)])
def test_dst_days_still_have_32_slots(day):
    assert len(day_slots(day, [], NOW)) == 32


def test_slots_around_a_booking():
    slots = {s.start: s.status for s in day_slots(DAY, [(ct(10), ct(12))], NOW)}
    assert slots[ct(9)] == "available"
    assert slots[ct(9, 30)] == "refueling"
    assert slots[ct(10)] == "booked"
    assert slots[ct(11, 30)] == "booked"
    assert slots[ct(12)] == "refueling"
    assert slots[ct(12, 30)] == "available"


def test_slots_before_now_are_past():
    slots = {s.start: s.status for s in day_slots(DAY, [], now=ct(9))}
    assert slots[ct(8, 30)] == "past"
    assert slots[ct(9)] == "available"
