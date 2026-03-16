import time
import pandas as pd
from pymongo import MongoClient
from sklearn.ensemble import RandomForestClassifier
import joblib

client = MongoClient("mongodb://mongodb:27017/")
db = client.wingo

while True:

    data = list(db.results.find())

    # wait until we have enough rows
    if len(data) < 30:
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

    if len(df) < 10:
        print("Not enough training samples after shift...")
        time.sleep(30)
        continue

    X = df[["lag1","lag2"]]
    y = df["number"]

    model = RandomForestClassifier()

    model.fit(X,y)

    joblib.dump(model, "models/model.pkl")

    print("Model trained successfully")

    time.sleep(120)