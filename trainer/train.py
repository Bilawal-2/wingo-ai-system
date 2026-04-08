import os
import time
import numpy as np
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, AdaBoostClassifier
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import KFold
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization, Input, Conv1D, MaxPooling1D, Flatten
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import joblib
import warnings
warnings.filterwarnings('ignore')

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "wingo")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]

SEQUENCE_LENGTH = 10
MIN_DATA_POINTS = 150  # Increased for better training

print("🚀 Trainer started!")

# -----------------------
# FEATURE ENGINEERING
# -----------------------
def extract_features(numbers):
    """
    Extract rich features from number sequences to improve predictions.
    
    Features include:
    - Rolling statistics (mean, std, min, max)
    - Trend indicators
    - Distance from previous numbers
    - Frequency patterns
    - Recency-weighted features
    """
    features = []
    window_sizes = [3, 5, 7]
    
    for i in range(SEQUENCE_LENGTH, len(numbers)):
        seq = numbers[i-SEQUENCE_LENGTH:i]
        f = []
        
        # Basic sequence stats
        f.append(np.mean(seq))           # Average
        f.append(np.std(seq))            # Volatility
        f.append(np.max(seq) - np.min(seq))  # Range
        
        # Trend features
        f.append(seq[-1] - seq[0])       # Overall trend
        f.append(seq[-1] - seq[-2] if len(seq) > 1 else 0)  # Recent change
        
        # Distance from averages
        running_avg = np.mean(seq[:-1]) if len(seq) > 1 else 5
        f.append(abs(seq[-1] - running_avg))  # Distance from trend
        
        # Recency weights (recent values matter more)
        weights = np.linspace(0.5, 2.0, len(seq))
        weighted_avg = np.average(seq, weights=weights)
        f.append(weighted_avg)
        
        # Frequency of high (5-9) vs low (0-4) numbers
        high_count = sum(1 for x in seq if x >= 5)
        f.append(high_count / len(seq))  # High number frequency
        
        # Position features
        f.append(seq[-1] / 9.0)          # Last number normalized
        f.append(max(seq) / 9.0)         # Max normalized
        f.append(min(seq) / 9.0)         # Min normalized
        
        features.append(f)
    
    return np.array(features, dtype=np.float32)

def get_big_small_label(number):
    """Convert number (0-9) to Big (1) or Small (0). Big=5-9, Small=0-4"""
    return 1 if number >= 5 else 0

def calculate_model_accuracy():
    """Calculate recent model accuracy from feedback data"""
    try:
        feedback_collection = db["predictions_feedback"]
        recent = list(feedback_collection.find().sort("timestamp", -1).limit(50))
        
        if not recent:
            return 50.0  # Default if no feedback
        
        correct_count = sum(1 for r in recent if r.get("correct", False))
        accuracy = (correct_count / len(recent)) * 100
        return accuracy
    except:
        return 50.0

def evaluate_model_with_cv(model, X, y, cv_folds=5):
    """
    Evaluate model using k-fold cross-validation to prevent overfitting.
    
    Returns:
    - Mean CV accuracy
    - Std of CV scores  
    - Individual fold scores
    """
    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=42)
    cv_scores = []
    
    for train_idx, val_idx in kf.split(X):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        # Clone and train model
        from sklearn.base import clone
        model_clone = clone(model)
        model_clone.fit(X_train, y_train)
        
        # Score
        score = model_clone.score(X_val, y_val)
        cv_scores.append(score)
    
    return np.mean(cv_scores), np.std(cv_scores), cv_scores

def analyze_feature_importance(model, feature_names):
    """
    Extract and display feature importance from tree-based models.
    """
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        
        # Get top features
        indices = np.argsort(importances)[::-1][:5]
        
        print("\n   📊 Top 5 Important Features:")
        for i, idx in enumerate(indices, 1):
            feat_name = feature_names[idx] if idx < len(feature_names) else f"Feature_{idx}"
            importance = importances[idx] * 100
            print(f"      {i}. {feat_name}: {importance:.2f}%")
        
        return importances
    return None

def create_lstm_model():
    """Create CNN-LSTM hybrid model for better pattern recognition"""
    model = Sequential([
        Input(shape=(SEQUENCE_LENGTH, 1)),
        
        # CNN layers - extract local patterns from sequence
        Conv1D(64, kernel_size=3, activation='relu', padding='same'),
        BatchNormalization(),
        Conv1D(32, kernel_size=3, activation='relu', padding='same'),
        MaxPooling1D(pool_size=2, padding='same'),
        Dropout(0.2),
        
        # LSTM layers - process temporal patterns from CNN output
        LSTM(64, activation='relu', return_sequences=True),
        Dropout(0.2),
        BatchNormalization(),
        
        LSTM(32, activation='relu', return_sequences=False),
        Dropout(0.2),
        BatchNormalization(),
        
        # Dense layers - final prediction
        Dense(32, activation='relu'),
        Dropout(0.3),
        
        Dense(16, activation='relu'),
        Dropout(0.2),
        
        Dense(10, activation='softmax')
    ])
    
    model.compile(
        loss='sparse_categorical_crossentropy',
        optimizer='adam',
        metrics=['accuracy']
    )
    return model

while True:
    try:
        # Check accuracy to determine training frequency
        accuracy = calculate_model_accuracy()
        
        # Increase training frequency if accuracy drops below 55%
        if accuracy < 55:
            train_interval = 20  # Train more frequently
            print(f"⚠️  Low accuracy ({accuracy:.2f}%) - training more frequently")
        else:
            train_interval = 60  # Normal interval
        
        collection = db["results"]
        data = list(collection.find().sort("timestamp", 1))

        if len(data) < MIN_DATA_POINTS:
            print(f"⏳ Waiting for data ({len(data)}/{MIN_DATA_POINTS})")
            time.sleep(20)
            continue

        df = pd.DataFrame(data)

        if "number" not in df.columns:
            print("❌ Missing 'number' column")
            time.sleep(20)
            continue

        numbers = df["number"].values
        print(f"📊 Training with {len(numbers)} data points")

        # -------------------------
        # Build sequences & extract rich features
        # -------------------------
        X, y = [], []
        for i in range(SEQUENCE_LENGTH, len(numbers)):
            X.append(numbers[i-SEQUENCE_LENGTH:i])
            y.append(numbers[i])

        X = np.array(X, dtype=np.float32)
        y = np.array(y, dtype=np.int32)
        
        if len(X) < 10:
            print("❌ Not enough sequences")
            time.sleep(20)
            continue

        # -------------------------
        # Extract enhanced features for ensemble models
        # -------------------------
        X_features = extract_features(numbers)
        feature_names = [
            "mean", "std", "range", "trend", "recent_change",
            "distance_from_avg", "weighted_avg", "high_freq",
            "last_norm", "max_norm", "min_norm"
        ]
        print(f"✨ Extracted {X_features.shape[1]} features per sequence")
        
        # -------------------------
        # Normalize for LSTM
        # -------------------------
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(X.reshape(-1, 1)).reshape(X.shape)
        X_scaled_lstm = X_scaled.reshape((X_scaled.shape[0], X_scaled.shape[1], 1))
        
        # -------------------------
        # Normalize features for ensemble
        # -------------------------
        feature_scaler = MinMaxScaler()
        X_features_scaled = feature_scaler.fit_transform(X_features)

        # -------------------------
        # LSTM MODEL - ENHANCED
        # -------------------------
        print("🚀 Training LSTM (enhanced)...")
        lstm_model = create_lstm_model()
        
        early_stop = EarlyStopping(monitor='loss', patience=5, restore_best_weights=True)
        reduce_lr = ReduceLROnPlateau(monitor='loss', factor=0.5, patience=3, min_lr=1e-7)

        lstm_model.fit(
            X_scaled_lstm, y,
            epochs=100,             # Increased for better convergence on random data
            batch_size=8,           # Smaller batch for more updates
            validation_split=0.15,  # Use validation split to monitor
            verbose=0,
            callbacks=[early_stop, reduce_lr]
        )

        lstm_model.save("models/lstm_model.keras")
        print("✅ LSTM saved")

        # -------------------------
        # RANDOM FOREST - ENHANCED WITH CV
        # -------------------------
        print("🚀 Training Random Forest (enhanced)...")
        rf = RandomForestClassifier(
            n_estimators=400,      # Balanced for memory/accuracy
            max_depth=18,          # Reasonable depth
            min_samples_split=3,   # More conservative splits
            min_samples_leaf=2,
            max_features='sqrt',   # Standard feature selection
            n_jobs=-1,
            random_state=42,
            class_weight='balanced',  # Handle class imbalance
            criterion='gini',
            bootstrap=True
        )
        rf.fit(X_features_scaled, y)
        
        # Evaluate with CV
        try:
            rf_cv_mean, rf_cv_std, rf_cv_scores = evaluate_model_with_cv(
                RandomForestClassifier(
                    n_estimators=300, max_depth=22, min_samples_split=2,
                    max_features='sqrt', random_state=42, class_weight='balanced'
                ),
                X_features_scaled, y, cv_folds=5
            )
            print(f"   RF CV Accuracy: {rf_cv_mean:.4f} (+/- {rf_cv_std:.4f})")
        except Exception as e:
            print(f"   RF CV failed: {e}")
            rf_cv_mean = 0
        
        joblib.dump(rf, "models/rf_model.pkl")
        print("✅ RF saved")
        
        # Analyze feature importance
        analyze_feature_importance(rf, feature_names)

        # -------------------------
        # GRADIENT BOOSTING - ENHANCED WITH CV
        # -------------------------
        print("🚀 Training Gradient Boosting (enhanced)...")
        gb = GradientBoostingClassifier(
            n_estimators=350,      # Balanced for training speed
            learning_rate=0.03,    # Moderate learning rate
            max_depth=8,           # Reasonable depth
            min_samples_split=3,
            min_samples_leaf=2,
            subsample=0.8,         # Better sampling
            random_state=42,
            validation_fraction=0.1  # Use validation set
        )
        gb.fit(X_features_scaled, y)
        
        # Evaluate with CV
        try:
            gb_cv_mean, gb_cv_std, gb_cv_scores = evaluate_model_with_cv(
                GradientBoostingClassifier(
                    n_estimators=300, learning_rate=0.02, max_depth=10,
                    min_samples_split=2, subsample=0.8, random_state=42
                ),
                X_features_scaled, y, cv_folds=5
            )
            print(f"   GB CV Accuracy: {gb_cv_mean:.4f} (+/- {gb_cv_std:.4f})")
        except Exception as e:
            print(f"   GB CV failed: {e}")
            gb_cv_mean = 0
        
        joblib.dump(gb, "models/gb_model.pkl")
        print("✅ GB saved")
        
        # Analyze feature importance
        analyze_feature_importance(gb, feature_names)

        # -------------------------
        # ADABOOST - ENHANCED WITH CV
        # -------------------------
        print("🚀 Training AdaBoost (enhanced)...")
        ab = AdaBoostClassifier(
            n_estimators=500,      # More boosting rounds
            learning_rate=0.5,     # Slightly reduced for stability
            random_state=42,
            algorithm='SAMME'      # Use SAMME for multi-class
        )
        ab.fit(X_features_scaled, y)
        
        # Evaluate with CV
        try:
            ab_cv_mean, ab_cv_std, ab_cv_scores = evaluate_model_with_cv(
                AdaBoostClassifier(n_estimators=250, learning_rate=0.5, random_state=42, algorithm='SAMME'),
                X_features_scaled, y, cv_folds=5
            )
            print(f"   AB CV Accuracy: {ab_cv_mean:.4f} (+/- {ab_cv_std:.4f})")
        except Exception as e:
            print(f"   AB CV failed: {e}")
            ab_cv_mean = 0
        
        joblib.dump(ab, "models/ab_model.pkl")
        print("✅ AB saved")

        # -------------------------
        # BIG/SMALL MODELS - BINARY CLASSIFICATION (Much easier!)
        # -------------------------
        try:
            print("\n🎯 Training Big/Small Models (Binary Classification)...")
            
            # Convert labels to Big/Small (1=Big (5-9), 0=Small (0-4))
            y_bigsmall = np.array([get_big_small_label(num) for num in y], dtype=np.int32)
            
            # Count balance
            small_count = np.sum(y_bigsmall == 0)
            big_count = np.sum(y_bigsmall == 1)
            print(f"   Class Balance: Small={small_count}, Big={big_count}")
            
            # Random Forest for Big/Small
            print("   🚀 Training RF for Big/Small...")
            rf_bs = RandomForestClassifier(
                n_estimators=400,
                max_depth=18,
                min_samples_split=3,
                min_samples_leaf=2,
                max_features='sqrt',
                n_jobs=-1,
                random_state=42,
                class_weight='balanced'
            )
            rf_bs.fit(X_features_scaled, y_bigsmall)
            joblib.dump(rf_bs, "models/rf_bigsmall_model.pkl")
            print("   ✅ RF Big/Small saved")
            
            # Gradient Boosting for Big/Small
            print("   🚀 Training GB for Big/Small...")
            gb_bs = GradientBoostingClassifier(
                n_estimators=300,
                learning_rate=0.03,
                max_depth=8,
                min_samples_split=3,
                min_samples_leaf=2,
                subsample=0.8,
                random_state=42
            )
            gb_bs.fit(X_features_scaled, y_bigsmall)
            joblib.dump(gb_bs, "models/gb_bigsmall_model.pkl")
            print("   ✅ GB Big/Small saved")
            
            # AdaBoost for Big/Small
            print("   🚀 Training AB for Big/Small...")
            ab_bs = AdaBoostClassifier(
                n_estimators=300,
                learning_rate=0.6,
                random_state=42,
                algorithm='SAMME'
            )
            ab_bs.fit(X_features_scaled, y_bigsmall)
            joblib.dump(ab_bs, "models/ab_bigsmall_model.pkl")
            print("   ✅ AB Big/Small saved")
            
            # Test Big/Small accuracy with CV
            try:
                rf_bs_cv_mean, _, _ = evaluate_model_with_cv(
                    RandomForestClassifier(n_estimators=250, max_depth=16, min_samples_split=3, 
                                         max_features='sqrt', random_state=42, class_weight='balanced'),
                    X_features_scaled, y_bigsmall, cv_folds=5
                )
                gb_bs_cv_mean, _, _ = evaluate_model_with_cv(
                    GradientBoostingClassifier(n_estimators=200, learning_rate=0.03, max_depth=8,
                                             min_samples_split=3, subsample=0.8, random_state=42),
                    X_features_scaled, y_bigsmall, cv_folds=5
                )
                ab_bs_cv_mean, _, _ = evaluate_model_with_cv(
                    AdaBoostClassifier(n_estimators=200, learning_rate=0.6, random_state=42, algorithm='SAMME'),
                    X_features_scaled, y_bigsmall, cv_folds=5
                )
                print(f"   📊 Big/Small CV Accuracy: RF={rf_bs_cv_mean:.2%}, GB={gb_bs_cv_mean:.2%}, AB={ab_bs_cv_mean:.2%}")
            except Exception as e:
                print(f"   ⚠️  Big/Small CV failed: {e}")
                
        except Exception as bs_error:
            print(f"   ❌ Big/Small Training Error: {bs_error}")
            import traceback
            traceback.print_exc()

        # save scalers
        joblib.dump(scaler, "models/scaler.pkl")
        joblib.dump(feature_scaler, "models/feature_scaler.pkl")
        print("✅ Scalers saved")

        print("🔥 All models trained (Number + Big/Small)!")
        print(f"📈 Samples: {len(X)} sequences")
        print(f"📊 Recent Feedback Accuracy: {accuracy:.2f}%")
        print(f"🎯 Cross-Validation Scores: RF={rf_cv_mean:.2%}, GB={gb_cv_mean:.2%}, AB={ab_cv_mean:.2%}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    time.sleep(train_interval)