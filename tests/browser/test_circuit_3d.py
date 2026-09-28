import pytest


DETAIL_PATH = "/grand-prix/2026/16/"
TIMEZONE_BOUNDARY_DETAIL_PATH = "/grand-prix/2026/18/"


def _capture_errors(page):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "response",
        lambda response: errors.append(f"HTTP {response.status}: {response.url}")
        if response.status >= 400
        else None,
    )
    return errors


@pytest.mark.django_db(transaction=True)
def test_technical_blueprint_renders_three_sectors_and_legend(page, live_server):
    errors = _capture_errors(page)

    page.goto(f"{live_server.url}{DETAIL_PATH}", wait_until="networkidle")

    blueprint = page.locator("[data-track-blueprint]")
    assert blueprint.is_visible()
    assert blueprint.locator(".track-blueprint__sector").count() == 3
    assert blueprint.locator(".track-blueprint__legend").is_visible()
    assert "Старт / финиш" in blueprint.inner_text()
    assert page.locator("[data-circuit-canvas]").count() == 0
    assert errors == []


@pytest.mark.django_db(transaction=True)
def test_schedule_is_a_top_to_bottom_chronological_timeline(page, live_server):
    errors = _capture_errors(page)

    page.goto(f"{live_server.url}{DETAIL_PATH}", wait_until="networkidle")

    sessions = page.locator(".schedule-session")
    names = sessions.locator(".schedule-session__copy strong").all_inner_texts()
    positions = [box["y"] for box in (item.bounding_box() for item in sessions.all()) if box]
    assert len(names) >= 4
    assert names[-1] == "Race"
    assert positions == sorted(positions)
    assert page.locator("[data-schedule-day]").count() >= 2
    assert errors == []


@pytest.mark.django_db(transaction=True)
def test_grand_prix_typography_does_not_overflow_mobile_viewport(browser, live_server):
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    page = context.new_page()
    errors = _capture_errors(page)

    page.goto(f"{live_server.url}{DETAIL_PATH}", wait_until="networkidle")

    title = page.locator(".detail__title")
    box = title.bounding_box()
    assert box is not None
    assert box["x"] >= 0
    assert box["x"] + box["width"] <= 390
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert errors == []
    context.close()


@pytest.mark.django_db(transaction=True)
def test_homepage_hero_typography_does_not_overflow_mobile_viewport(browser, live_server):
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    page = context.new_page()
    errors = _capture_errors(page)

    page.goto(live_server.url, wait_until="networkidle")

    title = page.locator("#next-race-heading")
    box = title.bounding_box()
    assert box is not None
    assert box["x"] >= 0
    assert box["x"] + box["width"] <= 390
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert errors == []
    context.close()


@pytest.mark.django_db(transaction=True)
def test_compact_schedule_times_stay_compact_after_timezone_javascript(page, live_server):
    errors = _capture_errors(page)

    page.goto(f"{live_server.url}{DETAIL_PATH}", wait_until="networkidle")

    first_time = page.locator(".schedule-session time").first
    assert first_time.inner_text().count("·") == 0
    assert first_time.inner_text().endswith("UTC")

    page.locator("[data-timezone-select]").select_option("Europe/Moscow")
    page.wait_for_function(
        "document.querySelector('.schedule-session time').textContent.trim().endsWith('МСК')"
    )
    rendered = first_time.inner_text().strip()
    assert rendered.endswith("МСК")
    assert rendered.count("·") == 0
    assert len(rendered.split()[0]) == 5
    assert errors == []


@pytest.mark.django_db(transaction=True)
def test_timezone_switch_reloads_and_regroups_sessions_across_midnight(page, live_server):
    errors = _capture_errors(page)

    page.goto(
        f"{live_server.url}{TIMEZONE_BOUNDARY_DETAIL_PATH}",
        wait_until="networkidle",
    )

    practice_two = page.locator(".schedule-session", has_text="Practice 2")
    utc_day = practice_two.locator("xpath=ancestor::li[@data-schedule-day]")
    assert utc_day.locator(".schedule-day__header span").text_content() == "Пятница"
    assert practice_two.locator("time").inner_text().strip() == "21:00 UTC"

    with page.expect_navigation(wait_until="networkidle"):
        page.locator("[data-timezone-select]").select_option("Europe/Moscow")

    practice_two = page.locator(".schedule-session", has_text="Practice 2")
    moscow_day = practice_two.locator("xpath=ancestor::li[@data-schedule-day]")
    assert moscow_day.get_attribute("data-schedule-day") == "2026-10-24"
    assert moscow_day.locator(".schedule-day__header span").text_content() == "Суббота"
    assert practice_two.locator("time").inner_text().strip() == "00:00 МСК"
    assert errors == []


@pytest.mark.django_db(transaction=True)
def test_team_logos_load_from_local_static_assets(page, live_server):
    errors = _capture_errors(page)

    page.goto(f"{live_server.url}/championship/", wait_until="networkidle")

    logos = page.locator("img.team-logo")
    assert logos.count() >= 11
    broken = logos.evaluate_all(
        "items => items.filter((item) => !item.complete || item.naturalWidth === 0)"
        ".map((item) => item.src)"
    )
    assert broken == []
    assert logos.evaluate_all(
        "items => items.every((item) => new URL(item.src).origin === location.origin)"
    )
    assert errors == []
