from django.urls import path

from core import views


urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("health/", views.health, name="health"),
    path(
        "preferences/timezone/",
        views.update_timezone,
        name="preference-timezone",
    ),
    path(
        "preferences/calendar-view/",
        views.update_calendar_view,
        name="preference-calendar-view",
    ),
    path(
        "preferences/favorites/<int:pk>/",
        views.update_favorite,
        name="preference-favorite",
    ),
]
