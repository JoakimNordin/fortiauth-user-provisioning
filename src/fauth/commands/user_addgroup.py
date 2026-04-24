from __future__ import annotations

import click

from fauth.audit import log_event
from fauth.lookup import group_by_name, membership_for, user_by_name


@click.command("user-addgroup")
@click.argument("username")
@click.argument("group")
@click.pass_obj
def cmd(ctx, username: str, group: str) -> None:
    """Add user to a group."""
    try:
        user = user_by_name(ctx.ro, username)
        grp = group_by_name(ctx.ro, group)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    existing = membership_for(ctx.ro, user["resource_uri"], grp["resource_uri"])
    if existing:
        click.echo(f"User '{username}' is already in group '{group}'.")
        return

    payload = {"user": user["resource_uri"], "group": grp["resource_uri"]}

    if ctx.dry_run:
        click.echo(f"[dry-run] POST /localgroup-memberships/ {payload}")
        return

    ctx.rw.post("/localgroup-memberships/", json=payload)
    click.echo(f"User '{username}' added to group '{group}'.")
    log_event(
        command="user-addgroup",
        instance=ctx.instance_name,
        result="success",
        details={"username": username, "group": group},
    )
