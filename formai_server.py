#!/usr/bin/env python3
"""
FormAI Quick Server - Instant startup alternative
Serves the static files while the Rust backend compiles
"""

import os
import sys
import subprocess
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

class FormAIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="static", **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress logs for cleaner output
        pass

def start_rust_backend():
    """Start the Rust backend in the background"""
    try:
        # Check if already compiled
        exe_path = "target\\release\\formai-rust.exe"
        if os.path.exists(exe_path):
            print("✅ Starting pre-compiled FormAI backend...")
            subprocess.run([exe_path])
        else:
            print("🔨 Compiling FormAI backend (one-time setup)...")
            subprocess.run(["cargo", "build", "--release"])
            if os.path.exists(exe_path):
                print("✅ Compilation complete! Starting backend...")
                subprocess.run([exe_path])
    except Exception as e:
        print(f"Backend error: {e}")

def main():
    print("\n" + "="*40)
    print("    FormAI - Instant Start")
    print("="*40 + "\n")

    # Kill any existing processes
    os.system("taskkill /F /IM formai-rust.exe >nul 2>&1")
    os.system("taskkill /F /IM python.exe >nul 2>&1")

    # Ensure CSS is built
    if os.path.exists("package.json") and not os.path.exists("static\\css\\tailwind.css"):
        print("Building CSS...")
        os.system("npm run build-css")

    # Start Rust backend in background thread
    backend_thread = threading.Thread(target=start_rust_backend, daemon=True)
    backend_thread.start()

    # Start Python server immediately for static files
    PORT = 5511
    print(f"🌐 FormAI is available at:")
    print(f"   http://localhost:{PORT}")
    print(f"\n📝 Static interface ready immediately!")
    print(f"⚙️  Backend compiling in background...\n")
    print("Press Ctrl+C to stop\n")

    httpd = HTTPServer(('localhost', PORT), FormAIHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ FormAI stopped")
        os.system("taskkill /F /IM formai-rust.exe >nul 2>&1")

if __name__ == "__main__":
    main()