#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test server to debug startup issues
"""

import sys
import os

# Fix Windows encoding issues
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

print("Test server starting...")

try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    print("HTTP server imports successful")

    class TestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'FormAI Test Server is working!')

    print("Handler class created")

    PORT = 5511
    print(f"Starting server on port {PORT}...")

    httpd = HTTPServer(('localhost', PORT), TestHandler)
    print(f"Server created successfully")
    print(f"Test server running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop")

    httpd.serve_forever()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()