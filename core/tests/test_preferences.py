from django.test import SimpleTestCase

from core.preferences import (
    get_preferences,
    set_calendar_view,
    set_timezone,
    toggle_favorite,
)


class PreferenceServiceTests(SimpleTestCase):
    def test_invalid_timezone_raises_value_error_without_changing_session(self):
        session = {"timezone": "Europe/Moscow"}

        with self.assertRaises(ValueError):
            set_timezone(session, "Moon/Sea_of_Tranquility")

        self.assertEqual(session, {"timezone": "Europe/Moscow"})

    def test_toggle_favorite_is_idempotent_and_returns_new_state(self):
        session = {}

        self.assertTrue(toggle_favorite(session, 42))
        self.assertEqual(session["favorite_grand_prix_ids"], [42])
        self.assertFalse(toggle_favorite(session, 42))
        self.assertEqual(session["favorite_grand_prix_ids"], [])

    def test_unknown_calendar_view_falls_back_to_cards(self):
        session = {"calendar_view": "wall"}

        set_calendar_view(session, "wall")

        self.assertEqual(session["calendar_view"], "cards")

    def test_get_preferences_tolerates_stale_grand_prix_ids(self):
        session = {
            "timezone": "Invalid/Zone",
            "calendar_view": "compact",
            "favorite_grand_prix_ids": [7, "stale", -1, 7, 9],
            "last_grand_prix_id": "removed",
        }

        preferences = get_preferences(session)

        self.assertEqual(preferences.timezone, "UTC")
        self.assertEqual(preferences.calendar_view, "compact")
        self.assertEqual(preferences.favorite_grand_prix_ids, (7, 9))
        self.assertIsNone(preferences.last_grand_prix_id)
