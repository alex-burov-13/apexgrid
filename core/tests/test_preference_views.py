from django.test import Client, TestCase

from racing.tests.factories import make_grand_prix


class PreferenceViewTests(TestCase):
    def test_timezone_endpoint_rejects_get(self):
        response = self.client.get("/preferences/timezone/")

        self.assertEqual(response.status_code, 405)

    def test_timezone_endpoint_rejects_invalid_zone_without_session_mutation(self):
        session = self.client.session
        session["timezone"] = "Europe/Moscow"
        session.save()

        response = self.client.post(
            "/preferences/timezone/",
            {"timezone": "Moon/Sea_of_Tranquility"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {"error": "Неизвестный часовой пояс."})
        self.assertEqual(self.client.session["timezone"], "Europe/Moscow")

    def test_preference_endpoints_are_csrf_protected(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(
            "/preferences/timezone/",
            {"timezone": "Europe/Moscow"},
        )

        self.assertEqual(response.status_code, 403)

    def test_favorite_endpoint_requires_existing_grand_prix(self):
        response = self.client.post("/preferences/favorites/9999/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertJSONEqual(response.content, {"error": "Этап не найден."})

    def test_valid_preferences_are_returned_and_saved(self):
        grand_prix = make_grand_prix()

        timezone_response = self.client.post(
            "/preferences/timezone/",
            {"timezone": "Europe/Moscow"},
            HTTP_X_REQUESTED_WITH="fetch",
        )
        view_response = self.client.post(
            "/preferences/calendar-view/",
            {"view": "compact"},
            HTTP_X_REQUESTED_WITH="fetch",
        )
        favorite_response = self.client.post(
            f"/preferences/favorites/{grand_prix.pk}/",
            HTTP_X_REQUESTED_WITH="fetch",
        )

        self.assertJSONEqual(
            timezone_response.content,
            {"timezone": "Europe/Moscow"},
        )
        self.assertJSONEqual(view_response.content, {"calendar_view": "compact"})
        self.assertJSONEqual(
            favorite_response.content,
            {"grand_prix_id": grand_prix.pk, "is_favorite": True},
        )
        self.assertEqual(self.client.session["timezone"], "Europe/Moscow")
        self.assertEqual(self.client.session["calendar_view"], "compact")
        self.assertEqual(
            self.client.session["favorite_grand_prix_ids"],
            [grand_prix.pk],
        )

    def test_plain_html_posts_redirect_back_instead_of_showing_json(self):
        grand_prix = make_grand_prix()

        timezone_response = self.client.post(
            "/preferences/timezone/",
            {"timezone": "Europe/Moscow", "next": "/calendar/"},
        )
        view_response = self.client.post(
            "/preferences/calendar-view/",
            {"view": "compact", "next": "/calendar/"},
        )
        favorite_response = self.client.post(
            f"/preferences/favorites/{grand_prix.pk}/",
            {"next": f"/grand-prix/2026/{grand_prix.round_number}/"},
        )

        self.assertRedirects(timezone_response, "/calendar/", fetch_redirect_response=False)
        self.assertRedirects(view_response, "/calendar/", fetch_redirect_response=False)
        self.assertRedirects(
            favorite_response,
            f"/grand-prix/2026/{grand_prix.round_number}/",
            fetch_redirect_response=False,
        )
