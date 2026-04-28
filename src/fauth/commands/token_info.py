from __future__ import annotations

import click


@click.command("token-info")
@click.argument("serial")
@click.pass_obj
def cmd(ctx, serial: str) -> None:
    """Show token details and which user (if any) holds it.

    Reverse lookup useful when troubleshooting a FortiToken Mobile entry on
    a user's phone - you have the serial from the token but need to find the
    matching user record.
    """
    page = ctx.ro.get("/fortitokens/", params={"serial__exact": serial})
    tokens = page.get("objects", []) if isinstance(page, dict) else []
    if not tokens:
        click.echo(f"Token '{serial}' not found.", err=True)
        raise SystemExit(1)

    token = tokens[0]

    click.echo(f"Serial:         {token.get('serial')}")
    click.echo(f"Type:           {token.get('type')}")
    click.echo(f"Status:         {token.get('status')}")
    click.echo(f"Locked:         {token.get('locked')}")
    click.echo(f"License:        {token.get('license') or '-'}")
    click.echo(f"Last used:      {token.get('last_used_at') or '-'}")
    click.echo(f"URI:            {token.get('resource_uri')}")

    # Find user holding this token
    user_page = ctx.ro.get(
        "/localusers/",
        params={"token_serial__exact": serial, "limit": 5},
    )
    holders = user_page.get("objects", []) if isinstance(user_page, dict) else []
    click.echo()
    if holders:
        click.echo(f"Held by ({len(holders)} user{'s' if len(holders) > 1 else ''}):")
        for u in holders:
            un = u.get("username")
            full = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
            email = u.get("email", "") or "-"
            click.echo(f"  {un}  ({full})  {email}")
    else:
        click.echo("Held by:        (no user)")
