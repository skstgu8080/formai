import asyncio
import re
from playwright.async_api import Playwright, async_playwright, expect


async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto("https://www.roboform.com/filling-test-all-fields")
    await page.locator("input[name=\"\\30 1___title\"]").click()
    await page.locator("input[name=\"\\30 1___title\"]").fill("ghkjhgkk")
    await page.locator("input[name=\"\\30 1___title\"]").press("Tab")
    await page.locator("input[name=\"\\30 2frstname\"]").fill("hksdhgkh")
    await page.locator("input[name=\"\\30 2frstname\"]").press("Tab")
    await page.locator("input[name=\"\\30 3middle_i\"]").fill("haksjghk")
    await page.locator("input[name=\"\\30 3middle_i\"]").press("Tab")
    await page.locator("input[name=\"\\30 4lastname\"]").fill("ahkghrkhzkdsj")
    await page.locator("input[name=\"\\30 4lastname\"]").press("CapsLock")
    await page.locator("input[name=\"\\30 4lastname\"]").press("Tab")
    await page.locator("input[name=\"\\30 4fullname\"]").fill("AHKGJHRKAG")
    await page.locator("input[name=\"\\30 4fullname\"]").press("Tab")
    await page.locator("input[name=\"\\30 5_company\"]").press("Tab")
    await page.locator("input[name=\"\\30 6position\"]").fill("GHKRJG")

    # ---------------------
    await context.close()
    await browser.close()


async def main() -> None:
    async with async_playwright() as playwright:
        await run(playwright)


asyncio.run(main())
