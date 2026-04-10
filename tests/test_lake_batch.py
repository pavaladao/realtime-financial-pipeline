"""Unit tests for S3A lake helpers (no Spark / MinIO required)."""

import pytest

from src.processors import lake_batch as lb


def test_is_lake_enabled_accepts_truthy(monkeypatch):
    for v in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv("LAKE_ENABLED", v)
        assert lb.is_lake_enabled() is True


def test_is_lake_enabled_false_when_unset_or_false(monkeypatch):
    monkeypatch.delenv("LAKE_ENABLED", raising=False)
    assert lb.is_lake_enabled() is False
    monkeypatch.setenv("LAKE_ENABLED", "false")
    assert lb.is_lake_enabled() is False
    monkeypatch.setenv("LAKE_ENABLED", "0")
    assert lb.is_lake_enabled() is False


def test_infer_ssl_and_path_style():
    assert lb.infer_ssl_and_path_style(None) == (True, False)
    assert lb.infer_ssl_and_path_style("") == (True, False)
    assert lb.infer_ssl_and_path_style("http://minio:9000") == (False, True)
    assert lb.infer_ssl_and_path_style("https://s3.amazonaws.com") == (True, True)


def test_trades_raw_base_uri():
    assert lb.trades_raw_base_uri("my-bucket") == "s3a://my-bucket/trades_raw"


def test_load_s3a_settings_from_env_raises_when_missing(monkeypatch):
    monkeypatch.delenv("S3A_BUCKET", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    with pytest.raises(RuntimeError, match="S3A_BUCKET"):
        lb.load_s3a_settings_from_env()

    monkeypatch.setenv("S3A_BUCKET", "b")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "s")
    with pytest.raises(RuntimeError, match="S3A_BUCKET"):
        lb.load_s3a_settings_from_env()


def test_load_s3a_settings_from_env_ok(monkeypatch):
    monkeypatch.setenv("S3A_BUCKET", "financial-pipeline-datalake")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "k")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("S3A_ENDPOINT", "http://minio:9000")
    bucket, endpoint, access, secret = lb.load_s3a_settings_from_env()
    assert bucket == "financial-pipeline-datalake"
    assert endpoint == "http://minio:9000"
    assert access == "k"
    assert secret == "secret"

    monkeypatch.delenv("S3A_ENDPOINT", raising=False)
    b2, ep2, _, _ = lb.load_s3a_settings_from_env()
    assert b2 == "financial-pipeline-datalake"
    assert ep2 is None
