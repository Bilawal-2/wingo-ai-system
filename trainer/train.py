import os
import time
import pandas as pd
from pymongo import MongoClient
from sklearn.ensemble import RandomForestClassifier
import joblib
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "wingo")
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]

while True:
    collection_name = os.getenv("MONGODB_COLLECTION", "results")
    collection = db[collection_name]
    data = list(collection.find())

    # wait until we have enough rows
    min_samples = int(os.getenv("MIN_TRAINING_SAMPLES", 30))
    if len(data) < min_samples:
        print("Waiting for enough data...")
        time.sleep(30)
        continue

    df = pd.DataFrame(data)

    if "number" not in df.columns:
        print("Number column missing...")
        time.sleep(30)
        continue

    df["lag1"] = df["number"].shift(1)
    df["lag2"] = df["number"].shift(2)

    df = df.dropna()

    min_data_shift = int(os.getenv("MIN_DATA_AFTER_SHIFT", 10))
    if len(df) < min_data_shift:
        print("Not enough training samples after shift...")
        time.sleep(30)
        continue

    X = df[["lag1","lag2"]]
    y = df["number"]

    model = RandomForestClassifier()

    model.fit(X,y)

    model_path = os.getenv("MODEL_PATH", "models/model.pkl")
    joblib.dump(model, model_path)

    print("Model trained successfully")

    sleep_interval = int(os.getenv("TRAINER_SLEEP_INTERVAL", 120))
    time.sleep(sleep_interval)