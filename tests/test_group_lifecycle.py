"""Tests for fauth group-create and group-delete commands."""
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


# --- group-create -----------------------------------------------------------


@responses.activate
def test_group_create_posts_payload(runner, config_file, mock_keyring, audit_dir):
    # Existence check: empty
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={"objects": []},
        status=200,
    )
    # Create
    responses.add(
        responses.POST,
        f"{BASE}/usergroups/",
        json={"id": 99, "name": "newcust_users", "group_type": "firewall"},
        status=200,
    )

    result = runner.invoke(main, ["group-create", "newcust_users"])
    assert result.exit_code == 0, result.output
    assert "created" in result.output

    post_calls = [c for c in responses.calls if c.request.method == "POST"]
    assert len(post_calls) == 1
    payload = json.loads(post_calls[0].request.body)
    assert payload == {"name": "newcust_users", "group_type": "firewall"}


@responses.activate
def test_group_create_rejects_duplicate(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={"objects": [{"id": 1, "name": "exists", "resource_uri": "/api/v1/usergroups/1/"}]},
        status=200,
    )

    result = runner.invoke(main, ["group-create", "exists"])
    assert result.exit_code != 0
    assert "already exists" in result.output


@responses.activate
def test_group_create_dry_run(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={"objects": []},
        status=200,
    )

    result = runner.invoke(main, ["--dry-run", "group-create", "newcust_users"])
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    post_calls = [c for c in responses.calls if c.request.method == "POST"]
    assert post_calls == []


@responses.activate
def test_group_create_with_custom_type(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={"objects": []},
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/usergroups/",
        json={"id": 100},
        status=200,
    )

    result = runner.invoke(
        main, ["group-create", "vpn_users", "--type", "vpn"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(
        [c.request.body for c in responses.calls if c.request.method == "POST"][0]
    )
    assert payload["group_type"] == "vpn"


# --- group-delete -----------------------------------------------------------


@responses.activate
def test_group_delete_empty_group(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={
            "objects": [
                {
                    "id": 5,
                    "name": "old",
                    "resource_uri": "/api/v1/usergroups/5/",
                    "users": [],
                }
            ]
        },
        status=200,
    )
    responses.add(
        responses.DELETE,
        f"{BASE}/usergroups/5/",
        status=204,
    )

    result = runner.invoke(main, ["group-delete", "old", "--yes"])
    assert result.exit_code == 0, result.output
    assert "deleted" in result.output

    delete_calls = [c for c in responses.calls if c.request.method == "DELETE"]
    assert len(delete_calls) == 1


@responses.activate
def test_group_delete_refuses_non_empty(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={
            "objects": [
                {
                    "id": 5,
                    "name": "in-use",
                    "resource_uri": "/api/v1/usergroups/5/",
                    "users": ["/api/v1/localusers/1/", "/api/v1/localusers/2/"],
                }
            ]
        },
        status=200,
    )

    result = runner.invoke(main, ["group-delete", "in-use", "--yes"])
    assert result.exit_code != 0
    assert "still has 2 members" in result.output
    delete_calls = [c for c in responses.calls if c.request.method == "DELETE"]
    assert delete_calls == []


@responses.activate
def test_group_delete_dry_run(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/usergroups/",
        json={
            "objects": [
                {
                    "id": 5,
                    "name": "old",
                    "resource_uri": "/api/v1/usergroups/5/",
                    "users": [],
                }
            ]
        },
        status=200,
    )

    result = runner.invoke(main, ["--dry-run", "group-delete", "old"])
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    delete_calls = [c for c in responses.calls if c.request.method == "DELETE"]
    assert delete_calls == []
