from __future__ import annotations

import click

from fauth.audit import log_event
from fauth.client import FACError
from fauth.lookup import group_by_name


@click.command("group-delete")
@click.argument("name")
@click.option("--yes", "skip_confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_obj
def cmd(ctx, name: str, skip_confirm: bool) -> None:
    """Delete a user group.

    Members are NOT deleted - they lose this group membership but otherwise
    remain. Refuses to delete groups that still have members unless you
    pre-empty the group with user-rmgroup first.
    """
    try:
        group = group_by_name(ctx.ro, name)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    group_uri = group["resource_uri"]
    member_count = len(group.get("users") or [])

    if member_count > 0:
        click.echo(
            f"Error: group '{name}' still has {member_count} members. "
            f"Empty the group first (user-rmgroup) or remove members manually.",
            err=True,
        )
        raise SystemExit(1)

    if not skip_confirm and not ctx.dry_run:
        click.confirm(f"Really delete empty group '{name}'?", abort=True)

    if ctx.dry_run:
        click.echo(f"[dry-run] DELETE {group_uri}")
        return

    try:
        ctx.rw.delete(group_uri)
    except FACError as e:
        click.echo(f"Failed to delete group: {e}", err=True)
        log_event(
            command="group-delete",
            instance=ctx.instance_name,
            result="failed",
            details={"name": name, "error": str(e)},
        )
        raise SystemExit(1)

    log_event(
        command="group-delete",
        instance=ctx.instance_name,
        result="success",
        details={"name": name, "group_uri": group_uri},
    )

    click.secho(f"Group '{name}' deleted.", fg="green")
