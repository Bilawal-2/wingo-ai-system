"""
API-based Wingo game scraper

Directly calls the WinGo API endpoint to fetch game results.
No browser required - much faster and more reliable.

API: https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json
"""

import requests
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API endpoints
API_BASE = "https://draw.ar-lottery01.com/WinGo"
API_ENDPOINT = f"{API_BASE}/WinGo_30S/GetHistoryIssuePage.json"

# Request headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Referer': 'https://www.fantasygems.run/',
}


class WinGoAPIScaper:
    """Scrapes WinGo results from official API"""
    
    def __init__(self, timeout: int = 10):
        """
        Initialize the scraper.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def fetch_latest_result(self) -> Optional[Dict[str, Any]]:
        """
        Fetch the latest game result from API.
        
        Returns:
            Dictionary with number, color, size, timestamp, or None if failed
        """
        try:
            # Get current timestamp in milliseconds
            ts = int(time.time() * 1000)
            
            params = {
                "ts": ts,
                "pageIndex": 1,
                "pageSize": 1
            }
            
            logger.info(f"🌐 Fetching from {API_ENDPOINT}")
            response = self.session.get(API_ENDPOINT, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"API Response: {data}")
            
            # Parse the result
            result = self._parse_api_response(data)
            
            if result:
                logger.info(f"✅ API result: {result}")
                return result
            else:
                logger.warning("Could not parse API response")
                return None
        
        except requests.Timeout:
            logger.error(f"Request timeout ({self.timeout}s)")
            return None
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching result: {e}")
            return None
    
    def fetch_history(self, page_index: int = 1, page_size: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch historical results from API.
        
        Args:
            page_index: Page number (1-based)
            page_size: Number of results per page (max usually 100)
            
        Returns:
            List of result dictionaries or None if failed
        """
        try:
            ts = int(time.time() * 1000)
            
            params = {
                "ts": ts,
                "pageIndex": page_index,
                "pageSize": page_size
            }
            
            logger.info(f"📚 Fetching history: page {page_index}, size {page_size}")
            response = self.session.get(API_ENDPOINT, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            results = self._parse_api_history(data)
            
            if results:
                logger.info(f"✅ Fetched {len(results)} historical results")
                return results
            else:
                logger.warning("No results in API response")
                return None
        
        except Exception as e:
            logger.error(f"Error fetching history: {e}")
            return None
    
    def _parse_api_response(self, data: Dict) -> Optional[Dict[str, Any]]:
        """
        Parse single result from API response.
        
        Common API response structures:
        {
            "code": 0,
            "msg": "success",
            "data": {
                "list": [{"period": "123", "number": "7", ...}],
                ...
            }
        }
        OR
        {
            "Data": [...],
            "Code": 0,
            ...
        }
        """
        try:
            # Try different response formats
            
            # Format 1: Nested in "data.list"
            if isinstance(data, dict) and "data" in data:
                data_obj = data["data"]
                if isinstance(data_obj, dict) and "list" in data_obj:
                    items = data_obj["list"]
                    if items and len(items) > 0:
                        return self._extract_result(items[0])
            
            # Format 2: Direct "Data" field
            if isinstance(data, dict) and "Data" in data:
                items = data["Data"]
                if items and len(items) > 0:
                    return self._extract_result(items[0])
            
            # Format 3: Direct list
            if isinstance(data, list) and len(data) > 0:
                return self._extract_result(data[0])
            
            logger.warning(f"Unknown API format: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            return None
        
        except Exception as e:
            logger.error(f"Error parsing API response: {e}")
            return None
    
    def _parse_api_history(self, data: Dict) -> Optional[List[Dict[str, Any]]]:
        """
        Parse multiple results from API response.
        
        Returns:
            List of result dictionaries
        """
        try:
            results = []
            
            # Try different response formats
            items = []
            
            # Format 1: Nested in "data.list"
            if isinstance(data, dict) and "data" in data:
                data_obj = data["data"]
                if isinstance(data_obj, dict) and "list" in data_obj:
                    items = data_obj["list"]
            
            # Format 2: Direct "Data" field
            if not items and isinstance(data, dict) and "Data" in data:
                items = data["Data"]
            
            # Format 3: Direct list
            if not items and isinstance(data, list):
                items = data
            
            # Extract results
            for item in items:
                result = self._extract_result(item)
                if result:
                    results.append(result)
            
            return results if results else None
        
        except Exception as e:
            logger.error(f"Error parsing history: {e}")
            return None
    
    @staticmethod
    def _extract_result(item: Dict) -> Optional[Dict[str, Any]]:
        """
        Extract result from API item.
        
        Try to find: number, timestamp/period
        
        Common fields:
        - number, result, Number, Result
        - period, time, Time, timestamp
        - color, Color, size, Size
        """
        try:
            # Find number (try multiple field names)
            number = None
            for field in ["number", "Number", "result", "Result"]:
                if field in item:
                    try:
                        number = int(item[field])
                        if 0 <= number <= 9:
                            break
                    except:
                        pass
            
            if number is None or not (0 <= number <= 9):
                logger.debug(f"Could not extract number from: {item}")
                return None
            
            # Find timestamp (try multiple field names)
            timestamp = None
            for field in ["time", "Time", "timestamp", "period", "Period"]:
                if field in item:
                    try:
                        val = item[field]
                        if isinstance(val, str):
                            # Try to convert string to timestamp
                            if val.isdigit():
                                ts = float(val)
                                # If it looks like milliseconds, convert to seconds
                                if ts > 1e11:
                                    ts = ts / 1000
                                timestamp = ts
                            else:
                                # Try to parse ISO format
                                dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                                timestamp = dt.timestamp()
                        else:
                            timestamp = float(val)
                        
                        if timestamp > 0:
                            break
                    except:
                        pass
            
            if timestamp is None:
                timestamp = time.time()  # Use current time if not found
            
            # Derive color and size
            color = WinGoAPIScaper._get_color(number)
            size = WinGoAPIScaper._get_size(number)
            
            return {
                "number": number,
                "color": color,
                "size": size,
                "timestamp": timestamp,
                "raw_item": item  # Include raw data for debugging
            }
        
        except Exception as e:
            logger.debug(f"Error extracting result: {e}")
            return None
    
    @staticmethod
    def _get_color(num: int) -> str:
        """Get color based on number"""
        if num in [0, 5]:
            return "Violet"
        return "Red" if num % 2 == 0 else "Green"
    
    @staticmethod
    def _get_size(num: int) -> str:
        """Get size based on number"""
        return "Big" if num >= 5 else "Small"
    
    def close(self):
        """Close the session"""
        self.session.close()
        logger.info("Session closed")


def fetch_wingo_result() -> Optional[Dict[str, Any]]:
    """
    Convenience function to fetch one result.
    
    Returns:
        Dictionary with game result or None if failed
    """
    scraper = WinGoAPIScaper()
    try:
        return scraper.fetch_latest_result()
    finally:
        scraper.close()


def fetch_wingo_history(pages: int = 1) -> Optional[List[Dict[str, Any]]]:
    """
    Convenience function to fetch historical results.
    
    Args:
        pages: Number of pages to fetch (each page ~100 results)
        
    Returns:
        List of game results or None
    """
    scraper = WinGoAPIScaper()
    try:
        all_results = []
        for page in range(1, pages + 1):
            results = scraper.fetch_history(page_index=page, page_size=100)
            if results:
                all_results.extend(results)
            else:
                break
        
        return all_results if all_results else None
    finally:
        scraper.close()


if __name__ == "__main__":
    # Test fetching latest result
    logger.info("=" * 80)
    logger.info("Testing WinGo API Scraper")
    logger.info("=" * 80)
    
    result = fetch_wingo_result()
    if result:
        print(f"\n✅ Latest result:")
        print(f"   Number: {result['number']}")
        print(f"   Color: {result['color']}")
        print(f"   Size: {result['size']}")
        print(f"   Timestamp: {result['timestamp']}")
    else:
        print("\n❌ Failed to fetch result")
    
    # Test fetching history
    logger.info("\nFetching historical data...")
    history = fetch_wingo_history(pages=1)
    if history:
        print(f"\n✅ Fetched {len(history)} historical results:")
        for i, res in enumerate(history[:5]):
            print(f"   [{i+1}] Number: {res['number']}, Color: {res['color']}, Size: {res['size']}")
    else:
        print("\n❌ Failed to fetch history")
