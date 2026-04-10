import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize(
    "relative",
    [
        "docker-compose.yaml",
        "sql/init.sql",
        "src/schemas/finnhub_trades_schema.avsc",
        "src/processors/kafka_reader.py",
        "src/processors/postgres_batch.py",
        "src/processors/lake_batch.py",
        "src/processors/streaming_processor.py",
        "src/processors/trade_transforms.py",
        "src/producers/producer.py",
        "src/consumers/consumer.py",
    ],
)
def test_expected_project_files_exist(relative):
    path = os.path.join(_ROOT, relative)
    assert os.path.isfile(path), f"missing: {relative}"
