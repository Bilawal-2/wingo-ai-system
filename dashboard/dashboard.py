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
        prediction = data.get("prediction", "No prediction")

        st.success(f"Next Prediction: {prediction}")

    else:
        st.error("API returned an error")

except Exception as e:
    st.warning("Waiting for API to be ready...")
    st.text(str(e))