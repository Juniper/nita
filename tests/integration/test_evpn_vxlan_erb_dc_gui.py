# Copyright (c) Hewlett Packard Enterprise, 2026. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Browser-based (Playwright) GUI integration tests for the NITA Webapp.

These tests exercise the same functional areas as the REST API tests in
``test_evpn_vxlan_erb_dc_integration.py`` but interact through the browser
GUI instead of the API.

Layout of the webapp GUI
------------------------
The main shell page (``/``) renders a two-panel layout with a tree on the
left and a content pane on the right.  The inner pages are standalone HTML
documents loaded into the content pane via jQuery AJAX.  These sub-pages are
also reachable directly by URL, which is how these tests exercise them — it
avoids the complexity of scripting cross-frame AJAX navigation.

Playwright setup
----------------
A single Playwright ``BrowserContext`` is created for the test session,
logged in once via the Django admin login form, and shared across all tests.
Each individual test receives a fresh ``Page`` object (so tests are isolated
from each other's navigation state) but shares the same session cookies.

Playwright is an optional dependency for local development; if it is not
importable the entire module is skipped automatically.

Prerequisites (same as the API tests):
  • ``NITA_BASE_URL``  — webapp URL           (default: http://localhost:8000)
  • ``NITA_USER``      — Django superuser      (default: vagrant)
  • ``NITA_PASS``      — Django superuser pass (default: vagrant123)
  • ``EVPN_FIXTURE_DIR`` — directory with fixture files
"""

import pathlib
import uuid

import pytest
import requests

# Skip the entire module if Playwright is not installed.
playwright_sync = pytest.importorskip(
    "playwright.sync_api",
    reason="playwright not installed — skipping GUI tests",
)

from playwright.sync_api import BrowserContext, Page, sync_playwright  # noqa: E402

from tests.integration.conftest import BASE_URL, FIXTURE_DIR, NITA_PASS, NITA_USER

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_LAUNCH_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"]
_LOGIN_URL = f"{BASE_URL}/admin/login/"
_DEFAULT_TIMEOUT = 15_000  # ms


# ---------------------------------------------------------------------------
# Session-scoped Playwright fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def _pw_browser():
    """Start Playwright and launch a headless Chromium browser for the session."""
    pw = sync_playwright().start()
    browser = pw.chromium.launch(args=_LAUNCH_ARGS)
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture(scope="session")
def pw_context(_pw_browser):
    """Return a logged-in ``BrowserContext`` shared across the whole session.

    Logs in once via the Django admin login form; subsequent tests reuse the
    resulting session cookie.
    """
    context = _pw_browser.new_context()
    page = context.new_page()
    try:
        page.goto(f"{_LOGIN_URL}?next=/", wait_until="domcontentloaded", timeout=_DEFAULT_TIMEOUT)
        page.fill("#id_username", NITA_USER)
        page.fill("#id_password", NITA_PASS)
        # Use expect_navigation so we wait for the redirect after submit, not
        # for networkidle (the index page has ongoing AJAX tree calls).
        with page.expect_navigation(timeout=_DEFAULT_TIMEOUT):
            page.click("input[type=submit]")
        assert "/admin/login/" not in page.url, (
            f"Login failed — still on login page.  URL: {page.url}"
        )
    finally:
        page.close()
    yield context
    context.close()


@pytest.fixture
def gui_page(pw_context: BrowserContext) -> Page:
    """Provide a fresh ``Page`` (with shared session cookies) for each test."""
    page = pw_context.new_page()
    yield page
    page.close()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


_NETWORKIDLE_TIMEOUT = 8_000  # ms — best-effort; the page may have ongoing XHR


def _goto(page: Page, path: str, *, timeout: int = _DEFAULT_TIMEOUT) -> None:
    """Navigate to an absolute path, wait for DOMContentLoaded then best-effort networkidle."""
    page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded", timeout=timeout)
    try:
        page.wait_for_load_state("networkidle", timeout=_NETWORKIDLE_TIMEOUT)
    except Exception:
        pass  # networkidle is best-effort; some pages have ongoing XHR polling


# ===========================================================================
# Section 1 — Authentication
# ===========================================================================


@pytest.mark.gui
def test_unauthenticated_visit_redirects_to_login():
    """Visiting the main page without a session must redirect to the login page."""
    # Use a fresh context (no cookies) to simulate an anonymous visitor.
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=_LAUNCH_ARGS)
        context = browser.new_context()
        page = context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=_DEFAULT_TIMEOUT)
        try:
            page.wait_for_load_state("networkidle", timeout=5_000)
        except Exception:
            pass
        assert "/admin/login/" in page.url, (
            f"Expected redirect to /admin/login/, got: {page.url}"
        )
        context.close()
        browser.close()


@pytest.mark.gui
def test_login_bad_credentials_shows_error_message():
    """Submitting wrong credentials must show an error, not redirect away."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=_LAUNCH_ARGS)
        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{_LOGIN_URL}?next=/", wait_until="domcontentloaded", timeout=_DEFAULT_TIMEOUT)
        page.fill("#id_username", "wrong_user")
        page.fill("#id_password", "wrong_pass")
        page.click("input[type=submit]")
        page.wait_for_load_state("networkidle", timeout=_DEFAULT_TIMEOUT)
        # Must remain on the login page
        assert "/admin/login/" in page.url
        # Django shows an error paragraph on bad credentials
        error_text = page.content()
        assert (
            "Please enter the correct" in error_text
            or "Invalid" in error_text
            or "errornote" in error_text
        ), "Expected an error message on the login page"
        context.close()
        browser.close()


# ===========================================================================
# Section 2 — Campus Type (Project) pages
# ===========================================================================


@pytest.mark.gui
def test_campus_type_mgmt_page_loads(gui_page: Page):
    """GET /campustype/ must return a page that includes the management heading."""
    _goto(gui_page, "/campustype/")
    content = gui_page.content()
    assert "Management" in content, "Campus type management page did not load"


@pytest.mark.gui
def test_campus_type_visible_in_list(gui_page: Page, evpn_campus_type_id: int):
    """The evpn_vxlan_erb_dc_1.3 type must appear in the campus type table."""
    _goto(gui_page, "/campustype/")
    # Wait for the table to be rendered (django_tables2 renders synchronously)
    gui_page.wait_for_selector("table", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    assert "evpn_vxlan_erb_dc_1.3" in content, (
        "evpn_vxlan_erb_dc_1.3 not found in campus type management page"
    )


@pytest.mark.gui
def test_campus_type_detail_shows_correct_name(
    gui_page: Page, evpn_campus_type_id: int
):
    """GET /campustype/{id}/ must show the correct campus type name."""
    _goto(gui_page, f"/campustype/{evpn_campus_type_id}/")
    gui_page.wait_for_selector("table", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    assert "evpn_vxlan_erb_dc_1.3" in content, (
        "Campus type name not found on detail page"
    )


@pytest.mark.gui
def test_campus_type_detail_shows_description(
    gui_page: Page, evpn_campus_type_id: int
):
    """GET /campustype/{id}/ must include the correct description."""
    _goto(gui_page, f"/campustype/{evpn_campus_type_id}/")
    gui_page.wait_for_selector("table", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    assert "EVPN VLXAN ERB Data Center" in content, (
        "Campus type description not found on detail page"
    )


@pytest.mark.gui
def test_campus_type_detail_shows_actions_section(
    gui_page: Page, evpn_campus_type_id: int
):
    """The campus type detail page must include an Actions section."""
    _goto(gui_page, f"/campustype/{evpn_campus_type_id}/")
    # The template renders an "Actions" h3 heading when actions exist
    gui_page.wait_for_selector("#actions-by-campus-type", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    assert "Actions" in content


@pytest.mark.gui
def test_campus_type_detail_shows_build_action(
    gui_page: Page, evpn_campus_type_id: int
):
    """The actions table must include a 'Build' action."""
    _goto(gui_page, f"/campustype/{evpn_campus_type_id}/")
    gui_page.wait_for_selector("#actions-by-campus-type", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    assert "Build" in content, "Build action not found in campus type detail page"


@pytest.mark.gui
def test_campus_type_detail_shows_test_action(
    gui_page: Page, evpn_campus_type_id: int
):
    """The actions table must include a 'Test' action."""
    _goto(gui_page, f"/campustype/{evpn_campus_type_id}/")
    gui_page.wait_for_selector("#actions-by-campus-type", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    assert "Test" in content, "Test action not found in campus type detail page"


# ===========================================================================
# Section 3 — Campus Network list and detail
# ===========================================================================


@pytest.mark.gui
def test_campus_network_mgmt_page_loads(gui_page: Page):
    """GET /campusnetwork/ must return the network management page."""
    _goto(gui_page, "/campusnetwork/")
    content = gui_page.content()
    assert "Management" in content, "Campus network management page did not load"


@pytest.mark.gui
def test_campus_network_appears_in_list(gui_page: Page, evpn_network: dict):
    """The newly created network must appear in the campus network table."""
    _goto(gui_page, "/campusnetwork/")
    gui_page.wait_for_selector("table", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    assert evpn_network["name"] in content, (
        f"Network '{evpn_network['name']}' not found in management page"
    )


@pytest.mark.gui
def test_campus_network_detail_page_loads(gui_page: Page, evpn_network: dict):
    """GET /campusnetwork/{id}/ must return the network detail shell (tabs)."""
    _goto(gui_page, f"/campusnetwork/{evpn_network['id']}/")
    # The campus_network.html template renders tab links; check for Summary tab
    content = gui_page.content()
    assert "Summary" in content, "Network detail page (tabs) did not load"


@pytest.mark.gui
def test_campus_network_summary_shows_name(gui_page: Page, evpn_network: dict):
    """GET /campus_network/{id}/summary/ must display the network name."""
    _goto(gui_page, f"/campus_network/{evpn_network['id']}/summary/")
    gui_page.wait_for_selector("table", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    assert evpn_network["name"] in content, (
        f"Network name '{evpn_network['name']}' not found on summary page"
    )


@pytest.mark.gui
def test_campus_network_summary_shows_description(
    gui_page: Page, evpn_network: dict
):
    """The summary page must include the network description."""
    _goto(gui_page, f"/campus_network/{evpn_network['id']}/summary/")
    gui_page.wait_for_selector("table", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    assert "EVPN DC1 integration test network" in content, (
        "Network description not found on summary page"
    )


@pytest.mark.gui
def test_campus_network_summary_shows_campus_type_name(
    gui_page: Page, evpn_network: dict
):
    """The summary page must show the associated campus type name."""
    _goto(gui_page, f"/campus_network/{evpn_network['id']}/summary/")
    gui_page.wait_for_selector("table", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    assert "evpn_vxlan_erb_dc_1.3" in content, (
        "Campus type name not found on network summary page"
    )


@pytest.mark.gui
def test_campus_network_summary_shows_actions_table(
    gui_page: Page, evpn_network: dict
):
    """The summary page must show the action list for the campus type."""
    _goto(gui_page, f"/campus_network/{evpn_network['id']}/summary/")
    # The template renders an <h3>Actions</h3> and the action table when present
    gui_page.wait_for_selector("#action-list", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    assert "Actions" in content


@pytest.mark.gui
def test_campus_network_summary_shows_status(gui_page: Page, evpn_network: dict):
    """The summary page must show the network status."""
    _goto(gui_page, f"/campus_network/{evpn_network['id']}/summary/")
    gui_page.wait_for_selector("table", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    # The network is created with status "Initialized"
    assert "Initialized" in content, "Status 'Initialized' not found on summary page"


# ===========================================================================
# Section 4 — Configuration (workbook) page
# ===========================================================================


@pytest.mark.gui
def test_configuration_page_loads(gui_page: Page, evpn_network: dict):
    """GET /campus_network/{id}/configuration_view/ must load the config page."""
    _goto(gui_page, f"/campus_network/{evpn_network['id']}/configuration_view/")
    # The page has Import / Export / Save / Delete buttons
    gui_page.wait_for_selector("#import-config-data", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    assert "Import" in content


@pytest.mark.gui
def test_configuration_page_shows_no_data_before_upload(
    gui_page: Page, evpn_network: dict
):
    """Before any upload the configuration page must report no data found."""
    _goto(gui_page, f"/campus_network/{evpn_network['id']}/configuration_view/")
    # The AJAX GET to /upload_file/ fills #grid; on empty DB it inserts the
    # "No configuration data found" message.  Wait for the loader to disappear.
    gui_page.wait_for_selector("#import-config-data", timeout=_DEFAULT_TIMEOUT)
    # Wait for the loading overlay to hide (inserted by page JS after AJAX completes)
    try:
        gui_page.wait_for_selector(
            "#loading_overlay[style*='display: none'], #loading_overlay:not([style])",
            timeout=10_000,
        )
    except Exception:
        pass  # overlay state might not be set via inline style on all paths
    content = gui_page.content()
    # Either explicit message or an empty grid is acceptable
    assert (
        "No configuration data found" in content
        or gui_page.locator("#grid").inner_text() == ""
    ), "Expected empty/no-data state before any workbook upload"


@pytest.mark.gui
def test_workbook_upload_success_modal_appears(gui_page: Page, evpn_network: dict):
    """Uploading dc1_data.xlsx via the GUI Import button must show a success modal."""
    xlsx_path = FIXTURE_DIR / "dc1_data.xlsx"
    _goto(gui_page, f"/campus_network/{evpn_network['id']}/configuration_view/")
    gui_page.wait_for_selector("#import-config-data", timeout=_DEFAULT_TIMEOUT)

    # 1. Open the upload modal
    gui_page.click("#import-config-data")
    gui_page.locator("#upload-modal").wait_for(state="visible", timeout=5_000)

    # 2. Attach the file to the hidden file input
    gui_page.set_input_files("#file_upload", str(xlsx_path))

    # 3. Click the modal's Import/submit button
    gui_page.click("#import")

    # 4. Wait for the success confirmation modal
    gui_page.locator("#upload-status-modal").wait_for(state="visible", timeout=30_000)
    content = gui_page.content()
    assert "imported successfully" in content, (
        "Workbook upload success message not found"
    )


@pytest.mark.gui
def test_workbook_upload_populates_grid(gui_page: Page, evpn_network: dict):
    """After uploading the workbook the SlickGrid must contain data rows."""
    xlsx_path = FIXTURE_DIR / "dc1_data.xlsx"
    _goto(gui_page, f"/campus_network/{evpn_network['id']}/configuration_view/")
    gui_page.wait_for_selector("#import-config-data", timeout=_DEFAULT_TIMEOUT)

    gui_page.click("#import-config-data")
    gui_page.locator("#upload-modal").wait_for(state="visible", timeout=5_000)
    gui_page.set_input_files("#file_upload", str(xlsx_path))
    gui_page.click("#import")

    # Wait for the success modal, then dismiss it
    gui_page.locator("#upload-status-modal").wait_for(state="visible", timeout=30_000)
    # Close the success modal by clicking OK
    gui_page.locator("#upload-status-modal button[data-dismiss='modal']").first.click()
    gui_page.locator("#upload-status-modal").wait_for(state="hidden", timeout=5_000)

    # After dismissal, the grid should be populated (loader gone + grid has rows)
    try:
        gui_page.wait_for_selector(
            "#loading_overlay[style*='display: none']", timeout=10_000
        )
    except Exception:
        pass
    # The grid must contain at least one tab (sheet) — tabs are rendered in #tabs-list
    gui_page.wait_for_selector("#tabs-list li, #grid .slick-row", timeout=10_000)


# ---------------------------------------------------------------------------
# 4.1  Workbook upload — error path
# ---------------------------------------------------------------------------


@pytest.mark.gui
def test_workbook_upload_without_file_shows_error(gui_page: Page, evpn_network: dict):
    """Clicking Import without selecting a file must show a validation alert."""
    _goto(gui_page, f"/campus_network/{evpn_network['id']}/configuration_view/")
    gui_page.wait_for_selector("#import-config-data", timeout=_DEFAULT_TIMEOUT)

    gui_page.click("#import-config-data")
    gui_page.locator("#upload-modal").wait_for(state="visible", timeout=5_000)
    # Submit without choosing a file
    gui_page.click("#import")

    # The JS shows #upload-status with the "Please Select a valid xlsx/xls file" alert
    gui_page.locator("#upload-status").wait_for(state="visible", timeout=5_000)
    content = gui_page.content()
    assert "valid" in content.lower() or "select" in content.lower(), (
        "Expected a file-validation error message"
    )


# ---------------------------------------------------------------------------
# 4.2  Workbook download
# ---------------------------------------------------------------------------


@pytest.mark.gui
def test_workbook_download_link_returns_xlsx(
    gui_page: Page, evpn_network_with_workbook: dict
):
    """Triggering the export download must deliver an xlsx file."""
    # We verify download by watching the network response for the download URL
    nid = evpn_network_with_workbook["id"]
    download_url = f"/campus_network/{nid}/download_config_data/"

    # First create the Excel file on the server by calling create_excel_data
    create_url = f"{BASE_URL}/campus_network/{nid}/create_excel_data/"
    # Use the API session to trigger excel creation (it's a GET/POST that
    # only requires a logged-in session; we use requests with the existing
    # Django session cookies captured from the Playwright context).
    cookies = {c["name"]: c["value"] for c in gui_page.context.cookies()}
    resp = requests.get(create_url, cookies=cookies, timeout=60)
    assert resp.status_code == 200, f"create_excel_data failed: {resp.status_code}"

    # Now navigate to the download URL inside the browser — Playwright will
    # capture the download.
    with gui_page.expect_download(timeout=30_000) as dl_info:
        gui_page.goto(f"{BASE_URL}{download_url}", wait_until="commit", timeout=30_000)
    download = dl_info.value
    assert download.suggested_filename.endswith(".xlsx"), (
        f"Download filename '{download.suggested_filename}' is not an xlsx file"
    )
    # Verify the downloaded bytes are a valid zip (xlsx is a zip archive)
    import io
    import zipfile

    path = download.path()
    with open(path, "rb") as f:
        content_bytes = f.read()
    assert len(content_bytes) > 0, "Downloaded file is empty"
    assert zipfile.is_zipfile(io.BytesIO(content_bytes)), (
        "Downloaded file is not a valid xlsx (zip) file"
    )


# ---------------------------------------------------------------------------
# 4.3  Workbook clear
# ---------------------------------------------------------------------------


@pytest.mark.gui
def test_workbook_clear_removes_data(
    gui_page: Page, evpn_network_with_workbook: dict
):
    """Clicking Delete→Confirm on the configuration page must clear the grid."""
    nid = evpn_network_with_workbook["id"]
    _goto(gui_page, f"/campus_network/{nid}/configuration_view/")
    gui_page.wait_for_selector("#delete-config-data", timeout=_DEFAULT_TIMEOUT)

    # 1. Click the 'Delete' button to open the clear-confirmation modal
    gui_page.click("#delete-config-data")
    gui_page.locator("#delete-config-modal").wait_for(state="visible", timeout=5_000)

    # 2. Confirm the deletion
    gui_page.click("#delete-config-data-confirm")
    gui_page.locator("#delete-config-modal").wait_for(state="hidden", timeout=5_000)

    # 3. Brief pause for the AJAX delete to complete
    try:
        gui_page.wait_for_load_state("networkidle", timeout=5_000)
    except Exception:
        pass

    # 4. Reload the page to verify the data has gone
    _goto(gui_page, f"/campus_network/{nid}/configuration_view/")
    gui_page.wait_for_selector("#import-config-data", timeout=_DEFAULT_TIMEOUT)
    try:
        gui_page.wait_for_selector(
            "#loading_overlay[style*='display: none']", timeout=10_000
        )
    except Exception:
        pass
    content = gui_page.content()
    assert "No configuration data found" in content, (
        "Grid still shows data after clearing — expected 'No configuration data found'"
    )


# ===========================================================================
# Section 5 — Action history page
# ===========================================================================


@pytest.mark.gui
def test_action_history_page_loads(gui_page: Page, evpn_network: dict):
    """GET /campus_network/{id}/action_history/ must load the action history page."""
    _goto(gui_page, f"/campus_network/{evpn_network['id']}/action_history/")
    gui_page.wait_for_selector("table", timeout=_DEFAULT_TIMEOUT)
    content = gui_page.content()
    # The action_history.html template renders an ActionHistoryTable; just
    # confirm we got a page (not an error / login redirect)
    assert "/admin/login/" not in gui_page.url
    assert "500" not in gui_page.title()


@pytest.mark.gui
def test_action_history_empty_for_new_network(gui_page: Page, evpn_network: dict):
    """A brand-new network must have an empty action history table."""
    _goto(gui_page, f"/campus_network/{evpn_network['id']}/action_history/")
    gui_page.wait_for_selector("table", timeout=_DEFAULT_TIMEOUT)
    # The table exists but has no data rows — just the header row
    rows = gui_page.locator("table tbody tr").all()
    # Either 0 rows or rows containing only "No data" / empty cells
    for row in rows:
        row_text = row.inner_text().strip()
        # django_tables2 renders an empty-table row with "No items" or similar
        assert row_text == "" or "no" in row_text.lower() or len(row_text) < 5, (
            f"Unexpected action history row in new network: {row_text!r}"
        )


# ===========================================================================
# Section 6 — Network deletion via GUI
# ===========================================================================


@pytest.mark.gui
def test_network_delete_via_gui(
    gui_page: Page, api_session: requests.Session, evpn_campus_type_id: int
):
    """Deleting a network through the summary page must remove it from the list.

    This test creates its own network (via API to avoid the Jenkins dependency
    in the GUI create form) and then deletes it through the browser.
    """
    # --- create a network via API so we own its lifecycle ---
    host_content = (FIXTURE_DIR / "dc1-hosts").read_text()
    name = f"evpn-gui-del-{uuid.uuid4().hex[:8]}"
    create_resp = api_session.post(
        f"{BASE_URL}/api/v1/networks/",
        json={
            "name": name,
            "status": "Initialized",
            "description": "GUI deletion test",
            "host_file": host_content,
            "campus_type": evpn_campus_type_id,
        },
        timeout=30,
    )
    assert create_resp.status_code == 201
    nid = create_resp.json()["id"]

    try:
        # --- verify it appears on the management page ---
        _goto(gui_page, "/campusnetwork/")
        gui_page.wait_for_selector("table", timeout=_DEFAULT_TIMEOUT)
        assert name in gui_page.content(), (
            f"Network '{name}' not found in management page before deletion"
        )

        # --- open the summary page and use the Delete button ---
        _goto(gui_page, f"/campus_network/{nid}/summary/")
        gui_page.wait_for_selector("#del_network-btn", timeout=_DEFAULT_TIMEOUT)
        gui_page.click("#del_network-btn")

        # The delete button triggers the delete modal
        gui_page.locator("#delete-campus-network-modal").wait_for(
            state="visible", timeout=5_000
        )
        gui_page.click("#campus-network-delete")

        # Wait for the page to react (modal triggers deleteCampusNetworksbyId AJAX)
        try:
            gui_page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass

        # --- verify the network is gone from the list (via API, most reliable) ---
        get_resp = api_session.get(
            f"{BASE_URL}/api/v1/networks/{nid}/", timeout=15
        )
        assert get_resp.status_code == 404, (
            f"Network {nid} still exists after GUI deletion (status {get_resp.status_code})"
        )
        nid = None  # prevent double-cleanup in finally

    finally:
        # Best-effort API cleanup in case the GUI deletion did not happen
        if nid is not None:
            api_session.delete(f"{BASE_URL}/api/v1/networks/{nid}/", timeout=15)
