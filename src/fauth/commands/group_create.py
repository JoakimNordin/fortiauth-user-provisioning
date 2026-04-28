from __future__ import annotations

import click

from fauth.audit import log_event
from fauth.client import FACError


@click.command("group-create")
@click.argument("name")
@click.option(
    "--type",
    "group_type",
    default="firewall",
    show_default=True,
    type=click.Choice(["firewall", "vpn", "radius", "tacacs+"]),
    help="Group type as defined by FortiAuthenticator",
)
@click.pass_obj
def cmd(ctx, name: str, group_type: str) -> None:
    """Create a new user group.

    Creates an empty group. Use 'fauth user-addgroup <user> <group>' to add
    members afterwards. Group types map to FortiAuthenticator's internal
    group_type values - 'firewall' is the most common for user-MFA-via-FortiGate
    scenarios.
    """
    existing = ctx.ro.get(
        "/usergroups/",
        params={"name__exact": name},
    )
    if (existing.get("objects") if isinstance(existing, dict) else None):
        click.echo(f"Error: group '{name}' already exists.", err=True)
        raise SystemExit(1)

    payload = {
        "name": name,
        "group_type": group_type,
    }

    click.echo(f"Group:       {name}")
    click.echo(f"Type:        {group_type}")

    if ctx.dry_run:
        click.echo(f"[dry-run] POST /usergroups/ with {payload}")
        return

    try:
        created = ctx.rw.post("/usergroups/", json=payload)
    except FACError as e:
        click.echo(f"Failed to create group: {e}", err=True)
        log_event(
            command="group-create",
            instance=ctx.instance_name,
            result="failed",
            details={"name": name, "type": group_type, "error": str(e)},
        )
        raise SystemExit(1)

    if isinstance(created, list) and created:
        created = created[0]

    group_id = created.get("id") if isinstance(created, dict) else None
    log_event(
        command="group-create",
        instance=ctx.instance_name,
        result="success",
        details={"name": name, "type": group_type, "group_id": group_id},
    )

    click.secho(f"\nGroup '{name}' created (type={group_type}, ID {group_id}).", fg="green")
