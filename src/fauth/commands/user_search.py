from __future__ import annotations

import click


@click.command("user-search")
@click.option("--email", help="Search by email (substring match)")
@click.option("--customer", help="Search by customer code / custom1 (exact)")
@click.option("--ticket", help="Search by ticket ID / custom2 (exact)")
@click.option("--name", help="Search by first or last name (substring match)")
@click.pass_obj
def cmd(
    ctx,
    email: str | None,
    customer: str | None,
    ticket: str | None,
    name: str | None,
) -> None:
    """Find users by email, customer, ticket, or name.

    Useful when you have a piece of data but not the exact username.
    Multiple flags combine with AND: all conditions must match.
    """
    if not any([email, customer, ticket, name]):
        click.echo(
            "Error: pass at least one of --email, --customer, --ticket, --name.",
            err=True,
        )
        raise SystemExit(2)

    params: dict = {"limit": 200}
    if email:
        params["email__icontains"] = email
    if customer:
        params["custom1__exact"] = customer
    if ticket:
        params["custom2__exact"] = ticket

    users = ctx.ro.get_all("/localusers/", params=params)

    if name:
        n = name.lower()
        users = [
            u for u in users
            if n in (u.get("first_name") or "").lower()
            or n in (u.get("last_name") or "").lower()
        ]

    if not users:
        click.echo("No users matched.")
        return

    users = sorted(users, key=lambda u: u.get("username", ""))

    un_w = max(len(u.get("username", "")) for u in users)
    un_w = max(un_w, len("Username"))
    name_w = max(
        len(f"{u.get('first_name', '')} {u.get('last_name', '')}".strip())
        for u in users
    )
    name_w = max(name_w, len("Name"))

    header = (
        f"{'Username':<{un_w}}  {'Name':<{name_w}}  "
        f"{'Active':^6}  {'MFA':^4}  Email                       Customer / Ticket"
    )
    click.echo(header)
    click.echo("-" * len(header))

    for u in users:
        un = u.get("username", "")
        full = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
        active = "yes" if u.get("active") else "no"
        mfa = u.get("token_type") or "-" if u.get("token_auth") else "-"
        em = u.get("email", "") or "-"
        c1 = u.get("custom1", "") or ""
        c2 = u.get("custom2", "") or ""
        custom = f"{c1} / {c2}" if (c1 or c2) else "-"
        click.echo(
            f"{un:<{un_w}}  {full:<{name_w}}  {active:^6}  {mfa:^4}  "
            f"{em:<28}  {custom}"
        )

    click.echo(f"\nTotal: {len(users)} users matched")
