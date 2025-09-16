import asyncio
from playwright.async_api import async_playwright, Playwright

async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto("https://www.macys.com/account/createaccount")
    await page.get_by_role("textbox", name="First name").click()
    await page.get_by_role("textbox", name="First name").fill("{{firstName}}")
    await page.get_by_role("textbox", name="Last name").click()
    await page.get_by_role("textbox", name="Last name").fill("{{lastName}}")
    await page.get_by_role("textbox", name="Email address").click()
    await page.get_by_role("textbox", name="Email address").fill("{{email}}")
    await page.get_by_role("textbox", name="Password").click()
    await page.get_by_role("textbox", name="Password").fill("{{password}}")
    await page.get_by_label("Birthday month").select_option("{{dobM}}")
    await page.get_by_label("Birthday day").select_option("{{dobD}}")
    await page.get_by_role("textbox", name="Phone Number").click()
    await page.get_by_role("textbox", name="Phone Number").fill("{{phoneNumber}}")
    await page.get_by_role("checkbox", name="My Preferences Text Alerts").check()
    await page.get_by_role("textbox", name="Mobile number").click()
    await page.get_by_role("textbox", name="Mobile number").fill("{{phoneNumber}}")
    await page.get_by_role("checkbox", name="My Preferences Promo Alerts").check()
    await page.get_by_role("checkbox", name="My Preferences Security Alerts").check()
    await page.get_by_role("checkbox", name="My Preferences Order Alerts").check()
    await page.get_by_role("button", name="create account").click()

    # ---------------------
    await context.close()
    await browser.close()

async def main() -> None:
    async with async_playwright() as playwright:
        await run(playwright)

asyncio.run(main())
