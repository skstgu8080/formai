"""
TempEmailHandler - Auto-generate and verify temporary emails.

Phase 3 Feature: Handle "Check your email" verification flows.

Uses mail.tm free API to:
1. Generate disposable email addresses
2. Poll inbox for verification emails
3. Extract verification links/codes
4. Complete the verification

NOTE: This is for testing/development purposes.
Always respect website terms of service.
"""

import asyncio
import json
import logging
import re
import secrets
import string
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import httpx

logger = logging.getLogger("email-handler")


@dataclass
class TempEmail:
    """Represents a temporary email account."""
    address: str
    password: str
    token: Optional[str] = None
    account_id: Optional[str] = None


@dataclass
class VerificationResult:
    """Result of email verification extraction."""
    found: bool = False
    verification_type: str = "none"  # "link", "code", "both"
    link: Optional[str] = None
    code: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    raw_body: Optional[str] = None


class TempEmailHandler:
    """
    Handles temporary email creation and verification polling.

    Uses mail.tm API (free, no auth required for basic operations).
    """

    # mail.tm API base
    API_BASE = "https://api.mail.tm"

    # Common verification patterns
    VERIFICATION_LINK_PATTERNS = [
        r'https?://[^\s<>"\']+(?:verify|confirm|activate|validation)[^\s<>"\']*',
        r'https?://[^\s<>"\']+(?:token|code|key)=[^\s<>"\']+',
        r'href=["\']?(https?://[^\s<>"\']+(?:verify|confirm|activate)[^\s<>"\']*)["\']?',
    ]

    VERIFICATION_CODE_PATTERNS = [
        r'(?:code|otp|pin|verification)[\s:]+([A-Z0-9]{4,8})',
        r'(?:enter|use)\s+(?:the\s+)?(?:code|otp)[\s:]+([A-Z0-9]{4,8})',
        r'\b([0-9]{4,8})\b',  # Numeric codes
        r'\b([A-Z0-9]{6})\b',  # Alphanumeric codes
    ]

    # Email keywords indicating verification
    VERIFICATION_KEYWORDS = [
        'verify', 'confirm', 'activate', 'validation', 'welcome',
        'registration', 'sign up', 'account', 'email address'
    ]

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.current_email: Optional[TempEmail] = None

    async def create_email(self, custom_prefix: str = None) -> TempEmail:
        """
        Create a new temporary email address.

        Args:
            custom_prefix: Optional prefix for the email (default: random)

        Returns:
            TempEmail with address and credentials
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # First, get available domains
                domains_resp = await client.get(f"{self.API_BASE}/domains")
                if domains_resp.status_code != 200:
                    raise Exception(f"Could not get domains: {domains_resp.status_code}")

                domains = domains_resp.json().get("hydra:member", [])
                if not domains:
                    raise Exception("No domains available")

                domain = domains[0].get("domain", "mail.tm")

                # Generate email address
                if custom_prefix:
                    prefix = custom_prefix.lower().replace(" ", "")
                else:
                    prefix = self._generate_random_prefix()

                address = f"{prefix}@{domain}"
                password = self._generate_password()

                # Create account
                account_resp = await client.post(
                    f"{self.API_BASE}/accounts",
                    json={
                        "address": address,
                        "password": password
                    }
                )

                if account_resp.status_code not in (200, 201):
                    # Try with a different prefix
                    prefix = self._generate_random_prefix()
                    address = f"{prefix}@{domain}"

                    account_resp = await client.post(
                        f"{self.API_BASE}/accounts",
                        json={
                            "address": address,
                            "password": password
                        }
                    )

                    if account_resp.status_code not in (200, 201):
                        raise Exception(f"Could not create account: {account_resp.text}")

                account_data = account_resp.json()

                # Get auth token
                token_resp = await client.post(
                    f"{self.API_BASE}/token",
                    json={
                        "address": address,
                        "password": password
                    }
                )

                token = None
                if token_resp.status_code == 200:
                    token = token_resp.json().get("token")

                self.current_email = TempEmail(
                    address=address,
                    password=password,
                    token=token,
                    account_id=account_data.get("id")
                )

                logger.info(f"[Email] Created temp email: {address}")
                return self.current_email

        except Exception as e:
            logger.error(f"[Email] Error creating email: {e}")
            # Fallback: generate a fake email (won't receive but useful for form filling)
            fallback = TempEmail(
                address=f"{self._generate_random_prefix()}@tempmail.local",
                password=self._generate_password()
            )
            self.current_email = fallback
            return fallback

    async def wait_for_verification(
        self,
        timeout: int = 120,
        check_interval: int = 5
    ) -> VerificationResult:
        """
        Poll inbox for verification email.

        Args:
            timeout: Max seconds to wait for email
            check_interval: Seconds between inbox checks

        Returns:
            VerificationResult with link/code if found
        """
        if not self.current_email or not self.current_email.token:
            logger.warning("[Email] No active email session")
            return VerificationResult()

        start_time = asyncio.get_event_loop().time()
        checked_ids = set()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {self.current_email.token}"}

                while (asyncio.get_event_loop().time() - start_time) < timeout:
                    # Get messages
                    messages_resp = await client.get(
                        f"{self.API_BASE}/messages",
                        headers=headers
                    )

                    if messages_resp.status_code != 200:
                        logger.warning(f"[Email] Could not get messages: {messages_resp.status_code}")
                        await asyncio.sleep(check_interval)
                        continue

                    messages = messages_resp.json().get("hydra:member", [])

                    for msg in messages:
                        msg_id = msg.get("id")
                        if msg_id in checked_ids:
                            continue

                        checked_ids.add(msg_id)

                        # Check if this looks like a verification email
                        subject = msg.get("subject", "").lower()
                        sender = msg.get("from", {}).get("address", "")

                        is_verification = any(kw in subject for kw in self.VERIFICATION_KEYWORDS)

                        if is_verification:
                            # Get full message
                            msg_resp = await client.get(
                                f"{self.API_BASE}/messages/{msg_id}",
                                headers=headers
                            )

                            if msg_resp.status_code == 200:
                                full_msg = msg_resp.json()
                                body = full_msg.get("text", "") or full_msg.get("html", "")

                                result = self._extract_verification(body)
                                result.subject = subject
                                result.sender = sender
                                result.raw_body = body[:500]  # First 500 chars

                                if result.found:
                                    logger.info(f"[Email] Found verification: {result.verification_type}")
                                    return result

                    logger.debug(f"[Email] Checked {len(messages)} messages, waiting...")
                    await asyncio.sleep(check_interval)

        except Exception as e:
            logger.error(f"[Email] Error polling inbox: {e}")

        return VerificationResult()

    def _extract_verification(self, body: str) -> VerificationResult:
        """Extract verification link/code from email body."""
        result = VerificationResult()

        if not body:
            return result

        # Look for verification links
        for pattern in self.VERIFICATION_LINK_PATTERNS:
            matches = re.findall(pattern, body, re.IGNORECASE)
            if matches:
                # Get the longest match (more likely to be complete)
                result.link = max(matches, key=len)
                result.found = True
                result.verification_type = "link"
                break

        # Look for verification codes
        for pattern in self.VERIFICATION_CODE_PATTERNS:
            matches = re.findall(pattern, body, re.IGNORECASE)
            if matches:
                # Filter out common false positives
                for match in matches:
                    if len(match) >= 4 and not match.lower() in ('http', 'https', 'www'):
                        result.code = match
                        result.found = True
                        if result.link:
                            result.verification_type = "both"
                        else:
                            result.verification_type = "code"
                        break

        return result

    async def complete_verification(self, page, verification: VerificationResult) -> Tuple[bool, str]:
        """
        Complete the verification using extracted link/code.

        Args:
            page: Playwright page object
            verification: VerificationResult with link/code

        Returns:
            (success, message) tuple
        """
        try:
            if verification.link:
                # Navigate to verification link
                logger.info(f"[Email] Navigating to verification link...")
                await page.goto(verification.link, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                # Check for success indicators
                page_text = await page.evaluate("document.body.innerText")
                page_text_lower = page_text.lower()

                if any(word in page_text_lower for word in ['verified', 'confirmed', 'success', 'thank you', 'activated']):
                    return True, "Email verified via link"
                elif any(word in page_text_lower for word in ['error', 'failed', 'invalid', 'expired']):
                    return False, "Verification link failed"
                else:
                    return True, "Verification link clicked (status unclear)"

            elif verification.code:
                # Try to find verification code input and fill it
                logger.info(f"[Email] Looking for code input to fill: {verification.code}")

                code_selectors = [
                    'input[name*="code"]',
                    'input[name*="otp"]',
                    'input[name*="verify"]',
                    'input[placeholder*="code"]',
                    'input[placeholder*="otp"]',
                    'input[type="text"]',  # Fallback
                ]

                for selector in code_selectors:
                    try:
                        input_el = await page.query_selector(selector)
                        if input_el and await input_el.is_visible():
                            await input_el.fill(verification.code)
                            logger.info(f"[Email] Filled code in {selector}")

                            # Try to submit
                            submit_btn = await page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Verify")')
                            if submit_btn:
                                await submit_btn.click()
                                await asyncio.sleep(2)

                            return True, f"Verification code filled: {verification.code}"
                    except:
                        continue

                return False, "Could not find code input field"

            return False, "No verification link or code found"

        except Exception as e:
            return False, f"Verification error: {e}"

    async def get_inbox(self) -> List[Dict]:
        """Get all messages in the inbox."""
        if not self.current_email or not self.current_email.token:
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {self.current_email.token}"}
                resp = await client.get(f"{self.API_BASE}/messages", headers=headers)

                if resp.status_code == 200:
                    return resp.json().get("hydra:member", [])

        except Exception as e:
            logger.error(f"[Email] Error getting inbox: {e}")

        return []

    def _generate_random_prefix(self) -> str:
        """Generate random email prefix."""
        chars = string.ascii_lowercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(10))

    def _generate_password(self) -> str:
        """Generate secure password."""
        chars = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(secrets.choice(chars) for _ in range(16))

    def get_current_address(self) -> Optional[str]:
        """Get current temp email address."""
        return self.current_email.address if self.current_email else None

    async def cleanup(self):
        """Delete the temp email account."""
        if not self.current_email or not self.current_email.token:
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"Authorization": f"Bearer {self.current_email.token}"}
                await client.delete(
                    f"{self.API_BASE}/accounts/{self.current_email.account_id}",
                    headers=headers
                )
                logger.info(f"[Email] Deleted temp email: {self.current_email.address}")
        except Exception as e:
            logger.warning(f"[Email] Could not delete account: {e}")

        self.current_email = None


# Convenience function for quick use
async def create_temp_email() -> str:
    """Quick helper to create a temp email and return the address."""
    handler = TempEmailHandler()
    email = await handler.create_email()
    return email.address
