from django.urls import path

from racing import views


urlpatterns = [
    path("calendar/", views.calendar, name="calendar"),
    path("circuits/", views.circuit_list, name="circuits"),
    path("championship/", views.standings, name="standings"),
    path(
        "grand-prix/<int:year>/<int:round_number>/",
        views.grand_prix_detail,
        name="grand-prix-detail",
    ),
]
