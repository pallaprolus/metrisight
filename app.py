"""MetriSight - Lightweight Metric Anomaly Dashboard."""

import pandas as pd
import streamlit as st

from metrisight.simulator import generate_metrics
from metrisight.detector import detect_zscore, detect_moving_avg, get_anomaly_summary
from metrisight.charts import plot_metric_with_anomalies

st.set_page_config(page_title="MetriSight", page_icon="📊", layout="wide")

st.title("📊 MetriSight")
st.caption("Lightweight metric anomaly detection dashboard")

# --- Sidebar controls ---
with st.sidebar:
    st.header("Configuration")

    data_source = st.radio("Data Source", ["simulated", "csv_upload"], format_func=lambda x: {
        "simulated": "Simulated Metrics",
        "csv_upload": "Upload CSV",
    }[x])

    st.divider()

    if data_source == "simulated":
        metric = st.selectbox("Metric", ["cpu", "memory", "latency"], format_func=lambda x: {
            "cpu": "CPU Usage (%)",
            "memory": "Memory Usage (%)",
            "latency": "Response Latency (ms)",
        }[x])
    else:
        metric = "custom"

    method = st.radio("Detection Method", ["zscore", "moving_avg"], format_func=lambda x: {
        "zscore": "Z-Score",
        "moving_avg": "Moving Average",
    }[x])

    st.divider()

    if method == "zscore":
        threshold = st.slider("Z-Score Threshold", 1.0, 5.0, 3.0, 0.1,
                              help="Flag points more than N std devs from mean")
    else:
        window = st.slider("Rolling Window", 5, 100, 20, 5,
                           help="Number of points for the rolling window")
        threshold = st.slider("Threshold Multiplier", 1.0, 5.0, 2.0, 0.1,
                              help="Multiplier for rolling std to set bounds")

    if data_source == "simulated":
        st.divider()

        duration = st.selectbox("Time Range", [6, 12, 24, 48], index=2,
                                format_func=lambda x: f"{x} hours")

        seed = st.number_input("Random Seed", min_value=0, max_value=9999, value=42,
                               help="Set seed for reproducible data")

        regenerate = st.button("🔄 Regenerate Data", use_container_width=True)

# --- Load data ---
raw_df = None

if data_source == "csv_upload":
    st.subheader("Upload Your Metric Data")
    st.markdown("""
    Upload a CSV file with your time-series metric data. Required columns:
    - **`timestamp`** — datetime (e.g., `2024-01-15 10:30:00`)
    - **`value`** — numeric metric value

    [Download sample CSV](https://gist.githubusercontent.com/) or use the format below:
    """)
    st.code("timestamp,value\n2024-01-15 10:00:00,45.2\n2024-01-15 10:01:00,47.8\n2024-01-15 10:02:00,44.1", language="csv")

    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded_file is not None:
        try:
            raw_df = pd.read_csv(uploaded_file)
            # Validate required columns
            if "timestamp" not in raw_df.columns or "value" not in raw_df.columns:
                st.error("CSV must have `timestamp` and `value` columns. Found: " + ", ".join(raw_df.columns))
                raw_df = None
            else:
                raw_df["timestamp"] = pd.to_datetime(raw_df["timestamp"])
                raw_df["value"] = pd.to_numeric(raw_df["value"], errors="coerce")
                raw_df = raw_df.dropna(subset=["timestamp", "value"])
                st.success(f"Loaded {len(raw_df):,} data points from `{uploaded_file.name}`")
        except Exception as e:
            st.error(f"Failed to parse CSV: {e}")
            raw_df = None
else:
    cache_key = f"{metric}_{duration}_{seed}"
    if regenerate or cache_key not in st.session_state:
        st.session_state[cache_key] = generate_metrics(
            metric_name=metric, duration_hours=duration, seed=seed
        )
    raw_df = st.session_state[cache_key]

if raw_df is None or len(raw_df) == 0:
    st.info("Upload a CSV file to get started, or switch to Simulated Metrics in the sidebar.")
    st.stop()

if method == "zscore":
    df = detect_zscore(raw_df, threshold=threshold)
else:
    df = detect_moving_avg(raw_df, window=window, threshold=threshold)

# --- Summary metrics ---
summary = get_anomaly_summary(df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Data Points", f"{summary['total_points']:,}")
col2.metric("Anomalies Detected", summary["anomaly_count"])
col3.metric("Anomaly Rate", f"{summary['anomaly_pct']}%")
col4.metric("Time Range", f"{duration}h")

# --- Chart ---
fig = plot_metric_with_anomalies(df, metric_name=metric, detection_method=method)
st.plotly_chart(fig, use_container_width=True)

# --- Anomaly table ---
with st.expander(f"View Anomalous Data Points ({summary['anomaly_count']})"):
    anomaly_df = df[df["is_anomaly"]][["timestamp", "value"]].reset_index(drop=True)
    if len(anomaly_df) > 0:
        st.dataframe(anomaly_df, use_container_width=True)
    else:
        st.info("No anomalies detected with current settings. Try lowering the threshold.")
