from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def validate_geometry(value: object) -> None:
    if not isinstance(value, dict):
        raise ValidationError("Геометрия трассы должна быть объектом JSON.")

    view_box = value.get("viewBox")
    if (
        not isinstance(view_box, list)
        or len(view_box) != 4
        or not all(isinstance(item, (int, float)) for item in view_box)
    ):
        raise ValidationError("Поле viewBox должно содержать четыре числа.")

    path = value.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValidationError("Поле path должно содержать SVG-контур трассы.")

    sectors = value.get("sectors", [])
    if not isinstance(sectors, list):
        raise ValidationError("Поле sectors должно быть списком.")


class Season(models.Model):
    year = models.PositiveSmallIntegerField("Год", unique=True)
    is_current = models.BooleanField("Текущий сезон", default=False)
    starts_on = models.DateField("Начало сезона", null=True, blank=True)
    ends_on = models.DateField("Окончание сезона", null=True, blank=True)
    synced_at = models.DateTimeField("Последнее обновление", null=True, blank=True)

    class Meta:
        ordering = ("-year",)
        verbose_name = "Сезон"
        verbose_name_plural = "Сезоны"

    def __str__(self) -> str:
        return str(self.year)


class Circuit(models.Model):
    class Direction(models.TextChoices):
        CLOCKWISE = "clockwise", "По часовой стрелке"
        COUNTERCLOCKWISE = "counterclockwise", "Против часовой стрелки"
        MIXED = "mixed", "Смешанное направление"

    external_id = models.SlugField("Идентификатор API", max_length=80, unique=True)
    slug = models.SlugField("Адрес", max_length=100, unique=True)
    name = models.CharField("Название", max_length=180)
    locality = models.CharField("Город", max_length=120)
    country = models.CharField("Страна", max_length=120)
    timezone = models.CharField("Часовой пояс", max_length=80, default="UTC")
    length_km = models.DecimalField(
        "Длина круга, км",
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
    )
    turns = models.PositiveSmallIntegerField("Повороты", null=True, blank=True)
    direction = models.CharField(
        "Направление",
        max_length=20,
        choices=Direction.choices,
        blank=True,
    )
    lap_record = models.CharField("Рекорд круга", max_length=40, blank=True)
    lap_record_driver = models.CharField(
        "Обладатель рекорда",
        max_length=140,
        blank=True,
    )
    summary = models.TextField("Краткая справка", blank=True)
    geometry = models.JSONField(
        "Геометрия трассы",
        default=dict,
        validators=[validate_geometry],
    )

    class Meta:
        ordering = ("country", "name")
        verbose_name = "Трасса"
        verbose_name_plural = "Трассы"

    def __str__(self) -> str:
        return self.name


class GrandPrix(models.Model):
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="grand_prix",
        verbose_name="Сезон",
    )
    circuit = models.ForeignKey(
        Circuit,
        on_delete=models.PROTECT,
        related_name="grand_prix",
        verbose_name="Трасса",
    )
    external_id = models.CharField("Идентификатор API", max_length=100, blank=True)
    round_number = models.PositiveSmallIntegerField("Номер этапа")
    name = models.CharField("Название", max_length=180)
    laps = models.PositiveSmallIntegerField("Круги", null=True, blank=True)
    is_sprint = models.BooleanField("Sprint-этап", default=False)
    editorial_summary = models.TextField("Краткая справка", blank=True)

    class Meta:
        ordering = ("season", "round_number")
        constraints = [
            models.UniqueConstraint(
                fields=("season", "round_number"),
                name="unique_round_per_season",
            )
        ]
        verbose_name = "Этап Grand Prix"
        verbose_name_plural = "Этапы Grand Prix"

    def __str__(self) -> str:
        return f"{self.season.year} · {self.name}"

    @property
    def race_distance_km(self) -> Decimal | None:
        if self.laps is None or self.circuit.length_km is None:
            return None
        return self.circuit.length_km * self.laps

    def computed_status(self, at=None) -> str:
        at = at or timezone.now()
        race = self.sessions.filter(session_type=RaceSession.Type.RACE).first()
        if race is None:
            return "upcoming"

        race_end = race.ends_at or race.starts_at + timedelta(hours=3)
        if at >= race_end:
            return "completed"
        if race.starts_at <= at < race_end:
            return "live"

        next_race = (
            RaceSession.objects.filter(
                grand_prix__season=self.season,
                session_type=RaceSession.Type.RACE,
                starts_at__gt=at,
            )
            .order_by("starts_at", "grand_prix__round_number")
            .first()
        )
        if next_race and next_race.grand_prix_id == self.pk:
            return "next"
        return "upcoming"


class RaceSession(models.Model):
    class Type(models.TextChoices):
        PRACTICE_1 = "practice_1", "Practice 1"
        PRACTICE_2 = "practice_2", "Practice 2"
        PRACTICE_3 = "practice_3", "Practice 3"
        SPRINT_QUALIFYING = "sprint_qualifying", "Sprint Qualifying"
        SPRINT = "sprint", "Sprint"
        QUALIFYING = "qualifying", "Qualifying"
        RACE = "race", "Race"

    grand_prix = models.ForeignKey(
        GrandPrix,
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name="Grand Prix",
    )
    session_type = models.CharField("Тип", max_length=24, choices=Type.choices)
    starts_at = models.DateTimeField("Начало")
    ends_at = models.DateTimeField("Окончание", null=True, blank=True)

    class Meta:
        ordering = ("starts_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("grand_prix", "session_type"),
                name="unique_session_type_per_grand_prix",
            )
        ]
        verbose_name = "Сессия"
        verbose_name_plural = "Сессии"

    def __str__(self) -> str:
        return f"{self.grand_prix.name} · {self.get_session_type_display()}"

    def clean(self) -> None:
        super().clean()
        if self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "Окончание должно быть позже начала."})
