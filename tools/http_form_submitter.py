"""
HTTP Form Submitter - Core engine for direct HTTP form submission
Integrates: parsing, CSRF detection, retry logic, rate limiting
"""
import httpx
import time
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, urlencode
from bs4 import BeautifulSoup

from tools.request_parser import ParsedRequest, auto_parse, FetchCodeParser, HARParser, CurlParser
from tools.csrf_detector import CSRFDetector, CSRFToken
from tools.retry_handler import RetryHandler, RetryConfig, RetryResult
from tools.rate_limiter import RateLimiter, RateLimitConfig


@dataclass
class SubmissionConfig:
    """Configuration for HTTP form submission"""
    timeout: float = 30.0
    follow_redirects: bool = True
    verify_ssl: bool = True
    user_agent: str = "FormAI-HTTP/1.0"
    retry_config: RetryConfig = None
    rate_limit_config: RateLimitConfig = None

    def __post_init__(self):
        if self.retry_config is None:
            self.retry_config = RetryConfig()
        if self.rate_limit_config is None:
            self.rate_limit_config = RateLimitConfig()


@dataclass
class SubmissionResult:
    """Result of form submission"""
    success: bool
    status_code: int
    response_body: str
    response_headers: Dict[str, str]
    redirect_url: Optional[str] = None
    csrf_token: Optional[Dict[str, str]] = None
    timing: Dict[str, float] = None
    attempts: int = 1
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.timing is None:
            self.timing = {}

    def to_dict(self) -> dict:
        return asdict(self)


class HTTPFormSubmitter:
    """
    Rock-solid HTTP form submitter with:
    - Multi-format import (fetch, HAR, cURL)
    - Smart CSRF detection
    - Exponential backoff retry
    - Token bucket rate limiting
    - Session management
    - Response validation
    """

    def __init__(self, config: SubmissionConfig = None):
        self.config = config or SubmissionConfig()

        # Initialize HTTP client with session management
        self.client = httpx.Client(
            timeout=self.config.timeout,
            follow_redirects=self.config.follow_redirects,
            verify=self.config.verify_ssl,
            headers={'User-Agent': self.config.user_agent}
        )

        # Initialize sub-systems
        self.csrf_detector = CSRFDetector()
        self.retry_handler = RetryHandler(self.config.retry_config)
        self.rate_limiter = RateLimiter(self.config.rate_limit_config)

    def __del__(self):
        """Clean up HTTP client on destruction"""
        try:
            self.client.close()
        except:
            pass

    # ========== Import Methods ==========

    def import_fetch_code(self, fetch_code: str) -> ParsedRequest:
        """Import JavaScript fetch() code from DevTools"""
        parser = FetchCodeParser()
        return parser.parse(fetch_code)

    def import_har_file(self, har_path: str) -> List[ParsedRequest]:
        """Import HAR file from DevTools or Burp Suite"""
        parser = HARParser()
        return parser.parse_file(har_path)

    def import_curl_command(self, curl_cmd: str) -> ParsedRequest:
        """Import cURL command from DevTools"""
        parser = CurlParser()
        return parser.parse(curl_cmd)

    def auto_import(self, input_str: str) -> ParsedRequest:
        """Auto-detect format and import"""
        return auto_parse(input_str)

    # ========== CSRF Detection ==========

    def detect_csrf(self, url: str) -> Optional[CSRFToken]:
        """
        Fetch page and detect CSRF token
        Returns CSRFToken or None if not found
        """
        try:
            # Rate limit the request
            self.rate_limiter.acquire(url, wait=True)

            # Fetch the page
            response = self.client.get(url)
            response.raise_for_status()

            # Extract cookies
            cookies = {cookie.name: cookie.value for cookie in self.client.cookies.jar}

            # Detect CSRF token
            csrf_token = self.csrf_detector.detect(response.text, cookies)

            if csrf_token:
                print(f"✓ CSRF token detected: {csrf_token.name} ({csrf_token.framework or 'generic'})")
            else:
                print("ℹ No CSRF token detected")

            return csrf_token

        except Exception as e:
            print(f"✗ Error detecting CSRF: {e}")
            return None

    # ========== Form Submission ==========

    def submit_form(
        self,
        url: str,
        form_data: Dict[str, Any],
        method: str = "POST",
        headers: Dict[str, str] = None,
        detect_csrf: bool = True
    ) -> SubmissionResult:
        """
        Submit form via HTTP
        Auto-detects and includes CSRF token if enabled
        """
        start_time = time.time()

        try:
            # Prepare headers
            if headers is None:
                headers = {}

            # Detect CSRF if enabled
            csrf_token = None
            if detect_csrf:
                csrf_token = self.detect_csrf(url)

                if csrf_token:
                    csrf_format = self.csrf_detector.get_submission_format(csrf_token)

                    if csrf_format['type'] == 'header':
                        # Add to headers
                        headers[csrf_format['name']] = csrf_format['value']
                    elif csrf_format['type'] == 'form_field':
                        # Add to form data
                        form_data[csrf_format['name']] = csrf_format['value']

            # Submit with retry logic
            def _submit():
                # Rate limit
                self.rate_limiter.acquire(url, wait=True)

                # Send request
                if method.upper() == "GET":
                    response = self.client.get(url, params=form_data, headers=headers)
                else:
                    response = self.client.post(url, data=form_data, headers=headers)

                return response

            # Execute with retry
            retry_result = self.retry_handler.execute_with_retry(_submit)

            if not retry_result.success:
                return SubmissionResult(
                    success=False,
                    status_code=0,
                    response_body="",
                    response_headers={},
                    attempts=retry_result.attempts,
                    error_message=str(retry_result.error),
                    timing={'total': retry_result.total_time}
                )

            response = retry_result.result

            # Handle Retry-After header for future requests
            if response.status_code == 429 and 'Retry-After' in response.headers:
                retry_after = float(response.headers['Retry-After'])
                self.rate_limiter.honor_retry_after(url, retry_after)

            # Build result
            return SubmissionResult(
                success=200 <= response.status_code < 300,
                status_code=response.status_code,
                response_body=response.text,
                response_headers=dict(response.headers),
                redirect_url=str(response.url) if str(response.url) != url else None,
                csrf_token=csrf_token.to_dict() if csrf_token else None,
                attempts=retry_result.attempts,
                timing={
                    'total': time.time() - start_time,
                    'retries': retry_result.total_time
                }
            )

        except Exception as e:
            return SubmissionResult(
                success=False,
                status_code=0,
                response_body="",
                response_headers={},
                error_message=str(e),
                timing={'total': time.time() - start_time}
            )

    def submit_from_parsed(
        self,
        parsed: ParsedRequest,
        form_data: Dict[str, Any] = None
    ) -> SubmissionResult:
        """
        Submit using ParsedRequest object
        Optionally override form data
        """
        # Use provided form data or fall back to parsed
        data = form_data or parsed.form_data or {}

        # Use parsed body if no form data
        if not data and parsed.body:
            data = parsed.body

        return self.submit_form(
            url=parsed.url,
            form_data=data,
            method=parsed.method,
            headers=parsed.headers,
            detect_csrf=True
        )

    # ========== Profile Integration ==========

    def map_profile_to_form(
        self,
        profile_data: Dict[str, Any],
        field_mappings: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Map profile fields to form fields
        field_mappings: {'form_field_name': 'profile_field_name'}
        """
        form_data = {}

        for form_field, profile_field in field_mappings.items():
            # Support nested profile fields (e.g., 'address.street')
            value = self._get_nested_value(profile_data, profile_field)
            if value is not None:
                form_data[form_field] = value

        return form_data

    def _get_nested_value(self, data: dict, key_path: str) -> Any:
        """Get value from nested dict using dot notation"""
        keys = key_path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def submit_with_profile(
        self,
        url: str,
        profile_data: Dict[str, Any],
        field_mappings: Dict[str, str],
        method: str = "POST"
    ) -> SubmissionResult:
        """
        Submit form using profile data
        Automatically maps profile fields to form fields
        """
        form_data = self.map_profile_to_form(profile_data, field_mappings)

        return self.submit_form(
            url=url,
            form_data=form_data,
            method=method,
            detect_csrf=True
        )

    # ========== Batch Processing ==========

    def submit_batch(
        self,
        url: str,
        profiles: List[Dict[str, Any]],
        field_mappings: Dict[str, str],
        method: str = "POST"
    ) -> List[SubmissionResult]:
        """
        Submit form for multiple profiles
        Returns list of results
        """
        results = []

        print(f"\n🚀 Starting batch submission ({len(profiles)} profiles)")

        for i, profile in enumerate(profiles, 1):
            profile_name = profile.get('name', profile.get('id', f'Profile {i}'))
            print(f"\n[{i}/{len(profiles)}] Submitting {profile_name}...")

            result = self.submit_with_profile(url, profile, field_mappings, method)

            if result.success:
                print(f"✓ Success (HTTP {result.status_code})")
            else:
                print(f"✗ Failed: {result.error_message}")

            results.append(result)

        # Summary
        successes = sum(1 for r in results if r.success)
        print(f"\n📊 Batch complete: {successes}/{len(profiles)} successful")

        return results

    # ========== Validation ==========

    def validate_response(
        self,
        result: SubmissionResult,
        expected_status: List[int] = None,
        success_patterns: List[str] = None,
        redirect_pattern: str = None
    ) -> bool:
        """
        Validate submission result
        Returns True if all validations pass
        """
        if expected_status is None:
            expected_status = [200, 201]

        # Check status code
        if result.status_code not in expected_status:
            return False

        # Check success patterns in response body
        if success_patterns:
            body_lower = result.response_body.lower()
            if not any(pattern.lower() in body_lower for pattern in success_patterns):
                return False

        # Check redirect URL pattern
        if redirect_pattern and result.redirect_url:
            if redirect_pattern not in result.redirect_url:
                return False

        return True

    # ========== Utility Methods ==========

    def test_connection(self, url: str) -> bool:
        """Test if URL is reachable"""
        try:
            response = self.client.head(url, timeout=5.0)
            return response.status_code < 500
        except:
            return False

    def analyze_form(self, url: str) -> dict:
        """
        Analyze form at URL
        Returns form metadata including fields and CSRF token
        """
        try:
            response = self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            forms = soup.find_all('form')

            if not forms:
                return {'error': 'No forms found on page'}

            # Analyze first form
            form = forms[0]

            # Extract form metadata
            action = form.get('action', url)
            method = form.get('method', 'GET').upper()
            enctype = form.get('enctype', 'application/x-www-form-urlencoded')

            # Extract fields
            fields = []
            for input_tag in form.find_all(['input', 'select', 'textarea']):
                field = {
                    'name': input_tag.get('name'),
                    'type': input_tag.get('type', 'text'),
                    'required': input_tag.has_attr('required'),
                    'value': input_tag.get('value', '')
                }
                if field['name']:
                    fields.append(field)

            # Detect CSRF
            cookies = {cookie.name: cookie.value for cookie in self.client.cookies.jar}
            csrf_token = self.csrf_detector.detect(response.text, cookies)

            return {
                'url': url,
                'action': action,
                'method': method,
                'enctype': enctype,
                'fields': fields,
                'csrf_token': csrf_token.to_dict() if csrf_token else None,
                'form_count': len(forms)
            }

        except Exception as e:
            return {'error': str(e)}

    def get_rate_limit_stats(self, url: str = None) -> dict:
        """Get rate limiting statistics"""
        return self.rate_limiter.get_stats(url)

    def reset_rate_limiter(self, url: str = None):
        """Reset rate limiter for URL or all domains"""
        self.rate_limiter.reset(url)
