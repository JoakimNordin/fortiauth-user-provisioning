"""Tests for user/group/membership lookups."""
from __future__ import annotations

import pytest
import responses

from fauth.client import FACClient
from fauth.lookup import group_by_name, membership_for, user_by_name


@pytest.fixture
def client():
    return FACClient("fac.example.com", "admin", "key")


# --- user_by_name -----------------------------------------------------------


@responses.activate
def test_user_by_name_returns_single_match(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/localusers/",
        json={"objects": [{"username": "sepros", "id": 26, "resource_uri": "/api/v1/localusers/26/"}]},
        status=200,
    )
    user = user_by_name(client, "sepros")
    assert user["username"] == "sepros"


@responses.activate
def test_user_by_name_raises_when_not_found(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/localusers/",
        json={"objects": []},
        status=200,
    )
    with pytest.raises(ValueError, match="not found"):
        user_by_name(client, "ghost")


@responses.activate
def test_user_by_name_raises_when_multiple_match(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/localusers/",
        json={"objects": [{"username": "a"}, {"username": "b"}]},
        status=200,
    )
    with pytest.raises(ValueError, match="expected 1"):
        user_by_name(client, "dup")


# --- group_by_name ----------------------------------------------------------


@responses.activate
def test_group_by_name_returns_group(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/usergroups/",
        json={"objects": [{"name": "admins", "resource_uri": "/api/v1/usergroups/1/"}]},
        status=200,
    )
    grp = group_by_name(client, "admins")
    assert grp["resource_uri"] == "/api/v1/usergroups/1/"


@responses.activate
def test_group_by_name_raises_when_not_found(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/usergroups/",
        json={"objects": []},
        status=200,
    )
    with pytest.raises(ValueError, match="not found"):
        group_by_name(client, "nonexistent")


# --- membership_for ---------------------------------------------------------


@responses.activate
def test_membership_for_returns_existing(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/localgroup-memberships/",
        json={"objects": [{"id": 42, "resource_uri": "/api/v1/localgroup-memberships/42/"}]},
        status=200,
    )
    m = membership_for(client, "/api/v1/localusers/26/", "/api/v1/usergroups/1/")
    assert m is not None
    assert m["id"] == 42


@responses.activate
def test_membership_for_returns_none_when_not_member(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/localgroup-memberships/",
        json={"objects": []},
        status=200,
    )
    m = membership_for(client, "/api/v1/localusers/26/", "/api/v1/usergroups/99/")
    assert m is None
