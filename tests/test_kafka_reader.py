import io
import json
from unittest.mock import MagicMock, patch

import fastavro
import pytest
import requests
from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
)

pytest.importorskip("pyspark")

from src.config.paths import FINNHUB_TRADES_AVRO_SCHEMA
from src.processors.kafka_reader import KafkaReader


def test_avro_type_to_spark_primitive_and_union():
    assert KafkaReader._avro_type_to_spark("string").typeName() == "string"
    assert KafkaReader._avro_type_to_spark(["null", "double"]).typeName() == "double"


def test_avro_type_to_spark_nested_record_matches_financial_schema():
    with open(FINNHUB_TRADES_AVRO_SCHEMA, encoding="utf-8") as f:
        schema = json.load(f)
    spark_type = KafkaReader._avro_type_to_spark(schema)
    assert isinstance(spark_type, StructType)
    names = [f.name for f in spark_type.fields]
    assert "type" in names and "data" in names


def test_avro_schema_to_spark_schema_roundtrip_shape():
    with open(FINNHUB_TRADES_AVRO_SCHEMA, encoding="utf-8") as f:
        avro_json = f.read()
    reader = object.__new__(KafkaReader)
    st = KafkaReader._avro_schema_to_spark_schema(reader, avro_json)
    assert isinstance(st, StructType)
    assert len(st.fields) >= 2


def test_fetch_schema_from_registry_success():
    sample_schema = '{"type":"record","name":"X","fields":[]}'
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"schema": sample_schema}
    mock_resp.raise_for_status = MagicMock()

    mock_spark = MagicMock()
    with patch("src.processors.kafka_reader.requests.get", return_value=mock_resp):
        kr = KafkaReader.__new__(KafkaReader)
        kr.topic = "trades-data"
        kr.schema_registry_url = "http://registry:8081"
        kr.spark = mock_spark
        out = KafkaReader._fetch_schema_from_registry(kr)
    assert out == sample_schema
    mock_resp.raise_for_status.assert_called_once()


def test_fetch_schema_from_registry_connection_error():
    mock_spark = MagicMock()
    with patch(
        "src.processors.kafka_reader.requests.get",
        side_effect=requests.exceptions.ConnectionError(),
    ):
        kr = KafkaReader.__new__(KafkaReader)
        kr.topic = "t"
        kr.schema_registry_url = "http://bad:8081"
        kr.spark = mock_spark
        with pytest.raises(RuntimeError, match="Could not connect"):
            KafkaReader._fetch_schema_from_registry(kr)


def test_deserialize_avro_with_confluent_wire_format():
    with open(FINNHUB_TRADES_AVRO_SCHEMA, encoding="utf-8") as f:
        avro_schema_dict = json.load(f)

    record = {
        "type": "trade",
        "data": [
            {"p": 150.25, "s": "AAPL", "t": 1_700_000_000_000, "v": 100.0, "c": None}
        ],
    }
    buf = io.BytesIO()
    fastavro.schemaless_writer(buf, avro_schema_dict, record)
    payload = buf.getvalue()
    wire = b"\x00" + (1).to_bytes(4, "big") + payload

    kr = KafkaReader.__new__(KafkaReader)
    kr.avro_schema_dict = avro_schema_dict
    out = KafkaReader._deserialize_avro(kr, wire)
    assert out["type"] == "trade"
    assert out["data"][0]["s"] == "AAPL"
    assert out["data"][0]["p"] == pytest.approx(150.25)
