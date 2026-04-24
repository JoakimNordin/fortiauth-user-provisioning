from __future__ import annotations

import click

from fauth.audit import log_event


@click.command("user-delete")
@click.argument("username")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
@click.pass_obj
def cmd(ctx, username: str, yes: bool) -> None:
    """Delete a user. Memberships are removed by FAC cascading on user delete."""
    page = ctx.ro.get("/localusers/", params={"username__exact": username})
    users = page.get("objects", []) if isinstance(page, dict) else []
    if not users:
        click.echo(f"User '{username}' not found.", err=True)
        raise SystemExit(1)

    user = users[0]
    user_id = user["id"]
    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "(no name)"

    if not yes and not ctx.dry_run:
        click.echo(f"About to delete user: {username} ({name}, ID {user_id})")
        if not click.confirm("Are you sure?"):
            click.echo("Aborted.")
            return

    if ctx.dry_run:
        click.echo(f"[dry-run] DELETE /localusers/{user_id}/")
        return

    ctx.rw.delete(f"/localusers/{user_id}/")
    click.echo(f"User '{username}' deleted.")
    log_event(
        command="user-delete",
        instance=ctx.instance_name,
        result="success",
        details={"username": username, "user_id": user_id, "name": name},
    )
