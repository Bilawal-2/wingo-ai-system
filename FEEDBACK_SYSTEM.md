# Feedback & Active Learning System

## Overview

The WinGo AI System now includes an intelligent feedback mechanism that allows the models to learn from prediction accuracy. When a prediction is correct or incorrect, the system records this feedback and uses it to:

1. **Track Accuracy**: Monitor real-time prediction performance
2. **Trigger Retraining**: Automatically retrain models when accuracy drops below 55%
3. **Improve Learning**: Use correct/incorrect predictions as training signals

## How It Works

### 1. Make a Prediction
```bash
curl https://signal.bilionix.com/api/predict
```

**Response:**
```json
{
  "number": 5,
  "confidence": 70.0,
  "color": "Red",
  "size": "Small",
  "lstm": 5,
  "rf": 5,
  "gb": 5,
  "ab": 5,
  "models_count": 4,
  "majority_votes": 4,
  "unique_predictions": 1
}
```

### 2. Submit Feedback
After the lottery draw, compare the predicted number with the actual result:

```bash
curl -X POST https://signal.bilionix.com/api/feedback \
  -H "Content-Type: application/json" \
  -d '{"predicted_number": 5, "actual_number": 5}'
```

**Response:**
```json
{
  "status": "recorded",
  "recent_accuracy": 100.0,
  "total_feedback": 1
}
```

### 3. Check Statistics
```bash
curl https://signal.bilionix.com/api/stats
```

**Response:**
```json
{
  "recent_accuracy": 100.0,
  "all_time_accuracy": 95.5,
  "recent_predictions": 50,
  "total_predictions": 200,
  "correct_predictions": 191
}
```

## Active Learning Features

### Automatic Retraining
- **Normal Mode** (accuracy ≥ 55%): Models retrain every **60 seconds**
- **Aggressive Mode** (accuracy < 55%): Models retrain every **20 seconds**

This means when predictions start failing, the system automatically increases training frequency to adapt and improve.

### Accuracy Monitoring
- The trainer calculates accuracy from the last **50 predictions**
- If accuracy drops below **55%**, training frequency increases 3x
- This is logged in real-time: `⚠️  Low accuracy (45.23%) - training more frequently`

## Using the Feedback Client

A Python client is provided for interactive feedback:

```bash
python3 feedback_client.py
```

This provides an interactive menu to:
- Get predictions
- Submit feedback
- View statistics
- Track accuracy improvements

## Integration Example

For automated systems, you can:

```python
import requests

# Get prediction
pred = requests.get('https://signal.bilionix.com/api/predict').json()
predicted = pred['number']

# ... Wait for actual result ...

# Submit feedback
feedback = requests.post(
    'https://signal.bilionix.com/api/feedback',
    json={'predicted_number': predicted, 'actual_number': actual}
)

print(f"Recent Accuracy: {feedback.json()['recent_accuracy']}%")
```

## Expected Improvements

1. **Better Model Convergence**: Models learn from both successes and failures
2. **Adaptive Training**: System responds quickly when accuracy drops
3. **Real-time Monitoring**: Track prediction quality continuously
4. **Continuous Improvement**: Accuracy trends visible in `/stats` endpoint

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/predict` | GET | Get a new prediction |
| `/api/feedback` | POST | Submit prediction feedback |
| `/api/stats` | GET | View accuracy statistics |

## Data Flow

```
┌─────────────────┐
│  Make Prediction │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Wait for Lottery Result    │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Submit Feedback (POST)      │
│ {predicted, actual}         │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ MongoDB records:            │
│ - Feedback entry            │
│ - Calculate accuracy        │
│ - Store in DB               │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Trainer detects low acc     │
│ - If <55%: increase freq    │
│ - Retrain models faster     │
│ - Test on new data          │
└─────────────────────────────┘
```

## MongoDB Collections

### `predictions_feedback`
```javascript
{
  "_id": ObjectId(...),
  "timestamp": 1711000000.5,
  "predicted": 5,
  "actual": 5,
  "correct": true
}
```

The trainer queries this collection to calculate accuracy and adjust training frequency.

## Monitoring

Watch the trainer logs to see active learning in action:

```bash
docker-compose logs trainer -f
```

You'll see:
- Normal training: `time.sleep(60)` - every 60 seconds
- Aggressive training: `⚠️  Low accuracy (45.23%) - training more frequently` - every 20 seconds
- Accuracy tracking: `📊 Recent Accuracy: 75.50%`

## Notes

- **Minimum 150 data points** required before first training
- **Accuracy calculation** uses the last 50 predictions
- **Confidence floor** at 70% ensures predictions are never too uncertain
- **Weighted ensemble** uses Random Forest and Gradient Boosting with 1.5x weight
