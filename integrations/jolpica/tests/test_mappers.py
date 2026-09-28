import json
from datetime import datetime, timezone
from pathlib import Path

from django.test import SimpleTestCase

from integrations.jolpica.errors import JolpicaInvalidPayload
from integrations.jolpica.mappers import (
    map_constructor_standings,
    map_driver_standings,
    map_results,
    map_schedule,
)


FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class JolpicaMapperTests(SimpleTestCase):
    def test_schedule_mapper_normalizes_sessions_to_aware_utc(self):
        events = map_schedule(fixture("schedule.json"))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].season, 2026)
        self.assertEqual(events[0].round_number, 1)
        self.assertEqual(events[0].circuit_external_id, "albert_park")
        self.assertEqual(
            [(session.session_type, session.starts_at) for session in events[0].sessions],
            [
                ("practice_1", datetime(2026, 3, 6, 1, 30, tzinfo=timezone.utc)),
                ("qualifying", datetime(2026, 3, 7, 5, 0, tzinfo=timezone.utc)),
                ("race", datetime(2026, 3, 8, 4, 0, tzinfo=timezone.utc)),
            ],
        )

    def test_result_mapper_accepts_missing_fastest_lap(self):
        results = map_results(fixture("results.json"))

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.driver_external_id, "norris")
        self.assertEqual(result.constructor_external_id, "mclaren")
        self.assertEqual(result.position, 1)
        self.assertIsNone(result.fastest_lap_time)
        self.assertIsNone(result.fastest_lap_rank)

    def test_standings_mappers_preserve_original_names(self):
        drivers = map_driver_standings(fixture("driver_standings.json"))
        constructors = map_constructor_standings(fixture("constructor_standings.json"))

        self.assertEqual(drivers[0].given_name, "Lando")
        self.assertEqual(drivers[0].family_name, "Norris")
        self.assertEqual(drivers[0].constructor_name, "McLaren")
        self.assertEqual(constructors[0].constructor_name, "McLaren")

    def test_mapper_rejects_payload_without_external_ids(self):
        payload = fixture("schedule.json")
        del payload["MRData"]["RaceTable"]["Races"][0]["Circuit"]["circuitId"]

        with self.assertRaises(JolpicaInvalidPayload):
            map_schedule(payload)
