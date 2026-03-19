import os
import time
import numpy as np
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping
import joblib

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "wingo")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]

SEQUENCE_LENGTH = 10
MIN_DATA_POINTS = 100  # Increased from 50

while True:
    collection = db["results"]
    data = list(collection.find().sort("timestamp", 1))

    if len(data) < MIN_DATA_POINTS:
        print(f"Waiting for enough data... ({len(data)}/{MIN_DATA_POINTS})")
        time.sleep(20)
        continue

    df = pd.DataFrame(data)

    if "number" not in df.columns:
        time.sleep(20)
        continue

    numbers = df["number"].values

    # -------------------------
    # Build sequences
    # -------------------------
    X, y = [], []
    for i in range(SEQUENCE_LENGTH, len(numbers)):
        X.append(numbers[i-SEQUENCE_LENGTH:i])
        y.append(numbers[i])

    X = np.array(X)
    y = np.array(y)

    # -------------------------
    # Normalize
    # -------------------------
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X.reshape(-1,1)).reshape(X.shape)
    
    # Reshape for LSTM
    X_scaled_lstm = X_scaled.reshape((X_scaled.shape[0], X_scaled.shape[1], 1))

    # -------------------------
    # LSTM MODEL - IMPROVED
    # -------------------------
    lstm_model = Sequential([
        LSTM(128, activation='relu', input_shape=(SEQUENCE_LENGTH, 1), return_sequences=True),
        Dropout(0.2),
        BatchNormalization(),
        
        LSTM(64, activation='relu', return_sequences=True),
        Dropout(0.2),
        BatchNormalization(),
        
        LSTM(32, activation='relu'),
        Dropout(0.2),
        BatchNormalization(),
        
        Dense(64, activation='relu'),
        Dropout(0.3),
        
        Dense(32, activation='relu'),
        Dropout(0.2),
        
        Dense(10, activation='softmax')
    ])

    lstm_model.compile(
        loss='sparse_categorical_crossentropy', 
        optimizer='adam', 
        metrics=['accuracy']
    )

    # Early stopping to prevent overfitting
    early_stop = EarlyStopping(monitor='loss', patience=3, restore_best_weights=True)

    print("🚀 Training LSTM model...")
    lstm_model.fit(
        X_scaled_lstm, y, 
        epochs=20,  # Increased from 5
        batch_size=16,
        verbose=0,
        callbacks=[early_stop]
    )

    lstm_model.save("models/lstm_model.keras")
    print("✅ LSTM model saved")

    # -------------------------
    # RANDOM FOREST - IMPROVED
    # -------------------------
    print("🚀 Training Random Forest model...")
    rf = RandomForestClassifier(
        n_estimators=200,      # Increased from default 100
        max_depth=15,          # Added depth constraint
        min_samples_split=5,   # Better leaf nodes
        min_samples_leaf=2,
        max_features='sqrt',
        n_jobs=-1
    )
    rf.fit(X, y)
    joblib.dump(rf, "models/rf_model.pkl")
    print("✅ Random Forest model saved")

    # -------------------------
    # GRADIENT BOOSTING - NEW
    # -------------------------
    print("🚀 Training Gradient Boosting model...")
    gb = GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.1,
        max_depth=5,
        min_samples_split=5,
        subsample=0.8
    )
    gb.fit(X, y)
    joblib.dump(gb, "models/gb_model.pkl")
    print("✅ Gradient Boosting model saved")

    # save scaler
    joblib.dump(scaler, "models/scaler.pkl")

    print("🔥 Ensemble models trained with improved confidence!")
    print(f"📊 Total training samples: {len(X)}")

    time.sleep(60)