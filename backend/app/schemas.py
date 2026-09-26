"""Request/response shapes. JSON uses camelCase (shipId) to match the brief; Python uses snake_case."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class ShipOut(ApiModel):
    id: int
    name: str


class BookingIn(ApiModel):
    ship_id: int
    pilot_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    # AwareDatetime rejects times without a timezone offset: "10:00" alone is ambiguous.
    start_time: AwareDatetime
    end_time: AwareDatetime


class BookingOut(ApiModel):
    id: int
    ship_id: int
    pilot_name: str
    start_time: datetime
    end_time: datetime


class SlotOut(ApiModel):
    start: datetime
    end: datetime
    status: Literal["available", "booked", "refueling", "past"]


class AvailabilityOut(ApiModel):
    ship_id: int
    date: date
    slot_minutes: int
    slots: list[SlotOut]
