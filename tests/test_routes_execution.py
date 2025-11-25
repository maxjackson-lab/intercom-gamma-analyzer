"""
Tests for FastAPI execution routes (SSE + background flows).
"""

import json
import time

def test_execute_stream_success(web_app):
    client = web_app["client"]
    execution_id = "exec-stream"
    params = {
        "command": "python",
        "args": json.dumps(["src/main.py", "--help"]),
        "execution_id": execution_id,
    }

    with client.stream("GET", "/execute", params=params, headers={"Accept": "text/event-stream"}) as response:
        payload = "".join(chunk for chunk in response.iter_text())

    assert response.status_code == 200
    assert execution_id in payload
    status = client.get(f"/execute/status/{execution_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["execution_id"] == execution_id
    assert body["status"] in {"running", "completed", "starting"}


def test_execute_stream_rejects_invalid_command(web_app):
    client = web_app["client"]
    response = client.get(
        "/execute",
        params={"command": "ls", "args": json.dumps([]), "execution_id": "bad"},
    )
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]


def test_start_execution_and_status(web_app):
    client = web_app["client"]
    response = client.post(
        "/execute/start",
        data={
            "command": "python",
            "args": json.dumps(["src/main.py", "voice-of-customer", "--help"]),
        },
    )
    assert response.status_code == 200
    execution_id = response.json()["execution_id"]
    assert execution_id.startswith("exec-")

    # Allow background task to initialize
    time.sleep(0.05)
    status = client.get(f"/execute/status/{execution_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["execution_id"] == execution_id
    assert "output_length" in body


def test_start_execution_rejects_bad_args(web_app):
    client = web_app["client"]
    response = client.post(
        "/execute/start",
        data={"command": "python", "args": "{not json"},
    )
    assert response.status_code == 400
    assert "Invalid args format" in response.json()["detail"]


def test_list_executions_returns_debug_block(web_app):
    client = web_app["client"]
    # create at least one execution
    client.post(
        "/execute/start",
        data={"command": "python", "args": json.dumps(["src/main.py", "--version"])},
    )
    response = client.get("/execute/list")
    payload = response.json()
    assert response.status_code == 200
    assert "executions" in payload
    assert "debug" in payload
    assert isinstance(payload["executions"], list)


def test_cancel_execution_success(web_app):
    client = web_app["client"]
    start_resp = client.post(
        "/execute/start",
        data={"command": "python", "args": json.dumps(["src/main.py", "sample-mode"])},
    )
    execution_id = start_resp.json()["execution_id"]

    cancel_resp = client.post(f"/execute/cancel/{execution_id}")
    assert cancel_resp.status_code == 200
    assert "cancelled" in cancel_resp.json()["message"].lower()

    status = client.get(f"/execute/status/{execution_id}")
    if status.status_code == 200:
        assert status.json()["status"] in {"cancelled", "completed", "failed", "error", "timeout"}

