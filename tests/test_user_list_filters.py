"""Tests for fauth user-list new filter flags (--no-mfa, --token-locked)."""
from __future__ import annotations

import pytest
import responses
from click.testing import CliRunner

from fauth.cli import main


BASE = "https://fac.example.com/api/v1"


@pytest.fixture
def runner():
    return CliRunner()


def _u(username, token_auth=False, token_serial="", active=True):
    return {
        "id": hash(username) % 1000,
        "username": username,
        "first_name": "",
        "last_name": "",
        "email": "",
        "active": active,
        "token_auth": token_auth,
        "token_serial": token_serial,
    }


@responses.activate
def test_user_list_no_mfa_filter(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={
            "meta": {"next": None},
            "objects": [
                _u("withmfa", token_auth=True, token_serial="FTKMOB-X1"),
                _u("nomfa1", token_auth=False),
                _u("nomfa2", token_auth=False),
            ],
        },
        status=200,
    )

    result = runner.invoke(main, ["user-list", "--no-mfa"])
    assert result.exit_code == 0, result.output
    assert "nomfa1" in result.output
    assert "nomfa2" in result.output
    assert "withmfa" not in result.output
    assert "Total: 2" in result.output


@responses.activate
def test_user_list_token_locked_filter(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={
            "meta": {"next": None},
            "objects": [
                _u("locked-user", token_auth=True, token_serial="LOCKED-1"),
                _u("ok-user", token_auth=True, token_serial="OK-1"),
            ],
        },
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/fortitokens/",
        json={
            "meta": {"next": None},
            "objects": [
                {"serial": "LOCKED-1", "locked": True, "status": "available"},
                {"serial": "OK-1", "locked": False, "status": "assigned"},
            ],
        },
        status=200,
    )

    result = runner.invoke(main, ["user-list", "--token-locked"])
    assert result.exit_code == 0, result.output
    assert "locked-user" in result.output
    assert "ok-user" not in result.output
