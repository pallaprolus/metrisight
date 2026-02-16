# MetriSight

A lightweight, self-hosted metric anomaly dashboard for developers. Detects anomalies in time-series metrics using statistical methods — no ML expertise or expensive APM tools required.

## Features

- **Real-time anomaly detection** using Z-score and Moving Average methods
- **Interactive dashboard** with Plotly charts and Streamlit
- **Simulated metrics** (CPU, Memory, Latency) with injected anomalies for demo
- **Configurable thresholds** via sidebar controls
- **Zero external dependencies** — no Prometheus, no cloud services needed to get started

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
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
│   └── charts.py           # Plotly chart builders
└── tests/
    └── test_detector.py    # Unit tests
```

## License

MIT
