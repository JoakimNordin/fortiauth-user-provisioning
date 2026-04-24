from __future__ import annotations

import click

from fauth.audit import log_event


@click.command("user-disable")
@click.argument("username")
@click.pass_obj
def cmd(ctx, username: str) -> None:
    """Disable a user (active=false). Does not remove group memberships."""
    page = ctx.ro.get("/localusers/", params={"username__exact": username})
    users = page.get("objects", []) if isinstance(page, dict) else []
    if not users:
        click.echo(f"User '{username}' not found.", err=True)
        raise SystemExit(1)

    user = users[0]
    user_id = user["id"]

    if user.get("active") is False:
        click.echo(f"User '{username}' is already inactive.")
        return

    if ctx.dry_run:
        click.echo(f"[dry-run] PATCH /localusers/{user_id}/ {{'active': false}}")
        return

    ctx.rw.patch(f"/localusers/{user_id}/", json={"active": False})
    click.echo(f"User '{username}' disabled (active=false).")
    log_event(
        command="user-disable",
        instance=ctx.instance_name,
        result="success",
        details={"username": username, "user_id": user_id},
    )
