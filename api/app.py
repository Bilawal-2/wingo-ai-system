import os
import time
import joblib
from flask import Flask, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "models/model.pkl")

# wait for model
while not os.path.exists(MODEL_PATH):
    print("Waiting for trained model...")
    time.sleep(5)

print("Model found. Loading...")
model = joblib.load(MODEL_PATH)

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "wingo")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]


# -------------------------------
# helper functions
# -------------------------------

def get_size(num):
    return "Big" if num >= 5 else "Small"


def get_color(num):

    if num in [0, 5]:
        return "Violet"

    if num % 2 == 0:
        return "Red"

    return "Green"


# -------------------------------
# prediction endpoint
# -------------------------------

@app.route("/predict")
def predict():

    collection_name = os.getenv("MONGODB_COLLECTION", "results")
    collection = db[collection_name]

    last = list(collection.find().sort("timestamp", -1).limit(2))

    if len(last) < 2:
        return jsonify({"error": "Not enough data"}), 400

    x = [[last[0]["number"], last[1]["number"]]]

    prediction = int(model.predict(x)[0])

    result = {
        "number": prediction,
        "color": get_color(prediction),
        "size": get_size(prediction)
    }

    return jsonify(result)


# -------------------------------
# run api
# -------------------------------

if __name__ == "__main__":

    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = int(os.getenv("API_PORT", 5000))

    app.run(host=api_host, port=api_port)