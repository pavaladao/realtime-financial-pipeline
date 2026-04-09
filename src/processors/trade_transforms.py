"""Spark transforms: flatten Finnhub trade payloads and windowed aggregates."""

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    avg,
    col,
    count,
    explode,
    max as spark_max,
    min as spark_min,
    stddev,
    sum as spark_sum,
    to_timestamp,
    window,
)


def trades_from_raw_stream(df: DataFrame) -> DataFrame:
    """Explode nested trade rows and project symbol, price, volume, event_time."""
    return (
        df.filter(col("type") == "trade")
        .select(explode(col("data")).alias("trade"))
        .select(
            col("trade.s").alias("symbol"),
            col("trade.p").alias("price"),
            col("trade.v").alias("volume"),
            to_timestamp((col("trade.t") / 1000)).alias("event_time"),
        )
    )


def aggregate_1min(df_trades: DataFrame) -> DataFrame:
    """1-minute tumbling windows per symbol with VWAP and volatility."""
    return (
        df_trades.withWatermark("event_time", "10 seconds")
        .groupBy(window("event_time", "1 minute"), col("symbol"))
        .agg(
            spark_sum("volume").alias("total_volume"),
            avg("price").alias("avg_price"),
            spark_min("price").alias("min_price"),
            spark_max("price").alias("max_price"),
            count("*").alias("trade_count"),
            stddev("price").alias("volatility"),
            spark_sum(col("price") * col("volume")).alias("_pv_sum"),
        )
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            "symbol",
            "total_volume",
            "avg_price",
            "min_price",
            "max_price",
            "trade_count",
            "volatility",
            (col("_pv_sum") / col("total_volume")).alias("vwap"),
        )
    )


def aggregate_5min(df_trades: DataFrame) -> DataFrame:
    """5-minute windows with 1-minute slide per symbol."""
    return (
        df_trades.withWatermark("event_time", "30 seconds")
        .groupBy(window("event_time", "5 minutes", "1 minute"), col("symbol"))
        .agg(
            spark_sum("volume").alias("total_volume"),
            avg("price").alias("avg_price"),
            stddev("price").alias("volatility"),
            spark_sum(col("price") * col("volume")).alias("_pv_sum"),
        )
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            "symbol",
            "total_volume",
            "avg_price",
            "volatility",
            (col("_pv_sum") / col("total_volume")).alias("vwap"),
        )
    )
