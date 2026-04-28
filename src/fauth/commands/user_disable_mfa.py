from __future__ import annotations

import click

from fauth.audit import log_event
from fauth.client import FACError
from fauth.lookup import user_by_name


@click.command("user-disable-mfa")
@click.argument("username")
@click.pass_obj
def cmd(ctx, username: str) -> None:
    """Disable FTM MFA on an existing user.

    Removes token_auth and frees the FortiToken back to the pool.
    Use when converting a user to a service account, or when correcting
    a wrongly-provisioned MFA setup.

    Flow:
      1. Look up the user, verify MFA is currently enabled.
      2. PATCH the user with token_auth=false and clear token_serial.
      3. Audit log records the freed serial.
    """
    try:
        user = user_by_name(ctx.ro, username)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if not user.get("token_auth"):
        click.echo(
            f"User '{username}' does not have MFA enabled - nothing to do."
        )
        return

    user_id = user["id"]
    user_uri = user["resource_uri"]
    old_serial = user.get("token_serial") or "(unknown)"

    payload = {
        "token_auth": False,
        "token_serial": "",
    }

    click.echo(f"User:        {username} (ID {user_id})")
    click.echo(f"Old token:   {old_serial}  (will be freed back to pool)")

    if ctx.dry_run:
        click.echo(f"[dry-run] PATCH {user_uri} with {payload}")
        return

    try:
        ctx.rw.patch(user_uri, json=payload)
    except FACError as e:
        click.echo(f"Failed to disable MFA: {e}", err=True)
        log_event(
            command="user-disable-mfa",
            instance=ctx.instance_name,
            result="failed",
            details={"username": username, "old_serial": old_serial, "error": str(e)},
        )
        raise SystemExit(1)

    log_event(
        command="user-disable-mfa",
        instance=ctx.instance_name,
        result="success",
        details={"username": username, "user_id": user_id, "freed_serial": old_serial},
    )

    click.secho(
        f"\nUser '{username}' MFA disabled. Token {old_serial} freed back to pool.",
        fg="green",
    )
