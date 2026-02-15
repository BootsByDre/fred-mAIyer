"""Tests for the CLI module."""

from pathlib import Path

from fred_maiyer.cli import _write_env


def test_write_env(tmp_path: Path, monkeypatch: object):
    env_file = tmp_path / ".env"
    monkeypatch.setattr("fred_maiyer.cli.ENV_PATH", env_file)

    _write_env("cid", "csecret", "atok", "rtok", "store123")

    content = env_file.read_text()
    assert "KROGER_CLIENT_ID=cid" in content
    assert "KROGER_CLIENT_SECRET=csecret" in content
    assert "KROGER_ACCESS_TOKEN=atok" in content
    assert "KROGER_REFRESH_TOKEN=rtok" in content
    assert "KROGER_STORE_ID=store123" in content
