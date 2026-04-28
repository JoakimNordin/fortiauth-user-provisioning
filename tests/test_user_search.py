"""Tests for fauth user-search command."""
from __future__ import annotations

import pytest
import responses
from click.testing import CliRunner

from fauth.cli import main


BASE = "https://fac.example.com/api/v1"


@pytest.fixture
def runner():
    return CliRunner()


def _user(username, first_name="", last_name="", email="", custom1="", custom2=""):
    return {
        "id": hash(username) % 1000,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "custom1": custom1,
        "custom2": custom2,
        "active": True,
        "token_auth": False,
    }


@responses.activate
def test_user_search_by_email(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={
            "meta": {"next": None},
            "objects": [_user("jdoe", "John", "Doe", "jdoe@acme.com")],
        },
        status=200,
    )

    result = runner.invoke(main, ["user-search", "--email", "jdoe@acme"])
    assert result.exit_code == 0, result.output
    assert "jdoe" in result.output
    assert "Total: 1" in result.output


@responses.activate
def test_user_search_by_customer_and_ticket(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={
            "meta": {"next": None},
            "objects": [_user("se1u1i", "Ludwig", "Hedeby", custom1="sweco", custom2="W227794")],
        },
        status=200,
    )

    result = runner.invoke(
        main, ["user-search", "--customer", "sweco", "--ticket", "W227794"]
    )
    assert result.exit_code == 0, result.output
    assert "se1u1i" in result.output


@responses.activate
def test_user_search_no_filter_fails(runner, config_file, mock_keyring, audit_dir):
    result = runner.invoke(main, ["user-search"])
    assert result.exit_code != 0
    assert "at least one" in result.output


@responses.activate
def test_user_search_filters_name_clientside(runner, config_file, mock_keyring, audit_dir):
    responses.add(
        responses.GET,
        f"{BASE}/localusers/",
        json={
            "meta": {"next": None},
            "objects": [
                _user("a1", "Alice", "Anderson", "a@x.se"),
                _user("a2", "Bob", "Brown", "b@x.se"),
            ],
        },
        status=200,
    )

    result = runner.invoke(main, ["user-search", "--email", "x.se", "--name", "Alice"])
    assert result.exit_code == 0
    assert "a1" in result.output
    assert "a2" not in result.output
