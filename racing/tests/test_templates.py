from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from racing.models import Constructor, ConstructorStanding, RaceSession
from racing.templatetags.racing_tags import TEAM_LOGOS
from racing.tests.factories import make_circuit, make_grand_prix


class PublicTemplateTests(TestCase):
    def setUp(self):
        self.grand_prix = make_grand_prix()

    def test_base_template_has_semantic_navigation_and_main_landmark(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, '<nav aria-label="Основная навигация"', html=False)
        self.assertContains(response, "<main", html=False)
        self.assertContains(response, "Учебный неофициальный проект")

    def test_session_time_is_rendered_in_saved_timezone_before_javascript(self):
        session = self.client.session
        session["timezone"] = "Europe/Moscow"
        session.save()
        response = self.client.get(
            reverse(
                "grand-prix-detail",
                kwargs={"year": 2026, "round_number": 1},
            )
        )

        self.assertContains(response, "data-utc=", html=False)
        self.assertContains(response, "МСК")

        session = self.client.session
        session["timezone"] = "UTC"
        session.save()
        utc_response = self.client.get(
            reverse(
                "grand-prix-detail",
                kwargs={"year": 2026, "round_number": 1},
            )
        )
        self.assertContains(utc_response, "UTC")
        self.assertNotContains(utc_response, "МСК")

    def test_grand_prix_has_accessible_svg_blueprint(self):
        response = self.client.get(
            reverse(
                "grand-prix-detail",
                kwargs={"year": 2026, "round_number": 1},
            )
        )

        self.assertContains(response, 'data-track-blueprint', html=False)
        self.assertContains(response, 'role="img"', html=False)
        self.assertContains(response, '<path', html=False)

    def test_grand_prix_embeds_informative_track_blueprint(self):
        response = self.client.get(
            reverse(
                "grand-prix-detail",
                kwargs={"year": 2026, "round_number": 1},
            )
        )

        self.assertContains(response, "data-track-blueprint", html=False)
        self.assertContains(
            response,
            'aria-label="Техническая схема трассы',
            html=False,
        )
        self.assertContains(response, "Сектор 1")
        self.assertContains(response, "Сектор 2")
        self.assertContains(response, "Сектор 3")
        self.assertContains(response, "Старт / финиш")
        self.assertContains(response, "Направление")
        self.assertNotContains(response, "data-circuit-3d", html=False)

    def test_grand_prix_title_uses_responsive_title_parts(self):
        response = self.client.get(
            reverse(
                "grand-prix-detail",
                kwargs={"year": 2026, "round_number": 1},
            )
        )

        self.assertContains(response, 'class="detail__title"', html=False)
        self.assertContains(response, 'class="detail__title-main"', html=False)

    def test_weekend_schedule_is_grouped_by_day_in_chronological_order(self):
        self.grand_prix.sessions.all().delete()
        sessions = [
            (RaceSession.Type.RACE, datetime(2026, 3, 8, 4, 0)),
            (RaceSession.Type.QUALIFYING, datetime(2026, 3, 7, 6, 0)),
            (RaceSession.Type.PRACTICE_1, datetime(2026, 3, 6, 3, 30)),
        ]
        for session_type, starts_at in sessions:
            RaceSession.objects.create(
                grand_prix=self.grand_prix,
                session_type=session_type,
                starts_at=timezone.make_aware(starts_at),
            )

        response = self.client.get(
            reverse(
                "grand-prix-detail",
                kwargs={"year": 2026, "round_number": 1},
            )
        )
        html = response.content.decode()

        self.assertEqual(html.count("data-schedule-day"), 3)
        self.assertLess(html.index("Practice 1"), html.index("Qualifying"))
        self.assertLess(html.index("Qualifying"), html.index(">Race<"))
        self.assertContains(response, "Пятница")
        self.assertContains(response, "Суббота")
        self.assertContains(response, "Воскресенье")
        self.assertContains(response, "Сессия 03")

    def test_home_renders_the_complete_season_with_country_flags(self):
        self.grand_prix.circuit.country = "Australia"
        self.grand_prix.circuit.save(update_fields=["country"])
        for round_number in range(2, 24):
            make_grand_prix(
                season=self.grand_prix.season,
                circuit=make_circuit(f"track-{round_number}"),
                round_number=round_number,
            )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.context["events"].count(), 23)
        self.assertEqual(response.content.decode().count("data-event-card"), 23)
        self.assertContains(response, "Календарь сезона")
        self.assertNotContains(response, "Линия сезона")
        self.assertContains(response, 'class="country-flag"', html=False)
        self.assertContains(response, "🇦🇺")

    def test_team_logos_are_local_and_visible_in_standings(self):
        constructor = Constructor.objects.create(
            external_id="mclaren",
            name="McLaren",
            nationality="British",
        )
        ConstructorStanding.objects.create(
            season=self.grand_prix.season,
            constructor=constructor,
            position=1,
            points=100,
        )

        response = self.client.get(reverse("standings"))

        self.assertContains(
            response,
            'src="/static/images/teams/mclaren.svg"',
            html=False,
        )
        self.assertContains(response, 'class="team-logo"', html=False)
        self.assertContains(response, 'alt=""', html=False)
        self.assertTrue(
            (Path(settings.BASE_DIR) / "static/images/teams/mclaren.svg").is_file()
        )

    def test_every_2026_constructor_maps_to_a_unique_local_team_asset(self):
        expected = {
            "alpine": "images/teams/alpine.svg",
            "aston_martin": "images/teams/aston_martin.jpg",
            "audi": "images/teams/audi.svg",
            "cadillac": "images/teams/cadillac.png",
            "ferrari": "images/teams/ferrari.svg",
            "haas": "images/teams/haas.svg",
            "mclaren": "images/teams/mclaren.svg",
            "mercedes": "images/teams/mercedes.svg",
            "rb": "images/teams/rb.svg",
            "red_bull": "images/teams/red_bull.png",
            "williams": "images/teams/williams.svg",
        }

        self.assertEqual(TEAM_LOGOS, expected)
        self.assertEqual(len(set(TEAM_LOGOS.values())), 11)
        for asset in expected.values():
            with self.subTest(asset=asset):
                self.assertTrue((Path(settings.BASE_DIR) / "static" / asset).is_file())
