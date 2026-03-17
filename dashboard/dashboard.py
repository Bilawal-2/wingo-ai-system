import os
import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()

st.title("Wingo AI Predictor")

try:
    api_url = os.getenv("DASHBOARD_API_URL", "http://api:5000")
    timeout = int(os.getenv("DASHBOARD_TIMEOUT", 5))

    res = requests.get(f"{api_url}/predict", timeout=timeout)

    if res.status_code == 200:

        data = res.json()

        number = data.get("number")
        color = data.get("color")
        size = data.get("size")

        st.success(f"Predicted Number: {number}")

        st.subheader("Color Prediction")

        if color == "Red":
            st.markdown("<h3 style='color:red'>RED</h3>", unsafe_allow_html=True)

        elif color == "Green":
            st.markdown("<h3 style='color:green'>GREEN</h3>", unsafe_allow_html=True)

        elif color == "Violet":
            st.markdown("<h3 style='color:purple'>VIOLET</h3>", unsafe_allow_html=True)

        st.subheader("Big / Small Prediction")

        if size == "Big":
            st.markdown("<h3 style='color:orange'>BIG</h3>", unsafe_allow_html=True)

        else:
            st.markdown("<h3 style='color:blue'>SMALL</h3>", unsafe_allow_html=True)

    else:
        st.error("API returned an error")

except Exception as e:
    st.warning("Waiting for API to be ready...")
    st.text(str(e))