from django.test import TestCase
from django.urls import reverse

from racing.tests.factories import make_grand_prix


class AccessibilityMarkupTests(TestCase):
    def setUp(self):
        self.event = make_grand_prix()

    def test_base_has_skip_link_single_main_and_labeled_navigation(self):
        response = self.client.get(reverse("home"))
        html = response.content.decode()

        self.assertIn('class="skip-link"', html)
        self.assertEqual(html.count("<main"), 1)
        self.assertIn('aria-label="Основная навигация"', html)
        self.assertIn('aria-current="page"', html)

    def test_track_cards_have_accessible_names_and_svg_fallback(self):
        response = self.client.get(reverse("calendar"))

        self.assertContains(response, 'class="track-map"', html=False)
        self.assertContains(response, 'role="img"', html=False)
        self.assertContains(response, 'aria-label="Схема трассы', html=False)
        self.assertContains(response, 'data-track-fallback', html=False)
        self.assertContains(response, "<path", html=False)

    def test_controls_use_native_interactive_elements(self):
        calendar_response = self.client.get(reverse("calendar"))
        circuits_response = self.client.get(reverse("circuits"))
        detail_response = self.client.get(
            reverse(
                "grand-prix-detail",
                kwargs={"year": 2026, "round_number": 1},
            )
        )
        html = (
            calendar_response.content.decode()
            + circuits_response.content.decode()
            + detail_response.content.decode()
        )

        self.assertNotIn('div role="button"', html)
        self.assertIn('<button type="button"', html)
        self.assertIn('<button type="submit"', html)
        self.assertIn('<input type="search"', html)
