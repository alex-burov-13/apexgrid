from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from integrations.jolpica.errors import JolpicaInvalidPayload, JolpicaRateLimited
from integrations.jolpica.schemas import (
    ConstructorStandingPayload,
    DriverStandingPayload,
    EventPayload,
    ResultPayload,
    SessionPayload,
)
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
    SyncRun,
)
from racing.services.sync import SyncSeasonError, sync_season


class FakeJolpicaClient:
    def __init__(self, *, result_round: int = 1, failure: Exception | None = None):
        start = timezone.now() + timedelta(days=10)
        self.events = (
            EventPayload(
                season=2026,
                round_number=1,
                external_id="2026-1",
                name="Australian Grand Prix",
                circuit_external_id="albert_park",
                circuit_name="Albert Park Grand Prix Circuit",
                locality="Melbourne",
                country="Australia",
                latitude=Decimal("-37.8497"),
                longitude=Decimal("144.968"),
                is_sprint=False,
                sessions=(SessionPayload("race", start),),
            ),
        )
        self.results = (
            ResultPayload(
                season=2026,
                round_number=result_round,
                driver_external_id="norris",
                given_name="Lando",
                family_name="Norris",
                code="NOR",
                permanent_number=4,
                driver_nationality="British",
                constructor_external_id="mclaren",
                constructor_name="McLaren",
                constructor_nationality="British",
                position=1,
                grid_position=1,
                points=Decimal("25"),
                status="Finished",
                time_text="1:28:32.000",
                gap=None,
                fastest_lap_time=None,
                fastest_lap_rank=None,
            ),
        )
        self.driver_standings = (
            DriverStandingPayload(
                season=2026,
                position=1,
                points=Decimal("25"),
                wins=1,
                driver_external_id="norris",
                given_name="Lando",
                family_name="Norris",
                code="NOR",
                permanent_number=4,
                nationality="British",
                constructor_external_id="mclaren",
                constructor_name="McLaren",
                constructor_nationality="British",
            ),
        )
        self.constructor_standings = (
            ConstructorStandingPayload(
                season=2026,
                position=1,
                points=Decimal("43"),
                wins=1,
                constructor_external_id="mclaren",
                constructor_name="McLaren",
                constructor_nationality="British",
            ),
        )
        self.failure = failure

    def get_schedule(self, season: int):
        return self.events

    def get_results(self, season: int):
        if self.failure:
            raise self.failure
        return self.results

    def get_driver_standings(self, season: int):
        return self.driver_standings

    def get_constructor_standings(self, season: int):
        return self.constructor_standings


class SeasonSyncTests(TestCase):
    def test_sync_creates_calendar_results_and_standings_atomically(self):
        summary = sync_season(
            2026,
            client=FakeJolpicaClient(),
            initiated_by="cli",
        )

        self.assertGreater(summary.created, 0)
        self.assertEqual(summary.results, 1)
        self.assertEqual(summary.standings, 2)
        self.assertEqual(Season.objects.get().year, 2026)
        self.assertEqual(GrandPrix.objects.get().name, "Australian Grand Prix")
        self.assertEqual(RaceSession.objects.get().session_type, "race")
        self.assertEqual(RaceResult.objects.get().driver.family_name, "Norris")
        self.assertEqual(DriverStanding.objects.get().position, 1)
        self.assertEqual(ConstructorStanding.objects.get().position, 1)
        self.assertEqual(SyncRun.objects.get().status, SyncRun.Status.SUCCESS)

    def test_sync_is_idempotent_for_same_payload(self):
        client = FakeJolpicaClient()
        sync_season(2026, client=client, initiated_by="cli")

        second = sync_season(2026, client=client, initiated_by="cli")

        self.assertEqual(second.created, 0)
        self.assertEqual(Season.objects.count(), 1)
        self.assertEqual(Circuit.objects.count(), 1)
        self.assertEqual(GrandPrix.objects.count(), 1)
        self.assertEqual(RaceResult.objects.count(), 1)
        self.assertEqual(DriverStanding.objects.count(), 1)

    def test_empty_remote_statistics_never_erase_existing_snapshot(self):
        sync_season(2026, client=FakeJolpicaClient(), initiated_by="cli")
        client = FakeJolpicaClient()
        client.results = ()
        client.driver_standings = ()
        client.constructor_standings = ()

        with self.assertRaises(SyncSeasonError):
            sync_season(2026, client=client, initiated_by="cli")

        self.assertEqual(RaceResult.objects.count(), 1)
        self.assertEqual(DriverStanding.objects.count(), 1)
        self.assertEqual(ConstructorStanding.objects.count(), 1)
        self.assertEqual(SyncRun.objects.filter(status=SyncRun.Status.FAILED).count(), 1)

    def test_truncated_non_empty_snapshot_never_replaces_complete_data(self):
        complete = FakeJolpicaClient()
        second_event = replace(
            complete.events[0],
            round_number=2,
            external_id="2026-2",
            name="Second Grand Prix",
            circuit_external_id="second-circuit",
            circuit_name="Second Circuit",
        )
        second_result = replace(
            complete.results[0],
            round_number=2,
            driver_external_id="piastri",
            given_name="Oscar",
            family_name="Piastri",
            code="PIA",
            permanent_number=81,
            position=2,
            points=Decimal("18"),
        )
        second_driver = replace(
            complete.driver_standings[0],
            position=2,
            points=Decimal("18"),
            wins=0,
            driver_external_id="piastri",
            given_name="Oscar",
            family_name="Piastri",
            code="PIA",
            permanent_number=81,
        )
        complete.events = (*complete.events, second_event)
        complete.results = (*complete.results, second_result)
        complete.driver_standings = (*complete.driver_standings, second_driver)
        sync_season(2026, client=complete, initiated_by="cli")

        with self.assertRaises(SyncSeasonError):
            sync_season(2026, client=FakeJolpicaClient(), initiated_by="cli")

        self.assertEqual(GrandPrix.objects.count(), 2)
        self.assertEqual(RaceResult.objects.count(), 2)
        self.assertEqual(DriverStanding.objects.count(), 2)
        self.assertEqual(SyncRun.objects.filter(status=SyncRun.Status.FAILED).count(), 1)

    def test_authoritative_schedule_removes_rounds_missing_from_new_snapshot(self):
        client = FakeJolpicaClient()
        second_event = replace(
            client.events[0],
            round_number=2,
            external_id="2026-2",
            name="Second Grand Prix",
            circuit_external_id="second-circuit",
            circuit_name="Second Circuit",
        )
        client.events = (*client.events, second_event)
        sync_season(2026, client=client, initiated_by="cli")
        self.assertEqual(GrandPrix.objects.count(), 2)

        sync_season(2026, client=FakeJolpicaClient(), initiated_by="cli")

        self.assertEqual(list(GrandPrix.objects.values_list("round_number", flat=True)), [1])

    def test_sync_never_overwrites_editorial_summary_geometry_or_team_color(self):
        season = Season.objects.create(year=2026)
        geometry = {"viewBox": [0, 0, 100, 100], "path": "M0 0 L100 100"}
        circuit = Circuit.objects.create(
            external_id="albert_park",
            slug="albert-park",
            name="Old Circuit Name",
            locality="Melbourne",
            country="Australia",
            timezone="Australia/Melbourne",
            summary="Редакторский текст",
            geometry=geometry,
        )
        GrandPrix.objects.create(
            season=season,
            circuit=circuit,
            round_number=1,
            name="Old Grand Prix Name",
            editorial_summary="История этапа",
        )
        Constructor.objects.create(
            external_id="mclaren",
            name="Old Team Name",
            color="#FF8700",
        )

        sync_season(2026, client=FakeJolpicaClient(), initiated_by="cli")

        circuit.refresh_from_db()
        grand_prix = GrandPrix.objects.get()
        constructor = Constructor.objects.get(external_id="mclaren")
        self.assertEqual(circuit.summary, "Редакторский текст")
        self.assertEqual(circuit.geometry, geometry)
        self.assertEqual(circuit.timezone, "Australia/Melbourne")
        self.assertEqual(grand_prix.editorial_summary, "История этапа")
        self.assertEqual(constructor.color, "#FF8700")

    def test_partial_payload_rolls_back_existing_season_and_records_failed_run(self):
        season = Season.objects.create(year=2026)
        circuit = Circuit.objects.create(
            external_id="albert_park",
            slug="albert-park",
            name="Original Name",
            locality="Melbourne",
            country="Australia",
            timezone="UTC",
            geometry={"viewBox": [0, 0, 10, 10], "path": "M0 0 L10 10"},
        )
        GrandPrix.objects.create(
            season=season,
            circuit=circuit,
            round_number=1,
            name="Original Grand Prix",
        )
        client = FakeJolpicaClient(
            failure=JolpicaInvalidPayload("partial payload\nTraceback: secret")
        )

        with self.assertRaises(SyncSeasonError):
            sync_season(2026, client=client, initiated_by="cli")

        self.assertEqual(GrandPrix.objects.get().name, "Original Grand Prix")
        run = SyncRun.objects.get()
        self.assertEqual(run.status, SyncRun.Status.FAILED)
        self.assertNotIn("Traceback", run.error_message)
        self.assertNotIn("secret", run.error_message)

    def test_invalid_result_reference_rolls_back_without_deleting_old_results(self):
        sync_season(2026, client=FakeJolpicaClient(), initiated_by="cli")

        with self.assertRaises(SyncSeasonError):
            sync_season(
                2026,
                client=FakeJolpicaClient(result_round=99),
                initiated_by="cli",
            )

        self.assertEqual(RaceResult.objects.count(), 1)
        self.assertEqual(RaceResult.objects.get().grand_prix.round_number, 1)
        self.assertEqual(SyncRun.objects.filter(status=SyncRun.Status.FAILED).count(), 1)

    def test_rate_limit_records_safe_message_without_traceback_content(self):
        client = FakeJolpicaClient(
            failure=JolpicaRateLimited("Traceback: API_TOKEN=secret")
        )

        with self.assertRaisesMessage(SyncSeasonError, "частоту запросов"):
            sync_season(2026, client=client, initiated_by="admin")

        run = SyncRun.objects.get()
        self.assertEqual(run.initiated_by, "admin")
        self.assertEqual(run.status, SyncRun.Status.FAILED)
        self.assertEqual(
            run.error_message,
            "Jolpica временно ограничил частоту запросов.",
        )
