from django.contrib import admin
from django.urls import include, path

from core.error_views import handler404 as apexgrid_handler404
from core.error_views import handler500 as apexgrid_handler500


handler404 = apexgrid_handler404
handler500 = apexgrid_handler500


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("racing.urls")),
    path("", include("core.urls")),
]
