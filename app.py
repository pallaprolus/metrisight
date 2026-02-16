"""MetriSight - Lightweight Metric Anomaly Dashboard."""

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

    metric = st.selectbox("Metric", ["cpu", "memory", "latency"], format_func=lambda x: {
        "cpu": "CPU Usage (%)",
        "memory": "Memory Usage (%)",
        "latency": "Response Latency (ms)",
    }[x])

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

    st.divider()

    duration = st.selectbox("Time Range", [6, 12, 24, 48], index=2,
                            format_func=lambda x: f"{x} hours")

    seed = st.number_input("Random Seed", min_value=0, max_value=9999, value=42,
                           help="Set seed for reproducible data")

    regenerate = st.button("🔄 Regenerate Data", use_container_width=True)

# --- Generate and detect ---
cache_key = f"{metric}_{duration}_{seed}"
if regenerate or cache_key not in st.session_state:
    st.session_state[cache_key] = generate_metrics(
        metric_name=metric, duration_hours=duration, seed=seed
    )

raw_df = st.session_state[cache_key]

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
