import asyncio
import re
from playwright.async_api import Playwright, async_playwright, expect


async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(headless=False, slow_mo=300)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto("https://www.facebook.com/r.php?entry_point=login")
    await page.get_by_role("textbox", name="First name").click()
    await page.get_by_role("textbox", name="First name").fill("{{firstName}}")
    await page.get_by_role("textbox", name="Last name").click()
    await page.get_by_role("textbox", name="Last name").fill("{{lastName}}")
    await page.get_by_label("Month").select_option("{{month}}")
    await page.get_by_label("Day").select_option("{{day}}")
    await page.get_by_label("Year").select_option("{{year}}")
    await page.get_by_role("radio", name="Male", exact=True).check()
    await page.get_by_role("textbox", name="Mobile number or email").click()
    await page.get_by_role("textbox", name="Mobile number or email").fill("{{mobilenumberoremail}}")
    await page.get_by_role("textbox", name="New password").click()
    await page.get_by_role("textbox", name="New password").fill("{{newpassword}}")
    await page.get_by_role("button", name="Sign Up").click()

    # ---------------------
    await context.close()
    await browser.close()


async def main() -> None:
    async with async_playwright() as playwright:
        await run(playwright)


asyncio.run(main())
