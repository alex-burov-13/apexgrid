import os

from django.contrib import messages
from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from integrations.jolpica.client import JolpicaClient
from racing.models import SyncRun
from racing.services.sync import SyncSeasonError, sync_season


SEASON = 2026


def _jolpica_client() -> JolpicaClient:
    return JolpicaClient(
        base_url=os.getenv("JOLPICA_BASE_URL", "https://api.jolpi.ca/ergast/f1"),
        user_agent=os.getenv("JOLPICA_USER_AGENT", "ApexGrid/1.0 Django/5.2"),
        timeout=(3.05, 10.0),
    )


def sync_2026_view(
    request: HttpRequest,
    *,
    admin_site: AdminSite,
) -> HttpResponse:
    if not request.user.has_perm("racing.change_syncrun"):
        raise PermissionDenied

    if request.method == "POST":
        try:
            summary = sync_season(
                SEASON,
                client=_jolpica_client(),
                initiated_by=SyncRun.Initiator.ADMIN,
            )
        except SyncSeasonError as error:
            messages.error(request, str(error))
        else:
            messages.success(
                request,
                f"Сезон {SEASON} обновлён — создано: {summary.created}, "
                f"обновлено: {summary.updated}, результаты: {summary.results}, "
                f"положения: {summary.standings}.",
            )
        return redirect(reverse("admin:racing_sync_2026"))

    context = {
        **admin_site.each_context(request),
        "title": f"Обновить сезон {SEASON}",
        "season": SEASON,
        "latest_run": SyncRun.objects.first(),
    }
    return TemplateResponse(request, "admin/racing/sync_form.html", context)
