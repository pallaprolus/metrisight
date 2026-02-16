"""MetriSight - Lightweight metric anomaly detection dashboard."""

__version__ = "0.1.0"

from metrisight.detector import detect_zscore, detect_moving_avg, get_anomaly_summary
from metrisight.simulator import generate_metrics
from metrisight.charts import plot_metric_with_anomalies
from metrisight.prometheus import query_prometheus, check_connection, PrometheusError

__all__ = [
    "__version__",
    "detect_zscore",
    "detect_moving_avg",
    "get_anomaly_summary",
    "generate_metrics",
    "plot_metric_with_anomalies",
    "query_prometheus",
    "check_connection",
    "PrometheusError",
]
