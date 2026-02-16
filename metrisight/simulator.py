"""Simulates realistic time-series metrics with injected anomalies."""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def generate_metrics(
    metric_name: str = "cpu",
    duration_hours: int = 24,
    interval_seconds: int = 60,
    anomaly_ratio: float = 0.03,
    seed: int | None = None,
) -> pd.DataFrame:
    """Generate simulated metric data with injected anomalies.

    Args:
        metric_name: One of "cpu", "memory", "latency".
        duration_hours: How many hours of data to generate.
        interval_seconds: Seconds between data points.
        anomaly_ratio: Fraction of points to make anomalous.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with columns: timestamp, value, is_injected_anomaly
    """
    rng = np.random.default_rng(seed)
    n_points = int(duration_hours * 3600 / interval_seconds)
    timestamps = [
        datetime.now() - timedelta(hours=duration_hours) + timedelta(seconds=i * interval_seconds)
        for i in range(n_points)
    ]
    t = np.arange(n_points)

    if metric_name == "cpu":
        values = _generate_cpu(t, n_points, rng)
    elif metric_name == "memory":
        values = _generate_memory(t, n_points, rng)
    elif metric_name == "latency":
        values = _generate_latency(t, n_points, rng)
    else:
        raise ValueError(f"Unknown metric: {metric_name}. Use 'cpu', 'memory', or 'latency'.")

    # Inject anomalies
    is_anomaly = np.zeros(n_points, dtype=bool)
    n_anomalies = max(1, int(n_points * anomaly_ratio))
    anomaly_indices = rng.choice(n_points, size=n_anomalies, replace=False)

    for idx in anomaly_indices:
        anomaly_type = rng.choice(["spike", "dip", "shift"])
        if anomaly_type == "spike":
            values[idx] += rng.uniform(3, 6) * np.std(values)
        elif anomaly_type == "dip":
            values[idx] -= rng.uniform(3, 5) * np.std(values)
        elif anomaly_type == "shift":
            shift_len = min(rng.integers(5, 15), n_points - idx)
            values[idx : idx + shift_len] += rng.uniform(2, 4) * np.std(values)
            is_anomaly[idx : idx + shift_len] = True
        is_anomaly[idx] = True

    # Clamp values to reasonable ranges
    if metric_name == "cpu":
        values = np.clip(values, 0, 100)
    elif metric_name == "memory":
        values = np.clip(values, 0, 100)
    elif metric_name == "latency":
        values = np.clip(values, 0, None)

    return pd.DataFrame({
        "timestamp": timestamps,
        "value": values,
        "is_injected_anomaly": is_anomaly,
    })


def _generate_cpu(t: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """CPU: sinusoidal daily pattern + noise, baseline ~40-60%."""
    base = 50 + 15 * np.sin(2 * np.pi * t / n)  # daily cycle
    noise = rng.normal(0, 3, n)
    return base + noise


def _generate_memory(t: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """Memory: gradual climb with periodic drops (GC), baseline ~50-75%."""
    base = 50 + 20 * (t / n)  # gradual climb
    # simulate GC drops
    gc_drops = np.zeros(n)
    for gc_point in rng.choice(n, size=max(1, n // 200), replace=False):
        drop_len = min(rng.integers(3, 10), n - gc_point)
        gc_drops[gc_point : gc_point + drop_len] = -rng.uniform(5, 15)
    noise = rng.normal(0, 2, n)
    return base + gc_drops + noise


def _generate_latency(t: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """Latency: low baseline with occasional spikes, baseline ~20-50ms."""
    base = 30 + 5 * np.sin(2 * np.pi * t / n)
    # occasional micro-spikes (normal traffic bursts)
    spikes = np.zeros(n)
    for spike_point in rng.choice(n, size=max(1, n // 50), replace=False):
        spikes[spike_point] = rng.uniform(10, 30)
    noise = rng.normal(0, 3, n)
    return base + spikes + noise
