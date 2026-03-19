"""
Main scraper service for Wingo game predictor

This service continuously fetches real Wingo game results from the official API
and stores them in MongoDB for model training and prediction.
"""

import asyncio
import os
import time
import logging
from typing import Optional, Dict, Any
from pymongo import MongoClient
from dotenv import load_dotenv
from api_scraper import fetch_wingo_result, fetch_wingo_history
from data_validator import WinGoDataValidator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "wingo")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "results")
SCRAPER_INTERVAL = int(os.getenv("SCRAPER_INTERVAL", 30))  # Seconds between scrapes
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
RETRY_BACKOFF = int(os.getenv("RETRY_BACKOFF", 2))  # Shorter backoff for API

# MongoDB connection
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]
collection = db[MONGODB_COLLECTION]
validator = WinGoDataValidator()


def validate_result(result: Dict[str, Any]) -> bool:
    """
    Validate scraped result before storing.
    
    Args:
        result: Dictionary with number, color, size, timestamp
        
    Returns:
        True if valid, False otherwise
    """
    is_valid, error = validator.validate(result)
    
    if not is_valid:
        logger.warning(f"Validation failed: {error}. Result: {result}")
        return False
    
    return True


def scrape_with_retry() -> Optional[Dict[str, Any]]:
    """
    Attempt to scrape a result with retries on failure.
    
    Returns:
        Result dictionary or None if all retries exhausted
    """
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"API call attempt {attempt + 1}/{MAX_RETRIES}...")
            
            result = fetch_wingo_result()
            
            if result:
                # Complete result with missing fields
                result = validator.complete_result(result)
                logger.info(f"✅ API call successful: #{result['number']}")
                return result
            else:
                logger.warning("API returned None")
        
        except Exception as e:
            logger.error(f"API call failed: {e}")
        
        # Retry with backoff
        if attempt < MAX_RETRIES - 1:
            backoff = RETRY_BACKOFF * (2 ** attempt)
            logger.info(f"Retrying in {backoff}s...")
            time.sleep(backoff)
    
    logger.error(f"❌ All {MAX_RETRIES} API attempts failed")
    return None


def get_recent_results(limit: int = 5) -> list:
    """Get recent results from MongoDB for duplicate detection"""
    try:
        return list(collection.find().sort("timestamp", -1).limit(limit))
    except:
        return []


def store_result(result: Dict[str, Any]) -> bool:
    """
    Store result in MongoDB.
    
    Args:
        result: Dictionary with game result
        
    Returns:
        True if stored successfully
    """
    try:
        # Check for duplicates
        recent = get_recent_results(10)
        if validator.detect_duplicates(result, recent, time_window=90):
            logger.debug(f"⚠️  Likely duplicate detected, skipping: #{result['number']}")
            return False
        
        # Add metadata
        result_with_meta = {
            **result,
            "stored_at": time.time(),
            "scraped_at": result.get("timestamp")
        }
        
        # Remove raw_item to save space
        result_with_meta.pop("raw_item", None)
        
        # Insert into MongoDB
        collection.insert_one(result_with_meta)
        logger.info(f"💾 Stored: #{result['number']} | {result['color']}/{result['size']}")
        return True
    
    except Exception as e:
        logger.error(f"Error storing result in MongoDB: {e}")
        return False


def get_last_stored_count() -> int:
    """Get count of stored results"""
    try:
        return collection.count_documents({})
    except:
        return 0


def load_historical_data():
    """Load initial historical data from API"""
    logger.info("\n" + "=" * 80)
    logger.info("📚 Loading Historical Data (First Time)")
    logger.info("=" * 80)
    
    count_before = get_last_stored_count()
    stored_count = 0
    
    try:
        # Fetch 3 pages of history (~300 results)
        logger.info("Fetching historical data from API (this may take a minute)...")
        history = fetch_wingo_history(pages=3)
        
        if history:
            logger.info(f"✅ Got {len(history)} historical results from API")
            
            for result in history:
                if validate_result(result):
                    if store_result(result):
                        stored_count += 1
            
            logger.info(f"✅ Stored {stored_count}/{len(history)} historical records")
        else:
            logger.warning("❌ Failed to fetch historical data")
    
    except Exception as e:
        logger.error(f"Error loading history: {e}")
    
    count_after = get_last_stored_count()
    logger.info(f"Total in DB: {count_before} → {count_after}")
    logger.info("=" * 80)


async def run_scraper_loop():
    """Main scraper loop"""
    logger.info("\n" + "=" * 80)
    logger.info(f"🎮 Wingo Game Scraper Started")
    logger.info(f"MongoDB: {MONGODB_DB}.{MONGODB_COLLECTION}")
    logger.info(f"Interval: {SCRAPER_INTERVAL}s")
    logger.info(f"API: draw.ar-lottery01.com")
    logger.info("=" * 80)
    
    # Load historical data on first run
    if get_last_stored_count() < 50:
        load_historical_data()
    
    consecutive_failures = 0
    max_consecutive_failures = 10
    
    while True:
        try:
            total = get_last_stored_count()
            logger.info(f"\n▶️  Scrape cycle | Total stored: {total}")
            
            # Fetch latest result
            result = scrape_with_retry()
            
            if result and validate_result(result):
                # Store in MongoDB
                if store_result(result):
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
            else:
                consecutive_failures += 1
                logger.warning(f"Validation failed. Failures: {consecutive_failures}/{max_consecutive_failures}")
            
            # Check if too many failures
            if consecutive_failures >= max_consecutive_failures:
                logger.error(f"❌ {max_consecutive_failures} consecutive failures. Exiting.")
                break
            
            # Wait before next scrape
            logger.debug(f"⏳ Waiting {SCRAPER_INTERVAL}s...")
            await asyncio.sleep(SCRAPER_INTERVAL)
        
        except KeyboardInterrupt:
            logger.info("\n⏹️  Scraper stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            consecutive_failures += 1
            if consecutive_failures < max_consecutive_failures:
                await asyncio.sleep(RETRY_BACKOFF)
            else:
                break
    
    logger.info(f"\n🏁 Scraper finished. Total stored: {get_last_stored_count()}")


if __name__ == "__main__":
    try:
        asyncio.run(run_scraper_loop())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
