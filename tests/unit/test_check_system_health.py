import httpx

import scripts.check_system_health as health_check


def test_check_model_artifacts_reports_present_when_files_exist():
    ok, detail = health_check.check_model_artifacts()
    assert ok is True
    assert detail == "present"


def test_check_http_ok_on_200(monkeypatch):
    def fake_get(url, timeout):
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    ok, detail = health_check.check_http("http://x/health", "X")
    assert ok is True
    assert "200" in detail


def test_check_http_fails_on_non_200(monkeypatch):
    def fake_get(url, timeout):
        return httpx.Response(503, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    ok, _ = health_check.check_http("http://x/health", "X")
    assert ok is False


def test_check_http_fails_on_connection_error(monkeypatch):
    def fake_get(url, timeout):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "get", fake_get)
    ok, detail = health_check.check_http("http://x/health", "X")
    assert ok is False
    assert "unreachable" in detail
