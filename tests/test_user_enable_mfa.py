"""Tests for fauth user-enable-mfa command."""
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


def _mock_user(user_id=26, token_auth=False, mobile=""):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={
            "objects": [
                {
                    "id": user_id,
                    "username": "jdoe",
                    "resource_uri": f"/api/v1/localusers/{user_id}/",
                    "token_auth": token_auth,
                    "token_serial": "EXISTING-SERIAL" if token_auth else "",
                    "mobile_number": mobile,
                }
            ]
        },
        status=200,
    )


def _mock_token_pool(serials=("NEW-TOKEN",)):
    objects = [
        {
            "serial": s,
            "status": "available",
            "type": "ftm",
            "locked": False,
            "license": "EFTM-PROD",
        }
        for s in serials
    ]
    responses.add(
        responses.GET,
        f"{BASE}/fortitokens/",
        json={"meta": {"next": None}, "objects": objects},
        status=200,
    )


def _mock_patch_user(user_id=26):
    responses.add(
        responses.PATCH,
        f"{BASE}/localusers/{user_id}/",
        json={"id": user_id, "token_auth": True, "token_serial": "NEW-TOKEN"},
        status=200,
    )


# --- Happy path -------------------------------------------------------------


@responses.activate
def test_user_enable_mfa_picks_token_and_patches(runner, config_file, mock_keyring, audit_dir):
    _mock_user(token_auth=False)
    _mock_token_pool(serials=("NEW-TOKEN",))
    _mock_patch_user()

    result = runner.invoke(main, ["user-enable-mfa", "jdoe"])
    assert result.exit_code == 0, result.output
    assert "MFA enabled" in result.output

    patch_calls = [c for c in responses.calls if c.request.method == "PATCH"]
    assert len(patch_calls) == 1
    payload = json.loads(patch_calls[0].request.body)
    assert payload["token_auth"] is True
    assert payload["token_type"] == "ftm"
    assert payload["token_serial"] == "NEW-TOKEN"
    assert payload["ftm_act_method"] == "email"


# --- Validation -------------------------------------------------------------


@responses.activate
def test_user_enable_mfa_fails_if_user_already_has_mfa(runner, config_file, mock_keyring, audit_dir):
    _mock_user(token_auth=True)

    result = runner.invoke(main, ["user-enable-mfa", "jdoe"])
    assert result.exit_code != 0
    assert "already has MFA" in result.output
    assert "user-retoken" in result.output


@responses.activate
def test_user_enable_mfa_sms_requires_mobile(runner, config_file, mock_keyring, audit_dir):
    _mock_user(token_auth=False, mobile="")

    result = runner.invoke(main, ["user-enable-mfa", "jdoe", "--sms-activation"])
    assert result.exit_code != 0
    assert "mobile" in result.output.lower()


@responses.activate
def test_user_enable_mfa_sms_works_with_mobile(runner, config_file, mock_keyring, audit_dir):
    _mock_user(token_auth=False, mobile="+46-701234567")
    _mock_token_pool()
    _mock_patch_user()

    result = runner.invoke(main, ["user-enable-mfa", "jdoe", "--sms-activation"])
    assert result.exit_code == 0, result.output

    payload = json.loads([c.request.body for c in responses.calls if c.request.method == "PATCH"][0])
    assert payload["ftm_act_method"] == "sms"


# --- Dry run ----------------------------------------------------------------


@responses.activate
def test_user_enable_mfa_dry_run(runner, config_file, mock_keyring, audit_dir):
    _mock_user(token_auth=False)
    _mock_token_pool(serials=("NEW",))

    result = runner.invoke(main, ["--dry-run", "user-enable-mfa", "jdoe"])
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    patch_calls = [c for c in responses.calls if c.request.method == "PATCH"]
    assert patch_calls == []
