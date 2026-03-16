import streamlit as st
import requests

st.title("Wingo AI Predictor")

try:
    res = requests.get("http://api:5000/predict", timeout=5)

    if res.status_code == 200:
        data = res.json()
        prediction = data.get("prediction", "No prediction")

        st.success(f"Next Prediction: {prediction}")

    else:
        st.error("API returned an error")

except Exception as e:
    st.warning("Waiting for API to be ready...")
    st.text(str(e))