"""Tests for fauth user-update command."""
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


def _mock_user():
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={
            "objects": [
                {
                    "id": 26,
                    "username": "jdoe",
                    "resource_uri": "/api/v1/localusers/26/",
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "old@example.com",
                    "mobile_number": "+46-700000000",
                    "custom1": "oldcust",
                    "custom2": "T-OLD",
                }
            ]
        },
        status=200,
    )


def _mock_patch():
    responses.add(
        responses.PATCH,
        f"{BASE}/localusers/26/",
        json={"id": 26},
        status=200,
    )


@responses.activate
def test_user_update_email_only(runner, config_file, mock_keyring, audit_dir):
    _mock_user()
    _mock_patch()

    result = runner.invoke(main, ["user-update", "jdoe", "--email", "new@example.com"])
    assert result.exit_code == 0, result.output

    payload = json.loads(
        [c.request.body for c in responses.calls if c.request.method == "PATCH"][0]
    )
    assert payload == {"email": "new@example.com"}


@responses.activate
def test_user_update_multiple_fields(runner, config_file, mock_keyring, audit_dir):
    _mock_user()
    _mock_patch()

    result = runner.invoke(
        main,
        [
            "user-update", "jdoe",
            "--first-name", "Jonas",
            "--mobile", "+46-721234567",
            "--ticket", "T-NEW",
        ],
    )
    assert result.exit_code == 0, result.output

    payload = json.loads(
        [c.request.body for c in responses.calls if c.request.method == "PATCH"][0]
    )
    assert payload == {
        "first_name": "Jonas",
        "mobile_number": "+46-721234567",
        "custom2": "T-NEW",
    }


@responses.activate
def test_user_update_rejects_bad_mobile(runner, config_file, mock_keyring, audit_dir):
    result = runner.invoke(main, ["user-update", "jdoe", "--mobile", "0701234567"])
    assert result.exit_code != 0
    assert "+[country]-[number]" in result.output


@responses.activate
def test_user_update_requires_at_least_one_field(runner, config_file, mock_keyring, audit_dir):
    _mock_user()

    result = runner.invoke(main, ["user-update", "jdoe"])
    assert result.exit_code != 0
    assert "no fields to update" in result.output


@responses.activate
def test_user_update_dry_run(runner, config_file, mock_keyring, audit_dir):
    _mock_user()

    result = runner.invoke(
        main, ["--dry-run", "user-update", "jdoe", "--email", "new@example.com"]
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    patch_calls = [c for c in responses.calls if c.request.method == "PATCH"]
    assert patch_calls == []
