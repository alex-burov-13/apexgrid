from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from racing.models import (
    Circuit,
    Constructor,
    ConstructorStanding,
    Driver,
    DriverStanding,
    GrandPrix,
    RaceSession,
    Season,
)


VALID_GEOMETRY = {
    "viewBox": [0, 0, 800, 520],
    "path": "M 10 10 C 120 40 200 180 350 220 Z",
}


class DomainModelTests(TestCase):
    def setUp(self):
        self.season = Season.objects.create(year=2026, is_current=True)
        self.circuit = Circuit.objects.create(
            external_id="albert_park",
            slug="albert-park",
            name="Albert Park Grand Prix Circuit",
            locality="Melbourne",
            country="Australia",
            timezone="Australia/Melbourne",
            geometry=VALID_GEOMETRY,
        )

    def grand_prix(self, round_number: int, name: str) -> GrandPrix:
        return GrandPrix.objects.create(
            season=self.season,
            circuit=self.circuit,
            round_number=round_number,
            name=name,
        )

    def test_grand_prix_is_unique_per_season_and_round(self):
        self.grand_prix(1, "Australian Grand Prix")

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.grand_prix(1, "Duplicate Grand Prix")

    def test_race_distance_uses_circuit_length_and_lap_count(self):
        self.circuit.length_km = Decimal("5.278")
        self.circuit.save(update_fields=["length_km"])
        grand_prix = GrandPrix.objects.create(
            season=self.season,
            circuit=self.circuit,
            round_number=1,
            name="Australian Grand Prix",
            laps=58,
        )

        self.assertEqual(grand_prix.race_distance_km, Decimal("306.124"))

    def test_computed_status_uses_race_session_boundaries(self):
        now = timezone.now()
        completed = self.grand_prix(1, "Completed Grand Prix")
        live = self.grand_prix(2, "Live Grand Prix")
        next_race = self.grand_prix(3, "Next Grand Prix")
        upcoming = self.grand_prix(4, "Upcoming Grand Prix")
        RaceSession.objects.bulk_create(
            [
                RaceSession(
                    grand_prix=completed,
                    session_type=RaceSession.Type.RACE,
                    starts_at=now - timedelta(days=8),
                    ends_at=now - timedelta(days=8, hours=-2),
                ),
                RaceSession(
                    grand_prix=live,
                    session_type=RaceSession.Type.RACE,
                    starts_at=now - timedelta(hours=1),
                    ends_at=now + timedelta(hours=1),
                ),
                RaceSession(
                    grand_prix=next_race,
                    session_type=RaceSession.Type.RACE,
                    starts_at=now + timedelta(days=7),
                    ends_at=now + timedelta(days=7, hours=2),
                ),
                RaceSession(
                    grand_prix=upcoming,
                    session_type=RaceSession.Type.RACE,
                    starts_at=now + timedelta(days=14),
                    ends_at=now + timedelta(days=14, hours=2),
                ),
            ]
        )

        self.assertEqual(completed.computed_status(now), "completed")
        self.assertEqual(live.computed_status(now), "live")
        self.assertEqual(next_race.computed_status(now), "next")
        self.assertEqual(upcoming.computed_status(now), "upcoming")

    def test_circuit_geometry_requires_path_and_viewbox(self):
        invalid = Circuit(
            external_id="invalid",
            slug="invalid",
            name="Invalid Circuit",
            locality="Nowhere",
            country="Nowhere",
            timezone="UTC",
            geometry={"path": "M0 0"},
        )

        with self.assertRaisesMessage(ValidationError, "viewBox"):
            invalid.full_clean()

    def test_standings_are_unique_per_season_and_competitor(self):
        driver = Driver.objects.create(
            external_id="lando_norris",
            given_name="Lando",
            family_name="Norris",
            code="NOR",
        )
        constructor = Constructor.objects.create(
            external_id="mclaren",
            name="McLaren",
            color="#FF8700",
        )
        DriverStanding.objects.create(
            season=self.season,
            driver=driver,
            position=1,
            points="25.0",
        )
        ConstructorStanding.objects.create(
            season=self.season,
            constructor=constructor,
            position=1,
            points="43.0",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            DriverStanding.objects.create(
                season=self.season,
                driver=driver,
                position=2,
                points="20.0",
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ConstructorStanding.objects.create(
                season=self.season,
                constructor=constructor,
                position=2,
                points="35.0",
            )

    def test_models_expose_russian_verbose_plural_names(self):
        self.assertEqual(Season._meta.verbose_name_plural, "Сезоны")
        self.assertEqual(Circuit._meta.verbose_name_plural, "Трассы")
        self.assertEqual(GrandPrix._meta.verbose_name_plural, "Этапы Grand Prix")
        self.assertEqual(Driver._meta.verbose_name_plural, "Пилоты")
        self.assertEqual(Constructor._meta.verbose_name_plural, "Команды")
