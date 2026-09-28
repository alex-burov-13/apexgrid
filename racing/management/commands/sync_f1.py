import os
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from integrations.jolpica.client import JolpicaClient
from racing.services.sync import SyncSeasonError, sync_season


class Command(BaseCommand):
    help = "Обновить календарь, результаты и standings из Jolpica F1 API."

    def add_arguments(self, parser):
        parser.add_argument("--season", type=int, required=True, help="Год сезона")

    def handle(self, *args, **options):
        season = options.get("season")
        if season is None or not 1950 <= season <= date.today().year + 1:
            raise CommandError(
                f"Сезон должен быть между 1950 и {date.today().year + 1}."
            )

        client = JolpicaClient(
            base_url=os.getenv(
                "JOLPICA_BASE_URL",
                "https://api.jolpi.ca/ergast/f1",
            ),
            user_agent=os.getenv("JOLPICA_USER_AGENT", "ApexGrid/1.0 Django/5.2"),
            timeout=(3.05, 10.0),
        )
        try:
            summary = sync_season(
                season,
                client=client,
                initiated_by="cli",
            )
        except SyncSeasonError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            self.style.SUCCESS(
                f"Сезон {season} обновлён — создано: {summary.created}, "
                f"обновлено: {summary.updated}, результаты: {summary.results}, "
                f"standings: {summary.standings}."
            )
        )
