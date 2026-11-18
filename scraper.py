import asyncio
import os
import time
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")


async def take_screenshot(url: str, restaurant_name: str, timeout: int = 15000) -> dict:
    """Take a screenshot of a restaurant's Yelp page.
    
    Returns dict with screenshot_path and status.
    """
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    
    timestamp = int(time.time())
    filename = f"{restaurant_name.replace(' ', '_')}_{timestamp}.png"
    filepath = os.path.join(SCREENSHOTS_DIR, filename)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        
        try:
            await page.goto(str(url), wait_until="networkidle", timeout=timeout)
            # Extra wait for dynamic content
            await asyncio.sleep(2)
            await page.screenshot(path=filepath, full_page=False)
            await browser.close()
            return {
                "screenshot_path": filepath,
                "status": "success"
            }
        except Exception as e:
            await browser.close()
            return {
                "screenshot_path": None,
                "status": f"error: {str(e)}"
            }
