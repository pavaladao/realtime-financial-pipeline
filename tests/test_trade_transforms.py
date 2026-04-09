"""Regression tests for Spark trade flattening and window aggregates (streaming pipeline core)."""

from datetime import datetime, timezone

import pytest
from pyspark.sql import Row

pytest.importorskip("pyspark")

from src.processors.trade_transforms import aggregate_1min, aggregate_5min, trades_from_raw_stream


def _ts_ms(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


@pytest.mark.spark
def test_trades_from_raw_stream_flattens_and_filters(spark_session):
    spark = spark_session
    t0 = _ts_ms(datetime(2024, 6, 1, 14, 30, 0, tzinfo=timezone.utc))
    raw = spark.createDataFrame(
        [
            Row(
                type="trade",
                data=[Row(s="AAPL", p=150.25, v=100.0, t=t0, c=None)],
            ),
            Row(type="ping", data=[]),
        ]
    )
    out = trades_from_raw_stream(raw).collect()
    assert len(out) == 1
    r = out[0]
    assert r.symbol == "AAPL"
    assert r.price == pytest.approx(150.25)
    assert r.volume == pytest.approx(100.0)


@pytest.mark.spark
def test_aggregate_1min_vwap_and_columns(spark_session):
    spark = spark_session
    base = datetime(2024, 6, 1, 14, 30, 5, tzinfo=timezone.utc)
    t1 = _ts_ms(base)
    t2 = _ts_ms(datetime(2024, 6, 1, 14, 30, 50, tzinfo=timezone.utc))
    raw = spark.createDataFrame(
        [
            Row(
                type="trade",
                data=[
                    Row(s="AAPL", p=100.0, v=10.0, t=t1, c=None),
                    Row(s="AAPL", p=110.0, v=5.0, t=t2, c=None),
                ],
            ),
        ]
    )
    trades = trades_from_raw_stream(raw)
    agg = aggregate_1min(trades)
    rows = agg.collect()
    assert len(rows) == 1
    r = rows[0]
    assert r.symbol == "AAPL"
    assert r.total_volume == pytest.approx(15.0)
    assert r.min_price == pytest.approx(100.0)
    assert r.max_price == pytest.approx(110.0)
    assert r.trade_count == 2
    expected_vwap = (100.0 * 10.0 + 110.0 * 5.0) / 15.0
    assert r.vwap == pytest.approx(expected_vwap)
    assert r.avg_price == pytest.approx(105.0)


@pytest.mark.spark
def test_aggregate_1min_output_schema_matches_jdbc_sinks(spark_session):
    """Columns expected by postgres_batch.make_anomaly_foreach_batch / table writers."""
    spark = spark_session
    t1 = _ts_ms(datetime(2024, 6, 1, 15, 0, 0, tzinfo=timezone.utc))
    raw = spark.createDataFrame(
        [
            Row(
                type="trade",
                data=[Row(s="X", p=1.0, v=1.0, t=t1, c=None)],
            ),
        ]
    )
    trades = trades_from_raw_stream(raw)
    agg = aggregate_1min(trades)
    names = agg.columns
    for required in (
        "window_start",
        "window_end",
        "symbol",
        "total_volume",
        "avg_price",
        "min_price",
        "max_price",
        "trade_count",
        "volatility",
        "vwap",
    ):
        assert required in names


@pytest.mark.spark
def test_aggregate_5min_output_schema(spark_session):
    spark = spark_session
    t1 = _ts_ms(datetime(2024, 6, 1, 16, 0, 0, tzinfo=timezone.utc))
    raw = spark.createDataFrame(
        [
            Row(
                type="trade",
                data=[Row(s="X", p=2.0, v=3.0, t=t1, c=None)],
            ),
        ]
    )
    trades = trades_from_raw_stream(raw)
    agg = aggregate_5min(trades)
    names = agg.columns
    for required in (
        "window_start",
        "window_end",
        "symbol",
        "total_volume",
        "avg_price",
        "volatility",
        "vwap",
    ):
        assert required in names
