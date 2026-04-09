import importlib
import os


def test_finnhub_token_loaded_from_environment(monkeypatch):
    monkeypatch.setenv("FINNHUB_TOKEN", "test-token-for-ci")
    import src.config.env as env

    importlib.reload(env)
    assert env.FINNHUB_TOKEN == "test-token-for-ci"


def test_finnhub_token_none_when_unset(monkeypatch):
    monkeypatch.delenv("FINNHUB_TOKEN", raising=False)
    import src.config.env as env

    importlib.reload(env)
    assert env.FINNHUB_TOKEN is None
