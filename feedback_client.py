#!/usr/bin/env python3
"""
Feedback Client for WinGo AI System
====================================
This script gets predictions and allows you to record feedback.
The system learns from both correct and incorrect predictions.

Usage:
    python3 feedback_client.py
"""

import requests
import json
import time

# Configuration
API_URL = "https://signal.bilionix.com/api"

def get_prediction():
    """Get a new prediction from the API"""
    try:
        response = requests.get(f"{API_URL}/predict", verify=False)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error getting prediction: {e}")
        return None

def submit_feedback(predicted, actual):
    """Submit feedback on prediction accuracy"""
    try:
        data = {
            "predicted_number": int(predicted),
            "actual_number": int(actual)
        }
        response = requests.post(
            f"{API_URL}/feedback",
            json=data,
            verify=False
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error submitting feedback: {e}")
        return None

def get_stats():
    """Get prediction statistics"""
    try:
        response = requests.get(f"{API_URL}/stats", verify=False)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return None

def main():
    """Main feedback loop"""
    print("=" * 60)
    print("🎮 WinGo AI Prediction Feedback System")
    print("=" * 60)
    
    while True:
        print("\n📊 Options:")
        print("  1. Get prediction")
        print("  2. Submit feedback")
        print("  3. View statistics")
        print("  4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            pred = get_prediction()
            if pred:
                print(f"\n✅ Prediction received:")
                print(f"  Number: #{pred['number']}")
                print(f"  Color: {pred['color']}")
                print(f"  Size: {pred['size']}")
                print(f"  Confidence: {pred['confidence']}%")
                print(f"  Models: {pred['models_count']}")
                print(f"  LSTM: {pred['lstm']} | RF: {pred['rf']} | GB: {pred['gb']} | AB: {pred['ab']}")
        
        elif choice == "2":
            predicted = input("Enter predicted number (0-9): ").strip()
            actual = input("Enter actual number (0-9): ").strip()
            
            feedback = submit_feedback(predicted, actual)
            if feedback:
                is_correct = predicted == actual
                status = "✅ CORRECT" if is_correct else "❌ INCORRECT"
                print(f"\n📝 Feedback recorded ({status})")
                print(f"  Recent Accuracy: {feedback['recent_accuracy']}%")
                print(f"  Total Feedback: {feedback['total_feedback']}")
        
        elif choice == "3":
            stats = get_stats()
            if stats:
                print(f"\n📈 Prediction Statistics:")
                print(f"  Recent Accuracy: {stats['recent_accuracy']}%")
                print(f"  All-Time Accuracy: {stats['all_time_accuracy']}%")
                print(f"  Recent Predictions: {stats['recent_predictions']}")
                print(f"  Total Predictions: {stats['total_predictions']}")
                print(f"  Correct Predictions: {stats['correct_predictions']}")
        
        elif choice == "4":
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option. Please try again.")

if __name__ == "__main__":
    main()
