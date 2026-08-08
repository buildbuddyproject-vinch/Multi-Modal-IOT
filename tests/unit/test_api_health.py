def test_health_check_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert isinstance(body["mongo_connected"], bool)
    assert "version" in body


def test_root_redirects_to_info(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "docs" in resp.json()


def test_openapi_schema_is_served(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["info"]["title"] == "Sepsis ICU Prediction API"


def test_swagger_docs_page_is_served(client):
    resp = client.get("/docs")
    assert resp.status_code == 200
