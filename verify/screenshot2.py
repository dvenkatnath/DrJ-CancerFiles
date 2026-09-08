import asyncio
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:4173"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium", headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        await page.goto(f"{BASE}/login")
        await page.fill("#email", "physician@democlinic.io")
        await page.fill("#password", "DemoPass123!")
        await page.click("button[type=submit]")
        await page.wait_for_url("**/patients", timeout=10000)

        await page.click("text=Maria Alvarez")
        await page.wait_for_url("**/summary", timeout=10000)

        # Documents -> click a row for preview pane
        await page.click("text=Documents")
        await page.wait_for_timeout(500)
        await page.click("text=Oncology Visit Note - 2024-01-10.txt")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="/tmp/shot_doc_preview.png", full_page=True)

        # Ask -> new conversation -> starter
        await page.click("text=Ask")
        await page.wait_for_timeout(500)
        await page.click("text=New conversation")
        await page.wait_for_timeout(300)
        await page.click("text=Any documented allergies?")
        await page.wait_for_timeout(2500)
        await page.screenshot(path="/tmp/shot_chat_answer.png", full_page=True)

        # Curation queue
        await page.click("text=Curation Queue")
        await page.wait_for_timeout(800)
        await page.screenshot(path="/tmp/shot_queue.png", full_page=True)

        await page.click("text=Maria Alvarez")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="/tmp/shot_curation_detail.png", full_page=True)

        # Accept first section, verify UI updates
        accept_btn = page.locator("button:has-text('Accept')").first
        await accept_btn.click()
        await page.wait_for_timeout(1000)
        await page.screenshot(path="/tmp/shot_curation_after_accept.png", full_page=True)

        print("CONSOLE_ERRORS:", errors)
        await browser.close()

asyncio.run(main())
