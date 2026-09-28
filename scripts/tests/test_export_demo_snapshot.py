import json
import tempfile
from pathlib import Path

from django.test import TestCase

from racing.models import Circuit, GrandPrix, RaceSession, Season
from scripts.export_demo_snapshot import (
    SnapshotExportError,
    enrich_season,
    export_snapshot,
)


PLACEHOLDER = {"viewBox": [0, 0, 10, 10], "path": "M0 0 L10 10"}


class SnapshotExporterTests(TestCase):
    def setUp(self):
        self.season = Season.objects.create(year=2026, is_current=True)
        self.circuit = Circuit.objects.create(
            external_id="albert_park",
            slug="albert-park",
            name="Albert Park Grand Prix Circuit",
            locality="Melbourne",
            country="Australia",
            geometry=PLACEHOLDER,
        )
        self.grand_prix = GrandPrix.objects.create(
            season=self.season,
            circuit=self.circuit,
            external_id="2026-1",
            round_number=1,
            name="Australian Grand Prix",
        )

    def test_enriches_circuit_and_exports_only_domain_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            geometry = {
                "slug": "albert_park",
                "viewBox": [0, 0, 500, 500],
                "path": "M10 10 L490 490",
                "source": "https://github.com/f1db/f1db",
                "license": "CC BY 4.0",
            }
            (root / "albert_park.json").write_text(json.dumps(geometry))
            (root / "metadata.json").write_text(
                json.dumps(
                    {
                        "albert_park": {
                            "timezone": "Australia/Melbourne",
                            "length_km": "5.278",
                            "turns": 14,
                            "direction": "clockwise",
                            "laps": 58,
                            "summary": "Albert Park",
                        }
                    }
                )
            )
            output = root / "snapshot.json"

            enriched = enrich_season(2026, root)
            export_snapshot(2026, output)

            self.assertEqual(enriched, 1)
            self.circuit.refresh_from_db()
            self.grand_prix.refresh_from_db()
            self.assertEqual(self.circuit.timezone, "Australia/Melbourne")
            self.assertEqual(self.circuit.geometry["path"], geometry["path"])
            self.assertEqual(self.grand_prix.laps, 58)
            models = {row["model"] for row in json.loads(output.read_text())}
            self.assertEqual(
                models,
                {"racing.season", "racing.circuit", "racing.grandprix"},
            )

    def test_rejects_season_without_geometry_for_every_circuit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "metadata.json").write_text(
                json.dumps({"albert_park": {"timezone": "Australia/Melbourne"}})
            )

            with self.assertRaisesRegex(SnapshotExportError, "albert_park"):
                enrich_season(2026, root)
