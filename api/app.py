import os
import time
import joblib
from flask import Flask, jsonify
from pymongo import MongoClient

app = Flask(__name__)

MODEL_PATH = "models/model.pkl"
# wait for model
while not os.path.exists(MODEL_PATH):
    print("Waiting for trained model...")
    time.sleep(5)

model = joblib.load(MODEL_PATH)

client = MongoClient("mongodb://mongodb:27017/")
db = client.wingo

@app.route("/predict")
def predict():

    last = list(db.results.find().sort("timestamp",-1).limit(2))

    x = [[last[0]["number"],last[1]["number"]]]

    prediction = int(model.predict(x)[0])

    return jsonify({"prediction":prediction})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)