"""Tests for fauth user-retoken command."""
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


def _mock_user(user_id=26, serial="OLD-SERIAL", token_auth=True, token_type="ftm", mobile=""):
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
                    "token_type": token_type,
                    "token_serial": serial,
                    "ftm_act_method": "email",
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
        json={"id": user_id, "token_serial": "NEW-TOKEN"},
        status=200,
    )


# --- Happy path -------------------------------------------------------------


@responses.activate
def test_user_retoken_picks_new_token_and_patches(runner, config_file, mock_keyring, audit_dir):
    _mock_user(serial="OLD-SERIAL")
    _mock_token_pool(serials=("NEW-TOKEN",))
    _mock_patch_user()

    result = runner.invoke(main, ["user-retoken", "jdoe"])
    assert result.exit_code == 0, result.output
    assert "re-tokened" in result.output

    # Verify PATCH payload
    patch_calls = [c for c in responses.calls if c.request.method == "PATCH"]
    assert len(patch_calls) == 1
    payload = json.loads(patch_calls[0].request.body)
    assert payload["token_serial"] == "NEW-TOKEN"
    assert payload["ftm_act_method"] == "email"


@responses.activate
def test_user_retoken_excludes_current_serial(runner, config_file, mock_keyring, audit_dir):
    """Must not re-assign the user's current token."""
    _mock_user(serial="CURRENT")
    # Pool has only the user's current token + one new one
    _mock_token_pool(serials=("CURRENT", "ALTERNATIVE"))
    _mock_patch_user()

    result = runner.invoke(main, ["user-retoken", "jdoe"])
    assert result.exit_code == 0, result.output

    payload = json.loads([c.request.body for c in responses.calls if c.request.method == "PATCH"][0])
    assert payload["token_serial"] == "ALTERNATIVE"
    assert payload["token_serial"] != "CURRENT"


# --- Validation -------------------------------------------------------------


@responses.activate
def test_user_retoken_fails_if_user_missing_mfa(runner, config_file, mock_keyring, audit_dir):
    _mock_user(token_auth=False)

    result = runner.invoke(main, ["user-retoken", "jdoe"])
    assert result.exit_code != 0
    assert "MFA" in result.output


@responses.activate
def test_user_retoken_fails_if_user_not_ftm(runner, config_file, mock_keyring, audit_dir):
    _mock_user(token_type="email")

    result = runner.invoke(main, ["user-retoken", "jdoe"])
    assert result.exit_code != 0
    assert "ftm" in result.output.lower()


@responses.activate
def test_user_retoken_sms_requires_mobile(runner, config_file, mock_keyring, audit_dir):
    _mock_user(mobile="")  # user has no mobile

    result = runner.invoke(main, ["user-retoken", "jdoe", "--sms-activation"])
    assert result.exit_code != 0
    assert "mobile" in result.output.lower()


@responses.activate
def test_user_retoken_sms_works_with_mobile(runner, config_file, mock_keyring, audit_dir):
    _mock_user(mobile="+46-701234567")
    _mock_token_pool()
    _mock_patch_user()

    result = runner.invoke(main, ["user-retoken", "jdoe", "--sms-activation"])
    assert result.exit_code == 0, result.output

    payload = json.loads([c.request.body for c in responses.calls if c.request.method == "PATCH"][0])
    assert payload["ftm_act_method"] == "sms"


# --- Dry run ----------------------------------------------------------------


@responses.activate
def test_user_retoken_dry_run(runner, config_file, mock_keyring, audit_dir):
    _mock_user(serial="OLD")
    _mock_token_pool(serials=("NEW",))

    result = runner.invoke(main, ["--dry-run", "user-retoken", "jdoe"])
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    patch_calls = [c for c in responses.calls if c.request.method == "PATCH"]
    assert patch_calls == []
