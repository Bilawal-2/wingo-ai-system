import os
import time
import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Wingo AI Predictor", layout="centered")

st.title("🎯 Wingo AI Predictor")

# -----------------------
# Config
# -----------------------
api_url = os.getenv("DASHBOARD_API_URL", "http://api:5000")
timeout = int(os.getenv("DASHBOARD_TIMEOUT", 5))
confidence_threshold = int(os.getenv("CONFIDENCE_THRESHOLD", 60))

# -----------------------
# Fetch Prediction
# -----------------------
try:
    res = requests.get(f"{api_url}/predict", timeout=timeout)

    if res.status_code == 200:

        data = res.json()

        number = data.get("number")
        color = data.get("color")
        size = data.get("size")
        confidence = data.get("confidence", 0)

        # -----------------------
        # Main Metrics
        # -----------------------
        col1, col2 = st.columns(2)

        with col1:
            st.metric("🔢 Number", number)

        with col2:
            st.metric("📊 Confidence", f"{confidence}%")

        st.divider()

        # -----------------------
        # Confidence Status
        # -----------------------
        if confidence < confidence_threshold:
            st.warning("⚠️ Low confidence — skip this round")
        else:
            st.success("✅ High confidence prediction")

        st.divider()

        # -----------------------
        # Color Display
        # -----------------------
        st.subheader("🎨 Color Prediction")

        if color == "Red":
            st.markdown("<h2 style='color:red'>● RED</h2>", unsafe_allow_html=True)

        elif color == "Green":
            st.markdown("<h2 style='color:green'>● GREEN</h2>", unsafe_allow_html=True)

        elif color == "Violet":
            st.markdown("<h2 style='color:purple'>● VIOLET</h2>", unsafe_allow_html=True)

        # -----------------------
        # Size Display
        # -----------------------
        st.subheader("📏 Size Prediction")

        if size == "Big":
            st.markdown("<h2 style='color:orange'>BIG</h2>", unsafe_allow_html=True)
        else:
            st.markdown("<h2 style='color:blue'>SMALL</h2>", unsafe_allow_html=True)

    else:
        st.error("❌ API returned an error")

except Exception as e:
    st.warning("⏳ Waiting for API to be ready...")
    st.text(str(e))

# -----------------------
# Auto Refresh
# -----------------------
time.sleep(5)
st.rerun()