# Copyright (c) Hewlett Packard Enterprise, 2026. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Screenshot test: capture the NITA webapp login page.

Self-contained — does not depend on any conftest.py fixtures.
Skipped automatically when playwright is not installed.

Run standalone:
    pytest tests/integration/test_screenshot_login.py -v
"""

import os
import pathlib

import pytest

BASE_URL: str = os.environ.get("NITA_BASE_URL", "http://localhost:8000").rstrip("/")
_SCREENSHOT_DIR = pathlib.Path("ci-screenshots")


@pytest.mark.screenshot
def test_capture_login_page():
    """Navigate to the webapp root and save a full-page screenshot.

    The webapp redirects unauthenticated requests to the login page; this
    test captures whatever the browser renders without attempting to log in.
    The test asserts that a non-empty PNG was written to ci-screenshots/.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed — skipping screenshot test")

    _SCREENSHOT_DIR.mkdir(exist_ok=True)
    dest = _SCREENSHOT_DIR / "login_page.png"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15_000)
        try:
            page.wait_for_load_state("networkidle", timeout=5_000)
        except Exception:
            pass
        page.screenshot(path=str(dest), full_page=True)
        browser.close()

    assert dest.exists(), f"Screenshot was not created at {dest}"
    assert dest.stat().st_size > 0, "Screenshot file is empty"
