"""Tests for JDBC env loading and foreachBatch factories (no real Postgres required)."""

from unittest.mock import MagicMock

import pytest

from src.processors.postgres_batch import (
    load_jdbc_settings_from_env,
    make_anomaly_foreach_batch,
    make_table_foreach_batch,
)


def test_load_jdbc_settings_from_env_success(monkeypatch):
    monkeypatch.setenv("POSTGRES_DB", "trades")
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    url, props = load_jdbc_settings_from_env()
    assert url == "jdbc:postgresql://postgres:5432/trades"
    assert props["user"] == "u"
    assert props["password"] == "p"
    assert props["driver"] == "org.postgresql.Driver"


@pytest.mark.parametrize(
    "missing",
    ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"],
)
def test_load_jdbc_settings_raises_when_missing(monkeypatch, missing):
    monkeypatch.setenv("POSTGRES_DB", "d")
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    monkeypatch.delenv(missing, raising=False)
    with pytest.raises(RuntimeError, match="POSTGRES_"):
        load_jdbc_settings_from_env()


def test_make_table_foreach_batch_skips_write_when_empty(monkeypatch):
    monkeypatch.setenv("POSTGRES_DB", "d")
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    fn = make_table_foreach_batch("trades_aggregated_1min")
    batch = MagicMock()
    batch.isEmpty.return_value = True
    write = MagicMock()
    batch.write = write
    fn(batch, 0)
    write.format.assert_not_called()


def test_make_anomaly_foreach_batch_noop_when_empty(monkeypatch):
    monkeypatch.setenv("POSTGRES_DB", "d")
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    fn = make_anomaly_foreach_batch()
    batch = MagicMock()
    batch.isEmpty.return_value = True
    fn(batch, 0)
    batch.groupBy.assert_not_called()
