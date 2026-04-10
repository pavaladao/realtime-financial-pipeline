"""Ensures the streaming entrypoint module wires the same pipeline pieces together."""

import importlib


def test_streaming_processor_module_imports():
    """Importing the entrypoint must not start Spark jobs (only __main__ does)."""
    m = importlib.import_module("src.processors.streaming_processor")
    assert m.KafkaReader.__name__ == "KafkaReader"
    assert m.trades_from_raw_stream.__name__ == "trades_from_raw_stream"
    assert m.aggregate_1min.__name__ == "aggregate_1min"
    assert m.aggregate_5min.__name__ == "aggregate_5min"
    assert m.make_table_foreach_batch.__name__ == "make_table_foreach_batch"
    assert m.make_anomaly_foreach_batch.__name__ == "make_anomaly_foreach_batch"
    assert m.is_lake_enabled.__name__ == "is_lake_enabled"
    assert m.apply_s3a_hadoop_conf.__name__ == "apply_s3a_hadoop_conf"
    assert m.make_raw_trades_parquet_foreach_batch.__name__ == "make_raw_trades_parquet_foreach_batch"


def test_streaming_processor_kafka_and_topic_defaults():
    """Guards bootstrap/topic/registry and sink table names used by the Dockerized pipeline."""
    import src.processors.streaming_processor as sp

    source = open(sp.__file__, encoding="utf-8").read()
    assert 'kafka_bootstrap="kafka:29092"' in source
    assert 'topic="trades-data"' in source
    assert 'schema_registry_url="http://schema-registry:8081"' in source
    assert 'make_table_foreach_batch("trades_aggregated_1min")' in source
    assert 'make_table_foreach_batch("trades_aggregated_5min")' in source
    assert "make_anomaly_foreach_batch()" in source
    assert "is_lake_enabled()" in source
    assert 'checkpointLocation", "/app/checkpoints/lake_raw"' in source
    assert "make_raw_trades_parquet_foreach_batch()" in source
