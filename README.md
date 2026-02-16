# MetriSight

A lightweight, self-hosted metric anomaly dashboard for developers. Detects anomalies in time-series metrics using statistical methods — no ML expertise or expensive APM tools required.

## Features

- **Real-time anomaly detection** using Z-score and Moving Average methods
- **Interactive dashboard** with Plotly charts and Streamlit
- **CSV upload** — bring your own metric data from any source
- **Simulated metrics** (CPU, Memory, Latency) with injected anomalies for demo
- **Configurable thresholds** via sidebar controls
- **Zero external dependencies** — no Prometheus, no cloud services needed to get started

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`. By default it runs with simulated metrics — switch to **Upload CSV** in the sidebar to use your own data.

## Connecting Real Data

### Option 1: CSV Upload (Built-in)

The dashboard supports direct CSV upload. Your CSV needs two columns:

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | datetime | e.g., `2024-01-15 10:30:00` |
| `value` | numeric | The metric value |

**Example CSV:**

```csv
timestamp,value
2024-01-15 10:00:00,45.2
2024-01-15 10:01:00,47.8
2024-01-15 10:02:00,44.1
2024-01-15 10:03:00,92.5
2024-01-15 10:04:00,46.0
```

### Option 2: Export from Prometheus

Query Prometheus and export to CSV, then upload:

```bash
# Using promtool
promtool query range \
  --start="2024-01-15T00:00:00Z" \
  --end="2024-01-15T23:59:59Z" \
  --step=60s \
  'node_cpu_seconds_total{mode="idle"}' \
  | jq -r '["timestamp","value"], (.[] | [.timestamp, .value]) | @csv' \
  > cpu_metrics.csv
```

Or use the Prometheus HTTP API:

```bash
curl -s 'http://localhost:9090/api/v1/query_range?query=node_cpu_seconds_total&start=2024-01-15T00:00:00Z&end=2024-01-15T23:59:59Z&step=60s' \
  | python3 -c "
import json, sys, csv
data = json.load(sys.stdin)['data']['result'][0]['values']
w = csv.writer(sys.stdout)
w.writerow(['timestamp', 'value'])
for ts, val in data:
    from datetime import datetime
    w.writerow([datetime.fromtimestamp(ts).isoformat(), val])
" > metrics.csv
```

### Option 3: Export from CloudWatch

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --start-time 2024-01-15T00:00:00Z \
  --end-time 2024-01-15T23:59:59Z \
  --period 60 \
  --statistics Average \
  --output json \
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

### Option 4: Export from Datadog

```bash
curl -s "https://api.datadoghq.com/api/v1/query?from=$(date -d '24 hours ago' +%s)&to=$(date +%s)&query=avg:system.cpu.user{*}" \
  -H "DD-API-KEY: $DD_API_KEY" \
  -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
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

### Option 5: Use the Detector Programmatically

You can use the detection module directly in your own scripts:

```python
import pandas as pd
from metrisight.detector import detect_zscore, detect_moving_avg, get_anomaly_summary

# Load your data (from any source)
df = pd.read_csv("my_metrics.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Run anomaly detection
result = detect_zscore(df, threshold=3.0)
# or: result = detect_moving_avg(df, window=20, threshold=2.0)

# Get summary
summary = get_anomaly_summary(result)
print(f"Found {summary['anomaly_count']} anomalies ({summary['anomaly_pct']}%)")

# Get anomalous data points
anomalies = result[result["is_anomaly"]]
print(anomalies[["timestamp", "value"]])
```

## Data Format Reference

MetriSight expects a pandas DataFrame with at minimum:

| Column | Required | Type | Notes |
|--------|----------|------|-------|
| `timestamp` | Yes | `datetime64` | Any parseable datetime format |
| `value` | Yes | `float64` | The metric value to analyze |

The detection functions add these columns to the output:

| Column | Added by | Description |
|--------|----------|-------------|
| `is_anomaly` | Both methods | `True` if the point is anomalous |
| `upper_bound` | Both methods | Upper threshold boundary |
| `lower_bound` | Both methods | Lower threshold boundary |
| `z_score` | Z-Score only | Standard deviations from mean |
| `rolling_mean` | Moving Avg only | Rolling window mean |
| `rolling_std` | Moving Avg only | Rolling window std deviation |

## How It Works

MetriSight uses two statistical methods to detect anomalies:

1. **Z-Score Detection** — flags data points that deviate more than N standard deviations from the mean
2. **Moving Average Detection** — flags data points that deviate from a rolling mean by more than N rolling standard deviations

## Project Structure

```
metrisight/
├── app.py                  # Streamlit dashboard (simulated + CSV upload)
├── metrisight/
│   ├── simulator.py        # Generates realistic fake metrics
│   ├── detector.py         # Anomaly detection algorithms
│   └── charts.py           # Plotly chart builders
└── tests/
    └── test_detector.py    # Unit tests
```

## License

MIT
