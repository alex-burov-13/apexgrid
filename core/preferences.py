from dataclasses import dataclass
from functools import lru_cache
from typing import Any, MutableMapping
from zoneinfo import available_timezones


DEFAULT_TIMEZONE = "UTC"
DEFAULT_CALENDAR_VIEW = "cards"
CALENDAR_VIEWS = frozenset({"cards", "compact"})
MAX_FAVORITES = 50


@dataclass(frozen=True, slots=True)
class UserPreferences:
    timezone: str
    calendar_view: str
    favorite_grand_prix_ids: tuple[int, ...]
    last_grand_prix_id: int | None


@lru_cache(maxsize=1)
def _timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def _positive_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _mark_modified(session: MutableMapping[str, Any]) -> None:
    if hasattr(session, "modified"):
        session.modified = True


def get_preferences(session: MutableMapping[str, Any]) -> UserPreferences:
    timezone_name = session.get("timezone", DEFAULT_TIMEZONE)
    if timezone_name not in _timezones():
        timezone_name = DEFAULT_TIMEZONE

    calendar_view = session.get("calendar_view", DEFAULT_CALENDAR_VIEW)
    if calendar_view not in CALENDAR_VIEWS:
        calendar_view = DEFAULT_CALENDAR_VIEW

    raw_favorites = session.get("favorite_grand_prix_ids", [])
    if not isinstance(raw_favorites, (list, tuple)):
        raw_favorites = []
    favorites = tuple(
        dict.fromkeys(
            item for item in raw_favorites if _positive_integer(item)
        )
    )[-MAX_FAVORITES:]

    raw_last = session.get("last_grand_prix_id")
    last_grand_prix_id = raw_last if _positive_integer(raw_last) else None

    return UserPreferences(
        timezone=timezone_name,
        calendar_view=calendar_view,
        favorite_grand_prix_ids=favorites,
        last_grand_prix_id=last_grand_prix_id,
    )


def set_timezone(session: MutableMapping[str, Any], timezone_name: str) -> None:
    if timezone_name not in _timezones():
        raise ValueError("Неизвестный часовой пояс.")
    session["timezone"] = timezone_name
    _mark_modified(session)


def set_calendar_view(session: MutableMapping[str, Any], view_name: str) -> None:
    session["calendar_view"] = (
        view_name if view_name in CALENDAR_VIEWS else DEFAULT_CALENDAR_VIEW
    )
    _mark_modified(session)


def toggle_favorite(
    session: MutableMapping[str, Any],
    grand_prix_id: int,
) -> bool:
    if not _positive_integer(grand_prix_id):
        raise ValueError("Идентификатор этапа должен быть положительным числом.")

    favorites = list(get_preferences(session).favorite_grand_prix_ids)
    if grand_prix_id in favorites:
        favorites.remove(grand_prix_id)
        is_favorite = False
    else:
        favorites.append(grand_prix_id)
        favorites = favorites[-MAX_FAVORITES:]
        is_favorite = True

    session["favorite_grand_prix_ids"] = favorites
    _mark_modified(session)
    return is_favorite


def remember_grand_prix(
    session: MutableMapping[str, Any],
    grand_prix_id: int,
) -> None:
    if not _positive_integer(grand_prix_id):
        raise ValueError("Идентификатор этапа должен быть положительным числом.")
    session["last_grand_prix_id"] = grand_prix_id
    _mark_modified(session)
