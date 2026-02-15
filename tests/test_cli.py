"""Tests for the CLI module."""

from pathlib import Path

from fred_maiyer.cli import GoogleConfig, _write_env


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
    assert "GOOGLE_" not in content


def test_write_env_with_google(tmp_path: Path, monkeypatch: object):
    env_file = tmp_path / ".env"
    monkeypatch.setattr("fred_maiyer.cli.ENV_PATH", env_file)

    google_config = GoogleConfig(
        client_id="gcid",
        client_secret="gcsecret",
        access_token="gatok",
        refresh_token="grtok",
        list_id="list-123",
    )
    _write_env("cid", "csecret", "atok", "rtok", "store123", google_config)

    content = env_file.read_text()
    assert "KROGER_CLIENT_ID=cid" in content
    assert "KROGER_STORE_ID=store123" in content
    assert "GOOGLE_CLIENT_ID=gcid" in content
    assert "GOOGLE_CLIENT_SECRET=gcsecret" in content
    assert "GOOGLE_ACCESS_TOKEN=gatok" in content
    assert "GOOGLE_REFRESH_TOKEN=grtok" in content
    assert "GOOGLE_TASKS_LIST_ID=list-123" in content
