"""Shared test fixtures."""
from __future__ import annotations

import pytest


TEST_CONFIG = """\
[fac.default]
host = "fac.example.com"
ro_keychain = "test-ro"
rw_keychain = "test-rw"

[defaults]
warn_tokens_below = 0
block_tokens_below = 0
license_prefix_allow = ["EFTM"]
"""


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """Create a temp config file and point FAUTH_CONFIG at it."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(TEST_CONFIG)
    monkeypatch.setenv("FAUTH_CONFIG", str(cfg))
    return cfg


@pytest.fixture
def mock_keyring(monkeypatch):
    """Replace keyring.get_password with a deterministic stub."""
    import keyring

    keys = {
        ("test-ro", "api_readonly"): "fake-ro-key",
        ("test-rw", "fauth-cli"): "fake-rw-key",
    }

    def fake_get(service, account):
        return keys.get((service, account))

    monkeypatch.setattr(keyring, "get_password", fake_get)


@pytest.fixture
def audit_dir(tmp_path, monkeypatch):
    """Redirect audit log to a temp directory."""
    monkeypatch.setattr(
        "fauth.audit.state_dir", lambda: tmp_path / "state"
    )
    return tmp_path / "state"
