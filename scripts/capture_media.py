#!/usr/bin/env python3
"""Capture reproducible README media from a running ApexGrid instance."""

import argparse
import io
import os
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "media"
CHROME_CANDIDATES = (
    os.getenv("PLAYWRIGHT_CHROME_EXECUTABLE"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
)


def _launch(playwright):
    executable = next(
        (candidate for candidate in CHROME_CANDIDATES if candidate and Path(candidate).is_file()),
        None,
    )
    options = {"headless": True}
    if executable:
        options["executable_path"] = executable
    return playwright.chromium.launch(**options)


def _png_frame(page) -> Image.Image:
    return Image.open(io.BytesIO(page.screenshot(type="png"))).convert("RGB")


def capture(base_url: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    gif_frames: list[Image.Image] = []

    with sync_playwright() as playwright:
        browser = _launch(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "response",
            lambda response: errors.append(f"HTTP {response.status}: {response.url}")
            if response.status >= 400
            else None,
        )

        page.goto(f"{base_url}/", wait_until="networkidle")
        page.screenshot(path=output / "home-desktop.png", full_page=False)
        gif_frames.extend([_png_frame(page)] * 4)

        page.goto(f"{base_url}/grand-prix/2026/16/", wait_until="networkidle")
        page.locator("[data-track-blueprint]").wait_for(state="visible")
        page.locator(".track-stage").screenshot(path=output / "circuit-blueprint.png")
        gif_frames.extend([_png_frame(page)] * 5)
        page.locator("#schedule-heading").scroll_into_view_if_needed()
        gif_frames.extend([_png_frame(page)] * 4)

        page.goto(f"{base_url}/championship/", wait_until="networkidle")
        page.screenshot(path=output / "standings-desktop.png", full_page=False)
        gif_frames.extend([_png_frame(page)] * 5)

        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=1,
            is_mobile=True,
        )
        mobile_page = mobile.new_page()
        mobile_page.goto(f"{base_url}/calendar/", wait_until="networkidle")
        mobile_page.screenshot(path=output / "calendar-mobile.png", full_page=False)
        mobile.close()

        context.close()
        browser.close()

    if errors:
        raise RuntimeError("Browser errors:\n" + "\n".join(errors))
    if not gif_frames:
        raise RuntimeError("No GIF frames were captured.")
    gif_frames[0].save(
        output / "apexgrid-tour.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=220,
        loop=0,
        optimize=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    capture(args.base_url.rstrip("/"), args.output)
    print(f"ApexGrid media captured in {args.output}")


if __name__ == "__main__":
    main()
