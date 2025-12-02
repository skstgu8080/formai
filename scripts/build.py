#!/usr/bin/env python3
"""
FormAI Build Script
Cross-platform build script for creating FormAI executables using PyInstaller.
Works on Windows, macOS, and Linux.

Usage:
    python scripts/build.py           # Interactive mode
    python scripts/build.py --ci      # CI mode (no prompts)
"""

import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path

# Build configuration
APP_NAME = "FormAI" if platform.system() == "Windows" else "formai"
MAIN_SCRIPT = "formai_server.py"

# Files/directories to include
DATA_DIRS = [
    ("web", "web"),
    ("static", "static"),
    ("tools", "tools"),
]

DATA_FILES = [
    ("package.json", "."),
    ("client_callback.py", "."),      # Admin callback system
    ("update_service.py", "."),        # Auto-update service
]

# Hidden imports for PyInstaller
HIDDEN_IMPORTS = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "seleniumbase",
    "selenium",
    "fastapi",
    "httpx",
    "client_callback",      # Admin callback system
    "update_service",        # Auto-update service
]

# Collect all from these packages
COLLECT_ALL = [
    "seleniumbase",
]


def print_banner():
    """Print build banner."""
    print()
    print("=" * 60)
    print("          Building FormAI Complete Package")
    print("=" * 60)
    print()
    print("This will create ONE executable with:")
    print("  - Python interpreter")
    print("  - All dependencies (FastAPI, SeleniumBase, etc.)")
    print("  - FormAI server")
    print("  - Web interface")
    print("  - Automation tools")
    print()


def get_platform_info():
    """Get platform and architecture info."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Normalize OS name
    if system == "darwin":
        os_name = "macos"
    elif system == "windows":
        os_name = "windows"
    else:
        os_name = "linux"

    # Normalize architecture
    if machine in ("x86_64", "amd64"):
        arch = "x64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        arch = machine

    return os_name, arch


def clean_build():
    """Clean previous build artifacts."""
    print("[->] Cleaning previous build...")

    dirs_to_clean = ["build", "dist", "__pycache__"]
    files_to_clean = [f"{APP_NAME}.spec", "FormAI.spec", "formai.spec"]

    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d)

    for f in files_to_clean:
        if os.path.exists(f):
            os.remove(f)

    print("[OK] Cleaned")
    print()


def install_pyinstaller():
    """Ensure PyInstaller is installed."""
    print("[->] Checking PyInstaller...")
    try:
        import PyInstaller
        print("[OK] PyInstaller already installed")
    except ImportError:
        print("[->] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])
        print("[OK] PyInstaller installed")
    print()


def build_executable():
    """Build the executable with PyInstaller."""
    print("[->] Building executable... (this takes 3-5 minutes)")
    print()

    # Determine separator based on OS
    sep = ";" if platform.system() == "Windows" else ":"

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--onefile",
        f"--name={APP_NAME}",
    ]

    # Add data directories
    for src, dst in DATA_DIRS:
        if os.path.exists(src):
            cmd.append(f"--add-data={src}{sep}{dst}")

    # Add data files
    for src, dst in DATA_FILES:
        if os.path.exists(src):
            cmd.append(f"--add-data={src}{sep}{dst}")

    # Add hidden imports
    for imp in HIDDEN_IMPORTS:
        cmd.append(f"--hidden-import={imp}")

    # Add collect-all
    for pkg in COLLECT_ALL:
        cmd.append(f"--collect-all={pkg}")

    # Add main script
    cmd.append(MAIN_SCRIPT)

    # Run PyInstaller
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print()
        print("[X] Build failed!")
        return False

    print()
    print("[OK] Build complete!")
    return True


def create_archive():
    """Create release archive."""
    os_name, arch = get_platform_info()

    if platform.system() == "Windows":
        exe_name = f"{APP_NAME}.exe"
        archive_name = f"formai-{os_name}-{arch}.zip"
    else:
        exe_name = APP_NAME
        archive_name = f"formai-{os_name}-{arch}.tar.gz"

    exe_path = Path("dist") / exe_name
    archive_path = Path("dist") / archive_name

    if not exe_path.exists():
        print(f"[X] Executable not found: {exe_path}")
        return None

    print(f"[->] Creating release archive: {archive_name}")

    if platform.system() == "Windows":
        import zipfile
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(exe_path, exe_name)
    else:
        import tarfile
        with tarfile.open(archive_path, "w:gz") as tf:
            tf.add(exe_path, arcname=exe_name)

    print(f"[OK] Created: {archive_path}")
    return archive_path


def print_success():
    """Print success message."""
    os_name, arch = get_platform_info()

    if platform.system() == "Windows":
        exe_path = f"dist\\{APP_NAME}.exe"
    else:
        exe_path = f"dist/{APP_NAME}"

    # Get file size
    if os.path.exists(exe_path.replace("\\", "/")):
        size_mb = os.path.getsize(exe_path.replace("\\", "/")) / 1024 / 1024
    else:
        size_mb = 0

    print()
    print("=" * 60)
    print()
    print(f"[OK] {APP_NAME} built successfully!")
    print()
    print(f"    Platform: {os_name} {arch}")
    print(f"    Location: {exe_path}")
    print(f"    Size: {size_mb:.1f} MB")
    print()
    print("What's included:")
    print("  - Python interpreter")
    print("  - All Python packages")
    print("  - FormAI server")
    print("  - Web interface")
    print("  - Automation tools")
    print()
    print("To test:")
    if platform.system() == "Windows":
        print(f"  1. Double-click {exe_path}")
    else:
        print(f"  1. Run: {exe_path}")
    print("  2. Browser opens to http://localhost:5511")
    print()
    print("=" * 60)
    print()


def main():
    """Main build process."""
    ci_mode = "--ci" in sys.argv

    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    print_banner()

    os_name, arch = get_platform_info()
    print(f"  Platform: {os_name} {arch}")
    print()

    if not ci_mode:
        input("Press Enter to start build...")
        print()

    clean_build()
    install_pyinstaller()

    if not build_executable():
        sys.exit(1)

    archive = create_archive()
    print_success()

    if not ci_mode:
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
