"""Tests for fauth user-disable-mfa command."""
from __future__ import annotations

import json

import pytest
import responses
from click.testing import CliRunner

from fauth.cli import main


BASE = "https://fac.example.com/api/v1"


@pytest.fixture
def runner():
    return CliRunner()


def _mock_user(token_auth=True, serial="EXISTING"):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={
            "objects": [
                {
                    "id": 26,
                    "username": "jdoe",
                    "resource_uri": "/api/v1/localusers/26/",
                    "token_auth": token_auth,
                    "token_serial": serial,
                }
            ]
        },
        status=200,
    )


def _mock_patch():
    responses.add(
        responses.PATCH,
        f"{BASE}/localusers/26/",
        json={"id": 26, "token_auth": False},
        status=200,
    )


@responses.activate
def test_user_disable_mfa_clears_token_and_auth(runner, config_file, mock_keyring, audit_dir):
    _mock_user(token_auth=True, serial="FTKMOB-FOO")
    _mock_patch()

    result = runner.invoke(main, ["user-disable-mfa", "jdoe"])
    assert result.exit_code == 0, result.output
    assert "MFA disabled" in result.output

    payload = json.loads(
        [c.request.body for c in responses.calls if c.request.method == "PATCH"][0]
    )
    assert payload == {"token_auth": False, "token_serial": ""}


@responses.activate
def test_user_disable_mfa_noop_if_no_mfa(runner, config_file, mock_keyring, audit_dir):
    _mock_user(token_auth=False, serial="")

    result = runner.invoke(main, ["user-disable-mfa", "jdoe"])
    assert result.exit_code == 0
    assert "nothing to do" in result.output
    patch_calls = [c for c in responses.calls if c.request.method == "PATCH"]
    assert patch_calls == []


@responses.activate
def test_user_disable_mfa_dry_run(runner, config_file, mock_keyring, audit_dir):
    _mock_user(token_auth=True)

    result = runner.invoke(main, ["--dry-run", "user-disable-mfa", "jdoe"])
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    patch_calls = [c for c in responses.calls if c.request.method == "PATCH"]
    assert patch_calls == []
