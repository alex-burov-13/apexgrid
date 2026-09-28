from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from racing.models import GrandPrix, RaceSession
from racing.selectors import (
    calendar_for,
    get_current_season,
    get_next_grand_prix,
    standings_for,
)
from racing.tests.factories import make_circuit, make_grand_prix, make_season


class PublicSelectorTests(TestCase):
    def test_empty_database_has_no_current_season_or_next_race(self):
        self.assertIsNone(get_current_season())
        self.assertIsNone(get_next_grand_prix())

    def test_next_race_includes_exact_start_boundary(self):
        now = timezone.now().replace(microsecond=0)
        season = make_season()
        circuit = make_circuit()
        first = make_grand_prix(
            season=season,
            circuit=circuit,
            round_number=1,
            starts_at=now,
        )
        make_grand_prix(
            season=season,
            circuit=circuit,
            round_number=2,
            starts_at=now + timedelta(days=7),
        )

        self.assertEqual(get_next_grand_prix(now), first)

    def test_calendar_filters_status_sprint_and_keeps_round_order(self):
        now = timezone.now()
        season = make_season()
        circuit = make_circuit()
        completed = make_grand_prix(
            season=season,
            circuit=circuit,
            round_number=1,
            starts_at=now - timedelta(days=2),
        )
        next_race = make_grand_prix(
            season=season,
            circuit=circuit,
            round_number=2,
            starts_at=now + timedelta(days=2),
        )
        sprint = make_grand_prix(
            season=season,
            circuit=circuit,
            round_number=3,
            starts_at=now + timedelta(days=9),
        )
        sprint.is_sprint = True
        sprint.save(update_fields=["is_sprint"])

        self.assertEqual(list(calendar_for(season)), [completed, next_race, sprint])
        self.assertEqual(list(calendar_for(season, status="completed")), [completed])
        self.assertEqual(
            list(calendar_for(season, status="upcoming")), [next_race, sprint]
        )
        self.assertEqual(list(calendar_for(season, sprint_only=True)), [sprint])

    def test_calendar_related_content_stays_within_three_queries(self):
        season = make_season()
        circuit = make_circuit()
        for round_number in range(1, 5):
            make_grand_prix(
                season=season,
                circuit=circuit,
                round_number=round_number,
            )

        with CaptureQueriesContext(connection) as captured:
            events = list(calendar_for(season))
            for event in events:
                _ = event.circuit.name
                _ = list(event.sessions.all())
                _ = list(event.results.all())

        self.assertLessEqual(len(captured), 3)

    def test_standings_selector_returns_stable_empty_querysets(self):
        season = make_season()

        drivers, constructors = standings_for(season)

        self.assertEqual(list(drivers), [])
        self.assertEqual(list(constructors), [])
