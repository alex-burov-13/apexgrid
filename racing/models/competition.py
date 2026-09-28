from django.core.validators import RegexValidator
from django.db import models

from racing.models.calendar import GrandPrix, Season


color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Цвет должен быть записан в формате #RRGGBB.",
)


class Driver(models.Model):
    external_id = models.SlugField("Идентификатор API", max_length=80, unique=True)
    given_name = models.CharField("Имя", max_length=80)
    family_name = models.CharField("Фамилия", max_length=80)
    code = models.CharField("Код", max_length=3, blank=True)
    permanent_number = models.PositiveSmallIntegerField(
        "Номер",
        null=True,
        blank=True,
    )
    nationality = models.CharField("Национальность", max_length=80, blank=True)

    class Meta:
        ordering = ("family_name", "given_name")
        verbose_name = "Пилот"
        verbose_name_plural = "Пилоты"

    @property
    def display_name(self) -> str:
        return f"{self.given_name} {self.family_name}".strip()

    def __str__(self) -> str:
        return self.display_name


class Constructor(models.Model):
    external_id = models.SlugField("Идентификатор API", max_length=80, unique=True)
    name = models.CharField("Название", max_length=120)
    nationality = models.CharField("Национальность", max_length=80, blank=True)
    color = models.CharField(
        "Цвет",
        max_length=7,
        default="#FFFFFF",
        validators=[color_validator],
    )

    class Meta:
        ordering = ("name",)
        verbose_name = "Команда"
        verbose_name_plural = "Команды"

    def __str__(self) -> str:
        return self.name


class RaceResult(models.Model):
    grand_prix = models.ForeignKey(
        GrandPrix,
        on_delete=models.CASCADE,
        related_name="results",
        verbose_name="Grand Prix",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.PROTECT,
        related_name="results",
        verbose_name="Пилот",
    )
    constructor = models.ForeignKey(
        Constructor,
        on_delete=models.PROTECT,
        related_name="results",
        verbose_name="Команда",
    )
    position = models.PositiveSmallIntegerField("Позиция", null=True, blank=True)
    grid_position = models.PositiveSmallIntegerField("Стартовая позиция", default=0)
    points = models.DecimalField("Очки", max_digits=7, decimal_places=2, default=0)
    status = models.CharField("Статус", max_length=100, blank=True)
    time_text = models.CharField("Время", max_length=80, blank=True)
    gap = models.CharField("Отставание", max_length=80, blank=True)
    fastest_lap_time = models.CharField("Быстрый круг", max_length=40, blank=True)
    fastest_lap_rank = models.PositiveSmallIntegerField(
        "Место быстрого круга",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("position", "driver__family_name")
        constraints = [
            models.UniqueConstraint(
                fields=("grand_prix", "driver"),
                name="unique_driver_result_per_grand_prix",
            )
        ]
        verbose_name = "Результат гонки"
        verbose_name_plural = "Результаты гонок"

    def __str__(self) -> str:
        return f"{self.grand_prix.name} · {self.driver.display_name}"


class DriverStanding(models.Model):
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="driver_standings",
        verbose_name="Сезон",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name="standings",
        verbose_name="Пилот",
    )
    constructor = models.ForeignKey(
        Constructor,
        on_delete=models.SET_NULL,
        related_name="driver_standings",
        verbose_name="Команда",
        null=True,
        blank=True,
    )
    position = models.PositiveSmallIntegerField("Позиция")
    points = models.DecimalField("Очки", max_digits=8, decimal_places=2, default=0)
    wins = models.PositiveSmallIntegerField("Победы", default=0)

    class Meta:
        ordering = ("position",)
        constraints = [
            models.UniqueConstraint(
                fields=("season", "driver"),
                name="unique_driver_standing_per_season",
            )
        ]
        verbose_name = "Положение пилота"
        verbose_name_plural = "Положение пилотов"

    def __str__(self) -> str:
        return f"{self.season.year} · P{self.position} · {self.driver.display_name}"


class ConstructorStanding(models.Model):
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="constructor_standings",
        verbose_name="Сезон",
    )
    constructor = models.ForeignKey(
        Constructor,
        on_delete=models.CASCADE,
        related_name="standings",
        verbose_name="Команда",
    )
    position = models.PositiveSmallIntegerField("Позиция")
    points = models.DecimalField("Очки", max_digits=8, decimal_places=2, default=0)
    wins = models.PositiveSmallIntegerField("Победы", default=0)

    class Meta:
        ordering = ("position",)
        constraints = [
            models.UniqueConstraint(
                fields=("season", "constructor"),
                name="unique_constructor_standing_per_season",
            )
        ]
        verbose_name = "Положение команды"
        verbose_name_plural = "Положение команд"

    def __str__(self) -> str:
        return f"{self.season.year} · P{self.position} · {self.constructor.name}"
