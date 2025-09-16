#!/usr/bin/env python3
"""
Simple FormAI Server - Basic working version
"""
import os
import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Fix Windows encoding
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class FormAIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=".", **kwargs)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # API endpoints
        if path == '/api/profiles':
            self.send_profiles()
        elif path == '/api/status':
            self.send_status()
        elif path == '/':
            # Serve simple dashboard
            self.path = '/web/simple.html'
            super().do_GET()
        else:
            # Serve static files
            super().do_GET()

    def send_profiles(self):
        """Return list of profiles"""
        profiles = []
        if os.path.exists('profiles'):
            for filename in os.listdir('profiles'):
                if filename.endswith('.json'):
                    try:
                        with open(f'profiles/{filename}', 'r', encoding='utf-8') as f:
                            profile = json.load(f)
                            profiles.append(profile)
                    except Exception as e:
                        print(f"Error reading profile {filename}: {e}")

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(profiles).encode())

    def send_status(self):
        """Return server status"""
        status = {
            "status": "running",
            "profiles_count": len([f for f in os.listdir('profiles') if f.endswith('.json')]) if os.path.exists('profiles') else 0,
            "message": "FormAI Simple Server is running"
        }

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(status).encode())

def main():
    PORT = 5511

    print("=" * 50)
    print("    FormAI Simple Server")
    print("=" * 50)
    print()
    print(f"Server running at: http://localhost:{PORT}")
    print("Open your browser to access the dashboard")
    print()
    print("Press Ctrl+C to stop")
    print()

    try:
        httpd = HTTPServer(('localhost', PORT), FormAIHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")

if __name__ == "__main__":
    main()