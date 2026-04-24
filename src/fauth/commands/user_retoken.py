from __future__ import annotations

import click

from fauth.audit import log_event
from fauth.client import FACError
from fauth.lookup import user_by_name
from fauth.token_pool import select_available_token


@click.command("user-retoken")
@click.argument("username")
@click.option(
    "--sms-activation",
    is_flag=True,
    help="Use SMS instead of email for FTM activation (requires user to have mobile_number set)",
)
@click.pass_obj
def cmd(ctx, username: str, sms_activation: bool) -> None:
    """Assign a new FortiToken Mobile serial to an existing user.

    Use when a user changes phone and needs re-provisioning. FAC issues a new
    activation mail/SMS automatically when the token_serial is updated.

    Flow:
      1. Look up the user, verify they have MFA enabled.
      2. Select a new available FTM token from the allowed-license pool,
         excluding the user's current token to avoid a no-op.
      3. PATCH the user with the new token_serial.
      4. FAC emails the new activation code.
      5. Audit log records both old and new serials.
    """
    try:
        user = user_by_name(ctx.ro, username)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if not user.get("token_auth"):
        click.echo(
            f"Error: user '{username}' does not have MFA enabled. "
            f"Use 'fauth user-add' or set token_auth first.",
            err=True,
        )
        raise SystemExit(1)

    if user.get("token_type") != "ftm":
        click.echo(
            f"Error: user '{username}' uses token_type='{user.get('token_type')}', "
            f"only 'ftm' is supported by user-retoken.",
            err=True,
        )
        raise SystemExit(1)

    if sms_activation and not user.get("mobile_number"):
        click.echo(
            f"Error: --sms-activation requires the user to have mobile_number set. "
            f"'{username}' has none.",
            err=True,
        )
        raise SystemExit(2)

    old_serial = user.get("token_serial") or ""
    old_act_method = user.get("ftm_act_method") or ""
    user_id = user["id"]
    user_uri = user["resource_uri"]

    # Exclude current token from selection so we don't re-assign the same one
    exclude = {old_serial} if old_serial else set()
    new_serial = select_available_token(ctx, exclude_serials=exclude)
    if new_serial is None:
        raise SystemExit(1)

    new_act_method = "sms" if sms_activation else "email"
    payload = {
        "token_serial": new_serial,
        "ftm_act_method": new_act_method,
    }

    click.echo(f"User:        {username} (ID {user_id})")
    click.echo(f"Old token:   {old_serial or '(none)'}  (activation: {old_act_method or '-'})")
    click.echo(f"New token:   {new_serial}  (activation: {new_act_method})")

    if ctx.dry_run:
        click.echo(f"[dry-run] PATCH {user_uri} with {payload}")
        return

    try:
        ctx.rw.patch(user_uri, json=payload)
    except FACError as e:
        click.echo(f"Failed to update token: {e}", err=True)
        log_event(
            command="user-retoken",
            instance=ctx.instance_name,
            result="failed",
            details={
                "username": username,
                "old_serial": old_serial,
                "new_serial": new_serial,
                "error": str(e),
            },
        )
        raise SystemExit(1)

    log_event(
        command="user-retoken",
        instance=ctx.instance_name,
        result="success",
        details={
            "username": username,
            "user_id": user_id,
            "old_serial": old_serial,
            "new_serial": new_serial,
            "activation": new_act_method,
        },
    )

    click.secho(
        f"\nUser '{username}' re-tokened. FAC will mail new FTM activation via {new_act_method}.",
        fg="green",
    )
    click.echo("Tell the user to remove the old FortiToken entry from their app and scan the new QR code.")
