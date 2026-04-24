from __future__ import annotations

import click


@click.command("groups")
@click.option("--filter", "filter_prefix", help="Only show groups whose name starts with this prefix")
@click.pass_obj
def cmd(ctx, filter_prefix: str | None) -> None:
    """List user groups with member counts and URIs."""
    groups = ctx.ro.get_all("/usergroups/", params={"limit": 100})

    if filter_prefix:
        groups = [g for g in groups if g.get("name", "").startswith(filter_prefix)]

    if not groups:
        click.echo("No groups found.")
        return

    groups = sorted(groups, key=lambda g: g.get("name", ""))

    name_w = max(len(g.get("name", "")) for g in groups)
    name_w = max(name_w, len("Name"))

    header = f"{'Name':<{name_w}}  {'Users':>5}  URI"
    click.echo(header)
    click.echo("-" * len(header))
    for g in groups:
        name = g.get("name", "")
        users = len(g.get("users") or [])
        uri = g.get("resource_uri", "")
        click.echo(f"{name:<{name_w}}  {users:>5}  {uri}")

    click.echo(f"\nTotal: {len(groups)} groups")
