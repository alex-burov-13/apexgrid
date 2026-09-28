from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from racing.models import GrandPrix, SyncRun
from racing.services.sync import SyncSeasonError, SyncSummary


class AdminSyncTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username="marshal",
            password="test-password",
            is_staff=True,
        )
        self.staff.user_permissions.add(
            Permission.objects.get(codename="change_syncrun")
        )
        self.staff_without_sync_permission = user_model.objects.create_user(
            username="limited-staff",
            password="test-password",
            is_staff=True,
        )
        self.non_staff = user_model.objects.create_user(
            username="viewer",
            password="test-password",
        )
        self.url = reverse("admin:racing_sync_2026")

    def test_anonymous_user_is_redirected_to_admin_login(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            f"{reverse('admin:login')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_non_staff_user_cannot_run_sync(self):
        self.client.force_login(self.non_staff)

        with patch("racing.admin_views.sync_season") as sync:
            response = self.client.post(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response.url)
        sync.assert_not_called()

    def test_staff_without_sync_permission_gets_forbidden(self):
        self.client.force_login(self.staff_without_sync_permission)

        with patch("racing.admin_views.sync_season") as sync:
            response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)
        sync.assert_not_called()

    def test_get_only_shows_confirmation_and_post_calls_service_once(self):
        self.client.force_login(self.staff)

        with patch("racing.admin_views.sync_season") as sync:
            get_response = self.client.get(self.url)

        self.assertContains(get_response, "Обновить сезон 2026")
        self.assertContains(get_response, "Jolpica")
        sync.assert_not_called()

        summary = SyncSummary(created=3, updated=4, results=5, standings=6)
        with patch("racing.admin_views.sync_season", return_value=summary) as sync:
            post_response = self.client.post(self.url, follow=True)

        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "Сезон 2026 обновлён")
        self.assertContains(post_response, "создано: 3")
        sync.assert_called_once()
        args, kwargs = sync.call_args
        self.assertEqual(args[0], 2026)
        self.assertEqual(kwargs["initiated_by"], SyncRun.Initiator.ADMIN)

    def test_failed_sync_shows_safe_message_and_preserves_database(self):
        self.client.force_login(self.staff)
        before = GrandPrix.objects.count()

        with patch(
            "racing.admin_views.sync_season",
            side_effect=SyncSeasonError("Jolpica API недоступен. Локальные данные сохранены."),
        ):
            response = self.client.post(self.url, follow=True)

        self.assertEqual(GrandPrix.objects.count(), before)
        self.assertContains(response, "Jolpica API недоступен")
        self.assertNotContains(response, "Traceback")
