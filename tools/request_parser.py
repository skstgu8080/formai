"""
Request Parser - Parse DevTools fetch code, HAR files, and cURL commands
"""
import json
import re
import shlex
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, parse_qs


@dataclass
class ParsedRequest:
    """Represents a parsed HTTP request"""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = None
    body: Optional[str] = None
    cookies: Dict[str, str] = None
    form_data: Dict[str, str] = None
    content_type: Optional[str] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.cookies is None:
            self.cookies = {}
        if self.form_data is None:
            self.form_data = {}

    def to_dict(self) -> dict:
        return asdict(self)


class FetchCodeParser:
    """Parse JavaScript fetch() code from Chrome DevTools"""

    def parse(self, code: str) -> ParsedRequest:
        """
        Parse fetch code like:
        fetch("https://example.com/api", {
          "headers": {"content-type": "application/json"},
          "body": "...",
          "method": "POST"
        });
        """
        # Extract URL
        url_match = re.search(r'fetch\s*\(\s*["\']([^"\']+)["\']', code)
        if not url_match:
            raise ValueError("Could not extract URL from fetch code")
        url = url_match.group(1)

        # Try to extract options object
        options_match = re.search(r'fetch\s*\([^,]+,\s*(\{[^}]+\}|\{[\s\S]*?\n\s*\})', code, re.MULTILINE)

        method = "GET"
        headers = {}
        body = None
        cookies = {}

        if options_match:
            options_str = options_match.group(1)

            # Extract method
            method_match = re.search(r'["\']method["\']\s*:\s*["\']([^"\']+)["\']', options_str)
            if method_match:
                method = method_match.group(1).upper()

            # Extract headers
            headers_match = re.search(r'["\']headers["\']\s*:\s*(\{[^}]+\}|\{[\s\S]*?\})', options_str)
            if headers_match:
                headers = self._parse_object(headers_match.group(1))

            # Extract body
            body_match = re.search(r'["\']body["\']\s*:\s*["\']([^"\']*)["\']', options_str)
            if body_match:
                body = body_match.group(1)

            # Extract cookies from headers
            if 'cookie' in headers:
                cookies = self._parse_cookies(headers['cookie'])

        # Determine content type
        content_type = headers.get('content-type', '')

        # Parse form data if applicable
        form_data = {}
        if body and 'application/x-www-form-urlencoded' in content_type:
            form_data = dict(parse_qs(body))
            # Flatten single-item lists
            form_data = {k: v[0] if len(v) == 1 else v for k, v in form_data.items()}

        return ParsedRequest(
            url=url,
            method=method,
            headers=headers,
            body=body,
            cookies=cookies,
            form_data=form_data,
            content_type=content_type
        )

    def _parse_object(self, obj_str: str) -> Dict[str, str]:
        """Parse JavaScript object string into Python dict"""
        result = {}
        # Match key-value pairs
        pattern = r'["\']([^"\']+)["\']\s*:\s*["\']([^"\']*)["\']'
        for match in re.finditer(pattern, obj_str):
            key = match.group(1)
            value = match.group(2)
            result[key.lower()] = value
        return result

    def _parse_cookies(self, cookie_str: str) -> Dict[str, str]:
        """Parse cookie string into dict"""
        cookies = {}
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies


class HARParser:
    """Parse HAR (HTTP Archive) files from DevTools or Burp Suite"""

    def parse(self, har_data: dict) -> List[ParsedRequest]:
        """
        Parse HAR JSON and extract all HTTP requests
        Returns list of ParsedRequest objects
        """
        requests = []

        try:
            entries = har_data.get('log', {}).get('entries', [])

            for entry in entries:
                request_data = entry.get('request', {})

                # Extract basic info
                url = request_data.get('url', '')
                method = request_data.get('method', 'GET')

                # Extract headers
                headers = {}
                for header in request_data.get('headers', []):
                    name = header.get('name', '').lower()
                    value = header.get('value', '')
                    headers[name] = value

                # Extract cookies
                cookies = {}
                for cookie in request_data.get('cookies', []):
                    name = cookie.get('name', '')
                    value = cookie.get('value', '')
                    cookies[name] = value

                # Extract body
                post_data = request_data.get('postData', {})
                body = post_data.get('text', None)
                content_type = post_data.get('mimeType', headers.get('content-type', ''))

                # Extract form data if present
                form_data = {}
                if post_data.get('params'):
                    for param in post_data.get('params', []):
                        name = param.get('name', '')
                        value = param.get('value', '')
                        form_data[name] = value

                parsed = ParsedRequest(
                    url=url,
                    method=method,
                    headers=headers,
                    body=body,
                    cookies=cookies,
                    form_data=form_data,
                    content_type=content_type
                )

                requests.append(parsed)

        except Exception as e:
            raise ValueError(f"Failed to parse HAR file: {str(e)}")

        return requests

    def parse_file(self, har_path: str) -> List[ParsedRequest]:
        """Load and parse HAR file from disk"""
        with open(har_path, 'r', encoding='utf-8') as f:
            har_data = json.load(f)
        return self.parse(har_data)


class CurlParser:
    """Parse cURL commands from DevTools 'Copy as cURL'"""

    def parse(self, curl_cmd: str) -> ParsedRequest:
        """
        Parse cURL command like:
        curl 'https://example.com' -H 'User-Agent: Mozilla' --data 'key=value'
        """
        # Remove 'curl' prefix and clean up
        curl_cmd = curl_cmd.strip()
        if curl_cmd.startswith('curl '):
            curl_cmd = curl_cmd[5:]

        # Use shlex to properly handle quoted arguments
        try:
            parts = shlex.split(curl_cmd)
        except ValueError as e:
            raise ValueError(f"Failed to parse cURL command: {str(e)}")

        url = None
        method = "GET"
        headers = {}
        body = None
        cookies = {}

        i = 0
        while i < len(parts):
            part = parts[i]

            # URL (no flag)
            if not part.startswith('-') and url is None:
                url = part
                i += 1
                continue

            # Method
            if part in ['-X', '--request']:
                if i + 1 < len(parts):
                    method = parts[i + 1].upper()
                    i += 2
                    continue

            # Headers
            if part in ['-H', '--header']:
                if i + 1 < len(parts):
                    header = parts[i + 1]
                    if ':' in header:
                        key, value = header.split(':', 1)
                        headers[key.strip().lower()] = value.strip()
                    i += 2
                    continue

            # Body/Data
            if part in ['-d', '--data', '--data-raw', '--data-binary']:
                if i + 1 < len(parts):
                    body = parts[i + 1]
                    if method == "GET":
                        method = "POST"
                    i += 2
                    continue

            # Cookie
            if part in ['-b', '--cookie']:
                if i + 1 < len(parts):
                    cookie_str = parts[i + 1]
                    cookies = self._parse_cookies(cookie_str)
                    i += 2
                    continue

            i += 1

        if not url:
            raise ValueError("Could not extract URL from cURL command")

        # Determine content type
        content_type = headers.get('content-type', '')

        # Parse form data if applicable
        form_data = {}
        if body and 'application/x-www-form-urlencoded' in content_type:
            form_data = dict(parse_qs(body))
            # Flatten single-item lists
            form_data = {k: v[0] if len(v) == 1 else v for k, v in form_data.items()}

        return ParsedRequest(
            url=url,
            method=method,
            headers=headers,
            body=body,
            cookies=cookies,
            form_data=form_data,
            content_type=content_type
        )

    def _parse_cookies(self, cookie_str: str) -> Dict[str, str]:
        """Parse cookie string into dict"""
        cookies = {}
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies


# Convenience function to auto-detect and parse
def auto_parse(input_str: str) -> ParsedRequest:
    """
    Auto-detect format and parse accordingly
    Supports: fetch code, HAR JSON, cURL command
    """
    input_str = input_str.strip()

    # Detect fetch code
    if input_str.startswith('fetch(') or 'fetch(' in input_str[:100]:
        parser = FetchCodeParser()
        return parser.parse(input_str)

    # Detect cURL
    if input_str.startswith('curl '):
        parser = CurlParser()
        return parser.parse(input_str)

    # Try HAR JSON
    try:
        har_data = json.loads(input_str)
        if 'log' in har_data and 'entries' in har_data['log']:
            parser = HARParser()
            requests = parser.parse(har_data)
            if requests:
                return requests[0]  # Return first request
    except json.JSONDecodeError:
        pass

    raise ValueError("Could not auto-detect format. Please specify parser type.")
