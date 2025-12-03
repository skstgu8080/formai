"""
CAPTCHA Solver Module

Integrates with 2Captcha and Anti-Captcha services to solve CAPTCHAs during form automation.

Supports:
- reCAPTCHA v2 (checkbox)
- reCAPTCHA v3 (invisible)
- hCaptcha
- Image CAPTCHA
- Text CAPTCHA
"""

import asyncio
import logging
import time
import httpx
from typing import Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import json
import base64

logger = logging.getLogger(__name__)


@dataclass
class CaptchaResult:
    """Result of CAPTCHA solving attempt"""
    success: bool
    solution: Optional[str] = None
    captcha_id: Optional[str] = None
    cost: float = 0.0
    solve_time: float = 0.0
    error: Optional[str] = None


class CaptchaSolver:
    """
    CAPTCHA solving service integration.

    Supports 2Captcha and Anti-Captcha APIs.
    """

    # Service URLs
    SERVICES = {
        "2captcha": {
            "submit": "http://2captcha.com/in.php",
            "result": "http://2captcha.com/res.php",
        },
        "anticaptcha": {
            "submit": "https://api.anti-captcha.com/createTask",
            "result": "https://api.anti-captcha.com/getTaskResult",
        }
    }

    # Default timeouts
    DEFAULT_TIMEOUT = 120  # Max seconds to wait for solution
    POLL_INTERVAL = 5  # Seconds between result checks

    def __init__(self, service: str = "2captcha", api_key: Optional[str] = None):
        """
        Initialize CAPTCHA solver.

        Args:
            service: "2captcha" or "anticaptcha"
            api_key: API key for the service
        """
        self.service = service.lower()
        self.api_key = api_key
        self._load_api_key()

    def _load_api_key(self):
        """Load API key from config if not provided"""
        if self.api_key:
            return

        # Try to load from api_keys directory
        config_file = Path("api_keys") / f"{self.service}.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get("api_key")
            except Exception as e:
                logger.error(f"Error loading CAPTCHA API key: {e}")

    def is_configured(self) -> bool:
        """Check if the solver is properly configured"""
        return bool(self.api_key)

    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        invisible: bool = False
    ) -> CaptchaResult:
        """
        Solve reCAPTCHA v2 (checkbox or invisible).

        Args:
            site_key: The site key from the page
            page_url: URL of the page with CAPTCHA
            invisible: Whether this is invisible reCAPTCHA

        Returns:
            CaptchaResult with the g-recaptcha-response token
        """
        if not self.is_configured():
            return CaptchaResult(success=False, error="CAPTCHA service not configured")

        start_time = time.time()

        try:
            if self.service == "2captcha":
                result = await self._solve_2captcha_recaptcha(site_key, page_url, invisible)
            else:
                result = await self._solve_anticaptcha_recaptcha(site_key, page_url, invisible)

            result.solve_time = time.time() - start_time
            return result

        except Exception as e:
            logger.error(f"CAPTCHA solving error: {e}", exc_info=True)
            return CaptchaResult(
                success=False,
                error=str(e),
                solve_time=time.time() - start_time
            )

    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        action: str = "verify",
        min_score: float = 0.7
    ) -> CaptchaResult:
        """
        Solve reCAPTCHA v3 (invisible, score-based).

        Args:
            site_key: The site key from the page
            page_url: URL of the page
            action: The action parameter (e.g., "login", "submit")
            min_score: Minimum acceptable score (0.1-0.9)

        Returns:
            CaptchaResult with the token
        """
        if not self.is_configured():
            return CaptchaResult(success=False, error="CAPTCHA service not configured")

        start_time = time.time()

        try:
            if self.service == "2captcha":
                result = await self._solve_2captcha_recaptcha_v3(site_key, page_url, action, min_score)
            else:
                result = await self._solve_anticaptcha_recaptcha_v3(site_key, page_url, action, min_score)

            result.solve_time = time.time() - start_time
            return result

        except Exception as e:
            logger.error(f"CAPTCHA v3 solving error: {e}", exc_info=True)
            return CaptchaResult(
                success=False,
                error=str(e),
                solve_time=time.time() - start_time
            )

    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str
    ) -> CaptchaResult:
        """
        Solve hCaptcha.

        Args:
            site_key: The hCaptcha site key
            page_url: URL of the page

        Returns:
            CaptchaResult with the response token
        """
        if not self.is_configured():
            return CaptchaResult(success=False, error="CAPTCHA service not configured")

        start_time = time.time()

        try:
            if self.service == "2captcha":
                result = await self._solve_2captcha_hcaptcha(site_key, page_url)
            else:
                result = await self._solve_anticaptcha_hcaptcha(site_key, page_url)

            result.solve_time = time.time() - start_time
            return result

        except Exception as e:
            logger.error(f"hCaptcha solving error: {e}", exc_info=True)
            return CaptchaResult(
                success=False,
                error=str(e),
                solve_time=time.time() - start_time
            )

    async def solve_image_captcha(
        self,
        image_data: bytes,
        case_sensitive: bool = False,
        numeric_only: bool = False
    ) -> CaptchaResult:
        """
        Solve image-based CAPTCHA.

        Args:
            image_data: Raw image bytes
            case_sensitive: Whether solution is case-sensitive
            numeric_only: Whether solution contains only numbers

        Returns:
            CaptchaResult with the text solution
        """
        if not self.is_configured():
            return CaptchaResult(success=False, error="CAPTCHA service not configured")

        start_time = time.time()

        try:
            if self.service == "2captcha":
                result = await self._solve_2captcha_image(image_data, case_sensitive, numeric_only)
            else:
                result = await self._solve_anticaptcha_image(image_data, case_sensitive, numeric_only)

            result.solve_time = time.time() - start_time
            return result

        except Exception as e:
            logger.error(f"Image CAPTCHA solving error: {e}", exc_info=True)
            return CaptchaResult(
                success=False,
                error=str(e),
                solve_time=time.time() - start_time
            )

    # 2Captcha implementations

    async def _solve_2captcha_recaptcha(
        self,
        site_key: str,
        page_url: str,
        invisible: bool
    ) -> CaptchaResult:
        """Solve reCAPTCHA using 2Captcha"""
        async with httpx.AsyncClient() as client:
            # Submit task
            params = {
                "key": self.api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url,
                "json": 1
            }
            if invisible:
                params["invisible"] = 1

            response = await client.post(self.SERVICES["2captcha"]["submit"], data=params)
            result = response.json()

            if result.get("status") != 1:
                return CaptchaResult(success=False, error=result.get("error_text", "Submit failed"))

            captcha_id = result["request"]

            # Poll for result
            return await self._poll_2captcha_result(client, captcha_id)

    async def _solve_2captcha_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        action: str,
        min_score: float
    ) -> CaptchaResult:
        """Solve reCAPTCHA v3 using 2Captcha"""
        async with httpx.AsyncClient() as client:
            params = {
                "key": self.api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url,
                "version": "v3",
                "action": action,
                "min_score": min_score,
                "json": 1
            }

            response = await client.post(self.SERVICES["2captcha"]["submit"], data=params)
            result = response.json()

            if result.get("status") != 1:
                return CaptchaResult(success=False, error=result.get("error_text", "Submit failed"))

            captcha_id = result["request"]
            return await self._poll_2captcha_result(client, captcha_id)

    async def _solve_2captcha_hcaptcha(
        self,
        site_key: str,
        page_url: str
    ) -> CaptchaResult:
        """Solve hCaptcha using 2Captcha"""
        async with httpx.AsyncClient() as client:
            params = {
                "key": self.api_key,
                "method": "hcaptcha",
                "sitekey": site_key,
                "pageurl": page_url,
                "json": 1
            }

            response = await client.post(self.SERVICES["2captcha"]["submit"], data=params)
            result = response.json()

            if result.get("status") != 1:
                return CaptchaResult(success=False, error=result.get("error_text", "Submit failed"))

            captcha_id = result["request"]
            return await self._poll_2captcha_result(client, captcha_id)

    async def _solve_2captcha_image(
        self,
        image_data: bytes,
        case_sensitive: bool,
        numeric_only: bool
    ) -> CaptchaResult:
        """Solve image CAPTCHA using 2Captcha"""
        async with httpx.AsyncClient() as client:
            # Encode image as base64
            image_b64 = base64.b64encode(image_data).decode()

            params = {
                "key": self.api_key,
                "method": "base64",
                "body": image_b64,
                "json": 1
            }
            if case_sensitive:
                params["regsense"] = 1
            if numeric_only:
                params["numeric"] = 1

            response = await client.post(self.SERVICES["2captcha"]["submit"], data=params)
            result = response.json()

            if result.get("status") != 1:
                return CaptchaResult(success=False, error=result.get("error_text", "Submit failed"))

            captcha_id = result["request"]
            return await self._poll_2captcha_result(client, captcha_id)

    async def _poll_2captcha_result(
        self,
        client: httpx.AsyncClient,
        captcha_id: str
    ) -> CaptchaResult:
        """Poll 2Captcha for result"""
        start_time = time.time()

        while time.time() - start_time < self.DEFAULT_TIMEOUT:
            await asyncio.sleep(self.POLL_INTERVAL)

            params = {
                "key": self.api_key,
                "action": "get",
                "id": captcha_id,
                "json": 1
            }

            response = await client.get(self.SERVICES["2captcha"]["result"], params=params)
            result = response.json()

            if result.get("status") == 1:
                return CaptchaResult(
                    success=True,
                    solution=result["request"],
                    captcha_id=captcha_id
                )
            elif result.get("request") != "CAPCHA_NOT_READY":
                return CaptchaResult(
                    success=False,
                    error=result.get("error_text", result.get("request", "Unknown error")),
                    captcha_id=captcha_id
                )

        return CaptchaResult(success=False, error="Timeout waiting for solution", captcha_id=captcha_id)

    # Anti-Captcha implementations

    async def _solve_anticaptcha_recaptcha(
        self,
        site_key: str,
        page_url: str,
        invisible: bool
    ) -> CaptchaResult:
        """Solve reCAPTCHA using Anti-Captcha"""
        async with httpx.AsyncClient() as client:
            task_type = "RecaptchaV2TaskProxyless"
            if invisible:
                task_type = "RecaptchaV2EnterpriseTaskProxyless"

            payload = {
                "clientKey": self.api_key,
                "task": {
                    "type": task_type,
                    "websiteURL": page_url,
                    "websiteKey": site_key,
                    "isInvisible": invisible
                }
            }

            response = await client.post(self.SERVICES["anticaptcha"]["submit"], json=payload)
            result = response.json()

            if result.get("errorId") != 0:
                return CaptchaResult(success=False, error=result.get("errorDescription", "Submit failed"))

            task_id = result["taskId"]
            return await self._poll_anticaptcha_result(client, task_id)

    async def _solve_anticaptcha_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        action: str,
        min_score: float
    ) -> CaptchaResult:
        """Solve reCAPTCHA v3 using Anti-Captcha"""
        async with httpx.AsyncClient() as client:
            payload = {
                "clientKey": self.api_key,
                "task": {
                    "type": "RecaptchaV3TaskProxyless",
                    "websiteURL": page_url,
                    "websiteKey": site_key,
                    "minScore": min_score,
                    "pageAction": action
                }
            }

            response = await client.post(self.SERVICES["anticaptcha"]["submit"], json=payload)
            result = response.json()

            if result.get("errorId") != 0:
                return CaptchaResult(success=False, error=result.get("errorDescription", "Submit failed"))

            task_id = result["taskId"]
            return await self._poll_anticaptcha_result(client, task_id)

    async def _solve_anticaptcha_hcaptcha(
        self,
        site_key: str,
        page_url: str
    ) -> CaptchaResult:
        """Solve hCaptcha using Anti-Captcha"""
        async with httpx.AsyncClient() as client:
            payload = {
                "clientKey": self.api_key,
                "task": {
                    "type": "HCaptchaTaskProxyless",
                    "websiteURL": page_url,
                    "websiteKey": site_key
                }
            }

            response = await client.post(self.SERVICES["anticaptcha"]["submit"], json=payload)
            result = response.json()

            if result.get("errorId") != 0:
                return CaptchaResult(success=False, error=result.get("errorDescription", "Submit failed"))

            task_id = result["taskId"]
            return await self._poll_anticaptcha_result(client, task_id)

    async def _solve_anticaptcha_image(
        self,
        image_data: bytes,
        case_sensitive: bool,
        numeric_only: bool
    ) -> CaptchaResult:
        """Solve image CAPTCHA using Anti-Captcha"""
        async with httpx.AsyncClient() as client:
            image_b64 = base64.b64encode(image_data).decode()

            payload = {
                "clientKey": self.api_key,
                "task": {
                    "type": "ImageToTextTask",
                    "body": image_b64,
                    "case": case_sensitive,
                    "numeric": 1 if numeric_only else 0
                }
            }

            response = await client.post(self.SERVICES["anticaptcha"]["submit"], json=payload)
            result = response.json()

            if result.get("errorId") != 0:
                return CaptchaResult(success=False, error=result.get("errorDescription", "Submit failed"))

            task_id = result["taskId"]
            return await self._poll_anticaptcha_result(client, task_id)

    async def _poll_anticaptcha_result(
        self,
        client: httpx.AsyncClient,
        task_id: int
    ) -> CaptchaResult:
        """Poll Anti-Captcha for result"""
        start_time = time.time()

        while time.time() - start_time < self.DEFAULT_TIMEOUT:
            await asyncio.sleep(self.POLL_INTERVAL)

            payload = {
                "clientKey": self.api_key,
                "taskId": task_id
            }

            response = await client.post(self.SERVICES["anticaptcha"]["result"], json=payload)
            result = response.json()

            if result.get("errorId") != 0:
                return CaptchaResult(
                    success=False,
                    error=result.get("errorDescription", "Unknown error"),
                    captcha_id=str(task_id)
                )

            if result.get("status") == "ready":
                solution = result.get("solution", {})
                # Extract the appropriate response
                token = (
                    solution.get("gRecaptchaResponse") or
                    solution.get("text") or
                    solution.get("token")
                )
                return CaptchaResult(
                    success=True,
                    solution=token,
                    captcha_id=str(task_id),
                    cost=result.get("cost", 0)
                )

        return CaptchaResult(
            success=False,
            error="Timeout waiting for solution",
            captcha_id=str(task_id)
        )

    async def get_balance(self) -> Optional[float]:
        """Get current balance from the CAPTCHA service"""
        if not self.is_configured():
            return None

        try:
            async with httpx.AsyncClient() as client:
                if self.service == "2captcha":
                    params = {"key": self.api_key, "action": "getbalance", "json": 1}
                    response = await client.get(self.SERVICES["2captcha"]["result"], params=params)
                    result = response.json()
                    if result.get("status") == 1:
                        return float(result["request"])
                else:
                    payload = {"clientKey": self.api_key}
                    response = await client.post(
                        "https://api.anti-captcha.com/getBalance",
                        json=payload
                    )
                    result = response.json()
                    if result.get("errorId") == 0:
                        return result.get("balance")

            return None
        except Exception as e:
            logger.error(f"Error getting CAPTCHA balance: {e}")
            return None


# CAPTCHA Detection helpers

class CaptchaDetector:
    """Detect CAPTCHAs on a page"""

    @staticmethod
    def detect_recaptcha_v2(page_source: str) -> Optional[str]:
        """
        Detect reCAPTCHA v2 and extract site key.

        Returns site key if found, None otherwise.
        """
        import re

        # Look for data-sitekey attribute
        patterns = [
            r'data-sitekey="([^"]+)"',
            r"data-sitekey='([^']+)'",
            r'class="g-recaptcha"[^>]*data-sitekey="([^"]+)"',
        ]

        for pattern in patterns:
            match = re.search(pattern, page_source)
            if match:
                return match.group(1)

        return None

    @staticmethod
    def detect_recaptcha_v3(page_source: str) -> Optional[str]:
        """
        Detect reCAPTCHA v3 and extract site key.

        Returns site key if found, None otherwise.
        """
        import re

        patterns = [
            r'grecaptcha\.execute\(["\']([^"\']+)["\']',
            r'render=([0-9A-Za-z_-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, page_source)
            if match:
                return match.group(1)

        return None

    @staticmethod
    def detect_hcaptcha(page_source: str) -> Optional[str]:
        """
        Detect hCaptcha and extract site key.

        Returns site key if found, None otherwise.
        """
        import re

        patterns = [
            r'data-sitekey="([^"]+)"[^>]*class="[^"]*h-captcha',
            r'class="[^"]*h-captcha[^"]*"[^>]*data-sitekey="([^"]+)"',
            r'hcaptcha\.com/1/api\.js\?[^"]*sitekey=([^&"]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, page_source)
            if match:
                return match.group(1)

        return None


# Global instance
_solver = None

def get_captcha_solver(service: str = "2captcha") -> CaptchaSolver:
    """Get or create global CaptchaSolver instance"""
    global _solver
    if _solver is None or _solver.service != service:
        _solver = CaptchaSolver(service=service)
    return _solver
