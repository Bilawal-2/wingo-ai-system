#!/usr/bin/env python3
"""
Quick test script to verify the WinGo API is working
"""

from api_scraper import fetch_wingo_result, fetch_wingo_history
import json

print("=" * 80)
print("🧪 WinGo API Test Script")
print("=" * 80)

# Test 1: Fetch latest result
print("\n[Test 1] Fetching latest game result...")
result = fetch_wingo_result()

if result:
    print("✅ SUCCESS!")
    print(f"   Number: {result['number']}")
    print(f"   Color: {result['color']}")
    print(f"   Size: {result['size']}")
    print(f"   Timestamp: {result['timestamp']}")
else:
    print("❌ FAILED - Could not fetch result")

# Test 2: Fetch historical data
print("\n[Test 2] Fetching historical data (page 1)...")
history = fetch_wingo_history(pages=1)

if history:
    print(f"✅ SUCCESS! Fetched {len(history)} results")
    print("\n   First 5 results:")
    for i, res in enumerate(history[:5], 1):
        print(f"   [{i}] #{res['number']} | {res['color']:6s} | {res['size']:5s} | ts={res['timestamp']}")
    
    print(f"\n   Last 5 results:")
    for i, res in enumerate(history[-5:], len(history)-4):
        print(f"   [{i}] #{res['number']} | {res['color']:6s} | {res['size']:5s} | ts={res['timestamp']}")
else:
    print("❌ FAILED - Could not fetch history")

print("\n" + "=" * 80)
print("✅ API Test Complete")
print("=" * 80)
