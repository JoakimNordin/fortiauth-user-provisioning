"""Tests for FACClient URL handling, error mapping, and pagination."""
from __future__ import annotations

import pytest
import responses

from fauth.client import FACClient, FACError


@pytest.fixture
def client():
    return FACClient("fac.example.com", "admin", "key")


# --- URL handling -----------------------------------------------------------


@responses.activate
def test_shorthand_absolute_path_gets_api_v1_prefix(client):
    """GET '/localusers/' should hit https://host/api/v1/localusers/."""
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/localusers/",
        json={"objects": []},
        status=200,
    )
    client.get("/localusers/")
    assert len(responses.calls) == 1


@responses.activate
def test_full_api_path_no_double_prefix(client):
    """meta.next gives '/api/v1/fortitokens/?...' - no double prefix."""
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/fortitokens/?limit=100&offset=100",
        json={"objects": []},
        status=200,
        match_querystring=True,
    )
    client.get("/api/v1/fortitokens/?limit=100&offset=100")
    assert len(responses.calls) == 1


@responses.activate
def test_relative_path_appends_to_base_url(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/usergroups/",
        json={"objects": []},
        status=200,
    )
    client.get("usergroups/")
    assert len(responses.calls) == 1


# --- Error mapping ----------------------------------------------------------


@responses.activate
def test_401_raises_facerror(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/localusers/",
        json={"error": "unauthorized"},
        status=401,
    )
    with pytest.raises(FACError) as exc:
        client.get("/localusers/")
    assert exc.value.status == 401
    assert "Ogiltig" in str(exc.value) or "behörighet" in str(exc.value)


@responses.activate
def test_403_raises_facerror(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/passwordpolicies/",
        status=403,
    )
    with pytest.raises(FACError) as exc:
        client.get("/passwordpolicies/")
    assert exc.value.status == 403
    assert "Förbjudet" in str(exc.value) or "scope" in str(exc.value)


@responses.activate
def test_404_raises_facerror(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/localusers/9999/",
        status=404,
    )
    with pytest.raises(FACError) as exc:
        client.get("/localusers/9999/")
    assert exc.value.status == 404


@responses.activate
def test_400_includes_payload(client):
    responses.add(
        responses.POST,
        "https://fac.example.com/api/v1/localusers/",
        json={"error": "This serial number is not available for use."},
        status=400,
    )
    with pytest.raises(FACError) as exc:
        client.post("/localusers/", json={"token_serial": "X"})
    assert exc.value.status == 400
    assert "serial number" in str(exc.value)
    assert exc.value.payload == {"error": "This serial number is not available for use."}


@responses.activate
def test_500_raises_facerror(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/localusers/",
        status=500,
    )
    with pytest.raises(FACError) as exc:
        client.get("/localusers/")
    assert exc.value.status == 500


@responses.activate
def test_204_returns_none(client):
    responses.add(
        responses.DELETE,
        "https://fac.example.com/api/v1/localusers/1/",
        status=204,
    )
    result = client.delete("/localusers/1/")
    assert result is None


# --- Pagination -------------------------------------------------------------


@responses.activate
def test_get_all_follows_meta_next(client):
    """get_all should follow meta.next until null."""
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/fortitokens/",
        json={
            "meta": {"next": "/api/v1/fortitokens/?limit=2&offset=2", "offset": 0},
            "objects": [{"id": 1}, {"id": 2}],
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/fortitokens/?limit=2&offset=2",
        json={
            "meta": {"next": None, "offset": 2},
            "objects": [{"id": 3}],
        },
        status=200,
        match_querystring=True,
    )
    result = client.get_all("/fortitokens/", params={"limit": 2})
    assert [o["id"] for o in result] == [1, 2, 3]


@responses.activate
def test_get_all_stops_when_next_is_null(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/usergroups/",
        json={
            "meta": {"next": None},
            "objects": [{"name": "g1"}, {"name": "g2"}],
        },
        status=200,
    )
    result = client.get_all("/usergroups/")
    assert len(result) == 2
    assert len(responses.calls) == 1


# --- Auth -------------------------------------------------------------------


@responses.activate
def test_basic_auth_header_sent(client):
    """Client should send Authorization: Basic <base64(user:pass)>."""
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/",
        json={},
        status=200,
    )
    client.get("/")
    import base64
    expected = "Basic " + base64.b64encode(b"admin:key").decode()
    assert responses.calls[0].request.headers["Authorization"] == expected


@responses.activate
def test_accept_json_header_sent(client):
    responses.add(
        responses.GET,
        "https://fac.example.com/api/v1/",
        json={},
        status=200,
    )
    client.get("/")
    assert responses.calls[0].request.headers["Accept"] == "application/json"
