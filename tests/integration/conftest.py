# Copyright (c) Hewlett Packard Enterprise, 2026. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""pytest configuration for end-to-end integration tests.

These tests run against a *live* NITA webapp instance — no Django test
database or mock layers are used.  Configure the target via environment
variables:

  NITA_BASE_URL           Base URL of the running webapp
                          (default: http://localhost:8000)
  NITA_USER               Django superuser username  (default: vagrant)
  NITA_PASS               Django superuser password  (default: vagrant123)
  EVPN_FIXTURE_DIR        Directory that holds evpn_vxlan_erb_dc fixture
                          files (project.yaml, dc1-hosts, dc1_data.xlsx …).
                          Defaults to examples/evpn_vxlan_erb_dc/ relative
                          to the root of the nita repo (this file lives at
                          tests/integration/conftest.py).
"""

import os
import pathlib
import uuid

import pytest
import requests

# ---------------------------------------------------------------------------
# Configuration resolved from the environment
# ---------------------------------------------------------------------------

BASE_URL: str = os.environ.get("NITA_BASE_URL", "http://localhost:8000").rstrip("/")
NITA_USER: str = os.environ.get("NITA_USER", "vagrant")
NITA_PASS: str = os.environ.get("NITA_PASS", "vagrant123")

# Fixture data directory.
# _HERE = nita/tests/integration   → parents[1] = nita/
_HERE = pathlib.Path(__file__).resolve().parent
_EVPN_FIXTURE_DIR_ENV = os.environ.get("EVPN_FIXTURE_DIR")
if _EVPN_FIXTURE_DIR_ENV:
    FIXTURE_DIR = pathlib.Path(_EVPN_FIXTURE_DIR_ENV)
else:
    FIXTURE_DIR = _HERE.parents[1] / "examples" / "evpn_vxlan_erb_dc"


# ---------------------------------------------------------------------------
# Session-scoped HTTP session with token auth
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def api_session() -> requests.Session:
    """Return a requests.Session pre-loaded with a valid token auth header.

    The token is obtained once per test session via POST /api/v1/auth/token/.
    """
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/token/",
        json={"username": NITA_USER, "password": NITA_PASS},
        timeout=30,
    )
    assert resp.status_code == 200, (
        f"Failed to obtain auth token ({resp.status_code}): {resp.text}"
    )
    token = resp.json()["token"]
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})
    return session


# ---------------------------------------------------------------------------
# Helpers available to all integration tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def evpn_campus_type_id(api_session: requests.Session) -> int:
    """Register ``evpn_vxlan_erb_dc_1.4`` as a CampusType by uploading a zip
    containing ``project.yaml`` and ``ansible.cfg`` to
    ``POST /api/v1/network-types/upload/``.

    The fixture is idempotent: if the type already exists it returns its id
    without re-uploading.  On teardown the type is deleted so CI runs start
    clean.  The whole cluster is ephemeral so teardown is best-effort only.
    """
    import io
    import zipfile

    project_name = "evpn_vxlan_erb_dc_1.4"

    # --- idempotency check ---------------------------------------------------
    list_resp = api_session.get(
        f"{BASE_URL}/api/v1/network-types/?name={project_name}", timeout=30
    )
    assert list_resp.status_code == 200
    results = list_resp.json().get("results", [])
    if results:
        yield results[0]["id"]
        return

    # --- build the zip in memory ---------------------------------------------
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(FIXTURE_DIR / "project.yaml", f"{project_name}/project.yaml")
        zf.write(FIXTURE_DIR / "ansible.cfg",  f"{project_name}/ansible.cfg")
    buf.seek(0)

    # --- upload ---------------------------------------------------------------
    resp = api_session.post(
        f"{BASE_URL}/api/v1/network-types/upload/",
        files={"app_zip_file": (f"{project_name}.zip", buf, "application/zip")},
        timeout=180,   # Jenkins job must validate and store the zip
    )
    assert resp.status_code == 200, (
        f"Project upload failed ({resp.status_code}): {resp.text}"
    )
    body = resp.json()
    assert body.get("result") == "success", f"Upload result: {body}"

    # The upload response includes name + id (see networktypeparser.py)
    if "id" in body:
        campus_type_id = body["id"]
    else:
        # Fallback: look up by name (handles older webapp images)
        list_resp = api_session.get(
            f"{BASE_URL}/api/v1/network-types/?name={project_name}", timeout=30
        )
        assert list_resp.status_code == 200
        found = list_resp.json().get("results", [])
        assert found, f"CampusType '{project_name}' not found after upload"
        campus_type_id = found[0]["id"]

    yield campus_type_id

    # --- teardown (best-effort) -----------------------------------------------
    api_session.delete(
        f"{BASE_URL}/api/v1/network-types/{campus_type_id}/", timeout=30
    )


def _unique_name(prefix: str = "evpn-ci") -> str:
    """Return a short unique network name safe for repeated CI runs."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def evpn_network(api_session: requests.Session, evpn_campus_type_id: int):
    """Create a CampusNetwork backed by dc1-hosts, yield its response dict,
    then DELETE it after the test regardless of pass/fail.
    """
    host_content = (FIXTURE_DIR / "dc1-hosts").read_text()
    name = _unique_name()
    payload = {
        "name": name,
        "status": "Initialized",
        "description": "EVPN DC1 integration test network",
        "host_file": host_content,
        "campus_type": evpn_campus_type_id,
    }
    create_resp = api_session.post(
        f"{BASE_URL}/api/v1/networks/", json=payload, timeout=30
    )
    assert create_resp.status_code == 201, (
        f"Network creation failed ({create_resp.status_code}): {create_resp.text}"
    )
    network = create_resp.json()

    yield network

    # Teardown: delete the network (ignore 404 if already deleted by the test)
    api_session.delete(
        f"{BASE_URL}/api/v1/networks/{network['id']}/", timeout=30
    )


@pytest.fixture
def evpn_network_with_workbook(api_session: requests.Session, evpn_network: dict):
    """Extend evpn_network by uploading dc1_data.xlsx, then yield the network."""
    with (FIXTURE_DIR / "dc1_data.xlsx").open("rb") as fh:
        upload_resp = api_session.post(
            f"{BASE_URL}/api/v1/networks/{evpn_network['id']}/workbook/upload/",
            files={"up_file": ("dc1_data.xlsx", fh, "application/octet-stream")},
            timeout=60,
        )
    assert upload_resp.status_code == 200, (
        f"Workbook upload failed ({upload_resp.status_code}): {upload_resp.text}"
    )
    yield evpn_network
