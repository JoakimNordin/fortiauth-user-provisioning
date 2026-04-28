"""Tests for fauth token-info command."""
from __future__ import annotations

import pytest
import responses
from click.testing import CliRunner

from fauth.cli import main


BASE = "https://fac.example.com/api/v1"


@pytest.fixture
def runner():
    return CliRunner()


@responses.activate
def test_token_info_with_holder(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/fortitokens/",
        json={
            "objects": [
                {
                    "serial": "FTKMOB-X1",
                    "type": "ftm",
                    "status": "assigned",
                    "locked": False,
                    "license": "EFTM-PROD",
                    "last_used_at": "2026-04-28T07:00:00Z",
                    "resource_uri": "/api/v1/fortitokens/1/",
                }
            ]
        },
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={
            "objects": [
                {
                    "username": "jdoe",
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "jdoe@acme.com",
                }
            ]
        },
        status=200,
    )

    result = runner.invoke(main, ["token-info", "FTKMOB-X1"])
    assert result.exit_code == 0, result.output
    assert "FTKMOB-X1" in result.output
    assert "jdoe" in result.output
    assert "John Doe" in result.output


@responses.activate
def test_token_info_no_holder(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/fortitokens/",
        json={
            "objects": [
                {
                    "serial": "FTKMOB-FREE",
                    "type": "ftm",
                    "status": "available",
                    "locked": False,
                    "license": "EFTM-PROD",
                    "resource_uri": "/api/v1/fortitokens/2/",
                }
            ]
        },
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={"objects": []},
        status=200,
    )

    result = runner.invoke(main, ["token-info", "FTKMOB-FREE"])
    assert result.exit_code == 0, result.output
    assert "(no user)" in result.output


@responses.activate
def test_token_info_not_found(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/fortitokens/",
        json={"objects": []},
        status=200,
    )

    result = runner.invoke(main, ["token-info", "NONEXISTENT"])
    assert result.exit_code != 0
    assert "not found" in result.output
