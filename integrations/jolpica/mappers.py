from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from integrations.jolpica.errors import JolpicaInvalidPayload
from integrations.jolpica.schemas import (
    ConstructorStandingPayload,
    DriverStandingPayload,
    EventPayload,
    ResultPayload,
    SessionPayload,
)


SESSION_KEYS = (
    ("FirstPractice", "practice_1"),
    ("SecondPractice", "practice_2"),
    ("ThirdPractice", "practice_3"),
    ("SprintQualifying", "sprint_qualifying"),
    ("SprintShootout", "sprint_qualifying"),
    ("Sprint", "sprint"),
    ("Qualifying", "qualifying"),
)


def _mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise JolpicaInvalidPayload(f"{context}: ожидался объект.")
    return value


def _list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise JolpicaInvalidPayload(f"{context}: ожидался список.")
    return value


def _required(data: Mapping[str, Any], key: str, context: str) -> Any:
    value = data.get(key)
    if value in (None, ""):
        raise JolpicaInvalidPayload(f"{context}: отсутствует {key}.")
    return value


def _int(value: Any, context: str, *, optional: bool = False) -> int | None:
    if optional and value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise JolpicaInvalidPayload(f"{context}: ожидалось целое число.") from error


def _decimal(value: Any, context: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise JolpicaInvalidPayload(f"{context}: ожидалось число.") from error


def _optional_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    return _decimal(value, "координата")


def _datetime(data: Mapping[str, Any], context: str) -> datetime | None:
    date = data.get("date")
    time = data.get("time")
    if not date or not time:
        return None
    try:
        parsed = datetime.fromisoformat(f"{date}T{str(time).replace('Z', '+00:00')}")
    except ValueError as error:
        raise JolpicaInvalidPayload(f"{context}: неверная дата или время.") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _races(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mr_data = _mapping(payload.get("MRData"), "MRData")
    race_table = _mapping(mr_data.get("RaceTable"), "RaceTable")
    return [
        _mapping(item, "RaceTable.Races[]")
        for item in _list(race_table.get("Races"), "RaceTable.Races")
    ]


def map_schedule(payload: Mapping[str, Any]) -> tuple[EventPayload, ...]:
    events: list[EventPayload] = []
    for race in _races(payload):
        season = _int(_required(race, "season", "race"), "race.season")
        round_number = _int(_required(race, "round", "race"), "race.round")
        circuit = _mapping(_required(race, "Circuit", "race"), "race.Circuit")
        location = _mapping(
            _required(circuit, "Location", "race.Circuit"),
            "race.Circuit.Location",
        )
        circuit_id = str(_required(circuit, "circuitId", "race.Circuit"))

        sessions: list[SessionPayload] = []
        for api_key, session_type in SESSION_KEYS:
            if api_key not in race:
                continue
            session_data = _mapping(race[api_key], f"race.{api_key}")
            starts_at = _datetime(session_data, f"race.{api_key}")
            if starts_at is not None:
                sessions.append(SessionPayload(session_type, starts_at))
        race_start = _datetime(race, "race")
        if race_start is not None:
            sessions.append(SessionPayload("race", race_start))
        sessions.sort(key=lambda item: item.starts_at)

        events.append(
            EventPayload(
                season=season,
                round_number=round_number,
                external_id=f"{season}-{round_number}",
                name=str(_required(race, "raceName", "race")),
                circuit_external_id=circuit_id,
                circuit_name=str(_required(circuit, "circuitName", "race.Circuit")),
                locality=str(_required(location, "locality", "race.Circuit.Location")),
                country=str(_required(location, "country", "race.Circuit.Location")),
                latitude=_optional_decimal(location.get("lat")),
                longitude=_optional_decimal(location.get("long")),
                is_sprint="Sprint" in race,
                sessions=tuple(sessions),
            )
        )
    return tuple(events)


def map_results(payload: Mapping[str, Any]) -> tuple[ResultPayload, ...]:
    mapped: list[ResultPayload] = []
    for race in _races(payload):
        season = _int(_required(race, "season", "race"), "race.season")
        round_number = _int(_required(race, "round", "race"), "race.round")
        for raw in _list(race.get("Results", []), "race.Results"):
            result = _mapping(raw, "race.Results[]")
            driver = _mapping(_required(result, "Driver", "result"), "result.Driver")
            constructor = _mapping(
                _required(result, "Constructor", "result"),
                "result.Constructor",
            )
            fastest = _mapping(result.get("FastestLap", {}), "result.FastestLap")
            fastest_time = _mapping(fastest.get("Time", {}), "result.FastestLap.Time")
            timing = _mapping(result.get("Time", {}), "result.Time")
            timing_text = timing.get("time")
            is_gap = isinstance(timing_text, str) and timing_text.startswith("+")
            mapped.append(
                ResultPayload(
                    season=season,
                    round_number=round_number,
                    driver_external_id=str(_required(driver, "driverId", "result.Driver")),
                    given_name=str(_required(driver, "givenName", "result.Driver")),
                    family_name=str(_required(driver, "familyName", "result.Driver")),
                    code=str(driver.get("code", "")),
                    permanent_number=_int(
                        driver.get("permanentNumber"),
                        "result.Driver.permanentNumber",
                        optional=True,
                    ),
                    driver_nationality=str(driver.get("nationality", "")),
                    constructor_external_id=str(
                        _required(constructor, "constructorId", "result.Constructor")
                    ),
                    constructor_name=str(
                        _required(constructor, "name", "result.Constructor")
                    ),
                    constructor_nationality=str(constructor.get("nationality", "")),
                    position=_int(result.get("position"), "result.position", optional=True),
                    grid_position=_int(result.get("grid", 0), "result.grid"),
                    points=_decimal(result.get("points", 0), "result.points"),
                    status=str(result.get("status", "")),
                    time_text=None if is_gap or timing_text is None else str(timing_text),
                    gap=str(timing_text) if is_gap else None,
                    fastest_lap_time=(
                        str(fastest_time["time"]) if fastest_time.get("time") else None
                    ),
                    fastest_lap_rank=_int(
                        fastest.get("rank"),
                        "result.FastestLap.rank",
                        optional=True,
                    ),
                )
            )
    return tuple(mapped)


def _standings_list(payload: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
    mr_data = _mapping(payload.get("MRData"), "MRData")
    table = _mapping(mr_data.get("StandingsTable"), "StandingsTable")
    season = _int(_required(table, "season", "StandingsTable"), "StandingsTable.season")
    lists = _list(table.get("StandingsLists", []), "StandingsTable.StandingsLists")
    if not lists:
        return season, {}
    return season, _mapping(lists[0], "StandingsTable.StandingsLists[0]")


def map_driver_standings(
    payload: Mapping[str, Any],
) -> tuple[DriverStandingPayload, ...]:
    season, standings_list = _standings_list(payload)
    mapped: list[DriverStandingPayload] = []
    for raw in _list(standings_list.get("DriverStandings", []), "DriverStandings"):
        standing = _mapping(raw, "DriverStandings[]")
        driver = _mapping(_required(standing, "Driver", "standing"), "standing.Driver")
        constructors = _list(standing.get("Constructors", []), "standing.Constructors")
        constructor = _mapping(constructors[0], "standing.Constructors[0]") if constructors else {}
        mapped.append(
            DriverStandingPayload(
                season=season,
                position=_int(_required(standing, "position", "standing"), "standing.position"),
                points=_decimal(standing.get("points", 0), "standing.points"),
                wins=_int(standing.get("wins", 0), "standing.wins"),
                driver_external_id=str(_required(driver, "driverId", "standing.Driver")),
                given_name=str(_required(driver, "givenName", "standing.Driver")),
                family_name=str(_required(driver, "familyName", "standing.Driver")),
                code=str(driver.get("code", "")),
                permanent_number=_int(
                    driver.get("permanentNumber"),
                    "standing.Driver.permanentNumber",
                    optional=True,
                ),
                nationality=str(driver.get("nationality", "")),
                constructor_external_id=(
                    str(constructor["constructorId"])
                    if constructor.get("constructorId")
                    else None
                ),
                constructor_name=str(constructor["name"]) if constructor.get("name") else None,
                constructor_nationality=(
                    str(constructor.get("nationality", "")) if constructor else None
                ),
            )
        )
    return tuple(mapped)


def map_constructor_standings(
    payload: Mapping[str, Any],
) -> tuple[ConstructorStandingPayload, ...]:
    season, standings_list = _standings_list(payload)
    mapped: list[ConstructorStandingPayload] = []
    for raw in _list(
        standings_list.get("ConstructorStandings", []),
        "ConstructorStandings",
    ):
        standing = _mapping(raw, "ConstructorStandings[]")
        constructor = _mapping(
            _required(standing, "Constructor", "standing"),
            "standing.Constructor",
        )
        mapped.append(
            ConstructorStandingPayload(
                season=season,
                position=_int(_required(standing, "position", "standing"), "standing.position"),
                points=_decimal(standing.get("points", 0), "standing.points"),
                wins=_int(standing.get("wins", 0), "standing.wins"),
                constructor_external_id=str(
                    _required(constructor, "constructorId", "standing.Constructor")
                ),
                constructor_name=str(_required(constructor, "name", "standing.Constructor")),
                constructor_nationality=str(constructor.get("nationality", "")),
            )
        )
    return tuple(mapped)
