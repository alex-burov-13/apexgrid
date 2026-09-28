#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class SnapshotExportError(ValueError):
    pass


def _read_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SnapshotExportError(f"Не удалось прочитать {path}") from error
    if not isinstance(value, dict):
        raise SnapshotExportError(f"Ожидался JSON-объект: {path}")
    return value


def enrich_season(season_year: int, data_dir: Path) -> int:
    from django.db import transaction

    from racing.models import GrandPrix

    metadata = _read_object(data_dir / "metadata.json")
    grand_prix = list(
        GrandPrix.objects.filter(season__year=season_year)
        .select_related("circuit")
        .order_by("round_number")
    )
    if not grand_prix:
        raise SnapshotExportError(f"Сезон {season_year} не найден или пуст.")

    with transaction.atomic():
        for event in grand_prix:
            external_id = event.circuit.external_id
            geometry_path = data_dir / f"{external_id}.json"
            if not geometry_path.is_file():
                raise SnapshotExportError(f"Нет геометрии для трассы {external_id}.")
            circuit_metadata = metadata.get(external_id)
            if not isinstance(circuit_metadata, dict):
                raise SnapshotExportError(f"Нет метаданных для трассы {external_id}.")

            circuit = event.circuit
            circuit.geometry = _read_object(geometry_path)
            for field in (
                "timezone",
                "length_km",
                "turns",
                "direction",
                "lap_record",
                "lap_record_driver",
                "summary",
            ):
                if field in circuit_metadata:
                    setattr(circuit, field, circuit_metadata[field])
            circuit.full_clean()
            circuit.save()

            event.laps = circuit_metadata.get("laps")
            event.save(update_fields=["laps"])
    return len(grand_prix)


def _domain_objects(season_year: int) -> list[object]:
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
    )

    season = Season.objects.get(year=season_year)
    events = GrandPrix.objects.filter(season=season).order_by("round_number")
    circuit_ids = events.values_list("circuit_id", flat=True)
    event_ids = events.values_list("id", flat=True)
    results = RaceResult.objects.filter(grand_prix_id__in=event_ids).order_by(
        "grand_prix__round_number", "position", "id"
    )
    driver_standings = DriverStanding.objects.filter(season=season).order_by(
        "position", "id"
    )
    constructor_standings = ConstructorStanding.objects.filter(season=season).order_by(
        "position", "id"
    )
    driver_ids = set(results.values_list("driver_id", flat=True)) | set(
        driver_standings.values_list("driver_id", flat=True)
    )
    constructor_ids = set(results.values_list("constructor_id", flat=True)) | set(
        driver_standings.exclude(constructor_id=None).values_list(
            "constructor_id", flat=True
        )
    ) | set(constructor_standings.values_list("constructor_id", flat=True))

    objects: list[object] = [season]
    objects.extend(Circuit.objects.filter(id__in=circuit_ids).order_by("external_id"))
    objects.extend(events)
    objects.extend(
        RaceSession.objects.filter(grand_prix_id__in=event_ids).order_by(
            "grand_prix__round_number", "starts_at"
        )
    )
    objects.extend(Driver.objects.filter(id__in=driver_ids).order_by("external_id"))
    objects.extend(
        Constructor.objects.filter(id__in=constructor_ids).order_by("external_id")
    )
    objects.extend(results)
    objects.extend(driver_standings)
    objects.extend(constructor_standings)
    return objects


def export_snapshot(season_year: int, output_path: Path) -> int:
    from django.core import serializers

    objects = _domain_objects(season_year)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serializers.serialize("json", objects, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(objects)


def main() -> None:
    parser = argparse.ArgumentParser(description="Собрать offline-snapshot ApexGrid")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument(
        "--data-dir", type=Path, default=Path("racing/data/circuits")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("racing/fixtures/apexgrid_2026.json")
    )
    arguments = parser.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    enriched = enrich_season(arguments.season, arguments.data_dir)
    exported = export_snapshot(arguments.season, arguments.output)
    print(f"Обогащено этапов: {enriched}; экспортировано объектов: {exported}")


if __name__ == "__main__":
    main()
