"""Tests for Prometheus client module."""

import json
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from metrisight.prometheus import query_prometheus, check_connection, PrometheusError


def _mock_prom_response(values: list[list], status: str = "success"):
    """Create a mock Prometheus API response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "status": status,
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"__name__": "test_metric"},
                    "values": values,
                }
            ],
        },
    }
    return resp


class TestQueryPrometheus:
    @patch("metrisight.prometheus.requests.get")
    def test_parses_valid_response(self, mock_get):
        values = [
            [1700000000, "42.5"],
            [1700000060, "43.1"],
            [1700000120, "41.8"],
        ]
        mock_get.return_value = _mock_prom_response(values)

        df = query_prometheus("http://localhost:9090", "test_query", lookback_hours=1)

        assert len(df) == 3
        assert list(df.columns) == ["timestamp", "value"]
        assert df["value"].iloc[0] == 42.5
        assert isinstance(df["timestamp"].iloc[0], datetime)

    @patch("metrisight.prometheus.requests.get")
    def test_empty_result_returns_empty_df(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "status": "success",
            "data": {"resultType": "matrix", "result": []},
        }
        mock_get.return_value = resp

        df = query_prometheus("http://localhost:9090", "test_query")
        assert len(df) == 0
        assert "timestamp" in df.columns
        assert "value" in df.columns

    @patch("metrisight.prometheus.requests.get")
    def test_error_status_raises(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "status": "error",
            "error": "bad query",
        }
        mock_get.return_value = resp

        with pytest.raises(PrometheusError, match="bad query"):
            query_prometheus("http://localhost:9090", "bad{query")

    @patch("metrisight.prometheus.requests.get")
    def test_http_error_raises(self, mock_get):
        resp = MagicMock()
        resp.status_code = 500
        resp.text = "Internal Server Error"
        mock_get.return_value = resp

        with pytest.raises(PrometheusError, match="HTTP 500"):
            query_prometheus("http://localhost:9090", "test_query")

    @patch("metrisight.prometheus.requests.get")
    def test_connection_error_raises(self, mock_get):
        import requests
        mock_get.side_effect = requests.ConnectionError("refused")

        with pytest.raises(PrometheusError, match="Cannot connect"):
            query_prometheus("http://localhost:9090", "test_query")

    @patch("metrisight.prometheus.requests.get")
    def test_timeout_raises(self, mock_get):
        import requests
        mock_get.side_effect = requests.Timeout("timed out")

        with pytest.raises(PrometheusError, match="timed out"):
            query_prometheus("http://localhost:9090", "test_query")

    @patch("metrisight.prometheus.requests.get")
    def test_passes_correct_params(self, mock_get):
        mock_get.return_value = _mock_prom_response([[1700000000, "1.0"]])

        query_prometheus(
            "http://prom:9090/",
            "up",
            lookback_hours=6,
            step_seconds=30,
        )

        call_args = mock_get.call_args
        assert call_args[0][0] == "http://prom:9090/api/v1/query_range"
        params = call_args[1]["params"]
        assert params["query"] == "up"
        assert params["step"] == "30s"

    @patch("metrisight.prometheus.requests.get")
    def test_bearer_token_sent_in_header(self, mock_get):
        mock_get.return_value = _mock_prom_response([[1700000000, "1.0"]])

        query_prometheus(
            "http://prom:9090",
            "up",
            bearer_token="my-secret-token",
        )

        call_args = mock_get.call_args
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer my-secret-token"
        assert call_args[1]["auth"] is None

    @patch("metrisight.prometheus.requests.get")
    def test_basic_auth_sent(self, mock_get):
        mock_get.return_value = _mock_prom_response([[1700000000, "1.0"]])

        query_prometheus(
            "http://prom:9090",
            "up",
            basic_auth=("admin", "password123"),
        )

        call_args = mock_get.call_args
        assert call_args[1]["auth"] == ("admin", "password123")
        assert call_args[1]["headers"] == {}

    @patch("metrisight.prometheus.requests.get")
    def test_no_auth_by_default(self, mock_get):
        mock_get.return_value = _mock_prom_response([[1700000000, "1.0"]])

        query_prometheus("http://prom:9090", "up")

        call_args = mock_get.call_args
        assert call_args[1]["headers"] == {}
        assert call_args[1]["auth"] is None


class TestCheckConnection:
    @patch("metrisight.prometheus.requests.get")
    def test_successful_connection(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"data": {"version": "2.48.0"}}
        mock_get.return_value = resp

        ok, msg = check_connection("http://localhost:9090")
        assert ok is True
        assert "2.48.0" in msg

    @patch("metrisight.prometheus.requests.get")
    def test_connection_refused(self, mock_get):
        import requests
        mock_get.side_effect = requests.ConnectionError("refused")

        ok, msg = check_connection("http://localhost:9090")
        assert ok is False
        assert "Cannot connect" in msg

    @patch("metrisight.prometheus.requests.get")
    def test_timeout(self, mock_get):
        import requests
        mock_get.side_effect = requests.Timeout()

        ok, msg = check_connection("http://localhost:9090")
        assert ok is False
        assert "timed out" in msg

    @patch("metrisight.prometheus.requests.get")
    def test_401_unauthorized(self, mock_get):
        resp = MagicMock()
        resp.status_code = 401
        mock_get.return_value = resp

        ok, msg = check_connection("http://localhost:9090")
        assert ok is False
        assert "401" in msg

    @patch("metrisight.prometheus.requests.get")
    def test_403_forbidden(self, mock_get):
        resp = MagicMock()
        resp.status_code = 403
        mock_get.return_value = resp

        ok, msg = check_connection("http://localhost:9090")
        assert ok is False
        assert "403" in msg

    @patch("metrisight.prometheus.requests.get")
    def test_bearer_token_passed(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"data": {"version": "2.48.0"}}
        mock_get.return_value = resp

        ok, msg = check_connection("http://localhost:9090", bearer_token="tok123")
        assert ok is True
        call_args = mock_get.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer tok123"

    @patch("metrisight.prometheus.requests.get")
    def test_basic_auth_passed(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"data": {"version": "2.48.0"}}
        mock_get.return_value = resp

        ok, msg = check_connection("http://localhost:9090", basic_auth=("user", "pass"))
        assert ok is True
        call_args = mock_get.call_args
        assert call_args[1]["auth"] == ("user", "pass")
