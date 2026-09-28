import os
from pathlib import Path

import pytest
from django.core.management import call_command
from playwright.sync_api import sync_playwright


@pytest.fixture(autouse=True)
def demo_snapshot(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("seed_demo", verbosity=0)


def _chrome_executable() -> str | None:
    candidates = [
        os.getenv("PLAYWRIGHT_CHROME_EXECUTABLE"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    return next((path for path in candidates if path and Path(path).is_file()), None)


@pytest.fixture
def browser():
    with sync_playwright() as playwright:
        executable = _chrome_executable()
        options = {"headless": True}
        if executable:
            options["executable_path"] = executable
        try:
            instance = playwright.chromium.launch(**options)
        except Exception as error:
            pytest.skip(f"Для browser smoke недоступен Chromium: {error}")
        yield instance
        instance.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    current_page = context.new_page()
    current_page.set_default_timeout(8_000)
    current_page.set_default_navigation_timeout(10_000)
    yield current_page
    context.close()
