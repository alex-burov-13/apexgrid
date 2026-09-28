from django.urls import reverse
from django.test import TestCase

from racing.tests.factories import make_grand_prix


class PublicViewTests(TestCase):
    def setUp(self):
        self.grand_prix = make_grand_prix()

    def test_all_public_routes_render_in_russian(self):
        routes = {
            reverse("home"): "Следующий Grand Prix",
            reverse("calendar"): "Календарь сезона",
            reverse("circuits"): "Трассы сезона",
            reverse(
                "grand-prix-detail",
                kwargs={"year": 2026, "round_number": 1},
            ): "Расписание уик-энда",
            reverse("standings"): "Чемпионат",
            reverse("about"): "Об ApexGrid",
        }

        for url, heading in routes.items():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, heading)

    def test_grand_prix_detail_remembers_last_viewed_id(self):
        self.client.get(
            reverse(
                "grand-prix-detail",
                kwargs={"year": 2026, "round_number": 1},
            )
        )

        self.assertEqual(
            self.client.session["last_grand_prix_id"], self.grand_prix.pk
        )

    def test_missing_optional_session_fields_render_no_data(self):
        response = self.client.get(
            reverse(
                "grand-prix-detail",
                kwargs={"year": 2026, "round_number": 1},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Нет данных")

    def test_unknown_grand_prix_returns_404(self):
        response = self.client.get(
            reverse(
                "grand-prix-detail",
                kwargs={"year": 2026, "round_number": 99},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_calendar_filters_are_reflected_in_context(self):
        response = self.client.get(reverse("calendar"), {"status": "upcoming"})

        self.assertEqual(response.context["active_status"], "upcoming")
        self.assertEqual(list(response.context["events"]), [self.grand_prix])
