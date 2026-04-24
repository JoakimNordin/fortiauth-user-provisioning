"""Helpers for resolving user/group names to URIs and IDs."""
from __future__ import annotations

from fauth.client import FACClient


def user_by_name(client: FACClient, username: str) -> dict:
    """Return the user dict for an exact username match, or raise ValueError."""
    page = client.get("/localusers/", params={"username__exact": username})
    users = page.get("objects", []) if isinstance(page, dict) else []
    if not users:
        raise ValueError(f"User '{username}' not found")
    if len(users) > 1:
        raise ValueError(f"{len(users)} users matched '{username}' (expected 1)")
    return users[0]


def group_by_name(client: FACClient, group_name: str) -> dict:
    """Return the group dict for an exact name match, or raise ValueError."""
    page = client.get("/usergroups/", params={"name__exact": group_name})
    groups = page.get("objects", []) if isinstance(page, dict) else []
    if not groups:
        raise ValueError(f"Group '{group_name}' not found")
    if len(groups) > 1:
        raise ValueError(f"{len(groups)} groups matched '{group_name}' (expected 1)")
    return groups[0]


def membership_for(client: FACClient, user_uri: str, group_uri: str) -> dict | None:
    """Find the membership record linking a user to a group."""
    # API filters: user, group (both exact, per schema)
    user_id = user_uri.rstrip("/").rsplit("/", 1)[-1]
    group_id = group_uri.rstrip("/").rsplit("/", 1)[-1]
    page = client.get(
        "/localgroup-memberships/",
        params={"user": user_id, "group": group_id},
    )
    rows = page.get("objects", []) if isinstance(page, dict) else []
    return rows[0] if rows else None
