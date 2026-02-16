"""Prometheus HTTP API client for querying time-series metrics."""

from datetime import datetime, timedelta

import pandas as pd
import requests


def query_prometheus(
    url: str,
    query: str,
    lookback_hours: float = 24,
    step_seconds: int = 60,
    timeout: int = 30,
) -> pd.DataFrame:
    """Query Prometheus range API and return a DataFrame.

    Args:
        url: Prometheus base URL (e.g., http://localhost:9090).
        query: PromQL query string.
        lookback_hours: How many hours of data to fetch.
        step_seconds: Resolution step in seconds.
        timeout: HTTP request timeout in seconds.

    Returns:
        DataFrame with columns: timestamp, value

    Raises:
        PrometheusError: If the query fails or returns unexpected data.
    """
    url = url.rstrip("/")
    end = datetime.utcnow()
    start = end - timedelta(hours=lookback_hours)

    params = {
        "query": query,
        "start": start.isoformat() + "Z",
        "end": end.isoformat() + "Z",
        "step": f"{step_seconds}s",
    }

    try:
        resp = requests.get(f"{url}/api/v1/query_range", params=params, timeout=timeout)
    except requests.ConnectionError:
        raise PrometheusError(f"Cannot connect to Prometheus at {url}")
    except requests.Timeout:
        raise PrometheusError(f"Prometheus query timed out after {timeout}s")

    if resp.status_code != 200:
        raise PrometheusError(f"Prometheus returned HTTP {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    if data.get("status") != "success":
        error_msg = data.get("error", "Unknown error")
        raise PrometheusError(f"Prometheus query failed: {error_msg}")

    results = data.get("data", {}).get("result", [])
    if not results:
        return pd.DataFrame(columns=["timestamp", "value"])

    # Use the first result series
    values = results[0].get("values", [])
    if not values:
        return pd.DataFrame(columns=["timestamp", "value"])

    rows = []
    for ts, val in values:
        rows.append({
            "timestamp": datetime.utcfromtimestamp(float(ts)),
            "value": float(val),
        })

    return pd.DataFrame(rows)


def check_connection(url: str, timeout: int = 5) -> tuple[bool, str]:
    """Check if a Prometheus instance is reachable.

    Args:
        url: Prometheus base URL.
        timeout: HTTP timeout in seconds.

    Returns:
        Tuple of (is_connected, message).
    """
    url = url.rstrip("/")
    try:
        resp = requests.get(f"{url}/api/v1/status/buildinfo", timeout=timeout)
        if resp.status_code == 200:
            version = resp.json().get("data", {}).get("version", "unknown")
            return True, f"Connected to Prometheus v{version}"
        return False, f"Unexpected status code: {resp.status_code}"
    except requests.ConnectionError:
        return False, f"Cannot connect to {url}"
    except requests.Timeout:
        return False, f"Connection timed out"
    except Exception as e:
        return False, str(e)


class PrometheusError(Exception):
    """Raised when a Prometheus query fails."""
