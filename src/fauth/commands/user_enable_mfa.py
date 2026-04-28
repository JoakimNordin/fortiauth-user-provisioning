from __future__ import annotations

import click

from fauth.audit import log_event
from fauth.client import FACError
from fauth.lookup import user_by_name
from fauth.token_pool import select_available_token


@click.command("user-enable-mfa")
@click.argument("username")
@click.option(
    "--sms-activation",
    is_flag=True,
    help="Use SMS instead of email for FTM activation (requires user to have mobile_number set)",
)
@click.pass_obj
def cmd(ctx, username: str, sms_activation: bool) -> None:
    """Enable FTM MFA on an existing user that does not have MFA yet.

    Use when a user was created without MFA (e.g. via the FortiAuthenticator
    GUI, or via 'fauth user-add --no-mfa') and now needs FTM activation.
    For users who already have MFA and need a new token (phone change),
    use 'fauth user-retoken' instead.

    Flow:
      1. Look up the user, verify MFA is not yet enabled.
      2. Select an available FTM token from the allowed-license pool.
      3. PATCH the user with token_auth=true, token_type=ftm, token_serial,
         and ftm_act_method (email or sms).
      4. FAC emails (or SMSes) the activation code.
      5. Audit log records the assigned serial.
    """
    try:
        user = user_by_name(ctx.ro, username)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if user.get("token_auth"):
        existing_serial = user.get("token_serial") or "(unknown)"
        click.echo(
            f"Error: user '{username}' already has MFA enabled "
            f"(token {existing_serial}). Use 'fauth user-retoken' to swap token.",
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

    user_id = user["id"]
    user_uri = user["resource_uri"]

    new_serial = select_available_token(ctx)
    if new_serial is None:
        raise SystemExit(1)

    new_act_method = "sms" if sms_activation else "email"
    payload = {
        "token_auth": True,
        "token_type": "ftm",
        "token_serial": new_serial,
        "ftm_act_method": new_act_method,
    }

    click.echo(f"User:        {username} (ID {user_id})")
    click.echo(f"Token:       {new_serial}  (activation: {new_act_method})")

    if ctx.dry_run:
        click.echo(f"[dry-run] PATCH {user_uri} with {payload}")
        return

    try:
        ctx.rw.patch(user_uri, json=payload)
    except FACError as e:
        click.echo(f"Failed to enable MFA: {e}", err=True)
        log_event(
            command="user-enable-mfa",
            instance=ctx.instance_name,
            result="failed",
            details={
                "username": username,
                "token_serial": new_serial,
                "error": str(e),
            },
        )
        raise SystemExit(1)

    log_event(
        command="user-enable-mfa",
        instance=ctx.instance_name,
        result="success",
        details={
            "username": username,
            "user_id": user_id,
            "token_serial": new_serial,
            "activation": new_act_method,
        },
    )

    click.secho(
        f"\nUser '{username}' MFA enabled. FAC will mail FTM activation via {new_act_method}.",
        fg="green",
    )
    click.echo("Tell the user to install FortiToken Mobile and scan the activation QR code.")
