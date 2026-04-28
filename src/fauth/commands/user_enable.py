from __future__ import annotations

import click

from fauth.audit import log_event


@click.command("user-enable")
@click.argument("username")
@click.pass_obj
def cmd(ctx, username: str) -> None:
    """Re-enable a previously disabled user (active=true)."""
    page = ctx.ro.get("/localusers/", params={"username__exact": username})
    users = page.get("objects", []) if isinstance(page, dict) else []
    if not users:
        click.echo(f"User '{username}' not found.", err=True)
        raise SystemExit(1)

    user = users[0]
    user_id = user["id"]

    if user.get("active") is True:
        click.echo(f"User '{username}' is already active.")
        return

    if ctx.dry_run:
        click.echo(f"[dry-run] PATCH /localusers/{user_id}/ {{'active': true}}")
        return

    ctx.rw.patch(f"/localusers/{user_id}/", json={"active": True})
    click.echo(f"User '{username}' enabled (active=true).")
    log_event(
        command="user-enable",
        instance=ctx.instance_name,
        result="success",
        details={"username": username, "user_id": user_id},
    )
