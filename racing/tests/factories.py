from datetime import timedelta

from django.utils import timezone

from racing.models import Circuit, GrandPrix, RaceSession, Season


def make_season(year: int = 2026, *, is_current: bool = True) -> Season:
    return Season.objects.create(year=year, is_current=is_current)


def make_circuit(external_id: str = "test-circuit") -> Circuit:
    return Circuit.objects.create(
        external_id=external_id,
        slug=external_id,
        name="Test Circuit",
        locality="Test City",
        country="Test Country",
        timezone="UTC",
        geometry={"viewBox": [0, 0, 100, 100], "path": "M0 0 L100 100"},
    )


def make_grand_prix(
    *,
    season: Season | None = None,
    circuit: Circuit | None = None,
    round_number: int = 1,
    starts_at=None,
) -> GrandPrix:
    season = season or make_season()
    circuit = circuit or make_circuit()
    grand_prix = GrandPrix.objects.create(
        season=season,
        circuit=circuit,
        round_number=round_number,
        name=f"Round {round_number} Grand Prix",
    )
    starts_at = starts_at or timezone.now() + timedelta(days=round_number)
    RaceSession.objects.create(
        grand_prix=grand_prix,
        session_type=RaceSession.Type.RACE,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
    )
    return grand_prix
