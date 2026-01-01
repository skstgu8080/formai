#!/usr/bin/env python3
"""
FormAI CLI - Fill web forms from the terminal

Usage:
    python cli.py sites                    # List all sites
    python cli.py profiles                 # List all profiles
    python cli.py fill <site_id>           # Fill single site (headless)
    python cli.py fill <site_id> --visible # Fill with browser visible
    python cli.py fill-all                 # Fill all enabled sites
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.sites_manager import SitesManager
from tools.simple_autofill import SimpleAutofill
from database import init_db, ProfileRepository, FillHistoryRepository
import time


def load_profiles():
    """Load all profiles from database."""
    init_db()
    profiles = {}
    for profile in ProfileRepository.get_all():
        profiles[profile.get('id', '')] = profile
    return profiles


def load_profiles_old():
    """Load all profiles from JSON files (deprecated)."""
    profiles = {}
    profiles_dir = Path("profiles")
    if profiles_dir.exists():
        for file in profiles_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    profile = json.load(f)
                    profiles[profile.get('id', file.stem)] = profile
            except Exception as e:
                print(f"Error loading {file}: {e}")
    return profiles


def list_sites():
    """List all sites."""
    sm = SitesManager()
    sites = sm.get_all_sites()

    print(f"\n{'='*80}")
    print(f"{'SITES':^80}")
    print(f"{'='*80}")
    print(f"{'ID':<10} | {'Name':<30} | {'Status':<10} | {'Fields':<6}")
    print(f"{'-'*80}")

    for s in sites:
        sid = s.get('id', '')[:8]
        name = s.get('name', '')[:28]
        status = s.get('last_status', 'pending') or 'pending'
        fields = s.get('fields_filled', 0)
        enabled = '[ON]' if s.get('enabled', True) else '[OFF]'
        print(f"{sid:<10} | {name:<30} | {status:<10} | {fields:<6} {enabled}")

    stats = sm.get_stats()
    print(f"\nTotal: {stats['total']} sites | Enabled: {stats['enabled']} | Success: {stats['success']} | Failed: {stats['failed']}")


def list_profiles():
    """List all profiles."""
    profiles = load_profiles()

    print(f"\n{'='*60}")
    print(f"{'PROFILES':^60}")
    print(f"{'='*60}")
    print(f"{'ID':<25} | {'Name':<15} | {'Email':<20}")
    print(f"{'-'*60}")

    for pid, p in profiles.items():
        name = p.get('firstName', '') + ' ' + p.get('lastName', '')
        email = p.get('email', '')[:18]
        print(f"{pid[:23]:<25} | {name[:13]:<15} | {email:<20}")

    print(f"\nTotal: {len(profiles)} profiles")


async def fill_site(site_id: str, profile_id: str = None, headless: bool = True, submit: bool = False):
    """Fill a site with a profile and optionally submit."""
    sm = SitesManager()
    site = sm.get_site(site_id)

    if not site:
        # Try partial match
        for s in sm.get_all_sites():
            if s.get('id', '').startswith(site_id):
                site = s
                break

    if not site:
        print(f"ERROR: Site not found: {site_id}")
        return False

    profiles = load_profiles()

    if profile_id:
        profile = profiles.get(profile_id)
        if not profile:
            # Try partial match
            for pid, p in profiles.items():
                if pid.startswith(profile_id):
                    profile = p
                    break
    else:
        # Use first profile
        profile = list(profiles.values())[0] if profiles else None

    if not profile:
        print(f"ERROR: No profile found")
        return False

    url = site.get('url', 'Unknown')
    pname = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
    if not pname:
        pname = profile.get('name', profile.get('id', 'Unknown'))

    print(f"\n{'='*60}")
    print(f"FILLING: {site.get('name', site_id)}")
    print(f"URL: {url}")
    print(f"PROFILE: {pname} ({profile.get('email', '')})")
    print(f"MODE: {'Headless' if headless else 'Visible'}{' + SUBMIT' if submit else ''}")
    print(f"{'='*60}\n")

    engine = SimpleAutofill(headless=headless, submit=submit)
    start_time = time.time()

    try:
        result = await engine.fill(url, profile)
        duration_ms = int((time.time() - start_time) * 1000)

        # Update site status
        sm.update_site_status(
            site['id'],
            "success" if result.success else "failed",
            result.fields_filled
        )

        # Log to fill history
        FillHistoryRepository.record(
            site_id=site['id'],
            profile_id=profile.get('id', ''),
            url=url,
            success=result.success,
            fields_filled=result.fields_filled,
            error=result.error,
            duration_ms=duration_ms
        )

        print(f"\n{'='*60}")
        print(f"RESULT: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"{'='*60}")
        print(f"  Fields filled: {result.fields_filled}")
        if hasattr(result, 'submitted'):
            print(f"  Form submitted: {'Yes' if result.submitted else 'No'}")
        if hasattr(result, 'final_url') and result.final_url and result.final_url != url:
            print(f"  Final URL: {result.final_url}")
        print(f"  Duration: {duration_ms}ms")
        if result.error:
            print(f"  Error: {result.error}")

        # Show missing fields that need to be added to profile
        if hasattr(result, 'missing_fields') and result.missing_fields:
            print(f"\n  MISSING PROFILE FIELDS (add to profile):")
            for field in result.missing_fields:
                name = field.get('name', '')
                placeholder = field.get('placeholder', '')
                label = field.get('label', '')
                hint = placeholder or label or ''
                print(f"    - {name}" + (f" ({hint})" if hint else ""))

        print(f"{'='*60}\n")

        return result.success

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        print(f"\nERROR: {e}")
        sm.update_site_status(site['id'], "failed", 0)

        # Log error to fill history
        FillHistoryRepository.record(
            site_id=site['id'],
            profile_id=profile.get('id', ''),
            url=url,
            success=False,
            fields_filled=0,
            error=str(e),
            duration_ms=duration_ms
        )
        return False


async def fill_all_sites(profile_id: str = None, headless: bool = True, submit: bool = False):
    """Fill all enabled sites and optionally submit."""
    sm = SitesManager()
    sites = sm.get_enabled_sites()

    if not sites:
        print("No enabled sites to fill")
        return

    profiles = load_profiles()

    if profile_id:
        profile = profiles.get(profile_id)
        if not profile:
            for pid, p in profiles.items():
                if pid.startswith(profile_id):
                    profile = p
                    break
    else:
        profile = list(profiles.values())[0] if profiles else None

    if not profile:
        print("ERROR: No profile found")
        return

    pname = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
    print(f"\n{'='*60}")
    print(f"BATCH FILL: {len(sites)} sites")
    print(f"PROFILE: {pname} ({profile.get('email', '')})")
    print(f"MODE: {'Headless' if headless else 'Visible'}{' + SUBMIT' if submit else ''}")
    print(f"{'='*60}\n")

    success_count = 0
    fail_count = 0
    submitted_count = 0

    for i, site in enumerate(sites, 1):
        print(f"[{i}/{len(sites)}] {site.get('name', site['id'])}...")

        engine = SimpleAutofill(headless=headless, submit=submit)
        try:
            result = await engine.fill(site['url'], profile)
            sm.update_site_status(
                site['id'],
                "success" if result.success else "failed",
                result.fields_filled
            )

            if result.success:
                success_count += 1
                submitted_str = ""
                if hasattr(result, 'submitted') and result.submitted:
                    submitted_count += 1
                    submitted_str = " [SUBMITTED]"
                print(f"  [OK] Filled {result.fields_filled} fields{submitted_str}")
            else:
                fail_count += 1
                print(f"  [FAIL] {result.error}")

        except Exception as e:
            fail_count += 1
            sm.update_site_status(site['id'], "failed", 0)
            print(f"  [ERROR] {e}")

    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {success_count} success, {fail_count} failed")
    if submit:
        print(f"FORMS SUBMITTED: {submitted_count}")
    print(f"{'='*60}\n")


async def setup_email(provider: str = "gmail"):
    """Open browser for user to sign into their email."""
    from playwright.async_api import async_playwright

    # Email provider URLs
    providers = {
        "gmail": "https://mail.google.com",
        "outlook": "https://outlook.live.com",
        "yahoo": "https://mail.yahoo.com",
    }

    url = providers.get(provider.lower(), providers["gmail"])
    state_file = Path("data/email_session.json")

    print(f"\n{'='*60}")
    print(f"EMAIL SETUP: {provider.upper()}")
    print(f"{'='*60}")
    print(f"1. Browser will open to {url}")
    print(f"2. Sign in to your email account")
    print(f"3. Once logged in, press ENTER in this terminal")
    print(f"4. Session will be saved for email verification")
    print(f"{'='*60}\n")

    async with async_playwright() as p:
        # Launch visible browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to email
        await page.goto(url)

        # Wait for user to sign in
        input("Press ENTER after you've signed in to your email...")

        # Save session state
        state_file.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(state_file))

        print(f"\n[OK] Email session saved to {state_file}")
        print("You can now use 'verify-email' command after form fills.\n")

        await browser.close()


async def verify_email(search_term: str = None):
    """Check email for verification links."""
    from playwright.async_api import async_playwright

    state_file = Path("data/email_session.json")

    if not state_file.exists():
        print("ERROR: No email session found. Run 'setup-email' first.")
        return None

    print(f"\n{'='*60}")
    print("CHECKING EMAIL FOR VERIFICATION")
    print(f"{'='*60}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state=str(state_file))
        page = await context.new_page()

        # Go to Gmail
        await page.goto("https://mail.google.com")
        await asyncio.sleep(3)

        # Search for verification emails if search term provided
        if search_term:
            try:
                search_box = page.locator('input[aria-label="Search mail"]')
                await search_box.fill(f"{search_term} verify")
                await search_box.press("Enter")
                await asyncio.sleep(2)
            except:
                pass

        print("Browser open - find and click verification link.")
        print("Press ENTER when done...")
        input()

        await browser.close()
        print("[OK] Email verification complete.\n")


def main():
    parser = argparse.ArgumentParser(description='FormAI CLI - Fill web forms from terminal')
    parser.add_argument('command', nargs='?', default='help',
                        help='Command: sites, profiles, fill, fill-all, setup-email, verify-email')
    parser.add_argument('site_id', nargs='?', help='Site ID to fill')
    parser.add_argument('--profile', '-p', help='Profile ID to use')
    # Always run headless for speed
    parser.add_argument('--submit', '-s', action='store_true', default=True,
                        help='Submit form after filling (default: True)')
    parser.add_argument('--no-submit', action='store_true',
                        help='Do NOT submit form after filling')
    parser.add_argument('--provider', default='gmail',
                        help='Email provider: gmail, outlook, yahoo')

    args = parser.parse_args()

    if args.command == 'help' or args.command == '-h':
        parser.print_help()
        print("\nExamples:")
        print("  python cli.py sites                    # List all sites")
        print("  python cli.py profiles                 # List all profiles")
        print("  python cli.py fill abc123              # Fill site (headless)")
        print("  python cli.py fill abc123 --visible    # Fill with browser visible")
        print("  python cli.py fill abc123 --submit     # Fill AND create account")
        print("  python cli.py fill abc123 -s --visible # Create account with visible browser")
        print("  python cli.py fill-all --submit        # Create accounts on all sites")
        print("  python cli.py setup-email              # Sign in to email (Gmail default)")
        print("  python cli.py verify-email             # Check for verification emails")
        return

    if args.command == 'sites':
        list_sites()
        return

    if args.command == 'profiles':
        list_profiles()
        return

    if args.command == 'fill':
        if not args.site_id:
            print("ERROR: Please provide a site ID")
            print("Usage: python cli.py fill <site_id>")
            return
        submit = not args.no_submit
        asyncio.run(fill_site(args.site_id, args.profile, True, submit))  # Always headless
        return

    if args.command == 'fill-all':
        submit = not args.no_submit
        asyncio.run(fill_all_sites(args.profile, True, submit))  # Always headless
        return

    if args.command == 'setup-email':
        asyncio.run(setup_email(args.provider))
        return

    if args.command == 'verify-email':
        search_term = args.site_id  # Reuse site_id arg as search term
        asyncio.run(verify_email(search_term))
        return

    # Unknown command
    print(f"Unknown command: {args.command}")
    print("Use 'python cli.py help' for usage")


if __name__ == '__main__':
    main()
