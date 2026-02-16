"""Anomaly detection algorithms for time-series metrics."""

import numpy as np
import pandas as pd


def detect_zscore(df: pd.DataFrame, threshold: float = 3.0) -> pd.DataFrame:
    """Detect anomalies using Z-score method.

    Flags data points whose Z-score (standard deviations from the mean)
    exceeds the given threshold.

    Args:
        df: DataFrame with a 'value' column.
        threshold: Number of standard deviations to flag as anomalous.

    Returns:
        DataFrame with added columns: z_score, is_anomaly, upper_bound, lower_bound
    """
    result = df.copy()
    mean = result["value"].mean()
    std = result["value"].std()

    if std == 0:
        result["z_score"] = 0.0
        result["is_anomaly"] = False
        result["upper_bound"] = mean
        result["lower_bound"] = mean
        return result

    result["z_score"] = (result["value"] - mean) / std
    result["is_anomaly"] = result["z_score"].abs() > threshold
    result["upper_bound"] = mean + threshold * std
    result["lower_bound"] = mean - threshold * std
    return result


def detect_moving_avg(
    df: pd.DataFrame, window: int = 20, threshold: float = 2.0
) -> pd.DataFrame:
    """Detect anomalies using moving average method.

    Flags data points that deviate from the rolling mean by more than
    threshold * rolling standard deviation.

    Args:
        df: DataFrame with a 'value' column.
        window: Rolling window size.
        threshold: Multiplier for rolling std to set bounds.

    Returns:
        DataFrame with added columns: rolling_mean, rolling_std, is_anomaly,
        upper_bound, lower_bound
    """
    result = df.copy()
    result["rolling_mean"] = result["value"].rolling(window=window, center=True).mean()
    result["rolling_std"] = result["value"].rolling(window=window, center=True).std()

    # Fill NaN edges with global stats
    global_mean = result["value"].mean()
    global_std = result["value"].std()
    result["rolling_mean"] = result["rolling_mean"].fillna(global_mean)
    result["rolling_std"] = result["rolling_std"].fillna(global_std)

    # Handle zero std
    result["rolling_std"] = result["rolling_std"].replace(0, global_std if global_std > 0 else 1.0)

    result["upper_bound"] = result["rolling_mean"] + threshold * result["rolling_std"]
    result["lower_bound"] = result["rolling_mean"] - threshold * result["rolling_std"]
    result["is_anomaly"] = (result["value"] > result["upper_bound"]) | (
        result["value"] < result["lower_bound"]
    )
    return result


def get_anomaly_summary(df: pd.DataFrame) -> dict:
    """Compute summary statistics for detected anomalies.

    Args:
        df: DataFrame with 'is_anomaly' and 'timestamp' columns.

    Returns:
        Dict with total_points, anomaly_count, anomaly_pct, time_range.
    """
    total = len(df)
    anomaly_count = int(df["is_anomaly"].sum())
    return {
        "total_points": total,
        "anomaly_count": anomaly_count,
        "anomaly_pct": round(anomaly_count / total * 100, 2) if total > 0 else 0,
        "time_range_start": df["timestamp"].min(),
        "time_range_end": df["timestamp"].max(),
    }
