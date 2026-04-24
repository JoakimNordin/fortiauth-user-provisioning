from __future__ import annotations

import getpass
import re
import socket
from typing import Any

import click

from fauth.audit import log_event
from fauth.client import FACError
from fauth.lookup import group_by_name


_MOBILE_PATTERN = re.compile(r"^\+\d{1,3}-\d{6,}$")


@click.command("user-add")
@click.option("--username", required=True, help="Username requested by customer")
@click.option("--first-name", required=True)
@click.option("--last-name", required=True)
@click.option("--email", required=True, help="Used for password + FTM activation mail")
@click.option("--mobile", help="Format: +46-701234567 (optional for email-activated FTM)")
@click.option("--group", "groups", multiple=True, required=True, help="Group name (can repeat)")
@click.option("--customer", help="Customer code, stored in custom1")
@click.option("--ticket", help="Ticket ID, stored in custom2")
@click.option("--no-mfa", is_flag=True, help="Create as service account without FTM token")
@click.option(
    "--sms-activation",
    is_flag=True,
    help="Use SMS instead of email for FTM activation (requires --mobile)",
)
@click.pass_obj
def cmd(
    ctx,
    username: str,
    first_name: str,
    last_name: str,
    email: str,
    mobile: str | None,
    groups: tuple[str, ...],
    customer: str | None,
    ticket: str | None,
    no_mfa: bool,
    sms_activation: bool,
) -> None:
    """Create a user with MFA (default) and group membership(s)."""

    # --- Validation ---
    if mobile and not _MOBILE_PATTERN.match(mobile):
        click.echo(
            f"Error: --mobile must match format +[country]-[number], e.g. +46-701234567. "
            f"Got: {mobile}",
            err=True,
        )
        raise SystemExit(2)

    if sms_activation and not mobile:
        click.echo("Error: --sms-activation requires --mobile.", err=True)
        raise SystemExit(2)

    if sms_activation and no_mfa:
        click.echo("Error: --sms-activation and --no-mfa are mutually exclusive.", err=True)
        raise SystemExit(2)

    # --- Pre-flight: check user does not already exist ---
    page = ctx.ro.get("/localusers/", params={"username__exact": username})
    if page.get("objects"):
        click.echo(f"Error: user '{username}' already exists.", err=True)
        raise SystemExit(1)

    # --- Pre-flight: resolve all groups before any write ---
    group_uris: list[str] = []
    for g_name in groups:
        try:
            g = group_by_name(ctx.ro, g_name)
            group_uris.append(g["resource_uri"])
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

    # --- Pre-flight: token pool check if MFA ---
    token_serial: str | None = None
    if not no_mfa:
        token_serial = _select_available_token(ctx)
        if token_serial is None:
            raise SystemExit(1)

    # --- Build payload ---
    who = f"{getpass.getuser()}@{socket.gethostname()}"
    payload: dict[str, Any] = {
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "active": True,
        "custom1": customer or "",
        "custom2": ticket or "",
        "custom3": f"fauth-cli:{who}",
    }
    if mobile:
        payload["mobile_number"] = mobile

    if not no_mfa:
        payload["token_auth"] = True
        payload["token_type"] = "ftm"
        payload["token_serial"] = token_serial
        payload["ftm_act_method"] = "sms" if sms_activation else "email"

    # --- Dry-run preview ---
    if ctx.dry_run:
        click.echo("[dry-run] Would create user:")
        _print_payload(payload)
        for g_uri in group_uris:
            click.echo(f"[dry-run] POST /localgroup-memberships/ {{'user': <new>, 'group': {g_uri!r}}}")
        return

    # --- Create user ---
    try:
        created = ctx.rw.post("/localusers/", json=payload)
    except FACError as e:
        click.echo(f"Failed to create user: {e}", err=True)
        log_event(
            command="user-add",
            instance=ctx.instance_name,
            result="failed-create",
            details={"username": username, "error": str(e)},
        )
        raise SystemExit(1)

    # FAC may return dict (single) or list (bulk-style). Normalize to dict.
    created_obj: dict | None = None
    if isinstance(created, dict):
        created_obj = created
    elif isinstance(created, list) and created:
        created_obj = created[0] if isinstance(created[0], dict) else None

    # If response didn't carry enough info, fall back to GET by username
    if not created_obj or not created_obj.get("resource_uri"):
        lookup = ctx.ro.get("/localusers/", params={"username__exact": username})
        users = lookup.get("objects", []) if isinstance(lookup, dict) else []
        if not users:
            click.echo(
                "Error: POST appeared to succeed but user not found via GET. "
                "Inspect FAC manually.",
                err=True,
            )
            raise SystemExit(1)
        created_obj = users[0]

    user_uri = created_obj["resource_uri"]
    user_id = created_obj["id"]
    click.echo(f"Created user '{username}' (ID {user_id}, {user_uri}).")

    # --- Add to groups (with rollback on failure) ---
    added_membership_uris: list[str] = []
    try:
        for g_uri, g_name in zip(group_uris, groups):
            m = ctx.rw.post(
                "/localgroup-memberships/",
                json={"user": user_uri, "group": g_uri},
            )
            if isinstance(m, dict) and m.get("resource_uri"):
                added_membership_uris.append(m["resource_uri"])
            click.echo(f"  added to group '{g_name}'")
    except FACError as e:
        click.secho(
            f"Group-add failed: {e}. Rolling back (delete user + memberships).",
            fg="red",
            err=True,
        )
        _rollback(ctx, user_uri, added_membership_uris)
        log_event(
            command="user-add",
            instance=ctx.instance_name,
            result="rolled-back",
            details={"username": username, "error": str(e)},
        )
        raise SystemExit(1)

    # --- Success ---
    log_event(
        command="user-add",
        instance=ctx.instance_name,
        result="success",
        details={
            "username": username,
            "user_id": user_id,
            "groups": list(groups),
            "customer": customer,
            "ticket": ticket,
            "mfa": not no_mfa,
            "token_serial": token_serial,
        },
    )

    click.echo()
    if no_mfa:
        click.secho(f"✓ Service account '{username}' ready. FAC will mail temporary password.", fg="green")
    else:
        activation = "SMS" if sms_activation else "email"
        click.secho(
            f"✓ User '{username}' created with FTM MFA (token {token_serial}). "
            f"FAC will mail password + activation via {activation}.",
            fg="green",
        )


def _select_available_token(ctx) -> str | None:
    """Pick a token serial from the allowed pool, or None if blocked."""
    all_tokens = ctx.ro.get_all("/fortitokens/", params={"limit": 100})
    allowed = ctx.config.defaults.license_prefix_allow

    available = [
        t
        for t in all_tokens
        if t.get("status") == "available"
        and t.get("type") == "ftm"
        and not t.get("locked")
        and t.get("license")
        and any(t["license"].startswith(p) for p in allowed)
    ]

    count = len(available)
    warn = ctx.config.defaults.warn_tokens_below
    block = ctx.config.defaults.block_tokens_below

    if count <= block:
        click.secho(
            f"BLOCKED: only {count} tokens available from allowed licenses "
            f"(threshold {block}). Order more licenses before continuing.",
            fg="red",
            err=True,
        )
        return None

    if count < warn:
        click.secho(
            f"WARNING: only {count} tokens available (threshold {warn}). "
            f"Proceeding, but order more licenses soon.",
            fg="yellow",
            err=True,
        )

    chosen = available[0]
    serial = chosen.get("serial")
    if not serial:
        click.echo(f"Error: selected token has no serial number: {chosen}", err=True)
        return None
    return serial


def _rollback(ctx, user_uri: str | None, membership_uris: list[str]) -> None:
    """Best-effort rollback: delete any memberships, then the user."""
    for m_uri in membership_uris:
        try:
            ctx.rw.delete(m_uri)
        except Exception as e:  # noqa: BLE001
            click.echo(f"  (rollback: failed to delete {m_uri}: {e})", err=True)
    if user_uri:
        try:
            ctx.rw.delete(user_uri)
            click.echo(f"  (rollback: deleted {user_uri})", err=True)
        except Exception as e:  # noqa: BLE001
            click.echo(f"  (rollback: failed to delete {user_uri}: {e})", err=True)


def _print_payload(payload: dict) -> None:
    """Pretty-print a payload, masking sensitive fields."""
    for k, v in payload.items():
        click.echo(f"    {k:<16} = {v!r}")
