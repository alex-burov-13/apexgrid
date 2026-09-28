from django.core.management import call_command
from django.core.management.base import BaseCommand

from racing.models import Season


class Command(BaseCommand):
    help = "Загрузить демонстрационный offline-snapshot сезона 2026"

    def handle(self, *args, **options):
        if Season.objects.exists():
            self.stdout.write("skipped: в базе уже есть сезон")
            return

        call_command("loaddata", "apexgrid_2026", verbosity=0)
        self.stdout.write(self.style.SUCCESS("loaded: offline-snapshot 2026"))
