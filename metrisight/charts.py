"""Plotly chart builders for metric visualization."""

import plotly.graph_objects as go
import pandas as pd


METRIC_UNITS = {
    "cpu": "%",
    "memory": "%",
    "latency": "ms",
    "prometheus": "",
    "custom": "",
}

METRIC_LABELS = {
    "cpu": "CPU Usage",
    "memory": "Memory Usage",
    "latency": "Response Latency",
    "prometheus": "Prometheus Metric",
    "custom": "Custom Metric",
}


def plot_metric_with_anomalies(
    df: pd.DataFrame,
    metric_name: str = "cpu",
    detection_method: str = "zscore",
) -> go.Figure:
    """Create an interactive Plotly chart with anomalies highlighted.

    Args:
        df: DataFrame with timestamp, value, is_anomaly, upper_bound, lower_bound.
        metric_name: Name of the metric for labels.
        detection_method: "zscore" or "moving_avg" for the title.

    Returns:
        Plotly Figure object.
    """
    label = METRIC_LABELS.get(metric_name, metric_name)
    unit = METRIC_UNITS.get(metric_name, "")
    method_label = "Z-Score" if detection_method == "zscore" else "Moving Average"

    fig = go.Figure()

    # Expected range band
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["upper_bound"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["lower_bound"],
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(100, 149, 237, 0.15)",
        name="Expected Range",
        hoverinfo="skip",
    ))

    # Normal values
    normal = df[~df["is_anomaly"]]
    fig.add_trace(go.Scatter(
        x=normal["timestamp"],
        y=normal["value"],
        mode="lines",
        name="Normal",
        line=dict(color="#3b82f6", width=1.5),
        hovertemplate=f"%{{y:.1f}} {unit}<extra>Normal</extra>",
    ))

    # Anomaly markers
    anomalies = df[df["is_anomaly"]]
    fig.add_trace(go.Scatter(
        x=anomalies["timestamp"],
        y=anomalies["value"],
        mode="markers",
        name=f"Anomaly ({len(anomalies)})",
        marker=dict(color="#ef4444", size=7, symbol="circle"),
        hovertemplate=f"%{{y:.1f}} {unit}<extra>Anomaly</extra>",
    ))

    fig.update_layout(
        title=f"{label} - Anomaly Detection ({method_label})",
        xaxis_title="Time",
        yaxis_title=f"{label} ({unit})",
        template="plotly_white",
        height=450,
        margin=dict(l=60, r=30, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    return fig
