"""MetriSight - Lightweight Metric Anomaly Dashboard."""

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from metrisight.simulator import generate_metrics
from metrisight.detector import detect_zscore, detect_moving_avg, get_anomaly_summary
from metrisight.charts import plot_metric_with_anomalies
from metrisight.prometheus import query_prometheus, check_connection, PrometheusError

st.set_page_config(page_title="MetriSight", page_icon="📊", layout="wide")

st.title("📊 MetriSight")
st.caption("Lightweight metric anomaly detection dashboard")

# --- Sidebar controls ---
with st.sidebar:
    st.header("Configuration")

    data_source = st.radio(
        "Data Source",
        ["simulated", "prometheus", "csv_upload"],
        format_func=lambda x: {
            "simulated": "Simulated Metrics",
            "prometheus": "Prometheus (Live)",
            "csv_upload": "Upload CSV",
        }[x],
    )

    st.divider()

    # Reset Prometheus connection when switching away
    if data_source != "prometheus":
        st.session_state.pop("prom_connected", None)

    if data_source == "simulated":
        metric = st.selectbox("Metric", ["cpu", "memory", "latency"], format_func=lambda x: {
            "cpu": "CPU Usage (%)",
            "memory": "Memory Usage (%)",
            "latency": "Response Latency (ms)",
        }[x])
    elif data_source == "prometheus":
        metric = "prometheus"
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

    if data_source == "prometheus":
        st.divider()
        st.subheader("Prometheus")

        prom_url = st.text_input(
            "Prometheus URL",
            value="http://localhost:9090",
            help="Base URL of your Prometheus instance",
        )

        prom_query = st.text_input(
            "PromQL Query",
            value='rate(node_cpu_seconds_total{mode="idle"}[5m])',
            help="PromQL query that returns a single time series",
        )

        lookback = st.selectbox(
            "Lookback Window",
            [1, 6, 24, 168],
            index=2,
            format_func=lambda x: {1: "1 hour", 6: "6 hours", 24: "24 hours", 168: "7 days"}[x],
        )

        step = st.selectbox(
            "Resolution",
            [15, 30, 60, 300],
            index=2,
            format_func=lambda x: {15: "15s", 30: "30s", 60: "1m", 300: "5m"}[x],
        )

        refresh_interval = st.selectbox(
            "Auto-Refresh",
            [0, 15, 30, 60, 300],
            index=0,
            format_func=lambda x: {
                0: "Off",
                15: "Every 15s",
                30: "Every 30s",
                60: "Every 1m",
                300: "Every 5m",
            }[x],
        )

        # --- Authentication ---
        st.divider()
        auth_method = st.radio(
            "Authentication",
            ["none", "bearer", "basic"],
            format_func=lambda x: {
                "none": "None (no auth)",
                "bearer": "Bearer Token",
                "basic": "Basic Auth",
            }[x],
            help="Most local setups need no auth. Grafana Cloud and managed Prometheus use Bearer Token.",
        )

        prom_bearer_token = None
        prom_basic_auth = None

        if auth_method == "bearer":
            prom_bearer_token = st.text_input(
                "Bearer Token",
                type="password",
                help="API token (e.g., from Grafana Cloud, Thanos, or Cortex)",
            )
        elif auth_method == "basic":
            prom_basic_user = st.text_input("Username")
            prom_basic_pass = st.text_input("Password", type="password")
            if prom_basic_user and prom_basic_pass:
                prom_basic_auth = (prom_basic_user, prom_basic_pass)

        st.divider()

        # Connection test button
        if st.button("🔌 Test Connection", use_container_width=True):
            with st.spinner("Connecting..."):
                ok, msg = check_connection(
                    prom_url,
                    bearer_token=prom_bearer_token,
                    basic_auth=prom_basic_auth,
                )
            if ok:
                st.success(msg)
            else:
                st.error(msg)

        # Connect & start querying
        if st.button("▶ Connect & Query", use_container_width=True, type="primary"):
            st.session_state["prom_connected"] = True

# --- Auto-refresh for Prometheus streaming ---
if data_source == "prometheus" and st.session_state.get("prom_connected") and refresh_interval > 0:
    st_autorefresh(interval=refresh_interval * 1000, key="prom_refresh")

# --- Load data ---
raw_df = None
duration_label = ""

if data_source == "prometheus":
    if not st.session_state.get("prom_connected"):
        st.info(
            "Configure your Prometheus connection in the sidebar, then click **Connect & Query** to start."
        )
        st.stop()

    if not prom_url or not prom_query:
        st.info("Enter a Prometheus URL and PromQL query in the sidebar.")
        st.stop()

    try:
        with st.spinner("Querying Prometheus..."):
            raw_df = query_prometheus(
                url=prom_url,
                query=prom_query,
                lookback_hours=lookback,
                step_seconds=step,
                bearer_token=prom_bearer_token,
                basic_auth=prom_basic_auth,
            )
        if len(raw_df) == 0:
            st.warning("Prometheus returned no data for this query. Check your PromQL expression.")
            st.stop()
        duration_label = {1: "1h", 6: "6h", 24: "24h", 168: "7d"}[lookback]
    except PrometheusError as e:
        st.error(f"Prometheus error: {e}")
        st.stop()

elif data_source == "csv_upload":
    st.subheader("Upload Your Metric Data")
    st.markdown("""
    Upload a CSV file with your time-series metric data. Required columns:
    - **`timestamp`** — datetime (e.g., `2024-01-15 10:30:00`)
    - **`value`** — numeric metric value
    """)
    st.code("timestamp,value\n2024-01-15 10:00:00,45.2\n2024-01-15 10:01:00,47.8\n2024-01-15 10:02:00,44.1", language="csv")

    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded_file is not None:
        try:
            raw_df = pd.read_csv(uploaded_file)
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
    duration_label = f"{duration}h"

if raw_df is None or len(raw_df) == 0:
    st.info("Upload a CSV file to get started, or switch to another data source in the sidebar.")
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
if duration_label:
    col4.metric("Time Range", duration_label)
else:
    time_span = summary["time_range_end"] - summary["time_range_start"]
    col4.metric("Time Range", str(time_span).split(".")[0])

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
