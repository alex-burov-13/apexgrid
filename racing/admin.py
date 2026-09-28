from django.contrib import admin
from django.urls import path

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


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("year", "is_current", "starts_on", "ends_on", "synced_at")
    list_filter = ("is_current",)
    ordering = ("-year",)


@admin.register(Circuit)
class CircuitAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "locality", "length_km", "turns")
    list_filter = ("country", "direction")
    search_fields = ("name", "country", "locality", "external_id")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(GrandPrix)
class GrandPrixAdmin(admin.ModelAdmin):
    list_display = ("season", "round_number", "name", "circuit", "is_sprint")
    list_filter = ("season", "is_sprint", "circuit__country")
    search_fields = ("name", "circuit__name", "circuit__country")
    list_select_related = ("season", "circuit")


@admin.register(RaceSession)
class RaceSessionAdmin(admin.ModelAdmin):
    list_display = ("grand_prix", "session_type", "starts_at", "ends_at")
    list_filter = ("session_type", "grand_prix__season")
    search_fields = ("grand_prix__name",)
    list_select_related = ("grand_prix",)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("display_name", "code", "permanent_number", "nationality")
    search_fields = ("given_name", "family_name", "code", "external_id")
    list_filter = ("nationality",)


@admin.register(Constructor)
class ConstructorAdmin(admin.ModelAdmin):
    list_display = ("name", "nationality", "color")
    search_fields = ("name", "external_id")
    list_filter = ("nationality",)


@admin.register(RaceResult)
class RaceResultAdmin(admin.ModelAdmin):
    list_display = ("grand_prix", "position", "driver", "constructor", "points")
    list_filter = ("grand_prix__season", "constructor")
    search_fields = ("driver__given_name", "driver__family_name", "grand_prix__name")
    list_select_related = ("grand_prix", "driver", "constructor")


@admin.register(DriverStanding)
class DriverStandingAdmin(admin.ModelAdmin):
    list_display = ("season", "position", "driver", "constructor", "points", "wins")
    list_filter = ("season", "constructor")
    list_select_related = ("season", "driver", "constructor")


@admin.register(ConstructorStanding)
class ConstructorStandingAdmin(admin.ModelAdmin):
    list_display = ("season", "position", "constructor", "points", "wins")
    list_filter = ("season",)
    list_select_related = ("season", "constructor")


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = ("season_year", "status", "initiated_by", "started_at", "finished_at")
    list_filter = ("status", "initiated_by", "season_year")
    readonly_fields = tuple(field.name for field in SyncRun._meta.fields)

    def get_urls(self):
        from racing.admin_views import sync_2026_view

        custom_urls = [
            path(
                "sync-2026/",
                self.admin_site.admin_view(
                    lambda request: sync_2026_view(
                        request,
                        admin_site=self.admin_site,
                    )
                ),
                name="racing_sync_2026",
            ),
        ]
        return custom_urls + super().get_urls()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
