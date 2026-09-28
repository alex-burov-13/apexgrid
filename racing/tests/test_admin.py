from django.contrib import admin
from django.test import RequestFactory, TestCase

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


class AdminConfigurationTests(TestCase):
    def test_all_domain_models_are_registered(self):
        expected = {
            Season,
            Circuit,
            GrandPrix,
            RaceSession,
            Driver,
            Constructor,
            RaceResult,
            DriverStanding,
            ConstructorStanding,
            SyncRun,
        }

        self.assertTrue(expected.issubset(admin.site._registry))

    def test_sync_run_is_read_only_in_admin(self):
        model_admin = admin.site._registry[SyncRun]
        request = RequestFactory().get("/admin/racing/syncrun/")
        field_names = {field.name for field in SyncRun._meta.fields}

        self.assertEqual(set(model_admin.get_readonly_fields(request)), field_names)
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))
