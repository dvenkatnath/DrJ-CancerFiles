import asyncio
from playwright.async_api import async_playwright

BASE = "http://localhost:4173"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        await page.goto(f"{BASE}/login")
        await page.fill('input[type="email"]', "admin@democlinic.io")
        await page.fill('input[type="password"]', "DemoPass123!")
        await page.click('button[type="submit"]')
        await page.wait_for_url(f"{BASE}/patients", timeout=10000)

        await page.goto(f"{BASE}/admin")
        await page.wait_for_selector("text=Admin / Settings")
        await page.wait_for_timeout(500)
        await page.screenshot(path="/tmp/shot_admin_users.png")

        await page.get_by_role("button", name="Audit Log", exact=True).click()
        await page.wait_for_timeout(500)
        await page.screenshot(path="/tmp/shot_admin_audit.png")

        await page.get_by_role("button", name="Ingestion Settings", exact=True).click()
        await page.wait_for_timeout(500)
        await page.screenshot(path="/tmp/shot_admin_settings.png")

        # tablet-width responsive check on patient summary
        await page.set_viewport_size({"width": 834, "height": 1100})
        await page.goto(f"{BASE}/patients")
        await page.wait_for_selector("text=Patients")
        await page.click('div.divide-y > button >> nth=0')
        await page.wait_for_timeout(800)
        await page.screenshot(path="/tmp/shot_tablet_summary.png")

        print("CONSOLE_ERRORS:", console_errors)
        await browser.close()

asyncio.run(main())
