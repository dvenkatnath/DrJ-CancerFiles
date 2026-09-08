import asyncio
from playwright.async_api import async_playwright

BASE = "http://localhost:4173"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = await browser.new_page(viewport={"width": 1200, "height": 1000})
        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        await page.goto(f"{BASE}/login")
        await page.fill('input[type="email"]', "physician@democlinic.io")
        await page.fill('input[type="password"]', "DemoPass123!")
        await page.click('button[type="submit"]')
        await page.wait_for_url(f"{BASE}/patients", timeout=10000)

        await page.click("text=James Whitfield")
        await page.wait_for_url("**/summary", timeout=10000)
        await page.wait_for_selector("text=Lab trends", timeout=10000)
        await page.wait_for_timeout(500)
        await page.screenshot(path="/tmp/shot_trends_james.png", full_page=True)

        print("CONSOLE_ERRORS:", console_errors)
        await browser.close()

asyncio.run(main())
