from playwright.async_api import async_playwright
from typing import Optional, Any
import logging
from dotenv import load_dotenv
import os
load_dotenv()

logger = logging.getLogger(__name__)

playwright_port = os.getenv("PLAYWRIGHT_PORT", 9300)

# Global variables to store browser instance and related objects
_playwright: Optional[Any] = None
_browser: Optional[Any] = None
_context: Optional[Any] = None
_page: Optional[Any] = None


async def run(url: str, browser_type: str = "chromium") -> bool:
    """
    Start a browser instance and navigate to the specified URL.
    If browser is already running, it will navigate to the new URL.

    Args:
        url: The URL to navigate to
        browser_type: The type of browser to use ("chromium", "firefox", or "webkit")

    Returns:
        bool: True if navigation was successful, False otherwise
    """
    global _playwright, _browser, _context, _page

    # Validate browser type
    if browser_type not in ["chromium", "firefox", "webkit"]:
        logger.warning(
            f"Invalid browser type: {browser_type}. Using chromium instead.")
        browser_type = "chromium"

    # If browser is not initialized, start a new instance
    if _browser is None and _playwright is None:
        logger.info(f"Initializing new {browser_type} browser instance")
        _playwright = await async_playwright().start()
        # Launch the specified browser
        browser_launcher = getattr(_playwright, browser_type)
        _browser = await browser_launcher.launch(headless=False)
        _context = await _browser.new_context()
        _page = await _context.new_page()
    else:
        logger.debug("Using existing browser instance")

    try:
        # Extra check before navigation to ensure page is still valid
        if _page is None or not hasattr(_page, "goto"):
            logger.warning("Page object is invalid, creating a new page")
            # If context is still valid, try to create a new page
            try:
                _page = await _context.new_page()
            except Exception:
                # If context is not valid, rebuild everything
                logger.warning("Context is invalid, restarting browser")
                await _browser.close() if _browser else None
                await _playwright.stop() if _playwright else None
                _playwright = await async_playwright().start()
                browser_launcher = getattr(_playwright, browser_type)
                _browser = await browser_launcher.launch(headless=False)
                _context = await _browser.new_context()
                _page = await _context.new_page()

        # Navigate to the URL (whether browser is new or existing) with a timeout
        logger.info(f"Navigating to {url}")
        await _page.goto(url, timeout=30000, wait_until="domcontentloaded")
        # Wait for the page to be fully loaded
        await _page.wait_for_load_state("networkidle")
        logger.info(f"Successfully loaded {url}")
        return True
    except Exception as e:
        logger.error(f"Error navigating to {url}: {str(e)}")
        # If we get a thread-related error, clean up and restart on next run
        if "thread" in str(e).lower() and "exited" in str(e).lower():
            logger.warning(
                "Browser thread has exited, will restart on next run")
            await stop()  # This will clean up all resources
        return False


async def get_page() -> Optional[Any]:
    """
    Get the current page object.

    Returns:
        Optional[Any]: The current page object or None if not available
    """
    global _page
    if _playwright is None:
        logger.warning("Playwright will be initialized")
        await connect_to_browser(f"http://localhost:{playwright_port}")

    if _page is None:
        logger.error("Failed to initialize page")
        return None
    return _page


async def connect_to_browser(instance_address: str) -> None:
    """
    Connect to an existing browser instance using the specified address.

    Args:
        instance_address: The address of the existing browser instance
    """
    global _playwright, _browser, _context, _page

    if _playwright is None:
        logger.info("Connecting to existing browser instance")
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.connect_over_cdp(instance_address)
        contexts = _browser.contexts
        if contexts:
            _context = contexts[0]
            pages = _context.pages
            if pages:
                _page = pages[0]
                logger.info(f"Connected to existing page: {await _page.title()}")
            else:
                logger.warning(
                    "No pages found in the context. Creating a new page.")
                _page = await _context.new_page()
        else:
            logger.warning(
                "No contexts found. Creating a new context and page.")
            _context = await _browser.new_context()
            _page = await _context.new_page()
    else:
        logger.debug("Already connected to a browser instance")


async def stop() -> None:
    """
    Close the browser instance if it's running.
    """
    global _playwright, _browser, _context, _page

    if _browser is not None:
        logger.info("Closing browser")
        await _browser.close()
        _browser = None

    if _playwright is not None:
        logger.info("Stopping playwright")
        await _playwright.stop()
        _playwright = None

    # Reset other globals
    _context = None
    _page = None
    logger.debug("Browser resources cleaned up")


async def run_browser_tool(url: str) -> bool:
    """
    Start a browser instance and navigate to the specified URL.

    Args:
        url: The URL to navigate to

    Returns:
        bool: True if navigation was successful, False otherwise
    """
    return await run(url)


async def stop_browser_tool() -> None:
    """
    Close the browser instance if it's running.
    """
    logger.info("Stopping browser tool")
    await stop()


if __name__ == "__main__":
    # Example usage with asyncio
    import asyncio

    async def main():
        await run_browser_tool("https://www.ufile.ca/")
        # Add a delay if needed
        await asyncio.sleep(10)

        await run_browser_tool("https://www.ufile.ca/")
        # await stop_browser_tool()

    asyncio.run(main())
