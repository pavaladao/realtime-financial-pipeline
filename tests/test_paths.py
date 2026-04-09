import os

from src.config import paths


def test_project_src_constant_points_at_src():
    assert os.path.isdir(paths.PROJECT_SRC)
    assert os.path.basename(paths.PROJECT_SRC) == "src"


def test_schema_files_exist():
    assert os.path.isfile(paths.FINNHUB_TRADES_AVRO_SCHEMA)
    assert os.path.isfile(paths.FINNHUB_TRADES_JSON_SCHEMA)


def test_avro_schema_is_readable_json():
    import json

    with open(paths.FINNHUB_TRADES_AVRO_SCHEMA, encoding="utf-8") as f:
        schema = json.load(f)
    assert schema.get("type") == "record"
    assert "fields" in schema
