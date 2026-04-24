"""Tests for config loading and keyring lookup."""
from __future__ import annotations

import pytest

from fauth.config import keychain_password, load_config


def test_load_config_parses_toml(config_file):
    cfg = load_config()
    assert "default" in cfg.instances
    assert cfg.instances["default"].host == "fac.example.com"
    assert cfg.instances["default"].ro_keychain == "test-ro"
    assert cfg.instances["default"].rw_keychain == "test-rw"
    assert cfg.defaults.warn_tokens_below == 0
    assert cfg.defaults.block_tokens_below == 0
    assert cfg.defaults.license_prefix_allow == ("EFTM",)


def test_load_config_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("FAUTH_CONFIG", str(tmp_path / "nonexistent.toml"))
    with pytest.raises(FileNotFoundError):
        load_config()


def test_keychain_password_returns_value(mock_keyring):
    assert keychain_password("test-ro", "api_readonly") == "fake-ro-key"
    assert keychain_password("test-rw", "fauth-cli") == "fake-rw-key"


def test_keychain_password_raises_when_missing(mock_keyring):
    with pytest.raises(RuntimeError, match="No keyring entry"):
        keychain_password("nonexistent-service", "whoever")
