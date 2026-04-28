from __future__ import annotations

import click


@click.command("user-list")
@click.option("--group", help="Filter by group name (exact match)")
@click.option("--customer", help="Filter by custom1 (kundkod), exact match")
@click.option("--inactive", is_flag=True, help="Only show inactive users (active=false)")
@click.option(
    "--no-mfa",
    "no_mfa",
    is_flag=True,
    help="Only users without MFA (compliance check)",
)
@click.option(
    "--token-locked",
    is_flag=True,
    help="Only users whose assigned token is in the locked pool",
)
@click.pass_obj
def cmd(
    ctx,
    group: str | None,
    customer: str | None,
    inactive: bool,
    no_mfa: bool,
    token_locked: bool,
) -> None:
    """List users, optionally filtered by group, customer, or status flags."""
    if group:
        users = _users_in_group(ctx, group)
    elif customer:
        users = ctx.ro.get_all("/localusers/", params={"custom1__exact": customer, "limit": 100})
    else:
        users = ctx.ro.get_all("/localusers/", params={"limit": 100})

    if inactive:
        users = [u for u in users if u.get("active") is False]

    if no_mfa:
        users = [u for u in users if not u.get("token_auth")]

    if token_locked:
        # Build a set of locked serials, then filter users whose serial is in it.
        all_tokens = ctx.ro.get_all("/fortitokens/", params={"limit": 100})
        locked_serials = {
            t.get("serial") for t in all_tokens if t.get("locked") and t.get("serial")
        }
        users = [
            u for u in users
            if u.get("token_serial") and u.get("token_serial") in locked_serials
        ]

    if not users:
        click.echo("No users found matching filter.")
        return

    users = sorted(users, key=lambda u: u.get("username", ""))

    un_w = max(len(u.get("username", "")) for u in users)
    un_w = max(un_w, len("Username"))
    name_w = max(len(f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()) for u in users)
    name_w = max(name_w, len("Name"))

    header = f"{'Username':<{un_w}}  {'Name':<{name_w}}  {'Active':^6}  {'MFA':^4}  Email"
    click.echo(header)
    click.echo("-" * len(header))

    for u in users:
        username = u.get("username", "")
        name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
        active = "yes" if u.get("active") else "no"
        mfa = u.get("token_type") or "-" if u.get("token_auth") else "-"
        email = u.get("email", "") or "-"
        click.echo(f"{username:<{un_w}}  {name:<{name_w}}  {active:^6}  {mfa:^4}  {email}")

    click.echo(f"\nTotal: {len(users)} users")


def _users_in_group(ctx, group_name: str) -> list[dict]:
    """Fetch users in a group via /localgroup-memberships/?group_name__exact=X, then GET each user."""
    memberships = ctx.ro.get_all(
        "/localgroup-memberships/",
        params={"group_name__exact": group_name, "limit": 200},
    )
    if not memberships:
        click.echo(f"No users found in group '{group_name}' (or group does not exist).", err=True)
        return []

    user_ids = {_id_from_uri(m["user"]) for m in memberships if m.get("user")}

    # Batch fetch users by ID (filter id__in)
    if not user_ids:
        return []

    users = ctx.ro.get_all(
        "/localusers/",
        params={"id__in": ",".join(sorted(user_ids)), "limit": 200},
    )
    return users


def _id_from_uri(uri: str) -> str:
    # "/api/v1/localusers/26/" -> "26"
    return uri.rstrip("/").rsplit("/", 1)[-1]
