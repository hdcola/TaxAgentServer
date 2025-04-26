import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import os

load_dotenv()

username = os.getenv("UFILE_USERNAME", "your_username")
print(f"Username: {username}")
password = os.getenv("UFILE_PASSWORD", "your_password")
playwright_port = os.getenv("PLAYWRIGHT_PORT", 9300)


async def main():

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[f'--remote-debugging-port={playwright_port}'],
        )
        print(
            f"Playwright instance address: http://localhost:{playwright_port}")

        # Create a page
        page = await browser.new_page()
        await page.goto('https://secure.ufile.ca/account/login?lang=en&mode=UFileT1')
        await page.fill('input[name="Username"]', username)
        await page.fill('input[name="Password"]', password)

        # Use a never-resolving future to keep the script running indefinitely
        # This is more reliable than using wait_for_timeout
        await asyncio.Future()

        # Alternative: use a very long but finite timeout (not recommended)
        # await page.wait_for_timeout(2147483647)  # Maximum 32-bit integer

asyncio.run(main())
