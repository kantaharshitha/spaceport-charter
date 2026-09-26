from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from psycopg import errors as pg_errors
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import get_db
from .models import Booking, Ship
from .rules import (
    REFUEL_BUFFER,
    SLOT_LENGTH,
    BookingRuleError,
    central_midnight,
    day_slots,
    operating_window,
    validate_booking_times,
)
from .schemas import AvailabilityOut, BookingIn, BookingOut, ShipOut


app = FastAPI(title="Spaceport Charter System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Allow requests from the React app
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = Annotated[Session, Depends(get_db)]


def get_ship_or_404(db: Session, ship_id: int) -> Ship:
    ship = db.get(Ship, ship_id)

    if ship is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Ship {ship_id} not found.",
        )

    return ship


@app.get("/ships", response_model=list[ShipOut])
def list_ships(db: DB):
    return db.scalars(select(Ship).order_by(Ship.id)).all()


@app.get("/ships/{ship_id}/availability", response_model=AvailabilityOut)
def ship_availability(
    ship_id: int,
    day: Annotated[date, Query(alias="date")],
    db: DB,
):
    """Get the available and unavailable time slots for a ship."""

    get_ship_or_404(db, ship_id)
    opens, closes = operating_window(day)

    # Get bookings that could affect this day's availability
    rows = db.execute(
        select(Booking.start_time, Booking.end_time).where(
            Booking.ship_id == ship_id,
            Booking.start_time < closes + REFUEL_BUFFER,
            Booking.end_time > opens - REFUEL_BUFFER,
        )
    ).all()

    slots = day_slots(
        day,
        [(r.start_time, r.end_time) for r in rows],
        datetime.now(UTC),
    )

    return AvailabilityOut(
        ship_id=ship_id,
        date=day,
        slot_minutes=int(SLOT_LENGTH.total_seconds() // 60),
        slots=[asdict(s) for s in slots],
    )


@app.get("/bookings", response_model=list[BookingOut])
def list_bookings(
    db: DB,
    ship_id: Annotated[int | None, Query(alias="shipId")] = None,
    from_date: Annotated[
        date | None,
        Query(alias="fromDate", description="Central Time date, inclusive"),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(alias="toDate", description="Central Time date, inclusive"),
    ] = None,
):
    query = select(Booking).order_by(
        Booking.ship_id,
        Booking.start_time,
    )

    if ship_id is not None:
        query = query.where(Booking.ship_id == ship_id)

    # Filter bookings by their Central Time date
    if from_date is not None:
        query = query.where(
            Booking.start_time >= central_midnight(from_date)
        )

    if to_date is not None:
        query = query.where(
            Booking.start_time
            < central_midnight(to_date + timedelta(days=1))
        )

    return db.scalars(query).all()


@app.post(
    "/bookings",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
)
def create_booking(payload: BookingIn, db: DB):
    get_ship_or_404(db, payload.ship_id)

    try:
        validate_booking_times(
            payload.start_time,
            payload.end_time,
            datetime.now(UTC),
        )
    except BookingRuleError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            str(e),
        )

    booking = Booking(
        ship_id=payload.ship_id,
        pilot_name=payload.pilot_name,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )

    db.add(booking)

    try:
        db.commit()

    except IntegrityError as e:
        db.rollback()

        # Handle bookings that overlap or don't leave enough time for refueling
        if isinstance(e.orig, pg_errors.ExclusionViolation):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "That time conflicts with another booking or its 30-minute refueling window.",
            )

        raise

    db.refresh(booking)

    return booking