from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from racing.services.sync import SyncSeasonError, SyncSummary


class SyncCommandTests(SimpleTestCase):
    def test_season_option_is_required_and_validated(self):
        with self.assertRaises(CommandError):
            call_command("sync_f1", stdout=StringIO(), stderr=StringIO())
        with self.assertRaisesMessage(CommandError, "Сезон должен быть"):
            call_command("sync_f1", season=1949, stdout=StringIO())

    @patch("racing.management.commands.sync_f1.sync_season")
    def test_success_prints_readable_summary_and_uses_cli_initiator(self, sync_mock):
        sync_mock.return_value = SyncSummary(
            created=12,
            updated=5,
            results=20,
            standings=30,
        )
        output = StringIO()

        call_command("sync_f1", season=2026, stdout=output)

        self.assertIn("Сезон 2026 обновлён", output.getvalue())
        self.assertIn("создано: 12", output.getvalue())
        self.assertEqual(sync_mock.call_args.kwargs["initiated_by"], "cli")

    @patch("racing.management.commands.sync_f1.sync_season")
    def test_service_failure_becomes_command_error_without_traceback(self, sync_mock):
        sync_mock.side_effect = SyncSeasonError("Jolpica API недоступен.")

        with self.assertRaisesMessage(CommandError, "Jolpica API недоступен"):
            call_command("sync_f1", season=2026, stdout=StringIO())
