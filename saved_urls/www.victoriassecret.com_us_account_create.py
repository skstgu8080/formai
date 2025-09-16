import asyncio
import re
from playwright.async_api import Playwright, async_playwright, expect


async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(headless=False, slow_mo=300)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto("https://www.victoriassecret.com/us/account/create")
    await page.get_by_role("button", name="PREFERENCES").click()
    await page.get_by_role("button", name="Close").click()
    await page.get_by_role("button", name="OK").click()
    await page.get_by_role("textbox", name="First Name *").click()
    await page.get_by_role("textbox", name="First Name *").fill("{{firstname*}}")
    await page.get_by_role("textbox", name="Last Name *").click()
    await page.get_by_role("textbox", name="Last Name *").fill("{{lastname*}}")
    await page.get_by_role("textbox", name="Email Address *").click()
    await page.get_by_role("textbox", name="Email Address *").fill("{{emailaddress*}}")
    await page.get_by_role("textbox", name="Create Password *").click()
    await page.get_by_role("textbox", name="Create Password *").fill("{{createpassword*}}")
    await page.get_by_test_id("phone-number").click()
    await page.get_by_test_id("phone-number").fill("(435) 534-54355")
    await page.get_by_test_id("SubmitOrCreateAccount").click()

    # ---------------------
    await context.close()
    await browser.close()


async def main() -> None:
    async with async_playwright() as playwright:
        await run(playwright)


asyncio.run(main())
