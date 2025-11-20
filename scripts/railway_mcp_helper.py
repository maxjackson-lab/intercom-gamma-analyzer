#!/usr/bin/env python3
"""
Railway MCP Helper Script

Helper functions for reading files from Railway via MCP or CLI.
This enables easy file access for debugging and analysis.

Usage:
    # Read latest execution files
    python scripts/railway_mcp_helper.py read-latest
    
    # Read specific file
    python scripts/railway_mcp_helper.py read-file outputs/executions/sample-mode_Last-Week_Nov-13-5-27pm/sample_mode_Nov-13-2025_05-27PM.json
    
    # List all files
    python scripts/railway_mcp_helper.py list-files
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime


def get_outputs_base_path() -> Path:
    """Resolve the correct outputs base path, honoring Railway persistent volumes."""
    volume_path = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    if volume_path:
        return Path(volume_path) / "outputs"
    return Path("/app/outputs")


def get_latest_execution_dir(base_path: Optional[Path] = None) -> Optional[Path]:
    """Get the most recent execution directory."""
    if base_path is None:
        base_path = get_outputs_base_path() / "executions"
    
    if not base_path.exists():
        return None
    
    execution_dirs = [d for d in base_path.iterdir() if d.is_dir()]
    if not execution_dirs:
        return None
    
    # Sort by modification time (newest first)
    execution_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return execution_dirs[0]


def list_files_in_execution(execution_dir: Path) -> List[Dict]:
    """List all files in an execution directory."""
    files = []
    for file_path in execution_dir.rglob('*'):
        if file_path.is_file():
            files.append({
                'name': file_path.name,
                'path': str(file_path.relative_to(execution_dir)),
                'size': file_path.stat().st_size,
                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                'type': file_path.suffix[1:] if file_path.suffix else 'unknown'
            })
    return sorted(files, key=lambda f: f['modified'], reverse=True)


def read_file_content(file_path: Path, max_size: int = 10 * 1024 * 1024) -> str:
    """Read file content with size limit."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_size = file_path.stat().st_size
    if file_size > max_size:
        raise ValueError(f"File too large ({file_size} bytes). Max size: {max_size} bytes")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def read_json_file(file_path: Path) -> dict:
    """Read and parse JSON file."""
    content = read_file_content(file_path)
    return json.loads(content)


def format_file_size(bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"


def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list-files":
        base_path = get_outputs_base_path() / "executions"
        latest_dir = get_latest_execution_dir(base_path)
        
        if not latest_dir:
            print("No execution directories found.")
            sys.exit(1)
        
        print(f"📁 Latest execution: {latest_dir.name}\n")
        files = list_files_in_execution(latest_dir)
        
        print(f"Found {len(files)} file(s):\n")
        for file_info in files:
            size_str = format_file_size(file_info['size'])
            print(f"  📄 {file_info['name']}")
            print(f"     Path: {file_info['path']}")
            print(f"     Size: {size_str} | Type: {file_info['type']}")
            print(f"     Modified: {file_info['modified']}\n")
    
    elif command == "read-latest":
        base_path = get_outputs_base_path() / "executions"
        latest_dir = get_latest_execution_dir(base_path)
        
        if not latest_dir:
            print("No execution directories found.")
            sys.exit(1)
        
        print(f"📁 Latest execution: {latest_dir.name}\n")
        files = list_files_in_execution(latest_dir)
        
        # Find JSON and log files
        json_files = [f for f in files if f['type'] == 'json']
        log_files = [f for f in files if f['type'] == 'log']
        
        if json_files:
            print("📊 JSON Files:\n")
            for file_info in json_files[:5]:  # Show first 5
                file_path = latest_dir / file_info['path']
                try:
                    data = read_json_file(file_path)
                    print(f"  {file_info['name']}:")
                    print(f"    Keys: {list(data.keys())[:10]}")
                    print()
                except Exception as e:
                    print(f"  {file_info['name']}: Error reading - {e}\n")
        
        if log_files:
            print("📋 Log Files:\n")
            for file_info in log_files[:3]:  # Show first 3
                file_path = latest_dir / file_info['path']
                try:
                    content = read_file_content(file_path, max_size=100000)  # 100KB limit
                    lines = content.split('\n')[:20]  # First 20 lines
                    print(f"  {file_info['name']}:")
                    print("    " + "\n    ".join(lines))
                    print("    ...\n")
                except Exception as e:
                    print(f"  {file_info['name']}: Error reading - {e}\n")
    
    elif command == "read-file":
        if len(sys.argv) < 3:
            print("Usage: python scripts/railway_mcp_helper.py read-file <file_path>")
            sys.exit(1)
        
        file_path = Path(sys.argv[2])
        
        # Handle relative paths
        if not file_path.is_absolute():
            # Try in outputs directory
            file_path = get_outputs_base_path() / file_path
        
        try:
            if file_path.suffix == '.json':
                data = read_json_file(file_path)
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                content = read_file_content(file_path)
                print(content)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

