# Plan: Real Wingo Game Predictor System

## TL;DR
Replace the current simulated lottery scraper with a **production-grade web scraper** that extracts real game data from fantasygems.run, properly validates and stores it, retrains models on real patterns, and deploys with comprehensive error handling and monitoring.

---

## Steps

### Phase 1: Data Source Analysis & Scraper Development (Blocking foundation, 2-3 days)

1. **Analyze fantasygems.run data structure**
   - Open browser DevTools to inspect network requests and DOM structure
   - Identify: where game results are rendered, what data fields exist (number, color, size, timestamp, game ID)
   - Test if content is server-side or client-side rendered (likely JavaScript-heavy)
   - Check for rate limiting, anti-bot measures, or API endpoints
   
2. **Design web scraper for real data**
   - Choose tool: **Playwright** (recommended over Selenium for speed/reliability)
   - Create `scraper/real_scraper.py` module that:
     - Navigates to fantasygems.run with WinGo_30S game code
     - Waits for game results to load dynamically
     - Extracts: number (0-9), color (Red/Green/Violet), size (Big/Small), timestamp, game_id
     - Validates extracted data against schema
     - Handles errors: network failures, page load timeouts, missing elements
   - **Test locally** with sample runs to verify reliability before containerizing

3. **Update Dockerfile for scraper**
   - Add Playwright + browser dependencies to `scraper/Dockerfile`
   - Ensure container includes headless browser support

---

### Phase 2: Data Pipeline Updates (Depends on Phase 1 - Data analysis, 1-2 days)

4. **Migrate scraper to use real data source**
   - Replace `scraper/scraper.py` random generation with real scraper module
   - Keep same MongoDB write patterns for compatibility with existing trainer/API
   - Add environment variable: `SCRAPER_MODE=real` to distinguish from simulation
   
5. **Add robust error handling & logging**
   - Implement retry logic: exponential backoff for transient failures (network, timeout)
   - Add structured logging (JSON format) with levels: DEBUG, INFO, WARN, ERROR
   - Log: scrape start/end, items extracted, validation failures, retry attempts
   - Create `logs/scraper.log` directory in container
   - On persistent failures after N retries: alert (email, webhook, or healthcheck endpoint)

6. **Data validation layer**
   - Create schema validator for scraped data (number ∈ [0,9], valid color, valid size)
   - Skip invalid records or log as anomalies
   - Add data quality metrics: % validity, extraction latency, item count per run

---

### Phase 3: Model Retraining & Validation (Parallel with Phase 2, 2-3 days)

7. **Accumulate real historical data**
   - Let scraper run for 24-48 hours to build meaningful dataset (minimum 500+ game records)
   - Monitor MongoDB for data accumulation
   
8. **Adapt trainer for real data patterns**
   - Update `trainer/train.py` to:
     - Handle real number sequences (should already work if data format matches)
     - Adjust retraining frequency (currently every 60s — may need tuning based on game frequency)
     - Detect data anomalies during training (e.g., sudden pattern shifts)
   - Run initial training batch on accumulated data
   
9. **Validate ensemble model performance**
   - Evaluate LSTM + Random Forest separately on hold-out test set (real data)
   - Compare predictions vs. actual outcomes
   - Measure: accuracy, precision, confidence calibration
   - Adjust model hyperparameters if needed (LSTM units, RF trees, etc.)
   - Document baseline metrics for later comparison

---

### Phase 4: Production Hardening (Parallel with Phase 3, 2-3 days)

10. **Add health checks & monitoring**
    - Implement `/health` endpoint in API that checks:
      - MongoDB connectivity
      - Model files present and recent (< 5 min old)
      - Last data point recency (should be < 5 min for 30S games)
    - Add prometheus-style metrics export (if monitoring infra exists)
    - Update docker-compose health check configs

11. **Improve error resilience**
    - **API**: Add try-catch for prediction endpoint, return error response with timestamp instead of crashing
    - **Trainer**: Add model save validation — only overwrite if training successful
    - **Dashboard**: Add error state display if API or data is unavailable
    - Implement fallback behaviors (e.g., return last known good prediction if update fails)

12. **Add data backup & archival**
    - Export MongoDB nightly to JSON/CSV for auditability
    - Store in `data/backups/` directory
    - Implement data retention policy (e.g., keep 30 days of game history)

---

### Phase 5: Enhanced Features (Optional, 1-2 days)

13. **Improve prediction accuracy**
    - Add feature engineering: 
      - Streak detection (3+ same colors/sizes in sequence)
      - Recency weighting (recent games weighted higher than old)
      - Pattern frequency analysis (most common transitions)
    - Experiment with ensemble weighting: LSTM vs RF confidence fusion
    
14. **Add advanced metrics to dashboard**
    - Show historical accuracy (prediction vs. actual for last 10 games)
    - Display prediction confidence and win rate for each prediction type
    - Add pattern analysis (current streak status, recent color distribution)

---

### Phase 6: Testing & Deployment (1-2 days)

15. **Integration tests**
    - Test full pipeline: scraper → MongoDB → trainer → API → dashboard
    - Mock fantasygems.run responses to avoid rate limiting during testing
    - Verify data format consistency throughout pipeline
    
16. **Load testing**
    - Simulate concurrent dashboard users
    - Verify API response time acceptable (< 200ms for predictions)
    
17. **Production deployment**
    - Update docker-compose with health checks
    - Deploy with monitoring (logs aggregation, alerting)
    - Document runbook: deployment, troubleshooting, data recovery procedures

---

## Relevant Files

- **Scraper implementation**: `scraper/scraper.py` — Replace with real web scraper (import from new module `scraper/real_scraper.py`)
- **Scraper Dockerfile**: `scraper/Dockerfile` — Add Playwright and browser dependencies
- **Trainer logic**: `trainer/train.py` — May need token adjustments for real data frequency; core logic should work unchanged
- **API endpoints**: `api/app.py` — Add `/health` endpoint, improve error handling in `/predict`
- **Dashboard**: `dashboard/dashboard.py` — Add error states, enhance metrics display
- **Docker Compose**: `docker-compose.yml` — Add health checks, environment variables for scraper mode
- **Environment config**: Create `.env` file with `SCRAPER_MODE=real`, `FANTASYGEMS_URL=https://www.fantasygems.run/#/...`, retry configs
- **Models directory**: `models/` — Will store retrained LSTM + RF models based on real data

---

## Verification

1. **Scraper verification** (end of Phase 1):
   - Run scraper locally for 5 min, verify data format matches MongoDB schema
   - Extract 10+ records, manually inspect a few against website
   - Test error handling by simulating network failure, verify retry behavior
   
2. **Data integrity** (end of Phase 2):
   - MongoDB contains 24+ hours of real game data
   - 100% of records pass validation schema
   - Extract random sample, manually spot-check against website for accuracy
   
3. **Model performance** (end of Phase 3):
   - Hold-out test set accuracy ≥ baseline random (50% for binary, ~30% for color/size)
   - Both LSTM and RF models successfully load in API
   - Sample predictions return valid number + confidence + color + size
   
4. **Production readiness** (end of Phase 4):
   - `/health` endpoint returns 200 OK when all systems operational
   - API handles mock failures gracefully (returns error response, not exception)
   - MongoDB backup created and retrievable
   - Dashboard displays error message gracefully if API unavailable
   
5. **Full system test** (end of Phase 6):
   - Run full docker-compose stack for 1 hour
   - Verify continuous scraping, model updates, and predictions
   - Dashboard refreshes show updated predictions every 5 sec
   - No exceptions in container logs

---

## Decisions & Scope

**Included:**
- Replace simulated data with real web scraping from fantasygems.run
- Production-grade error handling, logging, monitoring
- Retraining models on real data
- Health checks and resilience features
- Documentation and testing

**Explicitly excluded (future work):**
- Advanced ML models (e.g., Transformers, graph networks) — stick with LSTM + RF
- Real-time ML model serving (e.g., TensorFlow Serving) — keep embedded models
- Mobile app or advanced UI — dashboard remains Streamlit
- Integration with betting/winning logic — prediction only, no financial transactions

**Technology decisions:**
- **Scraper**: Playwright (recommended over Selenium for reliability with JS-heavy sites)
- **Storage**: Keep MongoDB; proven integration, no migration needed
- **Monitoring**: Start with log files + health endpoint; upgrade to Prometheus/ELK if needed later
- **No significant architecture changes** — build on existing microservices pattern

---

## Further Considerations

1. **Rate limiting & politeness**: fantasygems.run may rate-limit or block scrapers
   - **Recommendation**: Add delays between requests (1-3 sec), rotate user agents, consider checking robots.txt
   - If blocked, alternative: check if fantasygems.run offers API access or WebSocket connections for real-time data

2. **Data freshness**: WinGo 30S games complete every 30 seconds
   - **Recommendation**: Scrape frequency should match game frequency (every 30-45 sec) to catch all games
   - Monitor for missed games by checking for gaps in timestamp sequence

3. **Model retraining frequency**: Currently retrains every 60 sec
   - **Recommendation**: Adjust to every 5 min or every 10 games to balance freshness vs. computation cost
   - Monitor trainer CPU/memory usage in production
