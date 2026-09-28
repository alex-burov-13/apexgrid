import time
from collections.abc import Callable, Mapping
from typing import Any

import requests

from integrations.jolpica.errors import (
    JolpicaInvalidPayload,
    JolpicaRateLimited,
    JolpicaUnavailable,
)
from integrations.jolpica.mappers import (
    map_constructor_standings,
    map_driver_standings,
    map_results,
    map_schedule,
)
from integrations.jolpica.schemas import (
    ConstructorStandingPayload,
    DriverStandingPayload,
    EventPayload,
    ResultPayload,
)


class JolpicaClient:
    max_attempts = 3
    page_limit = 100
    max_retry_after_seconds = 2.0

    def __init__(
        self,
        base_url: str,
        user_agent: str,
        timeout: tuple[float, float],
        *,
        session: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json",
            }
        )
        self.sleep = sleep

    def get_schedule(self, season: int) -> tuple[EventPayload, ...]:
        return self._mapped_pages(f"/{season}.json", map_schedule)

    def get_results(self, season: int) -> tuple[ResultPayload, ...]:
        return self._mapped_pages(f"/{season}/results.json", map_results)

    def get_driver_standings(
        self,
        season: int,
    ) -> tuple[DriverStandingPayload, ...]:
        return self._mapped_pages(
            f"/{season}/driverstandings.json",
            map_driver_standings,
        )

    def get_constructor_standings(
        self,
        season: int,
    ) -> tuple[ConstructorStandingPayload, ...]:
        return self._mapped_pages(
            f"/{season}/constructorstandings.json",
            map_constructor_standings,
        )

    def _mapped_pages(self, path: str, mapper: Callable) -> tuple:
        mapped: list[Any] = []
        for payload in self._pages(path):
            mapped.extend(mapper(payload))
        return tuple(mapped)

    def _pages(self, path: str):
        offset = 0
        while True:
            payload = self._get_json(
                path,
                params={"limit": self.page_limit, "offset": offset},
            )
            yield payload

            mr_data = payload.get("MRData")
            if not isinstance(mr_data, Mapping):
                raise JolpicaInvalidPayload("MRData: ожидался объект.")
            if "total" not in mr_data:
                return
            try:
                total = int(mr_data["total"])
                returned_limit = int(mr_data.get("limit", self.page_limit))
                response_offset = int(mr_data.get("offset", offset))
            except (TypeError, ValueError) as error:
                raise JolpicaInvalidPayload(
                    "MRData: неверные параметры пагинации."
                ) from error
            if total <= response_offset + max(returned_limit, 1):
                return
            offset = response_offset + max(returned_limit, 1)

    def _get_json(self, path: str, *, params: dict[str, int]) -> Mapping[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_status: int | None = None
        for attempt in range(self.max_attempts):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as error:
                if attempt == self.max_attempts - 1:
                    raise JolpicaUnavailable("Jolpica API недоступен.") from error
                self.sleep(0.25 * (2**attempt))
                continue

            last_status = response.status_code
            if response.status_code == 429:
                if attempt == self.max_attempts - 1:
                    raise JolpicaRateLimited(
                        "Jolpica API временно ограничил частоту запросов."
                    )
                retry_after = response.headers.get("Retry-After", "0.25")
                try:
                    delay = float(retry_after)
                except (TypeError, ValueError):
                    delay = 0.25
                self.sleep(min(max(delay, 0.0), self.max_retry_after_seconds))
                continue

            if 500 <= response.status_code < 600:
                if attempt == self.max_attempts - 1:
                    raise JolpicaUnavailable(
                        f"Jolpica API вернул HTTP {response.status_code}."
                    )
                self.sleep(0.25 * (2**attempt))
                continue

            if response.status_code >= 400:
                raise JolpicaUnavailable(
                    f"Jolpica API вернул HTTP {response.status_code}."
                )

            try:
                payload = response.json()
            except (requests.JSONDecodeError, ValueError) as error:
                raise JolpicaInvalidPayload(
                    "Jolpica API вернул некорректный JSON."
                ) from error
            if not isinstance(payload, Mapping):
                raise JolpicaInvalidPayload("Корень ответа Jolpica должен быть объектом.")
            return payload

        raise JolpicaUnavailable(
            f"Jolpica API недоступен (последний HTTP {last_status})."
        )
