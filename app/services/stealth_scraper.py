"""Advanced Stealth Scraper with Playwright"""
import asyncio
import random
import logging
from typing import Optional, Dict, List
from fake_useragent import UserAgent

try:
    from playwright.async_api import async_playwright
    from playwright_stealth.stealth import Stealth
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)

class StealthScraper:
    """10/10 stealth scraper bypassing bot detection"""
    
    VIEWPORTS = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
    ]
    
    def __init__(self, headless: bool = True, delay_range: tuple = (2, 5)):
        self.headless = headless
        self.delay_range = delay_range
        self.ua = UserAgent()
    
    async def scrape(self, url: str, wait_for: Optional[str] = None, scroll_intensive: bool = False) -> Dict:
        """Scrape with full stealth - handles dynamic JavaScript content"""
        if not PLAYWRIGHT_AVAILABLE:
            return {"error": "Playwright not installed"}
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--window-size=1920,1080',
                    '--start-maximized',
                    '--hide-scrollbars',
                    '--mute-audio',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--force-device-scale-factor=1',
                ]
            )
            
            context = await browser.new_context(
                viewport=random.choice(self.VIEWPORTS),
                user_agent=self.ua.random,
                locale="en-US",
                timezone_id="America/New_York",
                color_scheme=random.choice(["light", "dark"]),
                geolocation={"latitude": 40.7128, "longitude": -74.0060},  # NYC
                permissions=["geolocation"],
            )
            
            # Advanced anti-detection
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                window.chrome = {runtime: {}};
                window.Notification = window.Notification || function() {};
                window.navigator.chrome = {runtime: {}};
                
                // Override permissions API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            page = await context.new_page()
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            
            # Set default timeout
            page.set_default_timeout(60000)
            page.set_default_navigation_timeout(60000)
            
            try:
                # Random initial delay
                await asyncio.sleep(random.uniform(1, 3))
                
                # Navigate with more permissive wait
                response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Wait for page to be fully interactive
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                except:
                    pass
                
                # Wait for specific element if requested
                if wait_for:
                    try:
                        await page.wait_for_selector(wait_for, timeout=15000)
                    except:
                        logger.warning(f"Selector {wait_for} not found, continuing anyway")
                
                # EXTENSIVE SCROLLING for lazy-loaded content
                if scroll_intensive:
                    logger.info("Starting intensive scroll for dynamic content...")
                    
                    # Scroll multiple times with pauses
                    for i in range(random.randint(5, 10)):
                        # Scroll down
                        scroll_amount = random.randint(500, 1000)
                        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                        await asyncio.sleep(random.uniform(1, 3))
                        
                        # Check if new content loaded
                        previous_height = await page.evaluate("document.body.scrollHeight")
                        await asyncio.sleep(1)
                        new_height = await page.evaluate("document.body.scrollHeight")
                        
                        if new_height > previous_height:
                            logger.info(f"New content loaded after scroll {i+1}")
                            # Scroll more to get all content
                            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                            await asyncio.sleep(random.uniform(1, 2))
                    
                    # Scroll back to top then down again to ensure all lazy content loads
                    await page.evaluate("window.scrollTo(0, 0)")
                    await asyncio.sleep(2)
                    
                    for i in range(random.randint(3, 5)):
                        await page.evaluate(f"window.scrollBy(0, {random.randint(800, 1200)})")
                        await asyncio.sleep(random.uniform(1, 2))
                else:
                    # Basic scrolling
                    for _ in range(random.randint(3, 6)):
                        await page.mouse.wheel(0, random.randint(300, 700))
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Final wait for any lazy content
                await asyncio.sleep(random.uniform(2, 4))
                
                # Get page content
                html = await page.content()
                
                await context.close()
                await browser.close()
                
                return {
                    "html": html,
                    "status": response.status if response else None,
                    "success": True,
                    "scroll_intensive": scroll_intensive
                }
                
            except Exception as e:
                logger.error(f"Scrape failed: {e}")
                try:
                    await context.close()
                    await browser.close()
                except:
                    pass
                return {"error": str(e), "success": False}
