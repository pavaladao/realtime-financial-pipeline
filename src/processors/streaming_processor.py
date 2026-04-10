"""Spark Structured Streaming entrypoint: Kafka Avro trades -> aggregates + PostgreSQL."""

import logging
import os
import sys

# Repo root on sys.path for `import src.*` when spark-submit cwd is /app (see docker spark-driver).
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.processors.kafka_reader import KafkaReader
from src.processors.lake_batch import (
    apply_s3a_hadoop_conf,
    is_lake_enabled,
    make_raw_trades_parquet_foreach_batch,
)
from src.processors.postgres_batch import make_anomaly_foreach_batch, make_table_foreach_batch
from src.processors.trade_transforms import aggregate_1min, aggregate_5min, trades_from_raw_stream

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
        force=True,
    )

    reader = KafkaReader(
        kafka_bootstrap="kafka:29092",
        topic="trades-data",
        schema_registry_url="http://schema-registry:8081",
    )

    reader.spark.sparkContext.setLogLevel("ERROR")

    df = reader.get_stream()
    df_trades = trades_from_raw_stream(df)
    df_1min = aggregate_1min(df_trades)
    df_5min = aggregate_5min(df_trades)

    if is_lake_enabled():
        apply_s3a_hadoop_conf(reader.spark)
        df_trades.writeStream.foreachBatch(
            make_raw_trades_parquet_foreach_batch()
        ).outputMode("append").option(
            "checkpointLocation", "/app/checkpoints/lake_raw"
        ).start()

    df_1min.writeStream.foreachBatch(
        make_table_foreach_batch("trades_aggregated_1min")
    ).outputMode("append").start()

    df_5min.writeStream.foreachBatch(
        make_table_foreach_batch("trades_aggregated_5min")
    ).outputMode("append").start()

    df_1min.writeStream.foreachBatch(make_anomaly_foreach_batch()).outputMode(
        "append"
    ).start()

    reader.spark.streams.awaitAnyTermination()
