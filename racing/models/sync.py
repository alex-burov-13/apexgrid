from django.db import models


class SyncRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Выполняется"
        SUCCESS = "success", "Успешно"
        FAILED = "failed", "Ошибка"

    class Initiator(models.TextChoices):
        CLI = "cli", "Командная строка"
        ADMIN = "admin", "Django Admin"

    season_year = models.PositiveSmallIntegerField("Сезон")
    initiated_by = models.CharField(
        "Инициатор",
        max_length=16,
        choices=Initiator.choices,
    )
    status = models.CharField(
        "Статус",
        max_length=16,
        choices=Status.choices,
        default=Status.RUNNING,
    )
    started_at = models.DateTimeField("Начало", auto_now_add=True)
    finished_at = models.DateTimeField("Окончание", null=True, blank=True)
    created_count = models.PositiveIntegerField("Создано", default=0)
    updated_count = models.PositiveIntegerField("Обновлено", default=0)
    results_count = models.PositiveIntegerField("Результаты", default=0)
    standings_count = models.PositiveIntegerField("Положения", default=0)
    error_message = models.TextField("Сообщение об ошибке", blank=True)

    class Meta:
        ordering = ("-started_at",)
        verbose_name = "Запуск синхронизации"
        verbose_name_plural = "Запуски синхронизации"

    def __str__(self) -> str:
        return f"{self.season_year} · {self.get_status_display()}"
