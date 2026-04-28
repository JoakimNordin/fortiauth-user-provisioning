from __future__ import annotations

import re

import click

from fauth.audit import log_event
from fauth.client import FACError
from fauth.lookup import user_by_name


_MOBILE_PATTERN = re.compile(r"^\+\d{1,3}-\d{6,}$")


@click.command("user-update")
@click.argument("username")
@click.option("--first-name", help="New first name")
@click.option("--last-name", help="New last name")
@click.option("--email", help="New email address")
@click.option("--mobile", help="New mobile number, format +46-701234567 (use empty string to clear)")
@click.option("--customer", help="New customer code (custom1)")
@click.option("--ticket", help="New ticket ID (custom2)")
@click.pass_obj
def cmd(
    ctx,
    username: str,
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    mobile: str | None,
    customer: str | None,
    ticket: str | None,
) -> None:
    """Update attributes on an existing user.

    Only the flags you pass are sent in the PATCH. To clear mobile, pass
    --mobile "" (empty string). Token, MFA state, group membership and
    active flag are managed by other commands and not touched here.
    """
    if mobile and not _MOBILE_PATTERN.match(mobile):
        click.echo(
            f"Error: --mobile must match format +[country]-[number], "
            f"e.g. +46-701234567. Got: {mobile}",
            err=True,
        )
        raise SystemExit(2)

    try:
        user = user_by_name(ctx.ro, username)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    payload: dict = {}
    if first_name is not None:
        payload["first_name"] = first_name
    if last_name is not None:
        payload["last_name"] = last_name
    if email is not None:
        payload["email"] = email
    if mobile is not None:
        payload["mobile_number"] = mobile
    if customer is not None:
        payload["custom1"] = customer
    if ticket is not None:
        payload["custom2"] = ticket

    if not payload:
        click.echo("Error: no fields to update. Pass at least one flag.", err=True)
        raise SystemExit(2)

    user_id = user["id"]
    user_uri = user["resource_uri"]

    click.echo(f"User:        {username} (ID {user_id})")
    click.echo("Changes:")
    for k, v in payload.items():
        old = user.get(k) or "(empty)"
        click.echo(f"  {k:<14} {old!r}  ->  {v!r}")

    if ctx.dry_run:
        click.echo(f"\n[dry-run] PATCH {user_uri} with {payload}")
        return

    try:
        ctx.rw.patch(user_uri, json=payload)
    except FACError as e:
        click.echo(f"Failed to update user: {e}", err=True)
        log_event(
            command="user-update",
            instance=ctx.instance_name,
            result="failed",
            details={"username": username, "fields": list(payload), "error": str(e)},
        )
        raise SystemExit(1)

    log_event(
        command="user-update",
        instance=ctx.instance_name,
        result="success",
        details={
            "username": username,
            "user_id": user_id,
            "fields": list(payload),
        },
    )

    click.secho(f"\nUser '{username}' updated.", fg="green")
