"""Tests for anomaly detection algorithms."""

import numpy as np
import pandas as pd
import pytest

from metrisight.detector import detect_zscore, detect_moving_avg, get_anomaly_summary


def _make_df(values: list[float]) -> pd.DataFrame:
    """Helper to create a simple test DataFrame."""
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=len(values), freq="min"),
        "value": values,
    })


class TestZScoreDetection:
    def test_catches_obvious_spike(self):
        values = [10.0] * 100
        values[50] = 100.0  # huge spike
        df = detect_zscore(_make_df(values), threshold=3.0)
        assert df.loc[50, "is_anomaly"] is True or df.loc[50, "is_anomaly"] == True

    def test_no_anomalies_in_flat_data(self):
        values = [50.0] * 100
        df = detect_zscore(_make_df(values), threshold=3.0)
        assert df["is_anomaly"].sum() == 0

    def test_lower_threshold_catches_more(self):
        rng = np.random.default_rng(42)
        values = list(rng.normal(50, 5, 200))
        values[100] = 75.0  # moderate spike

        df_strict = detect_zscore(_make_df(values), threshold=4.0)
        df_loose = detect_zscore(_make_df(values), threshold=2.0)
        assert df_loose["is_anomaly"].sum() >= df_strict["is_anomaly"].sum()

    def test_adds_expected_columns(self):
        df = detect_zscore(_make_df([1.0, 2.0, 3.0]), threshold=3.0)
        assert "is_anomaly" in df.columns
        assert "z_score" in df.columns
        assert "upper_bound" in df.columns
        assert "lower_bound" in df.columns

    def test_bounds_are_symmetric(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        df = detect_zscore(_make_df(values), threshold=2.0)
        mean = np.mean(values)
        assert abs(df["upper_bound"].iloc[0] - mean) == pytest.approx(
            abs(df["lower_bound"].iloc[0] - mean)
        )


class TestMovingAvgDetection:
    def test_catches_obvious_spike(self):
        values = [10.0] * 100
        values[50] = 100.0
        df = detect_moving_avg(_make_df(values), window=10, threshold=2.0)
        assert df.loc[50, "is_anomaly"] is True or df.loc[50, "is_anomaly"] == True

    def test_no_anomalies_in_flat_data(self):
        values = [50.0] * 100
        df = detect_moving_avg(_make_df(values), window=10, threshold=2.0)
        assert df["is_anomaly"].sum() == 0

    def test_adds_expected_columns(self):
        df = detect_moving_avg(_make_df([1.0, 2.0, 3.0, 4.0, 5.0]), window=3, threshold=2.0)
        assert "is_anomaly" in df.columns
        assert "rolling_mean" in df.columns
        assert "upper_bound" in df.columns
        assert "lower_bound" in df.columns

    def test_window_size_affects_detection(self):
        rng = np.random.default_rng(42)
        values = list(rng.normal(50, 5, 200))
        values[100] = 90.0

        df_small = detect_moving_avg(_make_df(values), window=5, threshold=2.0)
        df_large = detect_moving_avg(_make_df(values), window=50, threshold=2.0)
        # Both should catch the spike but results may differ
        assert df_small.loc[100, "is_anomaly"] or df_large.loc[100, "is_anomaly"]


class TestAnomalySummary:
    def test_summary_counts(self):
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="min"),
            "value": [1, 2, 3, 4, 5],
            "is_anomaly": [False, True, False, True, False],
        })
        summary = get_anomaly_summary(df)
        assert summary["total_points"] == 5
        assert summary["anomaly_count"] == 2
        assert summary["anomaly_pct"] == 40.0

    def test_no_anomalies(self):
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="min"),
            "value": [1, 2, 3],
            "is_anomaly": [False, False, False],
        })
        summary = get_anomaly_summary(df)
        assert summary["anomaly_count"] == 0
        assert summary["anomaly_pct"] == 0
