from django.db import DatabaseError, connection
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.preferences import (
    get_preferences,
    set_calendar_view,
    set_timezone,
    toggle_favorite,
)
from racing.models import GrandPrix
from racing.selectors import (
    calendar_for,
    get_current_season,
    get_next_grand_prix,
    standings_for,
)


def home(request: HttpRequest):
    season = get_current_season()
    next_event = get_next_grand_prix()
    events = calendar_for(season) if season else GrandPrix.objects.none()
    if season:
        driver_standings, constructor_standings = standings_for(season)
    else:
        driver_standings, constructor_standings = (), ()
    return render(
        request,
        "core/home.html",
        {
            "season": season,
            "next_event": next_event,
            "events": events,
            "driver_standings": driver_standings[:5],
            "constructor_standings": constructor_standings[:5],
            "preferences": get_preferences(request.session),
        },
    )


def about(request: HttpRequest):
    return render(request, "core/about.html")


def health(request: HttpRequest) -> JsonResponse:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse(
            {"status": "error", "database": "error"},
            status=503,
        )

    return JsonResponse({"status": "ok", "database": "ok"})


def _html_redirect(request: HttpRequest):
    target = request.POST.get("next")
    if (
        request.headers.get("X-Requested-With") == "fetch"
        or not target
        or not url_has_allowed_host_and_scheme(
            target,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
    ):
        return None
    return redirect(target)


@require_POST
def update_timezone(request: HttpRequest) -> JsonResponse:
    timezone_name = request.POST.get("timezone", "")
    try:
        set_timezone(request.session, timezone_name)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    if response := _html_redirect(request):
        return response
    return JsonResponse({"timezone": timezone_name})


@require_POST
def update_calendar_view(request: HttpRequest) -> JsonResponse:
    view_name = request.POST.get("view", "")
    set_calendar_view(request.session, view_name)
    if response := _html_redirect(request):
        return response
    return JsonResponse({"calendar_view": request.session["calendar_view"]})


@require_POST
def update_favorite(request: HttpRequest, pk: int) -> JsonResponse:
    if not GrandPrix.objects.filter(pk=pk).exists():
        return JsonResponse({"error": "Этап не найден."}, status=404)
    is_favorite = toggle_favorite(request.session, pk)
    if response := _html_redirect(request):
        return response
    return JsonResponse({"grand_prix_id": pk, "is_favorite": is_favorite})
