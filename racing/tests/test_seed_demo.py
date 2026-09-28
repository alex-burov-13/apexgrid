from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from racing.models import Circuit, GrandPrix, Season


class SeedDemoCommandTests(TestCase):
    def test_empty_database_loads_snapshot(self):
        output = StringIO()

        call_command("seed_demo", stdout=output)

        self.assertIn("loaded", output.getvalue())
        self.assertTrue(Season.objects.filter(year=2026).exists())
        self.assertEqual(GrandPrix.objects.filter(season__year=2026).count(), 23)
        self.assertEqual(
            Circuit.objects.filter(grand_prix__season__year=2026)
            .exclude(geometry={})
            .distinct()
            .count(),
            23,
        )

    def test_existing_season_is_not_overwritten(self):
        Season.objects.create(year=2030, is_current=True)
        output = StringIO()

        call_command("seed_demo", stdout=output)

        self.assertIn("skipped", output.getvalue())
        self.assertEqual(list(Season.objects.values_list("year", flat=True)), [2030])
