from itertools import groupby
from zoneinfo import ZoneInfo

from django.db.models import Prefetch
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, render

from core.preferences import get_preferences, remember_grand_prix
from racing.models import Circuit, GrandPrix, RaceResult, RaceSession
from racing.selectors import calendar_for, get_current_season, standings_for


WEEKDAYS_RU = (
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
)
MONTHS_RU = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def _schedule_days(sessions, timezone_name: str):
    zone = ZoneInfo(timezone_name)
    ordered_sessions = list(sessions)
    for position, session in enumerate(ordered_sessions, start=1):
        session.timeline_position = position

    def local_date(session):
        return session.starts_at.astimezone(zone).date()

    days = []
    for date, grouped_sessions in groupby(ordered_sessions, key=local_date):
        days.append(
            {
                "date": date,
                "weekday": WEEKDAYS_RU[date.weekday()],
                "label": f"{date.day:02d} {MONTHS_RU[date.month]}",
                "sessions": tuple(grouped_sessions),
            }
        )
    return days


def calendar(request: HttpRequest):
    season = get_current_season()
    active_status = request.GET.get("status")
    if active_status not in {"completed", "upcoming", "live", "next"}:
        active_status = None
    sprint_only = request.GET.get("sprint") == "1"
    events = (
        calendar_for(season, status=active_status, sprint_only=sprint_only)
        if season
        else GrandPrix.objects.none()
    )
    return render(
        request,
        "racing/calendar.html",
        {
            "season": season,
            "events": events,
            "active_status": active_status,
            "sprint_only": sprint_only,
            "preferences": get_preferences(request.session),
        },
    )


def circuit_list(request: HttpRequest):
    season = get_current_season()
    circuits = (
        Circuit.objects.filter(grand_prix__season=season)
        .order_by("country", "name")
        .distinct()
        if season
        else Circuit.objects.none()
    )
    return render(
        request,
        "racing/circuit_list.html",
        {"season": season, "circuits": circuits},
    )


def grand_prix_detail(request: HttpRequest, year: int, round_number: int):
    event = get_object_or_404(
        GrandPrix.objects.select_related("season", "circuit").prefetch_related(
            Prefetch("sessions", queryset=RaceSession.objects.order_by("starts_at")),
            Prefetch(
                "results",
                queryset=RaceResult.objects.select_related(
                    "driver", "constructor"
                ).order_by("position", "driver__family_name"),
            ),
        ),
        season__year=year,
        round_number=round_number,
    )
    remember_grand_prix(request.session, event.pk)
    preferences = get_preferences(request.session)
    return render(
        request,
        "racing/grand_prix_detail.html",
        {
            "event": event,
            "preferences": preferences,
            "schedule_days": _schedule_days(
                event.sessions.all(),
                preferences.timezone,
            ),
            "is_favorite": event.pk in preferences.favorite_grand_prix_ids,
        },
    )


def standings(request: HttpRequest):
    season = get_current_season()
    if season:
        drivers, constructors = standings_for(season)
    else:
        drivers, constructors = (), ()
    return render(
        request,
        "racing/standings.html",
        {"season": season, "drivers": drivers, "constructors": constructors},
    )
