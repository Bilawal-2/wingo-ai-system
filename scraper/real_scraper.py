"""
Real Wingo game scraper from fantasygems.run
Extracts game results for WinGo 30S games

Strategy:
1. First, try to intercept API responses from the page
2. If API-based scraping fails, fall back to DOM parsing
3. Both methods store results in the same MongoDB format
"""

import asyncio
import json
import logging
import time
import re
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Route, Response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WinGoScraper:
    """Scrapes real Wingo game results from fantasygems.run"""
    
    # Game URL for WinGo 30S
    WINGO_URL = "https://www.fantasygems.run/#/saasLottery/WinGo?gameCode=WinGo_30S&lottery=WinGo"
    
    def __init__(self, headless: bool = True):
        """
        Initialize the scraper.
        
        Args:
            headless: Run browser in headless mode (default True)
        """
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
        self.api_responses: List[Dict] = []
        self.last_result = None
        
    async def initialize(self):
        """Start the browser and navigate to the game page"""
        logger.info("Initializing browser...")
        self.playwright = await async_playwright().start()
        
        # Launch browser with anti-bot features disabled for scraping
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        self.page = await context.new_page()
        
        # Set viewport
        await self.page.set_viewport_size({"width": 1280, "height": 720})
        
        # Intercept API calls
        await self.page.route("**/*.json", self._handle_route)
        await self.page.route("**/api/**", self._handle_route)
        
        logger.info(f"Navigating to {self.WINGO_URL}")
        try:
            await self.page.goto(self.WINGO_URL, wait_until="networkidle", timeout=30000)
            await self.page.wait_for_timeout(2000)  # Wait for JavaScript to render
            logger.info("✅ Page loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load page: {e}")
            raise
    
    async def _handle_route(self, route: Route):
        """Intercept network requests to capture API responses"""
        try:
            response = await route.fetch()
            
            # Try to parse as JSON
            try:
                response_data = await response.json()
                self.api_responses.append({
                    "url": response.url,
                    "status": response.status,
                    "data": response_data
                })
                logger.debug(f"Captured API response from {response.url}")
            except:
                pass  # Not JSON
            
            await route.continue_()
        except Exception as e:
            logger.debug(f"Route handler error: {e}")
            await route.continue_()
    
    async def scrape_latest_result(self) -> Optional[Dict[str, Any]]:
        """
        Scrape the latest game result using multiple strategies:
        1. Extract from intercepted API responses
        2. Parse from DOM elements
        3. Extract from page text
        
        Returns:
            Dictionary with number, timestamp, or None if failed
        """
        # Strategy 1: Check API responses
        logger.info("Strategy 1: Checking API responses...")
        result = self._extract_from_api_responses()
        if result:
            logger.info(f"✅ Found result via API: {result}")
            self.last_result = result
            return result
        
        # Strategy 2: Try DOM parsing
        logger.info("Strategy 2: Attempting DOM parsing...")
        result = await self._extract_from_dom()
        if result:
            logger.info(f"✅ Found result via DOM: {result}")
            self.last_result = result
            return result
        
        # Strategy 3: Extract from page text
        logger.info("Strategy 3: Extracting from page content...")
        result = await self._extract_from_page_text()
        if result:
            logger.info(f"✅ Found result from page text: {result}")
            self.last_result = result
            return result
        
        logger.warning("❌ Could not extract result using any strategy")
        return None
    
    def _extract_from_api_responses(self) -> Optional[Dict[str, Any]]:
        """Try to find game result in intercepted API responses"""
        try:
            for api_resp in self.api_responses:
                data = api_resp.get("data", {})
                
                # Look for common result field names
                result_candidates = [
                    data.get("result"),
                    data.get("number"),
                    data.get("gameResult"),
                    data.get("lastResult"),
                    data.get("currentResult"),
                ]
                
                if isinstance(data, list) and len(data) > 0:
                    result_candidates.append(data[-1])  # Last item
                
                for candidate in result_candidates:
                    if candidate and isinstance(candidate, dict):
                        number = candidate.get("number")
                        if number is not None and 0 <= int(number) <= 9:
                            return {
                                "number": int(number),
                                "color": self._get_color(int(number)),
                                "size": self._get_size(int(number)),
                                "timestamp": time.time(),
                            }
                    elif isinstance(candidate, (int, str)):
                        try:
                            num = int(candidate)
                            if 0 <= num <= 9:
                                return {
                                    "number": num,
                                    "color": self._get_color(num),
                                    "size": self._get_size(num),
                                    "timestamp": time.time(),
                                }
                        except:
                            pass
        except Exception as e:
            logger.debug(f"Error extracting from API: {e}")
        
        return None
    
    async def _extract_from_dom(self) -> Optional[Dict[str, Any]]:
        """Try to extract result from DOM elements"""
        try:
            # Common selectors for game results
            selectors = [
                ".result-number", ".game-number", ".number-display",
                "[class*='result'] [class*='number']",
                "[data-testid='result-number']",
                ".outcome-number", ".final-number",
                ".big-number", ".large-number"
            ]
            
            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        number = self._parse_number(text)
                        if number is not None:
                            return {
                                "number": number,
                                "color": self._get_color(number),
                                "size": self._get_size(number),
                                "timestamp": time.time(),
                            }
                except:
                    pass
        except Exception as e:
            logger.debug(f"Error extracting from DOM: {e}")
        
        return None
    
    async def _extract_from_page_text(self) -> Optional[Dict[str, Any]]:
        """Try to extract number from all page text"""
        try:
            page_text = await self.page.content()
            
            # Look for patterns like game result JSON or numbers in context
            patterns = [
                r'"number"\s*:\s*(\d)',
                r'"result"\s*:\s*(\d)',
                r'"outcome"\s*:\s*(\d)',
                r'result["\']?\s*[:=]\s*["\']?(\d)["\']?',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    try:
                        num = int(match.group(1))
                        if 0 <= num <= 9:
                            return {
                                "number": num,
                                "color": self._get_color(num),
                                "size": self._get_size(num),
                                "timestamp": time.time(),
                            }
                    except:
                        pass
        except Exception as e:
            logger.debug(f"Error extracting from page text: {e}")
        
        return None
    
    def _parse_number(self, text: Optional[str]) -> Optional[int]:
        """Extract number 0-9 from text"""
        if not text:
            return None
        
        try:
            text = text.strip()
            
            # Try to find a single digit
            for char in text:
                if char.isdigit():
                    num = int(char)
                    if 0 <= num <= 9:
                        return num
            
            return None
        except Exception as e:
            logger.debug(f"Error parsing number: {e}")
            return None
    
    @staticmethod
    def _get_color(num: int) -> str:
        """Get color based on number (matches API logic)"""
        if num in [0, 5]:
            return "Violet"
        return "Red" if num % 2 == 0 else "Green"
    
    @staticmethod
    def _get_size(num: int) -> str:
        """Get size based on number (matches API logic)"""
        return "Big" if num >= 5 else "Small"
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
            logger.info("Browser closed")
        
        if self.playwright:
            await self.playwright.stop()


async def scrape_wingo_result(headless: bool = True) -> Optional[Dict[str, Any]]:
    """
    Convenience function to scrape one result.
    
    Args:
        headless: Run in headless mode
        
    Returns:
        Dictionary with number, color, size, timestamp, or None if failed
    """
    scraper = WinGoScraper(headless=headless)
    
    try:
        await scraper.initialize()
        result = await scraper.scrape_latest_result()
        return result
    finally:
        await scraper.close()


if __name__ == "__main__":
    # Test the scraper
    result = asyncio.run(scrape_wingo_result(headless=False))
    if result:
        print(f"✅ Scraped result: {result}")
    else:
        print("❌ Failed to scrape result")
