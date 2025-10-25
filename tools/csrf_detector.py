"""
CSRF Token Detector - Multi-strategy CSRF token detection
Supports: Laravel, Django, Rails, Spring, and generic patterns
"""
import re
from typing import Optional, Dict
from dataclasses import dataclass
import html.parser


@dataclass
class CSRFToken:
    """Represents a detected CSRF token"""
    name: str
    value: str
    location: str  # 'hidden_input', 'meta_tag', 'cookie', 'header'
    framework: Optional[str] = None  # 'laravel', 'django', 'rails', 'spring', etc.

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'value': self.value,
            'location': self.location,
            'framework': self.framework
        }


class CSRFDetector:
    """Multi-strategy CSRF token detection"""

    def __init__(self):
        # Common CSRF token field names
        self.common_names = [
            'csrf-token', 'csrf_token', 'csrftoken',
            '_csrf', '_token', 'authenticity_token',
            'csrf', 'token', 'xsrf-token', 'xsrf_token',
            'anti-csrf-token', '__requestverificationtoken'
        ]

    def detect(self, html: str, cookies: Dict[str, str] = None) -> Optional[CSRFToken]:
        """
        Auto-detect CSRF token using multiple strategies
        Returns first token found, or None if no token detected
        """
        if cookies is None:
            cookies = {}

        # Try framework-specific detection first (more reliable)
        for detector in [
            self.detect_laravel,
            self.detect_django,
            self.detect_rails,
            self.detect_spring
        ]:
            token = detector(html, cookies)
            if token:
                return token

        # Fall back to generic detection
        for detector in [
            self.detect_from_meta,
            self.detect_from_hidden_input,
            self.detect_from_cookies
        ]:
            token = detector(html, cookies)
            if token:
                return token

        return None

    def detect_laravel(self, html: str, cookies: Dict[str, str] = None) -> Optional[CSRFToken]:
        """
        Detect Laravel CSRF token
        Laravel uses: <meta name="csrf-token" content="...">
        """
        # Meta tag pattern
        meta_pattern = r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']'
        match = re.search(meta_pattern, html, re.IGNORECASE)
        if match:
            return CSRFToken(
                name='_token',  # Laravel form field name
                value=match.group(1),
                location='meta_tag',
                framework='laravel'
            )

        # Hidden input pattern
        input_pattern = r'<input[^>]*name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']'
        match = re.search(input_pattern, html, re.IGNORECASE)
        if match:
            return CSRFToken(
                name='_token',
                value=match.group(1),
                location='hidden_input',
                framework='laravel'
            )

        # Cookie pattern (Laravel uses XSRF-TOKEN)
        if cookies and 'XSRF-TOKEN' in cookies:
            return CSRFToken(
                name='X-XSRF-TOKEN',  # Header name
                value=cookies['XSRF-TOKEN'],
                location='cookie',
                framework='laravel'
            )

        return None

    def detect_django(self, html: str, cookies: Dict[str, str] = None) -> Optional[CSRFToken]:
        """
        Detect Django CSRF token
        Django uses: <input type="hidden" name="csrfmiddlewaretoken" value="...">
        """
        # Hidden input pattern
        input_pattern = r'<input[^>]*name=["\']csrfmiddlewaretoken["\'][^>]*value=["\']([^"\']+)["\']'
        match = re.search(input_pattern, html, re.IGNORECASE)
        if match:
            return CSRFToken(
                name='csrfmiddlewaretoken',
                value=match.group(1),
                location='hidden_input',
                framework='django'
            )

        # Cookie pattern (Django uses csrftoken)
        if cookies and 'csrftoken' in cookies:
            return CSRFToken(
                name='X-CSRFToken',  # Header name
                value=cookies['csrftoken'],
                location='cookie',
                framework='django'
            )

        return None

    def detect_rails(self, html: str, cookies: Dict[str, str] = None) -> Optional[CSRFToken]:
        """
        Detect Ruby on Rails CSRF token
        Rails uses: <meta name="csrf-token" content="...">
        And: <input type="hidden" name="authenticity_token" value="...">
        """
        # Meta tag pattern
        meta_pattern = r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']'
        match = re.search(meta_pattern, html, re.IGNORECASE)
        if match:
            return CSRFToken(
                name='authenticity_token',  # Rails form field name
                value=match.group(1),
                location='meta_tag',
                framework='rails'
            )

        # Hidden input pattern
        input_pattern = r'<input[^>]*name=["\']authenticity_token["\'][^>]*value=["\']([^"\']+)["\']'
        match = re.search(input_pattern, html, re.IGNORECASE)
        if match:
            return CSRFToken(
                name='authenticity_token',
                value=match.group(1),
                location='hidden_input',
                framework='rails'
            )

        return None

    def detect_spring(self, html: str, cookies: Dict[str, str] = None) -> Optional[CSRFToken]:
        """
        Detect Spring Framework CSRF token
        Spring uses: <input type="hidden" name="_csrf" value="...">
        """
        # Hidden input pattern
        input_pattern = r'<input[^>]*name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
        match = re.search(input_pattern, html, re.IGNORECASE)
        if match:
            return CSRFToken(
                name='_csrf',
                value=match.group(1),
                location='hidden_input',
                framework='spring'
            )

        # Meta tag pattern (some Spring apps)
        meta_pattern = r'<meta\s+name=["\']_csrf["\']\s+content=["\']([^"\']+)["\']'
        match = re.search(meta_pattern, html, re.IGNORECASE)
        if match:
            return CSRFToken(
                name='_csrf',
                value=match.group(1),
                location='meta_tag',
                framework='spring'
            )

        return None

    def detect_from_meta(self, html: str, cookies: Dict[str, str] = None) -> Optional[CSRFToken]:
        """
        Generic meta tag detection
        Pattern: <meta name="csrf-token" content="...">
        """
        for name in self.common_names:
            pattern = rf'<meta\s+name=["\']({name})["\']\s+content=["\']([^"\']+)["\']'
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return CSRFToken(
                    name=match.group(1),
                    value=match.group(2),
                    location='meta_tag'
                )

        return None

    def detect_from_hidden_input(self, html: str, cookies: Dict[str, str] = None) -> Optional[CSRFToken]:
        """
        Generic hidden input detection
        Pattern: <input type="hidden" name="csrf" value="...">
        """
        for name in self.common_names:
            # Try both orders (name then value, value then name)
            patterns = [
                rf'<input[^>]*name=["\']({name})["\'][^>]*value=["\']([^"\']+)["\']',
                rf'<input[^>]*value=["\']([^"\']+)["\'][^>]*name=["\']({name})["\']'
            ]

            for pattern in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    # Group order depends on pattern
                    if 'name=' in match.group(0)[:20]:
                        token_name = match.group(1)
                        token_value = match.group(2)
                    else:
                        token_value = match.group(1)
                        token_name = match.group(2)

                    return CSRFToken(
                        name=token_name,
                        value=token_value,
                        location='hidden_input'
                    )

        return None

    def detect_from_cookies(self, html: str, cookies: Dict[str, str] = None) -> Optional[CSRFToken]:
        """
        Detect CSRF token from cookies
        Common patterns: XSRF-TOKEN, csrftoken, csrf-token
        """
        if not cookies:
            return None

        for name in self.common_names:
            # Check both exact match and variations
            for cookie_name in cookies.keys():
                if cookie_name.lower().replace('-', '_') == name.replace('-', '_'):
                    return CSRFToken(
                        name=f'X-{cookie_name}',  # Header name convention
                        value=cookies[cookie_name],
                        location='cookie'
                    )

        return None

    def detect_all(self, html: str, cookies: Dict[str, str] = None) -> list[CSRFToken]:
        """
        Detect ALL CSRF tokens in the page
        Returns list of all detected tokens (may be empty)
        """
        if cookies is None:
            cookies = {}

        tokens = []

        # Try all detection methods
        all_detectors = [
            (self.detect_laravel, cookies),
            (self.detect_django, cookies),
            (self.detect_rails, cookies),
            (self.detect_spring, cookies),
            (self.detect_from_meta, cookies),
            (self.detect_from_hidden_input, cookies),
            (self.detect_from_cookies, cookies)
        ]

        for detector, args in all_detectors:
            try:
                token = detector(html, args) if args else detector(html)
                if token and token not in tokens:
                    tokens.append(token)
            except Exception:
                continue

        return tokens

    def validate_token(self, token: CSRFToken) -> bool:
        """
        Validate token format and value
        Returns True if token looks valid
        """
        if not token.value:
            return False

        # Check minimum length (most CSRF tokens are at least 20 chars)
        if len(token.value) < 10:
            return False

        # Check for suspicious values
        suspicious_values = ['null', 'undefined', 'test', '123456']
        if token.value.lower() in suspicious_values:
            return False

        return True

    def get_submission_format(self, token: CSRFToken) -> Dict[str, str]:
        """
        Get the correct format for submitting the CSRF token
        Returns dict with header or form field
        """
        if token.location == 'cookie':
            # Cookie-based tokens usually go in headers
            return {
                'type': 'header',
                'name': token.name,
                'value': token.value
            }
        else:
            # Meta tag and hidden input tokens go in form data
            return {
                'type': 'form_field',
                'name': token.name,
                'value': token.value
            }
