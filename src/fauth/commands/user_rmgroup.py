from __future__ import annotations

import click

from fauth.audit import log_event
from fauth.lookup import group_by_name, membership_for, user_by_name


@click.command("user-rmgroup")
@click.argument("username")
@click.argument("group")
@click.pass_obj
def cmd(ctx, username: str, group: str) -> None:
    """Remove user from a group."""
    try:
        user = user_by_name(ctx.ro, username)
        grp = group_by_name(ctx.ro, group)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    membership = membership_for(ctx.ro, user["resource_uri"], grp["resource_uri"])
    if not membership:
        click.echo(f"User '{username}' is not in group '{group}'.")
        return

    membership_uri = membership["resource_uri"]

    if ctx.dry_run:
        click.echo(f"[dry-run] DELETE {membership_uri}")
        return

    ctx.rw.delete(membership_uri)
    click.echo(f"User '{username}' removed from group '{group}'.")
    log_event(
        command="user-rmgroup",
        instance=ctx.instance_name,
        result="success",
        details={"username": username, "group": group, "membership_id": membership.get("id")},
    )
