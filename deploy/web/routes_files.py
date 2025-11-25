"""File browsing and download routes for the Railway web server."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse

from deploy.web.routes_execution import (
    check_rate_limit,
    discover_output_files,
    format_timestamp_from_epoch,
    get_output_paths,
)

files_router = APIRouter()


# ============================================
# Legacy Compatibility Routes (DEPRECATED)
# ============================================


@files_router.get("/download")
async def legacy_download_redirect(
    request: Request,
    file: str = Query(default="", description="File path to download"),
):
    """
    DEPRECATED: Legacy /download endpoint for backward compatibility.
    
    Redirects to the new /outputs/{file_path} endpoint.
    Clients should migrate to using /outputs/{file_path} directly.
    
    This route exists to support legacy clients (e.g., static/app.js) that
    still use the old /download?file=<filename> pattern from the removed
    root-level railway_web.py server.
    
    Returns:
        RedirectResponse: 301 permanent redirect to /outputs/{file}
    """
    await check_rate_limit(request)
    
    if not file:
        raise HTTPException(status_code=400, detail="Missing 'file' query parameter")
    
    # Security check: prevent directory traversal
    if ".." in file or file.startswith("/"):
        raise HTTPException(status_code=403, detail="Invalid file path")
    
    # Redirect to the new /outputs/{file_path} endpoint
    # Use 301 (permanent) to encourage clients to update their URLs
    return RedirectResponse(
        url=f"/outputs/{file}",
        status_code=301,
        headers={"X-Deprecated-Endpoint": "true", "X-New-Endpoint": f"/outputs/{file}"},
    )


# ============================================
# File Browsing Routes
# ============================================


@files_router.get("/api/browse-files")
async def browse_all_files(request: Request):
    """Browse all available output files grouped by execution directory."""
    await check_rate_limit(request)
    all_files = await discover_output_files()

    total_files = len(all_files)
    files_by_directory: Dict[str, List[Dict[str, object]]] = {}
    for file_info in all_files:
        dir_name = file_info.get("directory", "unknown")
        files_by_directory.setdefault(dir_name, []).append(file_info)

    for dir_files in files_by_directory.values():
        dir_files.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {
        "total_files": total_files,
        "directories": len(files_by_directory),
        "files_by_directory": files_by_directory,
        "all_files": all_files,
    }


@files_router.get("/outputs/{file_path:path}")
async def serve_output_file(file_path: str, request: Request):
    """Serve files from the outputs directory."""
    await check_rate_limit(request)

    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid file path")

    resolved_path: Optional[Path] = None
    for base_path in get_output_paths():
        candidate = (base_path / file_path).resolve()
        base_resolved = base_path.resolve()
        if not str(candidate).startswith(str(base_resolved)):
            continue
        if candidate.exists() and candidate.is_file():
            resolved_path = candidate
            break

    if not resolved_path:
        raise HTTPException(status_code=404, detail="File not found")

    filename = resolved_path.name.lower()
    content_type = "application/octet-stream"
    if filename.endswith(".json"):
        content_type = "application/json; charset=utf-8"
    elif filename.endswith(".csv"):
        content_type = "text/csv; charset=utf-8"
    elif filename.endswith(".md"):
        content_type = "text/markdown; charset=utf-8"
    elif filename.endswith(".txt") or filename.endswith(".log"):
        content_type = "text/plain; charset=utf-8"

    return FileResponse(
        path=str(resolved_path),
        media_type=content_type,
        filename=resolved_path.name,
    )


@files_router.get("/api/download-zip")
async def download_outputs_zip(
    request: Request,
    execution_id: Optional[str] = None,
    file_type: str = "all",
):
    """Download output files as a ZIP archive."""
    await check_rate_limit(request)

    zip_buffer = io.BytesIO()
    seen_paths = set()
    file_count = 0

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for outputs_dir in get_output_paths():
            if not outputs_dir.exists():
                continue
            for file_path in outputs_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                rel_path = file_path.relative_to(outputs_dir)
                rel_str = str(rel_path)
                if rel_str in seen_paths:
                    continue

                file_name = file_path.name
                is_audit = "audit_trail" in file_name.lower()
                if file_type == "audit" and not is_audit:
                    continue
                if file_type == "analysis" and is_audit:
                    continue
                if execution_id and execution_id not in file_name and execution_id not in rel_str:
                    continue

                zip_file.write(file_path, arcname=rel_str)
                seen_paths.add(rel_str)
                file_count += 1

    if file_count == 0:
        raise HTTPException(status_code=404, detail="No files found matching criteria")

    zip_buffer.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = (
        f"outputs_{execution_id}_{timestamp}.zip" if execution_id else f"outputs_{file_type}_{timestamp}.zip"
    )

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={zip_filename}",
            "Content-Length": str(len(zip_buffer.getvalue())),
        },
    )


@files_router.get("/api/download-folder-zip")
async def download_folder_zip(folder: str, request: Request):
    """Download a specific execution folder as a ZIP archive."""
    await check_rate_limit(request)
    if not folder:
        raise HTTPException(status_code=400, detail="Folder name is required")

    zip_buffer = io.BytesIO()
    found_folder = False

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for outputs_dir in get_output_paths():
            execution_dir = outputs_dir / "executions" / folder
            if not execution_dir.exists() or not execution_dir.is_dir():
                continue
            found_folder = True
            for file_path in execution_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                rel_path = file_path.relative_to(outputs_dir)
                zip_file.write(file_path, arcname=str(rel_path))

    if not found_folder:
        raise HTTPException(status_code=404, detail=f"Folder '{folder}' not found")

    zip_buffer.seek(0)
    zip_filename = f"{folder}.zip"
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={zip_filename}",
            "Content-Length": str(len(zip_buffer.getvalue())),
        },
    )


@files_router.get("/outputs")
async def list_output_files(
    request: Request,
    file_type: str = "all",
    execution_id: Optional[str] = None,
    limit: int = 100,
):
    """List files with optional filtering."""
    await check_rate_limit(request)

    files: List[Dict[str, object]] = []
    seen_paths = set()
    for outputs_dir in get_output_paths():
        if not outputs_dir.exists():
            continue
        for file_path in outputs_dir.rglob("*"):
            if not file_path.is_file():
                continue
            rel_path = file_path.relative_to(outputs_dir)
            rel_str = str(rel_path)
            if rel_str in seen_paths:
                continue

            file_name = file_path.name
            is_audit = "audit_trail" in file_name.lower()

            if file_type == "audit" and not is_audit:
                continue
            if file_type == "analysis" and is_audit:
                continue
            if execution_id and execution_id not in file_name and execution_id not in rel_str:
                continue

            stat = file_path.stat()
            files.append(
                {
                    "name": file_name,
                    "path": rel_str,
                    "size": stat.st_size,
                    "modified": format_timestamp_from_epoch(stat.st_mtime),
                    "modified_epoch": stat.st_mtime,
                    "created": format_timestamp_from_epoch(stat.st_ctime),
                    "created_epoch": stat.st_ctime,
                    "type": "audit" if is_audit else "analysis",
                    "extension": file_path.suffix,
                    "base_path": str(outputs_dir),
                }
            )
            seen_paths.add(rel_str)

    files.sort(key=lambda x: x["created_epoch"], reverse=True)
    limited_files = files[:limit]
    return {"files": limited_files, "total": len(files), "filtered_count": len(limited_files)}

