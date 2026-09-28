from datetime import datetime, timedelta

from django.db.models import Prefetch, Q, QuerySet
from django.utils import timezone

from racing.models import (
    ConstructorStanding,
    DriverStanding,
    GrandPrix,
    RaceResult,
    RaceSession,
    Season,
)


def get_current_season() -> Season | None:
    current = Season.objects.filter(is_current=True).order_by("-year").first()
    if current is not None:
        return current
    return Season.objects.order_by("-year").first()


def get_next_grand_prix(at: datetime | None = None) -> GrandPrix | None:
    season = get_current_season()
    if season is None:
        return None
    at = at or timezone.now()
    return (
        GrandPrix.objects.filter(
            season=season,
            sessions__session_type=RaceSession.Type.RACE,
            sessions__starts_at__gte=at,
        )
        .select_related("season", "circuit")
        .prefetch_related("sessions")
        .order_by("sessions__starts_at", "round_number")
        .first()
    )


def calendar_for(
    season: Season,
    *,
    status: str | None = None,
    sprint_only: bool = False,
) -> QuerySet[GrandPrix]:
    now = timezone.now()
    queryset = (
        GrandPrix.objects.filter(season=season)
        .select_related("season", "circuit")
        .prefetch_related(
            Prefetch("sessions", queryset=RaceSession.objects.order_by("starts_at")),
            Prefetch(
                "results",
                queryset=RaceResult.objects.select_related(
                    "driver", "constructor"
                ).order_by("position", "driver__family_name"),
            ),
        )
        .order_by("round_number")
    )
    race = Q(sessions__session_type=RaceSession.Type.RACE)
    if status == "completed":
        queryset = queryset.filter(
            race
            & (
                Q(sessions__ends_at__lte=now)
                | Q(
                    sessions__ends_at__isnull=True,
                    sessions__starts_at__lte=now - timedelta(hours=3),
                )
            )
        )
    elif status == "upcoming":
        queryset = queryset.filter(race & Q(sessions__starts_at__gt=now))
    elif status == "live":
        queryset = queryset.filter(
            race
            & Q(sessions__starts_at__lte=now)
            & (
                Q(sessions__ends_at__gt=now)
                | Q(
                    sessions__ends_at__isnull=True,
                    sessions__starts_at__gt=now - timedelta(hours=3),
                )
            )
        )
    elif status == "next":
        next_event = get_next_grand_prix(now)
        queryset = queryset.filter(pk=next_event.pk if next_event else None)

    if sprint_only:
        queryset = queryset.filter(is_sprint=True)
    return queryset.distinct()


def standings_for(
    season: Season,
) -> tuple[QuerySet[DriverStanding], QuerySet[ConstructorStanding]]:
    drivers = DriverStanding.objects.filter(season=season).select_related(
        "driver", "constructor"
    ).order_by("position")
    constructors = ConstructorStanding.objects.filter(season=season).select_related(
        "constructor"
    ).order_by("position")
    return drivers, constructors
