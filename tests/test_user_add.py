"""Tests for fauth user-add command."""
from __future__ import annotations

import pytest
import responses
from click.testing import CliRunner

from fauth.cli import main


BASE = "https://fac.example.com/api/v1"


@pytest.fixture
def runner():
    return CliRunner()


def _mock_localusers_empty():
    """Mock 'user does not exist yet' pre-check."""
    responses.add(responses.GET, f"{BASE}/localusers/", json={"objects": []}, status=200)


def _mock_group_lookup(name="customer_admins", uri="/api/v1/usergroups/1/"):
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={"objects": [{"name": name, "resource_uri": uri}]},
        status=200,
    )


def _mock_token_pool(serials=("FTKMOB-NEW",)):
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


def _mock_post_localuser(user_uri="/api/v1/localusers/257/", user_id=257):
    responses.add(
        responses.POST,
        f"{BASE}/localusers/",
        json={"id": user_id, "resource_uri": user_uri},
        status=201,
    )


def _mock_post_membership(uri="/api/v1/localgroup-memberships/100/"):
    responses.add(
        responses.POST,
        f"{BASE}/localgroup-memberships/",
        json={"id": 100, "resource_uri": uri},
        status=201,
    )


# --- Happy path ------------------------------------------------------------


@responses.activate
def test_user_add_mfa_happy_path(runner, config_file, mock_keyring, audit_dir):
    _mock_localusers_empty()       # pre-check: user doesn't exist
    _mock_group_lookup()            # resolve --group
    _mock_token_pool()              # pick token
    _mock_post_localuser()          # create user
    _mock_post_membership()         # add to group

    result = runner.invoke(
        main,
        [
            "user-add",
            "--username", "jdoe",
            "--first-name", "John",
            "--last-name", "Doe",
            "--email", "jdoe@customer.com",
            "--mobile", "+46-701234567",
            "--group", "customer_admins",
            "--customer", "acme",
            "--ticket", "W227971",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Created user 'jdoe'" in result.output
    # Verify payload to POST /localusers/
    post_body = [c.request for c in responses.calls if c.request.method == "POST" and "localusers" in c.request.url][0]
    import json
    payload = json.loads(post_body.body)
    assert payload["username"] == "jdoe"
    assert payload["token_auth"] is True
    assert payload["token_type"] == "ftm"
    assert payload["token_serial"] == "FTKMOB-NEW"
    assert payload["custom1"] == "acme"
    assert payload["custom2"] == "W227971"
    assert payload["custom3"].startswith("fauth-cli:")


@responses.activate
def test_user_add_no_mfa(runner, config_file, mock_keyring, audit_dir):
    """--no-mfa should skip token selection and not set token_auth."""
    _mock_localusers_empty()
    _mock_group_lookup(name="services", uri="/api/v1/usergroups/2/")
    _mock_post_localuser()
    _mock_post_membership()

    result = runner.invoke(
        main,
        [
            "user-add",
            "--username", "svc-foo",
            "--first-name", "Service",
            "--last-name", "Foo",
            "--email", "svc@example.com",
            "--group", "services",
            "--no-mfa",
        ],
    )
    assert result.exit_code == 0, result.output
    post_body = [c.request for c in responses.calls if c.request.method == "POST" and "localusers" in c.request.url][0]
    import json
    payload = json.loads(post_body.body)
    assert "token_auth" not in payload or payload.get("token_auth") is False
    assert "token_serial" not in payload


# --- List-response handling (FAC 8.0.0 quirk) ------------------------------


@responses.activate
def test_user_add_handles_list_response(runner, config_file, mock_keyring, audit_dir):
    """FAC 8.0.0 returnerar ibland [user] istället för user - koden ska hantera båda."""
    _mock_localusers_empty()
    _mock_group_lookup()
    _mock_token_pool()
    # POST returns a list (the quirk)
    responses.add(
        responses.POST,
        f"{BASE}/localusers/",
        json=[{"id": 257, "resource_uri": "/api/v1/localusers/257/"}],
        status=201,
    )
    _mock_post_membership()

    result = runner.invoke(
        main,
        [
            "user-add",
            "--username", "jdoe",
            "--first-name", "John",
            "--last-name", "Doe",
            "--email", "jdoe@example.com",
            "--group", "customer_admins",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Created user 'jdoe'" in result.output


# --- Pre-flight checks ------------------------------------------------------


@responses.activate
def test_user_add_fails_if_user_exists(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={"objects": [{"username": "jdoe", "id": 1}]},
        status=200,
    )
    result = runner.invoke(
        main,
        [
            "user-add",
            "--username", "jdoe",
            "--first-name", "John",
            "--last-name", "Doe",
            "--email", "j@d.com",
            "--group", "g",
        ],
    )
    assert result.exit_code != 0
    assert "already exists" in result.output


@responses.activate
def test_user_add_fails_if_group_missing(runner, config_file, mock_keyring, audit_dir):
    _mock_localusers_empty()
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={"objects": []},
        status=200,
    )
    result = runner.invoke(
        main,
        [
            "user-add",
            "--username", "jdoe",
            "--first-name", "J",
            "--last-name", "D",
            "--email", "j@d.com",
            "--group", "ghost-group",
        ],
    )
    assert result.exit_code != 0
    assert "ghost-group" in result.output and "not found" in result.output


@responses.activate
def test_user_add_blocks_when_token_pool_empty(runner, config_file, mock_keyring, audit_dir):
    _mock_localusers_empty()
    _mock_group_lookup()
    # Token pool has only locked tokens = 0 allocatable
    responses.add(
        responses.GET,
        f"{BASE}/fortitokens/",
        json={
            "meta": {"next": None},
            "objects": [
                {"serial": "A", "status": "available", "type": "ftm", "locked": True, "license": "EFTM-PROD"},
            ],
        },
        status=200,
    )

    result = runner.invoke(
        main,
        [
            "user-add",
            "--username", "jdoe",
            "--first-name", "J",
            "--last-name", "D",
            "--email", "j@d.com",
            "--group", "customer_admins",
        ],
    )
    assert result.exit_code != 0
    assert "BLOCKED" in result.output


# --- Validation -------------------------------------------------------------


def test_user_add_rejects_bad_mobile_format(runner, config_file, mock_keyring, audit_dir):
    result = runner.invoke(
        main,
        [
            "user-add",
            "--username", "jdoe",
            "--first-name", "J",
            "--last-name", "D",
            "--email", "j@d.com",
            "--mobile", "070-1234567",  # missing country code + wrong separator
            "--group", "g",
        ],
    )
    assert result.exit_code != 0
    assert "format" in result.output.lower()


def test_user_add_sms_requires_mobile(runner, config_file, mock_keyring, audit_dir):
    result = runner.invoke(
        main,
        [
            "user-add",
            "--username", "jdoe",
            "--first-name", "J",
            "--last-name", "D",
            "--email", "j@d.com",
            "--group", "g",
            "--sms-activation",
        ],
    )
    assert result.exit_code != 0
    assert "mobile" in result.output.lower()


def test_user_add_sms_and_no_mfa_mutually_exclusive(runner, config_file, mock_keyring, audit_dir):
    result = runner.invoke(
        main,
        [
            "user-add",
            "--username", "jdoe",
            "--first-name", "J",
            "--last-name", "D",
            "--email", "j@d.com",
            "--mobile", "+46-701234567",
            "--group", "g",
            "--sms-activation",
            "--no-mfa",
        ],
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output.lower()


# --- Dry run ---------------------------------------------------------------


@responses.activate
def test_user_add_dry_run_does_not_post(runner, config_file, mock_keyring, audit_dir):
    _mock_localusers_empty()
    _mock_group_lookup()
    _mock_token_pool()

    result = runner.invoke(
        main,
        [
            "--dry-run",
            "user-add",
            "--username", "jdoe",
            "--first-name", "J",
            "--last-name", "D",
            "--email", "j@d.com",
            "--group", "customer_admins",
        ],
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    post_calls = [c for c in responses.calls if c.request.method == "POST"]
    assert post_calls == []
