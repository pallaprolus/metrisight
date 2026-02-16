# MetriSight

A lightweight, self-hosted metric anomaly dashboard for developers. Detects anomalies in time-series metrics using statistical methods — no ML expertise or expensive APM tools required.

## Features

- **Prometheus live streaming** — connect to any Prometheus instance, auto-refresh on a configurable interval
- **Real-time anomaly detection** using Z-score and Moving Average methods
- **Interactive dashboard** with Plotly charts and Streamlit
- **CSV upload** — bring your own metric data from any source
- **Simulated metrics** (CPU, Memory, Latency) with injected anomalies for demo
- **Configurable thresholds** via sidebar controls

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`. By default it runs with simulated metrics — switch to **Prometheus (Live)** or **Upload CSV** in the sidebar.

## Connecting to Prometheus (Live Streaming)

MetriSight connects directly to your Prometheus instance and streams metrics with configurable auto-refresh.

### Setup

1. Select **Prometheus (Live)** in the sidebar
2. Enter your Prometheus URL (e.g., `http://localhost:9090`)
3. Enter a PromQL query (e.g., `rate(node_cpu_seconds_total{mode="idle"}[5m])`)
4. Choose a lookback window (1h, 6h, 24h, or 7 days)
5. Set auto-refresh interval (15s, 30s, 1m, or 5m) for live monitoring
6. Click **Test Connection** to verify connectivity

### Example PromQL queries

```promql
# CPU usage rate
rate(node_cpu_seconds_total{mode="idle"}[5m])

# Memory usage percentage
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100

# HTTP request latency (p95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# HTTP error rate
rate(http_requests_total{status=~"5.."}[5m])

# Disk I/O utilization
rate(node_disk_io_time_seconds_total[5m])
```

### Authentication

MetriSight supports authenticated Prometheus instances. Select the auth method in the sidebar under the Prometheus section.

| Method | When to use | Setup |
|--------|-------------|-------|
| **None** | Local/internal Prometheus without auth | Default, no config needed |
| **Bearer Token** | Grafana Cloud, Thanos, Cortex, managed Prometheus | Paste your API token |
| **Basic Auth** | Prometheus behind nginx/Apache reverse proxy | Enter username + password |

Credentials are passed via HTTP headers only — they are **never logged, stored on disk, or displayed** in the UI (password fields are masked).

**Grafana Cloud example:**

1. Get your API token from Grafana Cloud > your stack > Prometheus > Details
2. Set Prometheus URL to your Grafana Cloud Prometheus endpoint (e.g., `https://prometheus-prod-01-eu-west-0.grafana.net/api/prom`)
3. Select **Bearer Token** and paste your API key
4. Click **Test Connection** to verify — you'll see the Prometheus version if auth succeeds, or a `401 Unauthorized` error if the token is wrong

### How it works

- MetriSight queries the Prometheus `/api/v1/query_range` endpoint
- The lookback window determines how far back to fetch (rolling window)
- Auto-refresh re-queries Prometheus on the set interval, so the chart updates with live data
- Anomaly detection runs on each refresh against the full lookback window

### Lookback window guide

| Window | Best for | Typical resolution |
|--------|----------|-------------------|
| 1 hour | Real-time incident triage | 15s |
| 6 hours | Shift monitoring | 30s - 1m |
| 24 hours | Daily pattern analysis | 1m |
| 7 days | Weekly trend detection | 5m |

## Other Data Sources

### CSV Upload

Upload a CSV file with two columns:

```csv
timestamp,value
2024-01-15 10:00:00,45.2
2024-01-15 10:01:00,47.8
2024-01-15 10:02:00,44.1
```

### Exporting from other tools

**CloudWatch:**

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 --metric-name CPUUtilization \
  --start-time 2024-01-15T00:00:00Z --end-time 2024-01-15T23:59:59Z \
  --period 60 --statistics Average --output json \
  | python3 -c "
import json, sys, csv
data = json.load(sys.stdin)['Datapoints']
data.sort(key=lambda x: x['Timestamp'])
w = csv.writer(sys.stdout)
w.writerow(['timestamp', 'value'])
for d in data:
    w.writerow([d['Timestamp'], d['Average']])
" > cloudwatch_cpu.csv
```

**Datadog:**

```bash
curl -s "https://api.datadoghq.com/api/v1/query?from=$(date -d '24 hours ago' +%s)&to=$(date +%s)&query=avg:system.cpu.user{*}" \
  -H "DD-API-KEY: $DD_API_KEY" -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
  | python3 -c "
import json, sys, csv
from datetime import datetime
data = json.load(sys.stdin)['series'][0]['pointlist']
w = csv.writer(sys.stdout)
w.writerow(['timestamp', 'value'])
for ts_ms, val in data:
    w.writerow([datetime.fromtimestamp(ts_ms / 1000).isoformat(), val])
" > datadog_cpu.csv
```

### Programmatic Usage

```python
import pandas as pd
from metrisight.detector import detect_zscore, get_anomaly_summary

df = pd.read_csv("my_metrics.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])

result = detect_zscore(df, threshold=3.0)
summary = get_anomaly_summary(result)
print(f"Found {summary['anomaly_count']} anomalies ({summary['anomaly_pct']}%)")
```

## How It Works

MetriSight uses two statistical methods to detect anomalies:

1. **Z-Score Detection** — flags data points that deviate more than N standard deviations from the mean
2. **Moving Average Detection** — flags data points that deviate from a rolling mean by more than N rolling standard deviations

## Project Structure

```
metrisight/
├── app.py                  # Streamlit dashboard
├── metrisight/
│   ├── simulator.py        # Generates realistic fake metrics
│   ├── detector.py         # Anomaly detection algorithms
│   ├── prometheus.py       # Prometheus HTTP API client
│   └── charts.py           # Plotly chart builders
└── tests/
    ├── test_detector.py    # Detection algorithm tests
    └── test_prometheus.py  # Prometheus client tests
```

## License

MIT
