import httpx
import pytest

from dashboard.api_client import ApiClient, ApiError


def _client(handler) -> ApiClient:
    return ApiClient(base_url="http://testserver", token="fake-token", transport=httpx.MockTransport(handler))


def test_login_success_returns_token_payload():
    def handler(request):
        assert request.url.path == "/auth/login"
        return httpx.Response(200, json={"access_token": "abc", "token_type": "bearer", "username": "admin", "role": "admin"})

    body = _client(handler).login("admin", "pw")
    assert body["access_token"] == "abc"


def test_login_failure_raises_api_error_with_detail():
    def handler(request):
        return httpx.Response(401, json={"detail": "invalid username or password"})

    with pytest.raises(ApiError) as exc_info:
        _client(handler).login("admin", "wrong")
    assert exc_info.value.status_code == 401
    assert "invalid" in exc_info.value.detail


def test_authorization_header_is_attached_to_every_request():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json=[])

    _client(handler).list_patients()
    assert seen["auth"] == "Bearer fake-token"


def test_get_latest_vitals_returns_none_on_404_instead_of_raising():
    def handler(request):
        return httpx.Response(404, json={"detail": "no vitals found"})

    assert _client(handler).get_latest_vitals("p1") is None


def test_get_latest_vitals_still_raises_on_non_404_error():
    def handler(request):
        return httpx.Response(500, json={"detail": "boom"})

    with pytest.raises(ApiError):
        _client(handler).get_latest_vitals("p1")


def test_list_alerts_forwards_filters_as_query_params():
    seen = {}

    def handler(request):
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json=[])

    _client(handler).list_alerts(patient_id="p1", acknowledged=False, risk_level="Critical")
    assert seen["params"]["patient_id"] == "p1"
    assert seen["params"]["acknowledged"] == "false"
    assert seen["params"]["risk_level"] == "Critical"


def test_acknowledge_alert_posts_acknowledged_by():
    def handler(request):
        assert request.method == "PATCH"
        return httpx.Response(200, json={"acknowledged": True})

    result = _client(handler).acknowledge_alert("alert1", "dr_smith")
    assert result["acknowledged"] is True


def test_network_failure_raises_api_error_503():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(ApiError) as exc_info:
        _client(handler).health()
    assert exc_info.value.status_code == 503


def test_no_content_response_returns_empty_dict():
    def handler(request):
        return httpx.Response(204)

    assert _client(handler).get_me() == {}


def test_download_patient_report_returns_raw_pdf_bytes():
    def handler(request):
        assert request.url.path == "/patients/p1/report"
        return httpx.Response(200, content=b"%PDF-1.4 fake report bytes", headers={"content-type": "application/pdf"})

    result = _client(handler).download_patient_report("p1")
    assert result.startswith(b"%PDF")


def test_download_patient_report_raises_api_error_on_404():
    def handler(request):
        return httpx.Response(404, json={"detail": "patient 'p1' not found"})

    with pytest.raises(ApiError) as exc_info:
        _client(handler).download_patient_report("p1")
    assert exc_info.value.status_code == 404
