from datetime import datetime

from sqlalchemy import DDL, CheckConstraint, DateTime, ForeignKey, String, event, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Ship(Base):
    __tablename__ = "ships"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="ship")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    ship_id: Mapped[int] = mapped_column(ForeignKey("ships.id"))
    pilot_name: Mapped[str] = mapped_column(String(100))

    # Keep booking times timezone-aware
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    ship: Mapped[Ship] = relationship(back_populates="bookings")

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="end_after_start"),

        # Prevent the same ship from being booked twice,
        # including the 30-minute refueling time after each booking
        ExcludeConstraint(
            ("ship_id", "="),
            (text("booking_block(start_time, end_time)"), "&&"),
            name="no_overlap_with_refuel_buffer",
            using="gist",
        ),
    )


# Needed for the GiST constraint to compare ship IDs
event.listen(
    Base.metadata,
    "before_create",
    DDL("CREATE EXTENSION IF NOT EXISTS btree_gist"),
)


# Build the booking range with the 30-minute refueling buffer included
event.listen(
    Base.metadata,
    "before_create",
    DDL("""
        CREATE OR REPLACE FUNCTION booking_block(start_time timestamptz, end_time timestamptz)
        RETURNS tstzrange
        LANGUAGE sql IMMUTABLE
        AS $$ SELECT tstzrange(start_time, end_time + interval '30 minutes') $$
    """),
)