"""Tests for fauth user-enable command."""
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


def _mock_user(active=False):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={
            "objects": [
                {
                    "id": 26,
                    "username": "jdoe",
                    "resource_uri": "/api/v1/localusers/26/",
                    "active": active,
                }
            ]
        },
        status=200,
    )


def _mock_patch():
    responses.add(
        responses.PATCH,
        f"{BASE}/localusers/26/",
        json={"id": 26, "active": True},
        status=200,
    )


@responses.activate
def test_user_enable_patches_active_true(runner, config_file, mock_keyring, audit_dir):
    _mock_user(active=False)
    _mock_patch()

    result = runner.invoke(main, ["user-enable", "jdoe"])
    assert result.exit_code == 0, result.output
    assert "enabled" in result.output

    patch_calls = [c for c in responses.calls if c.request.method == "PATCH"]
    assert len(patch_calls) == 1
    payload = json.loads(patch_calls[0].request.body)
    assert payload == {"active": True}


@responses.activate
def test_user_enable_noop_when_already_active(runner, config_file, mock_keyring, audit_dir):
    _mock_user(active=True)

    result = runner.invoke(main, ["user-enable", "jdoe"])
    assert result.exit_code == 0
    assert "already active" in result.output
    patch_calls = [c for c in responses.calls if c.request.method == "PATCH"]
    assert patch_calls == []


@responses.activate
def test_user_enable_dry_run(runner, config_file, mock_keyring, audit_dir):
    _mock_user(active=False)

    result = runner.invoke(main, ["--dry-run", "user-enable", "jdoe"])
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    patch_calls = [c for c in responses.calls if c.request.method == "PATCH"]
    assert patch_calls == []
