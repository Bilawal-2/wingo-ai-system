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

model = joblib.load(MODEL_PATH)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "wingo")
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]

@app.route("/predict")
def predict():
    collection_name = os.getenv("MONGODB_COLLECTION", "results")
    collection = db[collection_name]
    last = list(collection.find().sort("timestamp",-1).limit(2))

    x = [[last[0]["number"],last[1]["number"]]]

    prediction = int(model.predict(x)[0])

    return jsonify({"prediction":prediction})

if __name__ == "__main__":
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = int(os.getenv("API_PORT", 5000))
    app.run(host=api_host, port=api_port)