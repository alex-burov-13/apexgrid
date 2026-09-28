from zoneinfo import ZoneInfo

from django import template
from django.utils import timezone


register = template.Library()


SESSION_NAMES = {
    "practice_1": "Practice 1",
    "practice_2": "Practice 2",
    "practice_3": "Practice 3",
    "sprint_qualifying": "Sprint Qualifying",
    "sprint": "Sprint",
    "qualifying": "Qualifying",
    "race": "Race",
}


COUNTRY_FLAGS = {
    "Australia": "🇦🇺",
    "Austria": "🇦🇹",
    "Azerbaijan": "🇦🇿",
    "Belgium": "🇧🇪",
    "Brazil": "🇧🇷",
    "Canada": "🇨🇦",
    "China": "🇨🇳",
    "Hungary": "🇭🇺",
    "Italy": "🇮🇹",
    "Japan": "🇯🇵",
    "Malaysia": "🇲🇾",
    "Mexico": "🇲🇽",
    "Monaco": "🇲🇨",
    "Netherlands": "🇳🇱",
    "Qatar": "🇶🇦",
    "Singapore": "🇸🇬",
    "Spain": "🇪🇸",
    "UAE": "🇦🇪",
    "UK": "🇬🇧",
    "USA": "🇺🇸",
}


TEAM_LOGOS = {
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


@register.filter
def session_name(value: str) -> str:
    return SESSION_NAMES.get(value, value)


@register.filter
def country_flag(value: str) -> str:
    return COUNTRY_FLAGS.get(value, "🏁")


@register.filter
def team_logo(value: str) -> str:
    return TEAM_LOGOS.get(value, "favicon.svg")


@register.filter
def display_time(value, timezone_name: str = "UTC") -> str:
    if value is None:
        return "Нет данных"
    aware = value if timezone.is_aware(value) else timezone.make_aware(value)
    try:
        zone = ZoneInfo(timezone_name)
    except (KeyError, TypeError, ValueError):
        zone = ZoneInfo("UTC")
        timezone_name = "UTC"
    label = "МСК" if timezone_name == "Europe/Moscow" else timezone_name
    return aware.astimezone(zone).strftime(f"%d.%m.%Y · %H:%M {label}")


@register.filter
def display_clock(value, timezone_name: str = "UTC") -> str:
    if value is None:
        return "Нет данных"
    aware = value if timezone.is_aware(value) else timezone.make_aware(value)
    try:
        zone = ZoneInfo(timezone_name)
    except (KeyError, TypeError, ValueError):
        zone = ZoneInfo("UTC")
        timezone_name = "UTC"
    label = "МСК" if timezone_name == "Europe/Moscow" else timezone_name
    return aware.astimezone(zone).strftime(f"%H:%M {label}")


@register.filter
def direction_name(value: str) -> str:
    return {
        "clockwise": "По часовой стрелке",
        "counterclockwise": "Против часовой стрелки",
        "mixed": "Смешанное направление",
    }.get(value, "Нет данных")
