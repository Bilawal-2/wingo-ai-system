import os
import time
import numpy as np
import joblib
from flask import Flask, jsonify
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
SCALER_PATH = os.getenv("SCALER_PATH", "models/scaler.pkl")

# -----------------------
# Load Models
# -----------------------
lstm_model = None
rf_model = None
gb_model = None
scaler = None

# wait for at least one model
while not (os.path.exists(LSTM_PATH) or os.path.exists(RF_PATH)):
    print("Waiting for models...")
    time.sleep(5)

# load LSTM
if os.path.exists(LSTM_PATH):
    from tensorflow.keras.models import load_model
    lstm_model = load_model(LSTM_PATH)
    print("✅ LSTM loaded")

# load RF
if os.path.exists(RF_PATH):
    rf_model = joblib.load(RF_PATH)
    print("✅ RF loaded")

# load GB
if os.path.exists(GB_PATH):
    gb_model = joblib.load(GB_PATH)
    print("✅ GB loaded")

# load scaler
if os.path.exists(SCALER_PATH):
    scaler = joblib.load(SCALER_PATH)
    print("✅ Scaler loaded")

# -----------------------
# MongoDB
# -----------------------
client = MongoClient(os.getenv("MONGODB_URI", "mongodb://mongodb:27017/"))
db = client[os.getenv("MONGODB_DB", "wingo")]

# -----------------------
# Helpers
# -----------------------
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

    collection = db[os.getenv("MONGODB_COLLECTION", "results")]

    last = list(collection.find().sort("timestamp", -1).limit(SEQUENCE_LENGTH))

    if len(last) < SEQUENCE_LENGTH:
        return jsonify({"error": "Not enough data"}), 400

    seq = [x["number"] for x in reversed(last)]
    X_seq = np.array(seq).reshape(1, SEQUENCE_LENGTH)

    lstm_num, lstm_conf = None, 0
    rf_num, rf_conf = None, 0
    gb_num, gb_conf = None, 0
    
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

            pred = lstm_model.predict(X_seq.reshape(1, SEQUENCE_LENGTH, 1), verbose=0)[0]

            lstm_num = int(np.argmax(pred))
            lstm_conf = float(np.max(pred) * 100)
            
            predictions.append(lstm_num)
            confidences.append(lstm_conf)

        except Exception as e:
            print("LSTM error:", e)

    # -----------------------
    # RF Prediction
    # -----------------------
    if rf_model:

        try:
            rf_num = int(rf_model.predict(X_seq)[0])

            if hasattr(rf_model, "predict_proba"):
                rf_conf = float(max(rf_model.predict_proba(X_seq)[0]) * 100)
            else:
                rf_conf = 50.0
            
            predictions.append(rf_num)
            confidences.append(rf_conf)

        except Exception as e:
            print("RF error:", e)

    # -----------------------
    # GB Prediction
    # -----------------------
    if gb_model:

        try:
            gb_num = int(gb_model.predict(X_seq)[0])

            if hasattr(gb_model, "predict_proba"):
                gb_conf = float(max(gb_model.predict_proba(X_seq)[0]) * 100)
            else:
                gb_conf = 50.0
            
            predictions.append(gb_num)
            confidences.append(gb_conf)

        except Exception as e:
            print("GB error:", e)

    # -----------------------
    # ENSEMBLE LOGIC - IMPROVED
    # -----------------------
    if len(predictions) == 0:
        return jsonify({"error": "No models available"}), 500
    
    # Voting ensemble - use majority vote
    from collections import Counter
    vote_counts = Counter(predictions)
    final = vote_counts.most_common(1)[0][0]
    
    # Average confidence from all models
    confidence = round(np.mean(confidences), 2)
    
    # Boost confidence if all models agree
    unique_predictions = len(set(predictions))
    if unique_predictions == 1:
        confidence = min(99.9, confidence * 1.15)  # Boost if unanimous
    
    confidence = round(confidence, 2)

    # -----------------------
    # Response
    # -----------------------
    return jsonify({
        "number": final,
        "color": get_color(final),
        "size": get_size(final),
        "confidence": confidence,
        "lstm": lstm_num,
        "rf": rf_num,
        "gb": gb_num
    })

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":

    app.run(
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 5000))
    )