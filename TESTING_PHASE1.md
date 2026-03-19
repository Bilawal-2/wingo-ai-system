# Phase 1: Real Scraper Testing Guide

## Overview
We've created a **production-grade web scraper** for fantasygems.run using Playwright. This guide walks through testing it locally to understand the website structure before deploying.

## Files Created

1. **`scraper/real_scraper.py`** - Core scraper module with 3 extraction strategies:
   - API response interception (most reliable)
   - DOM element parsing (fallback)
   - Page text extraction (last resort)

2. **`scraper/inspector.py`** - Website structure analyzer tool
   - Helps identify correct CSS selectors
   - Captures network requests
   - Lists all elements containing numbers

3. **`scraper/scraper_new.py`** - Production scraper service
   - Continuous polling loop
   - Retry logic with exponential backoff
   - MongoDB storage with validation
   - Detailed JSON logging

4. **`scraper/Dockerfile`** - Updated with Playwright support
   - Installs browser dependencies
   - Pre-downloads Chromium browser

5. **`scraper/requirements.txt`** - Added Playwright dependency

## Testing Steps

### Step 1: Set up local environment
```bash
cd scraper/
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Run the inspector tool
This opens the browser so you can manually inspect the page:
```bash
python inspector.py
```

**What to look for:**
- Open DevTools (F12)
- Go to Network tab
- Refresh the page
- Look for API calls returning game results
- Note the URL and response format
- Common patterns:
  - `/api/play` or `/api/lottery`
  - Response fields like `number`, `result`, `gameResult`
  - WebSocket connections for real-time updates

### Step 3: Test the real scraper
```bash
python -c "import asyncio; from real_scraper import scrape_wingo_result; result = asyncio.run(scrape_wingo_result(headless=False)); print(result)"
```

**Expected output:**
```json
{
  "number": 7,
  "color": "Green",
  "size": "Big",
  "timestamp": 1710764123.456
}
```

If it fails, the scraper will try multiple strategies and log which selectors it's testing.

### Step 4: Test multiple scrapes
```bash
python test_multi_scrape.py  # (file to create if needed)
```

### Step 5: Test the production scraper (without MongoDB)
Replace the MongoDB URI with a local test database, or comment out storage:
```bash
SCRAPER_INTERVAL=5 SCRAPER_TIMEOUT=20 python scraper_new.py
```

## Common Issues & Solutions

### Issue: "No element found" / ValueError parsing
**Cause**: CSS selectors don't match the actual page structure
**Solution**: 
1. Run inspector.py again with headless=False
2. Right-click on the number → Inspect
3. Copy the exact CSS selector/XPath
4. Update selectors in real_scraper.py

### Issue: Timeout after 25 seconds
**Cause**: Website takes too long to load or is slow
**Solution**: 
- Increase SCRAPER_TIMEOUT in .env (e.g., to 40)
- Check internet connection
- Check if fantasygems.run is up

### Issue: "Browser not found" / Playwright error
**Cause**: Browser not downloaded
**Solution**:
```bash
playwright install chromium
```

### Issue: Rate limiting / 429 errors
**Cause**: Too many requests
**Solution**:
- Increase SCRAPER_INTERVAL (currently 30s, might need 60s+)
- Add randomized delays
- Rotate user agents (already done in code)

## Data Format

Once working, each scraped result should have this format:

```json
{
  "number": 0-9,
  "color": "Red|Green|Violet",
  "size": "Big|Small",
  "timestamp": 1710764123.456,
  "raw_text": "optional raw text from scraper",
  "stored_at": 1710764124.5
}
```

**Validation Rules:**
- `number` must be integer 0-9
- `color` must be in [Red, Green, Violet]
- `size` must be in [Big, Small]
- `timestamp` must be positive float

Any record failing validation will be skipped and logged.

## Next Steps After Successful Testing

Once the scraper works locally:

1. **Verify data integrity** - Run 5+ consecutive scrapes, compare results with website
2. **Test error handling** - Disconnect internet, verify retry logic works
3. **Update production scraper** - Replace old random scraper with new real one in docker-compose.yml
4. **Accumulate data** - Let it run 24-48 hours to gather historical data
5. **Retrain models** - Trainer will automatically learn from real patterns
6. **Validate predictions** - Compare predictions vs actual outcomes

## Performance Expectations

- **Scrape time**: 15-25 seconds per game
- **Retry attempts**: Max 3 per failed scrape = ~1.5 min worst case
- **Data rate**: ~120 records per hour (one every 30 seconds)
- **Storage**: ~2 MB per 10,000 records

## Troubleshooting Commands

```bash
# Kill any stuck browser processes
pkill -f "chromium"

# Check if Playwright installed correctly
python -c "from playwright.async_api import async_playwright; print('OK')"

# Run with verbose logging
python scraper_new.py  # Logs to console by default

# Test MongoDB connection
python -c "from pymongo import MongoClient; client = MongoClient(); print(client.list_database_names())"
```

## Contact / Debug Info

If scraper fails, please provide:
1. Exact error message
2. Output from: `python inspector.py` (screenshot or text)
3. Network requests visible in browser DevTools
4. fantasygems.run page URL you're using
