"""Tests for user-disable, user-delete, user-addgroup, user-rmgroup."""
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


# --- user-disable -----------------------------------------------------------


@responses.activate
def test_user_disable_patches_active_false(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={"objects": [{"id": 26, "username": "jdoe", "active": True}]},
        status=200,
    )
    responses.add(
        responses.PATCH,
        f"{BASE}/localusers/26/",
        json={"id": 26, "active": False},
        status=200,
    )

    result = runner.invoke(main, ["user-disable", "jdoe"])
    assert result.exit_code == 0
    assert "disabled" in result.output.lower()

    payload = json.loads([c.request.body for c in responses.calls if c.request.method == "PATCH"][0])
    assert payload == {"active": False}


@responses.activate
def test_user_disable_noop_when_already_inactive(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={"objects": [{"id": 26, "username": "jdoe", "active": False}]},
        status=200,
    )

    result = runner.invoke(main, ["user-disable", "jdoe"])
    assert result.exit_code == 0
    assert "already inactive" in result.output.lower()
    # No PATCH should be made
    assert [c for c in responses.calls if c.request.method == "PATCH"] == []


# --- user-delete ------------------------------------------------------------


@responses.activate
def test_user_delete_with_yes_flag(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={"objects": [{"id": 26, "username": "jdoe", "first_name": "J", "last_name": "D"}]},
        status=200,
    )
    responses.add(
        responses.DELETE,
        f"{BASE}/localusers/26/",
        status=204,
    )

    result = runner.invoke(main, ["user-delete", "jdoe", "--yes"])
    assert result.exit_code == 0
    assert "deleted" in result.output.lower()


@responses.activate
def test_user_delete_fails_if_user_missing(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={"objects": []},
        status=200,
    )

    result = runner.invoke(main, ["user-delete", "ghost", "--yes"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


# --- user-addgroup ----------------------------------------------------------


@responses.activate
def test_user_addgroup_posts_membership(runner, config_file, mock_keyring, audit_dir):
    # Look up user
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={"objects": [{"id": 26, "username": "jdoe", "resource_uri": "/api/v1/localusers/26/"}]},
        status=200,
    )
    # Look up group
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={"objects": [{"name": "admins", "resource_uri": "/api/v1/usergroups/1/"}]},
        status=200,
    )
    # Check existing membership - none
    responses.add(
        responses.GET,
        f"{BASE}/localgroup-memberships/",
        json={"objects": []},
        status=200,
    )
    # POST new membership
    responses.add(
        responses.POST,
        f"{BASE}/localgroup-memberships/",
        json={"id": 100},
        status=201,
    )

    result = runner.invoke(main, ["user-addgroup", "jdoe", "admins"])
    assert result.exit_code == 0, result.output
    assert "added to group" in result.output.lower()


@responses.activate
def test_user_addgroup_noop_if_already_member(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={"objects": [{"id": 26, "username": "jdoe", "resource_uri": "/api/v1/localusers/26/"}]},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={"objects": [{"name": "admins", "resource_uri": "/api/v1/usergroups/1/"}]},
        status=200,
    )
    # Existing membership found
    responses.add(
        responses.GET,
        f"{BASE}/localgroup-memberships/",
        json={"objects": [{"id": 100, "resource_uri": "/api/v1/localgroup-memberships/100/"}]},
        status=200,
    )

    result = runner.invoke(main, ["user-addgroup", "jdoe", "admins"])
    assert result.exit_code == 0
    assert "already in group" in result.output.lower()
    # No POST made
    assert [c for c in responses.calls if c.request.method == "POST"] == []


# --- user-rmgroup -----------------------------------------------------------


@responses.activate
def test_user_rmgroup_deletes_membership(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={"objects": [{"id": 26, "username": "jdoe", "resource_uri": "/api/v1/localusers/26/"}]},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={"objects": [{"name": "admins", "resource_uri": "/api/v1/usergroups/1/"}]},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/localgroup-memberships/",
        json={"objects": [{"id": 100, "resource_uri": "/api/v1/localgroup-memberships/100/"}]},
        status=200,
    )
    responses.add(
        responses.DELETE,
        f"{BASE}/localgroup-memberships/100/",
        status=204,
    )

    result = runner.invoke(main, ["user-rmgroup", "jdoe", "admins"])
    assert result.exit_code == 0, result.output
    assert "removed from group" in result.output.lower()


@responses.activate
def test_user_rmgroup_noop_if_not_member(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={"objects": [{"id": 26, "username": "jdoe", "resource_uri": "/api/v1/localusers/26/"}]},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={"objects": [{"name": "admins", "resource_uri": "/api/v1/usergroups/1/"}]},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/localgroup-memberships/",
        json={"objects": []},
        status=200,
    )

    result = runner.invoke(main, ["user-rmgroup", "jdoe", "admins"])
    assert result.exit_code == 0
    assert "not in group" in result.output.lower()
    assert [c for c in responses.calls if c.request.method == "DELETE"] == []
