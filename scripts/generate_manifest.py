"""
Generate update manifest for hot updates.

Run this after making changes to deploy updates to clients.
Upload the manifest and changed files to your server/GitHub.
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent

def hash_file(path: Path) -> str:
    """Generate SHA256 hash of file."""
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]


def generate_manifest():
    """Generate update-manifest.json"""

    manifest = {
        "version": "1.0",
        "generated": datetime.now().isoformat(),
        "files": {
            "tools": [],
            "sites": [],
            "web": []
        }
    }

    # Tools - Python automation scripts
    tools_dir = BASE_DIR / "tools"
    important_tools = [
        "seleniumbase_agent.py",
        "autofill_engine.py",
        "captcha_solver.py",
        "site_analyzer.py",
        "field_analyzer.py",
        "hot_updater.py",
    ]

    for tool in important_tools:
        tool_path = tools_dir / tool
        if tool_path.exists():
            manifest["files"]["tools"].append({
                "name": tool,
                "hash": hash_file(tool_path),
                "size": tool_path.stat().st_size
            })

    # Sites database
    sites_dir = BASE_DIR / "sites"
    sites_file = sites_dir / "sites.json"
    if sites_file.exists():
        manifest["files"]["sites"].append({
            "name": "sites.json",
            "hash": hash_file(sites_file),
            "size": sites_file.stat().st_size
        })

    # Web UI files (optional - usually don't change)
    web_dir = BASE_DIR / "web"
    for html_file in web_dir.glob("*.html"):
        manifest["files"]["web"].append({
            "name": html_file.name,
            "hash": hash_file(html_file),
            "size": html_file.stat().st_size
        })

    # Write manifest
    manifest_path = BASE_DIR / "update-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print("=" * 60)
    print("  Update Manifest Generated")
    print("=" * 60)
    print(f"\n  Output: {manifest_path}")
    print(f"\n  Files included:")
    for category, files in manifest["files"].items():
        if files:
            print(f"    {category}: {len(files)} files")
            for f in files:
                print(f"      - {f['name']} ({f['size']} bytes)")

    print("\n  To deploy updates:")
    print("  1. Push these files to GitHub or your server:")
    print("     - update-manifest.json")
    for category, files in manifest["files"].items():
        for f in files:
            print(f"     - {category}/{f['name']}")
    print("\n  2. Clients will auto-update on next check")
    print("=" * 60)

    return manifest


if __name__ == "__main__":
    generate_manifest()
