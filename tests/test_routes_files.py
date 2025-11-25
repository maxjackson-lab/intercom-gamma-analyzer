"""
Tests for file browsing and download routes.
"""


def _prepare_files(outputs_dir):
    exec_dir = outputs_dir / "executions" / "exec-123"
    exec_dir.mkdir(parents=True, exist_ok=True)
    log_path = exec_dir / "analysis.log"
    log_path.write_text("analysis complete", encoding="utf-8")
    root_file = outputs_dir / "summary.txt"
    root_file.write_text("root summary", encoding="utf-8")
    return log_path.relative_to(outputs_dir), root_file.relative_to(outputs_dir)


def test_browse_files_and_downloads(web_app):
    client = web_app["client"]
    outputs_dir = web_app["outputs_dir"]
    rel_exec_log, rel_root = _prepare_files(outputs_dir)

    browse = client.get("/api/browse-files")
    data = browse.json()
    assert browse.status_code == 200
    assert data["total_files"] >= 2
    assert any("exec-123" in directory for directory in data["files_by_directory"])

    file_resp = client.get(f"/outputs/{rel_exec_log}")
    assert file_resp.status_code == 200
    assert file_resp.text == "analysis complete"

    list_resp = client.get("/outputs", params={"limit": 5})
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 2

    redirect = client.get("/download", params={"file": str(rel_root)})
    assert redirect.status_code == 301
    assert redirect.headers["Location"] == f"/outputs/{rel_root}"


def test_file_download_zip_variants(web_app):
    client = web_app["client"]
    outputs_dir = web_app["outputs_dir"]
    rel_log, _ = _prepare_files(outputs_dir)

    zip_resp = client.get("/api/download-zip", params={"execution_id": "exec-123"})
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"

    folder_zip = client.get("/api/download-folder-zip", params={"folder": "exec-123"})
    assert folder_zip.status_code == 200
    assert folder_zip.headers["content-type"] == "application/zip"

    invalid = client.get("/outputs/../secret.txt")
    assert invalid.status_code == 400

