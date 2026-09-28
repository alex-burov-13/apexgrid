from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SessionPayload:
    session_type: str
    starts_at: datetime


@dataclass(frozen=True, slots=True)
class EventPayload:
    season: int
    round_number: int
    external_id: str
    name: str
    circuit_external_id: str
    circuit_name: str
    locality: str
    country: str
    latitude: Decimal | None
    longitude: Decimal | None
    is_sprint: bool
    sessions: tuple[SessionPayload, ...]


@dataclass(frozen=True, slots=True)
class ResultPayload:
    season: int
    round_number: int
    driver_external_id: str
    given_name: str
    family_name: str
    code: str
    permanent_number: int | None
    driver_nationality: str
    constructor_external_id: str
    constructor_name: str
    constructor_nationality: str
    position: int | None
    grid_position: int
    points: Decimal
    status: str
    time_text: str | None
    gap: str | None
    fastest_lap_time: str | None
    fastest_lap_rank: int | None


@dataclass(frozen=True, slots=True)
class DriverStandingPayload:
    season: int
    position: int
    points: Decimal
    wins: int
    driver_external_id: str
    given_name: str
    family_name: str
    code: str
    permanent_number: int | None
    nationality: str
    constructor_external_id: str | None
    constructor_name: str | None
    constructor_nationality: str | None


@dataclass(frozen=True, slots=True)
class ConstructorStandingPayload:
    season: int
    position: int
    points: Decimal
    wins: int
    constructor_external_id: str
    constructor_name: str
    constructor_nationality: str
