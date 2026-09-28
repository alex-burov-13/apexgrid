from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from integrations.jolpica.client import JolpicaClient
from integrations.jolpica.errors import (
    JolpicaInvalidPayload,
    JolpicaRateLimited,
    JolpicaUnavailable,
)
from integrations.jolpica.schemas import (
    ConstructorStandingPayload,
    DriverStandingPayload,
    EventPayload,
    ResultPayload,
)
from racing.models import (
    Circuit,
    Constructor,
    ConstructorStanding,
    Driver,
    DriverStanding,
    GrandPrix,
    RaceResult,
    RaceSession,
    Season,
    SyncRun,
)


PLACEHOLDER_GEOMETRY = {
    "viewBox": [0, 0, 100, 60],
    "path": "M10 30 C25 8 75 8 90 30 C75 52 25 52 10 30 Z",
}


class SyncSeasonError(Exception):
    """A safe, user-facing synchronization failure."""


class SyncValidationError(Exception):
    """Fetched payloads do not form one consistent season snapshot."""


@dataclass(frozen=True, slots=True)
class SyncSummary:
    created: int
    updated: int
    results: int
    standings: int


@dataclass(slots=True)
class _Counters:
    created: int = 0
    updated: int = 0

    def record(self, was_created: bool) -> None:
        if was_created:
            self.created += 1
        else:
            self.updated += 1


def _safe_error(error: Exception) -> str:
    if isinstance(error, JolpicaRateLimited):
        return "Jolpica временно ограничил частоту запросов."
    if isinstance(error, JolpicaUnavailable):
        return "Jolpica API недоступен. Локальные данные сохранены."
    if isinstance(error, (JolpicaInvalidPayload, SyncValidationError)):
        return "Jolpica вернул неполные или некорректные данные."
    return "Не удалось обновить данные. Локальная версия сохранена."


def _validate_snapshot(
    season_year: int,
    events: tuple[EventPayload, ...],
    results: tuple[ResultPayload, ...],
    driver_standings: tuple[DriverStandingPayload, ...],
    constructor_standings: tuple[ConstructorStandingPayload, ...],
) -> None:
    if not events:
        raise SyncValidationError("Календарь сезона пуст.")
    if not results:
        raise SyncValidationError("Результаты сезона пусты.")
    if not driver_standings or not constructor_standings:
        raise SyncValidationError("Таблицы чемпионата пусты.")
    rounds = [event.round_number for event in events]
    if len(rounds) != len(set(rounds)):
        raise SyncValidationError("Календарь содержит повторяющиеся этапы.")
    if any(event.season != season_year for event in events):
        raise SyncValidationError("Календарь относится к другому сезону.")

    known_rounds = set(rounds)
    result_keys: set[tuple[int, str]] = set()
    for result in results:
        if result.season != season_year or result.round_number not in known_rounds:
            raise SyncValidationError("Результат ссылается на неизвестный этап.")
        key = (result.round_number, result.driver_external_id)
        if key in result_keys:
            raise SyncValidationError("Результат пилота продублирован.")
        result_keys.add(key)

    if any(item.season != season_year for item in driver_standings):
        raise SyncValidationError("Таблица пилотов относится к другому сезону.")
    if any(item.season != season_year for item in constructor_standings):
        raise SyncValidationError("Таблица команд относится к другому сезону.")


def _validate_against_existing(
    season_year: int,
    events: tuple[EventPayload, ...],
    results: tuple[ResultPayload, ...],
    driver_standings: tuple[DriverStandingPayload, ...],
    constructor_standings: tuple[ConstructorStandingPayload, ...],
) -> None:
    existing_rounds = set(
        GrandPrix.objects.filter(season__year=season_year).values_list(
            "round_number",
            flat=True,
        )
    )
    if not existing_rounds:
        return

    incoming_rounds = {event.round_number for event in events}
    missing_rounds = existing_rounds - incoming_rounds
    if len(missing_rounds) > 1:
        raise SyncValidationError("Новый календарь неожиданно потерял несколько этапов.")
    if missing_rounds and RaceResult.objects.filter(
        grand_prix__season__year=season_year,
        grand_prix__round_number__in=missing_rounds,
    ).exists():
        raise SyncValidationError("Новый календарь потерял этап с результатами.")

    existing_result_keys = set(
        RaceResult.objects.filter(grand_prix__season__year=season_year).values_list(
            "grand_prix__round_number",
            "driver__external_id",
        )
    )
    incoming_result_keys = {
        (result.round_number, result.driver_external_id) for result in results
    }
    if not existing_result_keys.issubset(incoming_result_keys):
        raise SyncValidationError("Новый набор результатов короче сохранённого.")

    existing_driver_ids = set(
        DriverStanding.objects.filter(season__year=season_year).values_list(
            "driver__external_id",
            flat=True,
        )
    )
    incoming_driver_ids = {item.driver_external_id for item in driver_standings}
    if not existing_driver_ids.issubset(incoming_driver_ids):
        raise SyncValidationError("Таблица пилотов короче сохранённой.")

    existing_constructor_ids = set(
        ConstructorStanding.objects.filter(season__year=season_year).values_list(
            "constructor__external_id",
            flat=True,
        )
    )
    incoming_constructor_ids = {
        item.constructor_external_id for item in constructor_standings
    }
    if not existing_constructor_ids.issubset(incoming_constructor_ids):
        raise SyncValidationError("Таблица команд короче сохранённой.")


def _update_fields(instance: Any, values: dict[str, Any]) -> bool:
    changed: list[str] = []
    for field, value in values.items():
        if getattr(instance, field) != value:
            setattr(instance, field, value)
            changed.append(field)
    if changed:
        instance.save(update_fields=changed)
    return bool(changed)


def _upsert_driver(payload: ResultPayload | DriverStandingPayload, counters: _Counters) -> Driver:
    nationality = (
        payload.driver_nationality
        if isinstance(payload, ResultPayload)
        else payload.nationality
    )
    driver, created = Driver.objects.get_or_create(
        external_id=payload.driver_external_id,
        defaults={
            "given_name": payload.given_name,
            "family_name": payload.family_name,
            "code": payload.code,
            "permanent_number": payload.permanent_number,
            "nationality": nationality,
        },
    )
    if created:
        counters.record(True)
    else:
        if _update_fields(
            driver,
            {
                "given_name": payload.given_name,
                "family_name": payload.family_name,
                "code": payload.code,
                "permanent_number": payload.permanent_number,
                "nationality": nationality,
            },
        ):
            counters.record(False)
    return driver


def _upsert_constructor(
    external_id: str,
    name: str,
    nationality: str,
    counters: _Counters,
) -> Constructor:
    constructor, created = Constructor.objects.get_or_create(
        external_id=external_id,
        defaults={"name": name, "nationality": nationality},
    )
    if created:
        counters.record(True)
    elif _update_fields(
        constructor,
        {"name": name, "nationality": nationality},
    ):
        counters.record(False)
    return constructor


def _apply_snapshot(
    season_year: int,
    events: tuple[EventPayload, ...],
    results: tuple[ResultPayload, ...],
    driver_standings: tuple[DriverStandingPayload, ...],
    constructor_standings: tuple[ConstructorStandingPayload, ...],
) -> SyncSummary:
    counters = _Counters()
    season, created = Season.objects.get_or_create(
        year=season_year,
        defaults={"is_current": True},
    )
    if created:
        counters.record(True)
    else:
        if _update_fields(season, {"is_current": True}):
            counters.record(False)
    Season.objects.exclude(pk=season.pk).filter(is_current=True).update(is_current=False)

    grand_prix_by_round: dict[int, GrandPrix] = {}
    session_times: list[datetime] = []
    for event in events:
        circuit, circuit_created = Circuit.objects.get_or_create(
            external_id=event.circuit_external_id,
            defaults={
                "slug": slugify(event.circuit_external_id),
                "name": event.circuit_name,
                "locality": event.locality,
                "country": event.country,
                "timezone": "UTC",
                "geometry": PLACEHOLDER_GEOMETRY,
            },
        )
        if circuit_created:
            counters.record(True)
        elif _update_fields(
            circuit,
            {
                "name": event.circuit_name,
                "locality": event.locality,
                "country": event.country,
            },
        ):
            counters.record(False)

        grand_prix, grand_prix_created = GrandPrix.objects.get_or_create(
            season=season,
            round_number=event.round_number,
            defaults={
                "circuit": circuit,
                "external_id": event.external_id,
                "name": event.name,
                "is_sprint": event.is_sprint,
            },
        )
        if grand_prix_created:
            counters.record(True)
        elif _update_fields(
            grand_prix,
            {
                "circuit": circuit,
                "external_id": event.external_id,
                "name": event.name,
                "is_sprint": event.is_sprint,
            },
        ):
            counters.record(False)
        grand_prix_by_round[event.round_number] = grand_prix

        session_types: list[str] = []
        for session_payload in event.sessions:
            race_session, session_created = RaceSession.objects.update_or_create(
                grand_prix=grand_prix,
                session_type=session_payload.session_type,
                defaults={"starts_at": session_payload.starts_at, "ends_at": None},
            )
            counters.record(session_created)
            session_types.append(race_session.session_type)
            session_times.append(race_session.starts_at)
        RaceSession.objects.filter(grand_prix=grand_prix).exclude(
            session_type__in=session_types
        ).delete()

    GrandPrix.objects.filter(season=season).exclude(
        round_number__in=grand_prix_by_round
    ).delete()

    if session_times:
        season.starts_on = min(session_times).date()
        season.ends_on = max(session_times).date()

    result_rows: list[RaceResult] = []
    RaceResult.objects.filter(grand_prix__season=season).delete()
    for payload in results:
        driver = _upsert_driver(payload, counters)
        constructor = _upsert_constructor(
            payload.constructor_external_id,
            payload.constructor_name,
            payload.constructor_nationality,
            counters,
        )
        result_rows.append(
            RaceResult(
                grand_prix=grand_prix_by_round[payload.round_number],
                driver=driver,
                constructor=constructor,
                position=payload.position,
                grid_position=payload.grid_position,
                points=payload.points,
                status=payload.status,
                time_text=payload.time_text or "",
                gap=payload.gap or "",
                fastest_lap_time=payload.fastest_lap_time or "",
                fastest_lap_rank=payload.fastest_lap_rank,
            )
        )
    RaceResult.objects.bulk_create(result_rows)

    ConstructorStanding.objects.filter(season=season).delete()
    constructor_rows: list[ConstructorStanding] = []
    for payload in constructor_standings:
        constructor = _upsert_constructor(
            payload.constructor_external_id,
            payload.constructor_name,
            payload.constructor_nationality,
            counters,
        )
        constructor_rows.append(
            ConstructorStanding(
                season=season,
                constructor=constructor,
                position=payload.position,
                points=payload.points,
                wins=payload.wins,
            )
        )
    ConstructorStanding.objects.bulk_create(constructor_rows)

    DriverStanding.objects.filter(season=season).delete()
    driver_rows: list[DriverStanding] = []
    for payload in driver_standings:
        driver = _upsert_driver(payload, counters)
        constructor = None
        if payload.constructor_external_id and payload.constructor_name:
            constructor = _upsert_constructor(
                payload.constructor_external_id,
                payload.constructor_name,
                payload.constructor_nationality or "",
                counters,
            )
        driver_rows.append(
            DriverStanding(
                season=season,
                driver=driver,
                constructor=constructor,
                position=payload.position,
                points=payload.points,
                wins=payload.wins,
            )
        )
    DriverStanding.objects.bulk_create(driver_rows)

    season.synced_at = timezone.now()
    season.save(update_fields=("starts_on", "ends_on", "synced_at"))
    return SyncSummary(
        created=counters.created,
        updated=counters.updated,
        results=len(result_rows),
        standings=len(constructor_rows) + len(driver_rows),
    )


def sync_season(
    season: int,
    *,
    client: JolpicaClient,
    initiated_by: str,
) -> SyncSummary:
    run = SyncRun.objects.create(
        season_year=season,
        initiated_by=initiated_by,
        status=SyncRun.Status.RUNNING,
    )
    try:
        events = tuple(client.get_schedule(season))
        results = tuple(client.get_results(season))
        driver_standings = tuple(client.get_driver_standings(season))
        constructor_standings = tuple(client.get_constructor_standings(season))
        _validate_snapshot(
            season,
            events,
            results,
            driver_standings,
            constructor_standings,
        )
        _validate_against_existing(
            season,
            events,
            results,
            driver_standings,
            constructor_standings,
        )
        with transaction.atomic():
            summary = _apply_snapshot(
                season,
                events,
                results,
                driver_standings,
                constructor_standings,
            )
    except Exception as error:
        safe_message = _safe_error(error)
        run.status = SyncRun.Status.FAILED
        run.error_message = safe_message
        run.finished_at = timezone.now()
        run.save(update_fields=("status", "error_message", "finished_at"))
        raise SyncSeasonError(safe_message) from error

    run.status = SyncRun.Status.SUCCESS
    run.finished_at = timezone.now()
    run.created_count = summary.created
    run.updated_count = summary.updated
    run.results_count = summary.results
    run.standings_count = summary.standings
    run.save(
        update_fields=(
            "status",
            "finished_at",
            "created_count",
            "updated_count",
            "results_count",
            "standings_count",
        )
    )
    return summary
