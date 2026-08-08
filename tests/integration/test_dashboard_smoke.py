"""End-to-end smoke test for the Step 9 dashboard against REAL running servers:
    uvicorn src.api.main:app --host 127.0.0.1 --port 8000
    python scripts/run_dashboard.py

Also requires an admin account (scripts/create_admin_user.py) and demo data
(scripts/seed_dashboard_demo_data.py) to already be seeded.

Dash's own callback wire-protocol (`/_dash-update-component`) hashes
allow_duplicate outputs in a way that's impractical to hand-construct in a
test, so instead of driving the app through a headless browser (not available
in this environment) this test invokes the real page callback FUNCTIONS
in-process, inside a real Flask session populated with a real JWT from the
live backend -- the exact same Python code Dash would run for a real
clinician, just called directly rather than through Dash's JS<->JSON
transport, which is framework plumbing rather than application logic.

Every page module (and dashboard.app itself) is imported at module scope,
before any Flask request context exists -- dash.register_page() refuses to run
inside a request context (it would be called from within a live callback
otherwise), so importing dashboard.pages.* lazily inside a test that already
holds a `test_request_context()` would fail."""
import dash
import httpx
import pytest

from dashboard import auth
from dashboard.app import poll_critical_alerts, server
from dashboard.pages.admin import load_admin_data
from dashboard.pages.admit_patient import handle_admit_patient
from dashboard.pages.alerts import load_alerts
from dashboard.pages.home import load_overview
from dashboard.pages.live_monitoring import load_patient_options, refresh_live_view
from dashboard.pages.login import handle_login
from dashboard.pages.patient_detail import load_patient_detail
from dashboard.pages.patients import load_patients

API_BASE_URL = "http://127.0.0.1:8000"
DASHBOARD_BASE_URL = "http://127.0.0.1:8050"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "SepsisIcu2026!"
SEEDED_PATIENT_ID = "demo_p02_gradual_sepsis"


def _api_available() -> bool:
    try:
        return httpx.get(f"{API_BASE_URL}/health", timeout=2.0).json().get("mongo_connected") is True
    except Exception:
        return False


def _dashboard_available() -> bool:
    try:
        return httpx.get(f"{DASHBOARD_BASE_URL}/login", timeout=2.0).status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (_api_available() and _dashboard_available()),
    reason="requires a live API (uvicorn src.api.main:app) and dashboard (scripts/run_dashboard.py) on localhost",
)


@pytest.fixture(scope="module")
def admin_token() -> str:
    resp = httpx.post(f"{API_BASE_URL}/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    resp.raise_for_status()
    return resp.json()["access_token"]


@pytest.fixture
def authenticated_request_context(admin_token):
    with server.test_request_context("/"):
        auth.log_in(admin_token, ADMIN_USERNAME, "admin")
        yield


def test_dashboard_shell_pages_are_reachable():
    for path in ["/", "/login", "/patients", "/admit-patient", "/live-monitoring", "/alerts", "/admin", f"/patients/{SEEDED_PATIENT_ID}"]:
        resp = httpx.get(f"{DASHBOARD_BASE_URL}{path}")
        assert resp.status_code == 200, path
        assert "Sepsis ICU Monitor" in resp.text


def test_dashboard_serves_dark_theme_assets():
    resp = httpx.get(f"{DASHBOARD_BASE_URL}/assets/dark_icu_theme.css")
    assert resp.status_code == 200
    assert "--icu-bg" in resp.text


def test_home_page_callback_loads_real_kpis(authenticated_request_context):
    kpi_row, recent_alerts = load_overview(1)
    assert type(kpi_row).__name__ == "Row"
    assert type(recent_alerts).__name__ in ("Table", "Alert")


def test_patients_page_callback_lists_seeded_patients(authenticated_request_context):
    table = load_patients(1)
    assert type(table).__name__ == "Table"
    assert SEEDED_PATIENT_ID in str(table)


def test_patient_detail_callback_loads_vitals_prediction_and_shap(authenticated_request_context):
    header, vitals_tab, prediction_tab, shap_tab = load_patient_detail(1, SEEDED_PATIENT_ID)
    assert type(header).__name__ == "Row"
    assert type(vitals_tab).__name__ == "Graph"
    assert type(prediction_tab).__name__ == "Graph"
    # the seed script computes a real SHAP explanation for every patient's latest prediction
    assert type(shap_tab).__name__ == "Div"


def test_live_monitoring_callbacks_load_real_data(authenticated_request_context):
    options, _default_value = load_patient_options(1)
    assert any(o["value"] == SEEDED_PATIENT_ID for o in options)

    body = refresh_live_view(1, SEEDED_PATIENT_ID)
    assert type(body).__name__ == "Div"


def test_alerts_page_lists_a_real_alert(authenticated_request_context):
    table = load_alerts(1, 0, "High", "false")
    assert type(table).__name__ in ("Table", "Alert")
    assert SEEDED_PATIENT_ID in str(table) or "demo_p03" in str(table) or "demo_p06" in str(table)


def test_admin_page_shows_health_users_and_audit_log(authenticated_request_context):
    health_view, users_table, audit_table = load_admin_data(1, None)
    assert "MongoDB connected: True" in str(health_view)
    assert ADMIN_USERNAME in str(users_table)
    assert "login" in str(audit_table)


def test_login_page_rejects_bad_credentials_end_to_end():
    with server.test_request_context("/login"):
        pathname, error = handle_login(1, 0, ADMIN_USERNAME, "wrong-password")
        assert pathname is dash.no_update
        assert "Invalid username or password" in error


def test_login_page_accepts_real_admin_credentials_end_to_end():
    with server.test_request_context("/login"):
        pathname, error = handle_login(1, 0, ADMIN_USERNAME, ADMIN_PASSWORD)
        assert pathname == "/"
        assert error == ""
        assert auth.is_authenticated() is True


def _signed_session_cookie(token: str, username: str, role: str) -> str:
    """Builds a real, validly-signed Flask session cookie value without going
    through server.test_client() -- that would dispatch the request through
    THIS pytest process's own `server` object, which (per this file's own
    module-scope imports of dashboard.pages.*) ends up with each page module
    imported under two different qualified names and trips Dash's
    duplicate-page-registry check. Signing a cookie by hand and sending it to
    the actually-running background dashboard process (DASHBOARD_BASE_URL)
    sidesteps that entirely -- same signing key, a real separate process."""
    from flask.sessions import SecureCookieSessionInterface

    serializer = SecureCookieSessionInterface().get_signing_serializer(server)
    return serializer.dumps({"token": token, "username": username, "role": role})


def test_download_patient_report_route_streams_a_real_pdf(admin_token):
    cookie = _signed_session_cookie(admin_token, ADMIN_USERNAME, "admin")
    resp = httpx.get(
        f"{DASHBOARD_BASE_URL}/downloads/patients/{SEEDED_PATIENT_ID}/report.pdf",
        cookies={"session": cookie},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert SEEDED_PATIENT_ID in resp.headers["content-disposition"]


def test_download_patient_report_route_redirects_when_not_authenticated():
    resp = httpx.get(
        f"{DASHBOARD_BASE_URL}/downloads/patients/{SEEDED_PATIENT_ID}/report.pdf",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


def test_poll_critical_alerts_surfaces_a_real_unacknowledged_high_risk_alert(authenticated_request_context):
    toasts, updated_seen_ids = poll_critical_alerts(1, [], [], "/")
    assert len(toasts) >= 1
    assert len(updated_seen_ids) >= 1
    assert any(type(t).__name__ == "Toast" for t in toasts)


def test_admit_patient_page_creates_a_real_patient_owned_by_the_caller(authenticated_request_context):
    import uuid
    patient_id = f"smoke_admit_{uuid.uuid4().hex[:8]}"

    feedback, cleared_id = handle_admit_patient(1, patient_id, "live", 58, "F", "MICU")
    assert type(feedback).__name__ == "Alert"
    assert patient_id in str(feedback)
    assert cleared_id == ""

    # confirm it's real: fetchable back through the actual API, owned by this account
    resp = httpx.get(f"{API_BASE_URL}/patients/{patient_id}", headers={"Authorization": f"Bearer {auth.current_token()}"})
    assert resp.status_code == 200
    assert resp.json()["created_by"] == ADMIN_USERNAME


def test_a_freshly_created_account_does_not_see_another_accounts_patients(admin_token):
    """The whole point of the per-account privacy model (src/api/routes/patients.py):
    a brand-new account -- created through the exact same POST /auth/register
    flow the Admin page uses -- must NOT see the seeded demo patient or
    anything else another account created."""
    import uuid

    new_username = f"smoke_clinician_{uuid.uuid4().hex[:8]}"
    new_password = "SmokeTestPass123!"
    register_resp = httpx.post(
        f"{API_BASE_URL}/auth/register",
        json={"username": new_username, "password": new_password, "role": "clinician"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert register_resp.status_code == 201

    login_resp = httpx.post(f"{API_BASE_URL}/auth/login", json={"username": new_username, "password": new_password})
    new_token = login_resp.json()["access_token"]

    with server.test_request_context("/"):
        auth.log_in(new_token, new_username, "clinician")
        table = load_patients(1)

    assert type(table).__name__ == "Alert"
    assert SEEDED_PATIENT_ID not in str(table)
