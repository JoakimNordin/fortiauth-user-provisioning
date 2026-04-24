from __future__ import annotations

import click


# Interna fält vi inte visar i vanlig output (för läsbarhet)
_HIDDEN_FIELDS = {"password", "recovery_answer", "recovery_question"}


@click.command("user-show")
@click.argument("username")
@click.option("--raw", is_flag=True, help="Show raw JSON instead of formatted table")
@click.pass_obj
def cmd(ctx, username: str, raw: bool) -> None:
    """Show a user by username."""
    page = ctx.ro.get("/localusers/", params={"username__exact": username})
    users = page.get("objects", []) if isinstance(page, dict) else []

    if not users:
        click.echo(f"User '{username}' not found.", err=True)
        raise SystemExit(1)

    if len(users) > 1:
        click.secho(f"Warning: {len(users)} users matched - showing first", fg="yellow", err=True)

    user = users[0]

    if raw:
        import json
        click.echo(json.dumps(user, indent=2, ensure_ascii=False))
        return

    # Formatted table
    click.echo(f"Username:       {user.get('username')}")
    click.echo(f"Name:           {user.get('first_name', '')} {user.get('last_name', '')}")
    click.echo(f"Email:          {user.get('email', '')}")
    click.echo(f"Mobile:         {user.get('mobile_number', '') or '-'}")
    click.echo(f"Active:         {user.get('active')}")
    click.echo(f"ID / URI:       {user.get('id')}  ({user.get('resource_uri')})")

    if user.get("token_auth"):
        click.echo(
            f"MFA:            {user.get('token_type')} "
            f"(serial {user.get('token_serial') or '-'}, "
            f"activation: {user.get('ftm_act_method') or '-'})"
        )
    else:
        click.echo("MFA:            disabled")

    if user.get("expires_at"):
        click.echo(f"Expires:        {user.get('expires_at')}")

    # Audit-fält
    custom_values = [(k, user.get(k)) for k in ("custom1", "custom2", "custom3") if user.get(k)]
    if custom_values:
        click.echo("\nAudit / custom fields:")
        for k, v in custom_values:
            click.echo(f"  {k:<10}    {v}")

    # Grupper
    groups = user.get("user_groups") or []
    if groups:
        click.echo("\nGroups:")
        for g_uri in groups:
            click.echo(f"  {g_uri}")
