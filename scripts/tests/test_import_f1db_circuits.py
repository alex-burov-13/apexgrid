import json
import tempfile
from pathlib import Path
from unittest import TestCase

from scripts.import_f1db_circuits import CircuitImportError, import_circuits


FIXTURES = Path(__file__).parent / "fixtures"


class CircuitImporterTests(TestCase):
    def test_importer_extracts_and_normalizes_viewbox_and_primary_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            (source / "albert-park.svg").write_text(
                (FIXTURES / "sample-circuit.svg").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            mapping = root / "mapping.json"
            mapping.write_text(
                json.dumps({"albert_park": "albert-park.svg"}),
                encoding="utf-8",
            )

            created = import_circuits(source, mapping, output)
            payload = json.loads(created[0].read_text(encoding="utf-8"))

            self.assertEqual(payload["slug"], "albert_park")
            self.assertEqual(payload["viewBox"], [0, 0, 800, 520])
            self.assertEqual(
                payload["path"],
                "M 80 270 C 130 70 370 40 520 120 C 720 230 650 450 420 430 C 210 410 30 360 80 270 Z",
            )

    def test_importer_rejects_svg_without_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "empty.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" />',
                encoding="utf-8",
            )
            mapping = root / "mapping.json"
            mapping.write_text(json.dumps({"empty": "empty.svg"}), encoding="utf-8")

            with self.assertRaisesRegex(CircuitImportError, "не содержит path"):
                import_circuits(source, mapping, root / "output")

    def test_importer_records_source_and_cc_by_license(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            (source / "test.svg").write_text(
                (FIXTURES / "sample-circuit.svg").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            mapping = root / "mapping.json"
            mapping.write_text(json.dumps({"test": "test.svg"}), encoding="utf-8")

            created = import_circuits(source, mapping, output)
            payload = json.loads(created[0].read_text(encoding="utf-8"))

            self.assertEqual(payload["source"], "https://github.com/f1db/f1db")
            self.assertEqual(payload["license"], "CC BY 4.0")

    def test_importer_uses_svg_dimensions_when_viewbox_is_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "production.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="500" height="300">'
                '<path d="M10 10 L490 290" /></svg>',
                encoding="utf-8",
            )
            mapping = root / "mapping.json"
            mapping.write_text(
                json.dumps({"production": "production.svg"}),
                encoding="utf-8",
            )

            created = import_circuits(source, mapping, root / "output")
            payload = json.loads(created[0].read_text(encoding="utf-8"))

            self.assertEqual(payload["viewBox"], [0, 0, 500, 300])
