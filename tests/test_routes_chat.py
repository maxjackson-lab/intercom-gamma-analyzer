"""
Tests for chat + schema metadata routes.
"""


def test_chat_endpoint_success(web_app):
    client = web_app["client"]
    response = client.post("/chat", json={"query": "Hello?", "context": {"mode": "sample"}})
    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert "Processed" in body["data"]["response"]


def test_chat_endpoint_handles_missing_interface(web_app):
    client = web_app["client"]
    client.app.state.chat_interface = None
    response = client.post("/chat", json={"query": "Hi", "context": {}})
    body = response.json()
    assert response.status_code == 200
    assert body["success"] is False
    assert body["data"]["error_type"] == "dependencies_missing"


def test_get_commands_reflects_canonical_schema(web_app):
    client = web_app["client"]
    response = client.get("/api/commands")
    body = response.json()
    assert response.status_code == 200
    assert "commands" in body
    assert isinstance(body["commands"], dict)
    assert "version" in body


def test_get_filters_and_stats_require_chat_interface(web_app):
    client = web_app["client"]
    filters_resp = client.get("/api/filters")
    assert filters_resp.status_code == 200
    assert "filters" in filters_resp.json()

    stats_resp = client.get("/api/stats")
    assert stats_resp.status_code == 200
    assert "stats" in stats_resp.json()

    # Remove interface and expect 500 errors
    client.app.state.chat_interface = None
    assert client.get("/api/filters").status_code == 500
    assert client.get("/api/stats").status_code == 500

