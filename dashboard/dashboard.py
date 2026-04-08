import os
import time
import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Wingo AI Predictor", layout="wide")

# Initialize session state
if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = False
    st.session_state.feedback_message = ""
    st.session_state.feedback_type = ""

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

        # -----------------------
        # Big/Small Specialized Prediction
        # -----------------------
        st.divider()
        st.subheader("🎲 Big/Small Specialized Prediction")
        
        try:
            bs_res = requests.get(f"{api_url}/predict-bigsmall", timeout=timeout)
            
            if bs_res.status_code == 200:
                bs_data = bs_res.json()
                
                bs_pred = bs_data.get("prediction", "—")
                bs_conf = bs_data.get("confidence", 0)
                bs_examples = bs_data.get("example_numbers", [])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if bs_pred == "Big":
                        st.markdown("<h3 style='color:orange'>🟠 BIG (5-9)</h3>", unsafe_allow_html=True)
                    else:
                        st.markdown("<h3 style='color:blue'>🔵 SMALL (0-4)</h3>", unsafe_allow_html=True)
                
                with col2:
                    st.metric("📊 Confidence", f"{bs_conf}%")
                
                # Show individual model predictions for Big/Small
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    rf_bs = bs_data.get("rf", {})
                    rf_bs_pred = rf_bs.get("prediction", "—")
                    rf_bs_conf = rf_bs.get("confidence", 0)
                    st.metric("RF Vote", rf_bs_pred, f"{rf_bs_conf:.1f}%")
                
                with col2:
                    gb_bs = bs_data.get("gb", {})
                    gb_bs_pred = gb_bs.get("prediction", "—")
                    gb_bs_conf = gb_bs.get("confidence", 0)
                    st.metric("GB Vote", gb_bs_pred, f"{gb_bs_conf:.1f}%")
                
                with col3:
                    ab_bs = bs_data.get("ab", {})
                    ab_bs_pred = ab_bs.get("prediction", "—")
                    ab_bs_conf = ab_bs.get("confidence", 0)
                    st.metric("AB Vote", ab_bs_pred, f"{ab_bs_conf:.1f}%")
                
                # Show example numbers
                st.info(f"💡 Example {bs_pred} numbers: **{', '.join(map(str, bs_examples))}**")
                
            else:
                st.warning("⏳ Big/Small prediction not available")
        
        except Exception as e:
            st.warning(f"⏳ Could not fetch Big/Small prediction: {str(e)}")

        # -----------------------
        # Model Details
        # -----------------------
        st.divider()
        st.subheader("🤖 Model Predictions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            lstm_data = data.get("lstm", {})
            if isinstance(lstm_data, dict):
                lstm_num = lstm_data.get("number", "—")
                lstm_conf = lstm_data.get("confidence", 0)
                st.metric("LSTM", f"{lstm_num}", f"{lstm_conf:.1f}%")
            else:
                st.metric("LSTM", "—")
        
        with col2:
            rf_data = data.get("rf", {})
            if isinstance(rf_data, dict):
                rf_num = rf_data.get("number", "—")
                rf_conf = rf_data.get("confidence", 0)
                st.metric("Random Forest", f"{rf_num}", f"{rf_conf:.1f}%")
            else:
                st.metric("Random Forest", "—")
        
        with col3:
            gb_data = data.get("gb", {})
            if isinstance(gb_data, dict):
                gb_num = gb_data.get("number", "—")
                gb_conf = gb_data.get("confidence", 0)
                st.metric("Gradient Boost", f"{gb_num}", f"{gb_conf:.1f}%")
            else:
                st.metric("Gradient Boost", "—")
        
        with col4:
            ab_data = data.get("ab", {})
            if isinstance(ab_data, dict):
                ab_num = ab_data.get("number", "—")
                ab_conf = ab_data.get("confidence", 0)
                st.metric("AdaBoost", f"{ab_num}", f"{ab_conf:.1f}%")
            else:
                st.metric("AdaBoost", "—")

    else:
        st.error("❌ API returned an error")

except Exception as e:
    st.warning("⏳ Waiting for API to be ready...")
    st.text(str(e))

# -----------------------
# Alternative Strategy: Frequency Betting
# -----------------------
st.divider()
st.subheader("📊 Alternative Strategy: Frequency Betting")

try:
    freq_res = requests.get(f"{api_url}/frequency-bet", timeout=timeout)
    
    if freq_res.status_code == 200:
        freq_data = freq_res.json()
        
        freq_number = freq_data.get("prediction")
        freq_color = freq_data.get("color")
        freq_size = freq_data.get("size")
        freq_confidence = freq_data.get("confidence", 0)
        freq_rationale = freq_data.get("rationale", "")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🎯 Prediction", freq_number)
        
        with col2:
            st.metric("📈 Confidence", f"{freq_confidence}%")
        
        with col3:
            st.metric("🎨 Color", freq_color)
        
        st.info(f"💡 {freq_rationale}")
        
        # Detailed frequency analysis
        with st.expander("📉 Detailed Frequency Analysis"):
            freq_analysis = freq_data.get("frequency_analysis", {})
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Most Frequent",
                    freq_analysis.get("most_frequent", "—"),
                    f"({freq_analysis.get('last_100_draws', {}).get(str(freq_analysis.get('most_frequent', 0)), 0)} times)"
                )
            
            with col2:
                st.metric(
                    "Least Frequent",
                    freq_analysis.get("least_frequent", "—"),
                    f"({freq_analysis.get('last_100_draws', {}).get(str(freq_analysis.get('least_frequent', 0)), 0)} times)"
                )
            
            with col3:
                st.metric(
                    "Avg Frequency",
                    f"{freq_analysis.get('average_frequency', 0):.1f}",
                    f"(Std: {freq_analysis.get('std_deviation', 0):.2f})"
                )
            
            # Show top 3 "due" numbers
            top_3 = freq_data.get("top_3_due", [])
            st.write("**Top 3 'Due' Numbers (Most Overdue):**")
            st.write(f"1. **{top_3[0] if len(top_3) > 0 else '—'}** (Primary prediction)")
            st.write(f"2. **{top_3[1] if len(top_3) > 1 else '—'}** (Backup option)")
            st.write(f"3. **{top_3[2] if len(top_3) > 2 else '—'}** (Third option)")
    else:
        st.error(f"❌ Frequency betting API error: {freq_res.status_code}")
    
except Exception as e:
    st.error(f"❌ Frequency betting error: {str(e)}")

# -----------------------
# Feedback & Statistics Panel
# -----------------------
try:
    st.divider()
    st.subheader("📈 Prediction Statistics & Feedback")
    
    stats_res = requests.get(f"{api_url}/stats", timeout=timeout)
    
    if stats_res.status_code == 200:
        stats = stats_res.json()
        
        # Display accuracy metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            recent_acc = stats.get("recent_accuracy", 0)
            st.metric(
                "📊 Recent Accuracy",
                f"{recent_acc:.1f}%",
                delta=f"(Last 50 predictions)"
            )
        
        with col2:
            all_acc = stats.get("all_time_accuracy", 0)
            st.metric(
                "🎯 All-Time Accuracy",
                f"{all_acc:.1f}%",
                delta=f"({stats.get('total_predictions', 0)} total)"
            )
        
        with col3:
            correct = stats.get("correct_predictions", 0)
            st.metric(
                "✅ Correct Predictions",
                correct,
                delta=f"out of {stats.get('total_predictions', 0)}"
            )
        
        with col4:
            recent_preds = stats.get("recent_predictions", 0)
            st.metric(
                "📝 Recent Predictions",
                recent_preds,
                delta="Last 50 recorded"
            )
        
        # Progress bar for accuracy
        st.progress(min(stats.get("all_time_accuracy", 0) / 100, 1.0))
        
        # Feedback submission form
        st.divider()
        st.subheader("💬 Submit Feedback")
        
        col_pred, col_actual, col_btn = st.columns([2, 2, 1])
        
        with col_pred:
            predicted = st.number_input(
                "Predicted Number",
                min_value=0,
                max_value=9,
                step=1,
                key="pred_num",
                help="What number did the AI predict?"
            )
        
        with col_actual:
            actual = st.number_input(
                "Actual Number",
                min_value=0,
                max_value=9,
                step=1,
                key="actual_num",
                help="What was the actual lottery result?"
            )
        
        with col_btn:
            st.write("")  # Spacing
            if st.button("📤 Submit", use_container_width=True):
                try:
                    feedback_res = requests.post(
                        f"{api_url}/feedback",
                        json={
                            "predicted_number": int(predicted),
                            "actual_number": int(actual)
                        },
                        timeout=timeout
                    )
                    
                    if feedback_res.status_code == 200:
                        fb_data = feedback_res.json()
                        is_correct = predicted == actual
                        
                        # Store in session state
                        st.session_state.feedback_submitted = True
                        st.session_state.feedback_type = "success" if is_correct else "warning"
                        st.session_state.feedback_message = (
                            f"{'✅ CORRECT!' if is_correct else '❌ INCORRECT'} | "
                            f"Recent Accuracy: {fb_data.get('recent_accuracy', 0):.1f}% | "
                            f"Total Feedback: {fb_data.get('total_feedback', 0)}"
                        )
                    else:
                        st.session_state.feedback_submitted = True
                        st.session_state.feedback_type = "error"
                        st.session_state.feedback_message = "Failed to submit feedback"
                
                except Exception as e:
                    st.session_state.feedback_submitted = True
                    st.session_state.feedback_type = "error"
                    st.session_state.feedback_message = f"Error: {str(e)}"
        
        # Display feedback message if submitted
        if st.session_state.feedback_submitted:
            if st.session_state.feedback_type == "success":
                st.success(st.session_state.feedback_message)
            elif st.session_state.feedback_type == "warning":
                st.warning(st.session_state.feedback_message)
            else:
                st.error(st.session_state.feedback_message)
            
            # Clear message after showing
            st.session_state.feedback_submitted = False
    
    else:
        st.warning("⏳ Statistics not available yet")

except Exception as e:
    st.warning(f"⏳ Statistics panel loading... {str(e)}")

# -----------------------
# Auto Refresh (Every 5 seconds)
# -----------------------
time.sleep(5)
st.rerun()