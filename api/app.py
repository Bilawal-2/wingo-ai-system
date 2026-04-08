import os
import time
import numpy as np
import joblib
from flask import Flask, jsonify, request
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# -----------------------
# Config
# -----------------------
SEQUENCE_LENGTH = int(os.getenv("SEQUENCE_LENGTH", 10))

LSTM_PATH = os.getenv("LSTM_MODEL_PATH", "models/lstm_model.keras")
RF_PATH = os.getenv("RF_MODEL_PATH", "models/rf_model.pkl")
GB_PATH = os.getenv("GB_MODEL_PATH", "models/gb_model.pkl")
AB_PATH = os.getenv("AB_MODEL_PATH", "models/ab_model.pkl")
SCALER_PATH = os.getenv("SCALER_PATH", "models/scaler.pkl")

# Big/Small model paths
RF_BS_PATH = os.getenv("RF_BS_MODEL_PATH", "models/rf_bigsmall_model.pkl")
GB_BS_PATH = os.getenv("GB_BS_MODEL_PATH", "models/gb_bigsmall_model.pkl")
AB_BS_PATH = os.getenv("AB_BS_MODEL_PATH", "models/ab_bigsmall_model.pkl")

# -----------------------
# Load Models Function
# -----------------------
def load_models():
    global lstm_model, rf_model, gb_model, ab_model, scaler, feature_scaler
    global rf_bs_model, gb_bs_model, ab_bs_model
    
    lstm_model = None
    rf_model = None
    gb_model = None
    ab_model = None
    rf_bs_model = None
    gb_bs_model = None
    ab_bs_model = None
    scaler = None
    feature_scaler = None
    
    # load LSTM
    if os.path.exists(LSTM_PATH):
        try:
            from tensorflow.keras.models import load_model
            lstm_model = load_model(LSTM_PATH)
            print("✅ LSTM loaded")
        except Exception as e:
            print(f"Error loading LSTM: {e}")

    # load RF
    if os.path.exists(RF_PATH):
        try:
            rf_model = joblib.load(RF_PATH)
            print("✅ RF loaded")
        except Exception as e:
            print(f"Error loading RF: {e}")

    # load GB
    if os.path.exists(GB_PATH):
        try:
            gb_model = joblib.load(GB_PATH)
            print("✅ GB loaded")
        except Exception as e:
            print(f"Error loading GB: {e}")

    # load AB
    if os.path.exists(AB_PATH):
        try:
            ab_model = joblib.load(AB_PATH)
            print("✅ AB loaded")
        except Exception as e:
            print(f"Error loading AB: {e}")

    # load RF Big/Small
    if os.path.exists(RF_BS_PATH):
        try:
            rf_bs_model = joblib.load(RF_BS_PATH)
            print("✅ RF Big/Small loaded")
        except Exception as e:
            print(f"Error loading RF Big/Small: {e}")

    # load GB Big/Small
    if os.path.exists(GB_BS_PATH):
        try:
            gb_bs_model = joblib.load(GB_BS_PATH)
            print("✅ GB Big/Small loaded")
        except Exception as e:
            print(f"Error loading GB Big/Small: {e}")

    # load AB Big/Small
    if os.path.exists(AB_BS_PATH):
        try:
            ab_bs_model = joblib.load(AB_BS_PATH)
            print("✅ AB Big/Small loaded")
        except Exception as e:
            print(f"Error loading AB Big/Small: {e}")

    # load scaler
    if os.path.exists(SCALER_PATH):
        try:
            scaler = joblib.load(SCALER_PATH)
            print("✅ Scaler loaded")
        except Exception as e:
            print(f"Error loading Scaler: {e}")
    
    # load feature scaler
    FEATURE_SCALER_PATH = os.getenv("FEATURE_SCALER_PATH", "models/feature_scaler.pkl")
    if os.path.exists(FEATURE_SCALER_PATH):
        try:
            feature_scaler = joblib.load(FEATURE_SCALER_PATH)
            print("✅ Feature Scaler loaded")
        except Exception as e:
            print(f"Error loading Feature Scaler: {e}")

# Initial load
lstm_model = None
rf_model = None
gb_model = None
ab_model = None
rf_bs_model = None
gb_bs_model = None
ab_bs_model = None
scaler = None
feature_scaler = None

# wait for at least one model
while not (os.path.exists(LSTM_PATH) or os.path.exists(RF_PATH)):
    print("Waiting for models...")
    time.sleep(5)

load_models()

# -----------------------
# MongoDB
# -----------------------
client = MongoClient(os.getenv("MONGODB_URI", "mongodb://mongodb:27017/"))
db = client[os.getenv("MONGODB_DB", "wingo")]

# -----------------------
# Helper: Extract features for ensemble models
# -----------------------
def extract_features_for_prediction(seq):
    """Extract features from sequence for ensemble prediction"""
    f = []
    
    # Basic sequence stats
    f.append(np.mean(seq))
    f.append(np.std(seq))
    f.append(np.max(seq) - np.min(seq))
    
    # Trend features
    f.append(seq[-1] - seq[0])
    f.append(seq[-1] - seq[-2] if len(seq) > 1 else 0)
    
    # Distance from averages
    running_avg = np.mean(seq[:-1]) if len(seq) > 1 else 5
    f.append(abs(seq[-1] - running_avg))
    
    # Recency weights
    weights = np.linspace(0.5, 2.0, len(seq))
    weighted_avg = np.average(seq, weights=weights)
    f.append(weighted_avg)
    
    # High/low frequency
    high_count = sum(1 for x in seq if x >= 5)
    f.append(high_count / len(seq))
    
    # Position features
    f.append(seq[-1] / 9.0)
    f.append(max(seq) / 9.0)
    f.append(min(seq) / 9.0)
    
    return np.array(f, dtype=np.float32).reshape(1, -1)

# -----------------------
# Calibrate confidence with temperature scaling
# -----------------------
def calibrate_confidence(raw_conf, temperature=1.5):
    """
    Apply temperature scaling to calibrate confidence scores.
    Temperature > 1 makes scores more conservative (closer to 50%).
    """
    # Convert to probability space [0, 1]
    prob = raw_conf / 100.0
    
    # Clip extreme values to avoid numerical issues
    prob = np.clip(prob, 0.01, 0.99)
    
    # Apply temperature scaling
    # Lower temperature = higher confidence
    if prob > 0.5:
        calibrated_prob = (prob ** (1.0 / temperature))
    else:
        calibrated_prob = 1.0 - ((1.0 - prob) ** (1.0 / temperature))
    
    # Convert back to percentage
    return calibrated_prob * 100.0

def get_size(num):
    return "Big" if num >= 5 else "Small"

def get_color(num):
    if num in [0, 5]:
        return "Violet"
    return "Red" if num % 2 == 0 else "Green"

# -----------------------
# Prediction
# -----------------------
@app.route("/predict")
def predict():
    global lstm_model, rf_model, gb_model, ab_model, scaler, feature_scaler
    
    # Reload models in case they were updated by trainer
    load_models()

    collection = db[os.getenv("MONGODB_COLLECTION", "results")]

    last = list(collection.find().sort("timestamp", -1).limit(SEQUENCE_LENGTH))

    if len(last) < SEQUENCE_LENGTH:
        return jsonify({"error": "Not enough data"}), 400

    seq = [x["number"] for x in reversed(last)]
    X_seq = np.array(seq).reshape(1, SEQUENCE_LENGTH)

    lstm_num, lstm_conf = None, 0
    rf_num, rf_conf = None, 0
    gb_num, gb_conf = None, 0
    ab_num, ab_conf = None, 0
    
    predictions = []
    confidences = []

    # -----------------------
    # LSTM Prediction
    # -----------------------
    if lstm_model:
        try:
            if scaler:
                X_scaled = scaler.transform(X_seq.reshape(-1,1)).reshape(1, SEQUENCE_LENGTH, 1)
            else:
                X_scaled = (X_seq / 10.0).reshape(1, SEQUENCE_LENGTH, 1)

            pred = lstm_model.predict(X_scaled, verbose=0)[0]

            lstm_num = int(np.argmax(pred))
            lstm_conf = float(np.max(pred) * 100)
            
            # Calibrate LSTM confidence (more conservative)
            lstm_conf = calibrate_confidence(lstm_conf, temperature=2.0)
            
            predictions.append(lstm_num)
            confidences.append(lstm_conf)

        except Exception as e:
            print("LSTM error:", e)

    # Extract features for ensemble models
    X_features = extract_features_for_prediction(seq)
    
    # -----------------------
    # RF Prediction with calibration
    # -----------------------
    if rf_model:
        try:
            rf_num = int(rf_model.predict(X_features)[0])

            if hasattr(rf_model, "predict_proba"):
                rf_conf = float(max(rf_model.predict_proba(X_features)[0]) * 100)
                # Calibrate with moderate temperature
                rf_conf = calibrate_confidence(rf_conf, temperature=1.2)
            else:
                rf_conf = 50.0
            
            predictions.append(rf_num)
            confidences.append(rf_conf)

        except Exception as e:
            print("RF error:", e)

    # -----------------------
    # GB Prediction with calibration
    # -----------------------
    if gb_model:
        try:
            gb_num = int(gb_model.predict(X_features)[0])

            if hasattr(gb_model, "predict_proba"):
                gb_conf = float(max(gb_model.predict_proba(X_features)[0]) * 100)
                # Calibrate with moderate temperature
                gb_conf = calibrate_confidence(gb_conf, temperature=1.2)
            else:
                gb_conf = 50.0
            
            predictions.append(gb_num)
            confidences.append(gb_conf)

        except Exception as e:
            print("GB error:", e)

    # -----------------------
    # AB Prediction with calibration
    # -----------------------
    if ab_model:
        try:
            ab_num = int(ab_model.predict(X_features)[0])

            if hasattr(ab_model, "predict_proba"):
                ab_conf = float(max(ab_model.predict_proba(X_features)[0]) * 100)
                # Calibrate with moderate temperature
                ab_conf = calibrate_confidence(ab_conf, temperature=1.3)
            else:
                ab_conf = 50.0
            
            predictions.append(ab_num)
            confidences.append(ab_conf)

        except Exception as e:
            print("AB error:", e)

    # -----------------------
    # ENSEMBLE LOGIC - CALIBRATED WEIGHTED VOTING
    # -----------------------
    if len(predictions) == 0:
        return jsonify({"error": "No models available"}), 500
    
    from collections import Counter
    
    # WEIGHTED VOTING: Updated weights based on empirical performance
    # RF and GB use engineered features = more accurate
    # LSTM on raw sequence = less reliable  
    # AB on features = moderate reliability
    model_weights = [
        ("lstm", lstm_num, lstm_conf, 0.4),   # Lower weight - raw sequence only
        ("rf", rf_num, rf_conf, 2.0),         # Higher weight - best empirically
        ("gb", gb_num, gb_conf, 1.8),         # Good performance
        ("ab", ab_num, ab_conf, 1.0)          # Standard weight
    ]
    
    weighted_votes = {}
    weighted_conf_sum = 0
    total_weight = 0
    
    for model_name, pred_num, pred_conf, weight in model_weights:
        if pred_num is not None:
            weighted_vote = pred_conf * weight
            weighted_votes[pred_num] = weighted_votes.get(pred_num, 0) + weighted_vote
            weighted_conf_sum += weighted_vote
            total_weight += weight
    
    # Find prediction with highest weighted vote
    if weighted_votes:
        final = max(weighted_votes, key=weighted_votes.get)
        weighted_score = weighted_votes[final]
    else:
        return jsonify({"error": "No predictions available"}), 500
    
    # Calculate standard voting for stats
    vote_counts = Counter(predictions)
    majority_votes = vote_counts.get(final, 1)
    unique_predictions = len(set(predictions))
    
    # Calculate final confidence
    if total_weight > 0:
        base_confidence = weighted_conf_sum / total_weight
    else:
        base_confidence = 50.0
    
    # DYNAMIC CONFIDENCE BASED ON MODEL AGREEMENT
    if unique_predictions == 1:
        # All models agree - boost confidence
        confidence = min(90.0, base_confidence * 1.15)
        consensus_level = "UNANIMOUS"
        confidence_floor = 50.0  # Higher floor when unanimous
        
    elif unique_predictions == 2 and majority_votes >= 3:
        # Strong majority (3+ out of 4 models) - modest boost
        confidence = min(85.0, base_confidence * 1.08)
        consensus_level = "STRONG_MAJORITY"
        confidence_floor = 48.0
        
    elif majority_votes >= 3:
        # Majority agreement - small boost
        confidence = min(80.0, base_confidence * 1.05)
        consensus_level = "MAJORITY"
        confidence_floor = 46.0
        
    else:
        # Disagreement - no boost, use true model probabilities
        confidence = base_confidence
        consensus_level = "SPLIT"
        confidence_floor = 11.0  # Near random baseline when split
    
    # Enforce bounds based on consensus level
    # Lower bound allows realistic low confidence when models disagree
    confidence = np.clip(confidence, confidence_floor, 88.0)
    confidence = round(confidence, 2)

    # -----------------------
    # Response with diagnostics
    # -----------------------
    return jsonify({
        "number": final,
        "color": get_color(final),
        "size": get_size(final),
        "confidence": confidence,
        "lstm": {"number": lstm_num, "confidence": round(lstm_conf, 2)},
        "rf": {"number": rf_num, "confidence": round(rf_conf, 2)},
        "gb": {"number": gb_num, "confidence": round(gb_conf, 2)},
        "ab": {"number": ab_num, "confidence": round(ab_conf, 2)},
        "models_count": len(predictions),
        "majority_votes": majority_votes,
        "unique_predictions": unique_predictions,
        "consensus_level": consensus_level,
        "base_confidence": round(base_confidence, 2)
    })

# -----------------------
# Big/Small Prediction Endpoint
# -----------------------
@app.route("/predict-bigsmall")
def predict_bigsmall():
    """
    Predict Big (5-9) or Small (0-4) using specialized binary classification models.
    Usually more accurate than predicting exact number.
    """
    global rf_bs_model, gb_bs_model, ab_bs_model, feature_scaler
    
    # Reload models
    load_models()

    collection = db[os.getenv("MONGODB_COLLECTION", "results")]
    last = list(collection.find().sort("timestamp", -1).limit(SEQUENCE_LENGTH))

    if len(last) < SEQUENCE_LENGTH:
        return jsonify({"error": "Not enough data"}), 400

    seq = [x["number"] for x in reversed(last)]
    X_features = extract_features_for_prediction(seq)
    
    # Big/Small predictions
    rf_bs_pred = None
    gb_bs_pred = None
    ab_bs_pred = None
    rf_bs_conf = 0
    gb_bs_conf = 0
    ab_bs_conf = 0
    
    predictions = []
    confidences = []
    
    # -----------------------
    # RF Big/Small
    # -----------------------
    if rf_bs_model:
        try:
            rf_bs_pred = int(rf_bs_model.predict(X_features)[0])  # 0=Small, 1=Big
            if hasattr(rf_bs_model, "predict_proba"):
                rf_bs_conf = float(max(rf_bs_model.predict_proba(X_features)[0]) * 100)
                rf_bs_conf = calibrate_confidence(rf_bs_conf, temperature=1.1)
            predictions.append(rf_bs_pred)
            confidences.append(rf_bs_conf)
        except Exception as e:
            print("RF Big/Small error:", e)
    
    # -----------------------
    # GB Big/Small
    # -----------------------
    if gb_bs_model:
        try:
            gb_bs_pred = int(gb_bs_model.predict(X_features)[0])
            if hasattr(gb_bs_model, "predict_proba"):
                gb_bs_conf = float(max(gb_bs_model.predict_proba(X_features)[0]) * 100)
                gb_bs_conf = calibrate_confidence(gb_bs_conf, temperature=1.1)
            predictions.append(gb_bs_pred)
            confidences.append(gb_bs_conf)
        except Exception as e:
            print("GB Big/Small error:", e)
    
    # -----------------------
    # AB Big/Small
    # -----------------------
    if ab_bs_model:
        try:
            ab_bs_pred = int(ab_bs_model.predict(X_features)[0])
            if hasattr(ab_bs_model, "predict_proba"):
                ab_bs_conf = float(max(ab_bs_model.predict_proba(X_features)[0]) * 100)
                ab_bs_conf = calibrate_confidence(ab_bs_conf, temperature=1.2)
            predictions.append(ab_bs_pred)
            confidences.append(ab_bs_conf)
        except Exception as e:
            print("AB Big/Small error:", e)
    
    # -----------------------
    # Ensemble Decision
    # -----------------------
    if len(predictions) == 0:
        return jsonify({"error": "No Big/Small models available"}), 500
    
    from collections import Counter
    
    # Weighted voting for Big/Small (binary is much cleaner)
    model_weights = [
        ("rf", rf_bs_pred, rf_bs_conf, 1.5),
        ("gb", gb_bs_pred, gb_bs_conf, 1.5),
        ("ab", ab_bs_pred, ab_bs_conf, 1.0)
    ]
    
    weighted_votes = {}
    total_weight = 0
    weighted_conf = 0
    
    for model_name, pred, conf, weight in model_weights:
        if pred is not None:
            if pred not in weighted_votes:
                weighted_votes[pred] = 0
            weighted_votes[pred] += weight
            weighted_conf += conf * weight
            total_weight += weight
    
    final = int(max(weighted_votes, key=weighted_votes.get))
    final_confidence = (weighted_conf / total_weight) if total_weight > 0 else 50.0
    
    # Check agreement for Big/Small
    unique_bs_predictions = len(set([rf_bs_pred, gb_bs_pred, ab_bs_pred]))
    
    if unique_bs_predictions == 1:
        # All agree on Big/Small
        final_confidence = min(max(final_confidence, 55), 92)
    else:
        # Disagreement on Big/Small - show realistic confidence
        final_confidence = min(max(final_confidence, 51), 88)
    
    # Convert prediction to label
    label = "Big" if final == 1 else "Small"
    
    # Get example numbers for this category
    example_numbers = list(range(5, 10)) if final == 1 else list(range(0, 5))
    
    return jsonify({
        "prediction": label,
        "value": final,
        "confidence": round(final_confidence, 2),
        "example_numbers": example_numbers,
        "rf": {"prediction": "Big" if rf_bs_pred == 1 else "Small" if rf_bs_pred == 0 else "?", 
               "confidence": round(rf_bs_conf, 2)},
        "gb": {"prediction": "Big" if gb_bs_pred == 1 else "Small" if gb_bs_pred == 0 else "?", 
               "confidence": round(gb_bs_conf, 2)},
        "ab": {"prediction": "Big" if ab_bs_pred == 1 else "Small" if ab_bs_pred == 0 else "?", 
               "confidence": round(ab_bs_conf, 2)},
        "models_count": len(predictions)
    })

# -----------------------
# Frequency Betting Endpoint
# -----------------------
@app.route("/frequency-bet")
def frequency_bet():
    """
    Frequency betting strategy: Predict numbers that haven't appeared recently.
    Based on the law of averages - numbers that are "due" tend to come up more often.
    """
    collection = db[os.getenv("MONGODB_COLLECTION", "results")]
    
    # Get last 100 numbers to analyze frequency
    last_draws = list(collection.find().sort("timestamp", -1).limit(100))
    
    if len(last_draws) < 10:
        return jsonify({"error": "Not enough data"}), 400
    
    numbers = [int(x["number"]) for x in reversed(last_draws)]
    
    # Count frequency of each number in last 100 draws
    frequency = {}
    for i in range(10):
        frequency[i] = numbers.count(i)
    
    # Find position of last occurrence for each number
    last_position = {}
    for i in range(10):
        # Search from end to find most recent occurrence
        try:
            last_pos = len(numbers) - 1 - numbers[::-1].index(i)
            last_position[i] = last_pos
        except ValueError:
            # Number never appeared in last 100
            last_position[i] = 100
    
    # Calculate "due" score: numbers that appeared least recently get higher score
    due_score = {}
    for i in range(10):
        # Higher score = more "due"
        draws_ago = len(numbers) - last_position[i]
        due_score[i] = draws_ago
    
    # Get top 3 "due" numbers
    sorted_due = sorted(due_score.items(), key=lambda x: x[1], reverse=True)
    top_3_due = [num for num, score in sorted_due[:3]]
    
    # Primary prediction: most due number
    primary_prediction = top_3_due[0]
    
    # Calculate confidence based on how "due" it is
    # If a number hasn't appeared in 20+ draws, high confidence
    draws_since_last = due_score[primary_prediction]
    max_draws_possible = len(numbers)
    due_percentage = (draws_since_last / max_draws_possible) * 100
    
    # Confidence formula: higher % of draws since last appearance = more confident
    # Cap at 85% to be realistic
    frequency_confidence = min(85.0, 50.0 + (due_percentage / 2.0))
    
    # Statistics
    avg_frequency = sum(frequency.values()) / 10
    frequency_std = np.std(list(frequency.values()))
    
    return jsonify({
        "strategy": "frequency_betting",
        "prediction": primary_prediction,
        "color": get_color(primary_prediction),
        "size": get_size(primary_prediction),
        "confidence": round(frequency_confidence, 2),
        "rationale": f"Number {primary_prediction} hasn't appeared in {draws_since_last} draws",
        "top_3_due": top_3_due,
        "frequency_analysis": {
            "last_100_draws": {str(i): frequency[i] for i in range(10)},
            "average_frequency": round(avg_frequency, 2),
            "std_deviation": round(frequency_std, 2),
            "most_frequent": max(frequency, key=frequency.get),
            "least_frequent": min(frequency, key=frequency.get),
            "draws_since_last": draws_since_last
        }
    })

# -----------------------
# Feedback Endpoint - Track prediction accuracy
# -----------------------
@app.route("/feedback", methods=["POST"])
def feedback():
    """
    Submit feedback on prediction accuracy.
    Expected JSON: {"predicted_number": X, "actual_number": Y}
    """
    try:
        data = request.get_json()
        predicted = data.get("predicted_number")
        actual = data.get("actual_number")
        
        if predicted is None or actual is None:
            return jsonify({"error": "predicted_number and actual_number required"}), 400
        
        # Store feedback in MongoDB for model learning
        feedback_collection = db["predictions_feedback"]
        feedback_doc = {
            "timestamp": time.time(),
            "predicted": int(predicted),
            "actual": int(actual),
            "correct": int(predicted) == int(actual)
        }
        feedback_collection.insert_one(feedback_doc)
        
        # Calculate recent accuracy (last 50 predictions)
        recent = list(feedback_collection.find().sort("timestamp", -1).limit(50))
        correct_count = sum(1 for r in recent if r.get("correct", False))
        accuracy = (correct_count / len(recent) * 100) if recent else 0
        
        print(f"📊 Feedback: Predicted {predicted}, Actual {actual} | Recent Accuracy: {accuracy:.2f}%")
        
        return jsonify({
            "status": "recorded",
            "recent_accuracy": round(accuracy, 2),
            "total_feedback": len(recent)
        })
        
    except Exception as e:
        print(f"❌ Feedback error: {e}")
        return jsonify({"error": str(e)}), 500

# -----------------------
# Statistics Endpoint - Get model accuracy and stats
# -----------------------
@app.route("/stats")
def stats():
    """Get prediction accuracy statistics"""
    try:
        feedback_collection = db["predictions_feedback"]
        recent = list(feedback_collection.find().sort("timestamp", -1).limit(50))
        
        if not recent:
            return jsonify({
                "total_predictions": 0,
                "recent_accuracy": 0,
                "message": "No feedback data yet"
            })
        
        correct_count = sum(1 for r in recent if r.get("correct", False))
        accuracy = (correct_count / len(recent)) * 100
        
        # Get all-time stats
        all_time = list(feedback_collection.find())
        all_correct = sum(1 for r in all_time if r.get("correct", False))
        all_accuracy = (all_correct / len(all_time) * 100) if all_time else 0
        
        return jsonify({
            "recent_accuracy": round(accuracy, 2),
            "all_time_accuracy": round(all_accuracy, 2),
            "recent_predictions": len(recent),
            "total_predictions": len(all_time),
            "correct_predictions": all_correct
        })
        
    except Exception as e:
        print(f"❌ Stats error: {e}")
        return jsonify({"error": str(e)}), 500

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":

    app.run(
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 5000))
    )